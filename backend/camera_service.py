"""
摄像头常驻识别服务 - 多脸识别 + 帧绘制 + 缓存
"""
import cv2
import time
import threading
import datetime
import numpy as np
from config import CAMERA_INDEX, DETECTION_EVERY_N_FRAMES, ENABLE_LIVENESS, DASHBOARD_DRAW_FACE_BOX
from logger import recognition_logger, app_logger

_status = {
    'running': False, 'last_frame_time': None, 'last_error': '',
    'fps': 0.0, 'detected_faces': 0, 'last_recognition_result': None,
    'current_detections': [],
}
_cap = None
_thread = None
_frame_count = 0
_last_recognized = {}
_flask_app = None
_embedding_cache = None

# 帧缓存
_latest_raw_frame = None
_latest_annotated_frame = None
_frame_lock = threading.Lock()


def init_app(app):
    global _flask_app; _flask_app = app

def invalidate_embedding_cache():
    global _embedding_cache; _embedding_cache = None

def _load_embeddings():
    global _embedding_cache
    from models import Member
    members = Member.query.filter_by(active=True).all()
    all_emb = []
    for m in members:
        if m.can_participate:
            for emb in m.face_embeddings.all():
                if emb.embedding_json:
                    all_emb.append((m.id, m.name, emb.embedding_json))
    _embedding_cache = all_emb
    return all_emb

def get_status():
    return dict(_status)

def get_stream_frame(annotated=True):
    with _frame_lock:
        if annotated and _latest_annotated_frame is not None:
            return _latest_annotated_frame.copy()
        if _latest_raw_frame is not None:
            return _latest_raw_frame.copy()
    return get_frame()

def start():
    global _cap, _thread, _status
    if _status['running']: return False, 'Camera already running'
    try:
        _cap = cv2.VideoCapture(CAMERA_INDEX)
        if not _cap.isOpened():
            _status['last_error'] = f'Cannot open camera index {CAMERA_INDEX}'
            return False, _status['last_error']
        _status.update({'running': True, 'last_error': '', 'current_detections': []})
        _thread = threading.Thread(target=_run_loop, daemon=True)
        _thread.start()
        app_logger.info(f'Camera started (index={CAMERA_INDEX})')
        return True, 'OK'
    except Exception as e:
        _status['last_error'] = str(e)
        return False, str(e)

def stop():
    global _cap, _thread, _status, _latest_raw_frame, _latest_annotated_frame
    _status['running'] = False
    if _cap: _cap.release(); _cap = None
    if _thread: _thread.join(timeout=3); _thread = None
    with _frame_lock:
        _latest_raw_frame = None
        _latest_annotated_frame = None
    _status.update({'detected_faces': 0, 'current_detections': [], 'last_recognition_result': None})
    app_logger.info('Camera stopped')
    return True, 'OK'

def get_frame():
    if _cap and _cap.isOpened():
        ret, frame = _cap.read()
        if ret: return frame
    return None


# ========== 主循环 ==========
def _run_loop():
    global _frame_count, _status, _last_recognized
    from face_service import detect_faces, is_model_available
    frame_times = []

    while _status['running']:
        try:
            ret, frame = _cap.read()
            if not ret:
                _status['last_error'] = 'Failed to read camera frame'
                time.sleep(0.5); continue

            now = time.time()
            frame_times.append(now)
            if len(frame_times) > 30: frame_times.pop(0)
            if len(frame_times) >= 2:
                _status['fps'] = round(len(frame_times) / (frame_times[-1] - frame_times[0]), 1)

            # RGBA→BGR(部分摄像头返回RGBA)
            if len(frame.shape) == 3 and frame.shape[2] == 4:
                frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)

            # 保存原始帧
            with _frame_lock:
                _latest_raw_frame = frame.copy()

            _status['last_frame_time'] = datetime.datetime.now()
            _frame_count += 1

            detections = []
            if _frame_count % DETECTION_EVERY_N_FRAMES == 0 and is_model_available():
                faces = detect_faces(frame)
                _status['detected_faces'] = len(faces)

                if _flask_app:
                    with _flask_app.app_context():
                        for face in faces:
                            bbox = [int(v) for v in face.bbox]
                            emb = face.normed_embedding
                            lp = lsc = None; lr = ''
                            if ENABLE_LIVENESS:
                                lp, lsc, lr = _basic_liveness(emb, bbox)
                            det = _do_recognition(emb, bbox, lp, lsc, lr)
                            detections.append(det)

                if detections:
                    _status['last_recognition_result'] = detections[-1]
                    _status['current_detections'] = detections
                elif not _status['current_detections']:
                    # 没有检测到人脸时才清空
                    _status['last_recognition_result'] = None
                    _status['current_detections'] = []

                # 绘制标注帧
                if DASHBOARD_DRAW_FACE_BOX:
                    annotated = _draw_detections(frame.copy(), _status['current_detections'])
                    with _frame_lock:
                        _latest_annotated_frame = annotated.copy()
            else:
                # 非检测帧：保持上次的识别结果，只更新原始帧
                with _frame_lock:
                    _latest_raw_frame = frame.copy()

        except Exception as e:
            _status['last_error'] = str(e)
            recognition_logger.exception('Camera loop error')
            time.sleep(1)

    _status['running'] = False


# ========== 识别 ==========
def _do_recognition(embedding, bbox, liveness_passed, liveness_score, liveness_reason):
    from models import db, Member, RecognitionEvent
    from face_service import match_member
    from config import FACE_MATCH_THRESHOLD, COOLDOWN_SECONDS
    from attendance_stats_service import mask_phone, mask_email
    import datetime as dt

    base = {'matched': False, 'member_id': None, 'member_name': '', 'confidence': 0.0,
            'distance': 0.0, 'bbox': bbox, 'checkin_created': False, 'failure_reason': '',
            'liveness_passed': liveness_passed, 'employee_id': '', 'department': '',
            'phone': '', 'email': ''}

    global _embedding_cache
    if _embedding_cache is None:
        _embedding_cache = _load_embeddings()

    if not _embedding_cache:
        base['failure_reason'] = 'no_member'
        return base

    match_result = match_member(embedding, _embedding_cache, FACE_MATCH_THRESHOLD)
    base['confidence'] = match_result['confidence']
    base['distance'] = match_result['distance']

    if not match_result['matched']:
        # 未匹配: 保留 bbox, 设 matched=False, 置信度用实际值
        base['failure_reason'] = 'confidence_too_low'
        base['matched'] = False
        base['member_name'] = ''
        try:
            event = RecognitionEvent(camera_id=CAMERA_INDEX, matched=False, confidence=base['confidence'],
                                     bbox=str(bbox), failure_reason=base['failure_reason'])
            db.session.add(event); db.session.commit()
        except Exception: db.session.rollback()
        return base

    base['matched'] = True
    base['member_id'] = match_result['member_id']
    base['member_name'] = match_result['member_name']

    if ENABLE_LIVENESS and not liveness_passed:
        base['failure_reason'] = 'liveness_failed'
        try:
            event = RecognitionEvent(camera_id=CAMERA_INDEX, matched=True, confidence=base['confidence'],
                                     bbox=str(bbox), failure_reason=base['failure_reason'],
                                     member_id=base['member_id'], member_name=base['member_name'])
            db.session.add(event); db.session.commit()
        except Exception: db.session.rollback()
        return base

    # 读取成员信息
    member = Member.query.get(base['member_id'])
    if member:
        base['employee_id'] = member.employee_id
        base['department'] = member.department or ''
        base['phone'] = mask_phone(member.phone)
        base['email'] = mask_email(member.email)

    # 冷却检查
    mid = base['member_id']
    now = dt.datetime.now()
    if mid in _last_recognized:
        elapsed = (now - _last_recognized[mid]).total_seconds()
        if elapsed < COOLDOWN_SECONDS:
            base['failure_reason'] = 'cooldown_not_reached'
            try:
                event = RecognitionEvent(camera_id=CAMERA_INDEX, matched=True, confidence=base['confidence'],
                                         bbox=str(bbox), failure_reason=base['failure_reason'],
                                         member_id=mid, member_name=base['member_name'])
                db.session.add(event); db.session.commit()
            except Exception: db.session.rollback()
            return base

    _last_recognized[mid] = now

    # 创建识别事件并考勤
    try:
        event = RecognitionEvent(camera_id=CAMERA_INDEX, matched=True,
                                 member_id=mid, member_name=base['member_name'],
                                 confidence=base['confidence'], distance=base['distance'],
                                 bbox=str(bbox))
        db.session.add(event)
        db.session.flush()

        from attendance_service import process_recognition
        checkin_created, reason = process_recognition(event)
        event.checkin_created = checkin_created
        base['checkin_created'] = checkin_created
        if not checkin_created:
            event.failure_reason = reason
            base['failure_reason'] = reason
        db.session.commit()
    except Exception as e:
        recognition_logger.exception('Recognition commit error')
        db.session.rollback()
        base['failure_reason'] = 'checkin_failed'
        base['checkin_created'] = False

    return base


# ========== 绘制 ==========
def _draw_detections(frame, detections):
    """在视频帧上绘制人脸框和人员信息(OpenCV)"""
    if frame is None or not detections:
        return frame
    try:
        # RGBA→BGR 转换(部分摄像头返回RGBA)
        if len(frame.shape) == 3 and frame.shape[2] == 4:
            frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)

        h, w = frame.shape[:2]
        # 排序：未匹配(红)先画，已匹配(绿/黄)后画，避免被覆盖
        detections_sorted = sorted(detections, key=lambda d: (d.get('matched', False), d.get('checkin_created', False)))
        drawn = 0
        for det in detections_sorted:
            bbox = det.get('bbox') or []
            if len(bbox) != 4:
                recognition_logger.warning(f'Skipped detection: invalid bbox={bbox}')
                continue
            x1, y1, x2, y2 = [max(0, min(int(v), (w-1) if i%2==0 else (h-1))) for i, v in enumerate(bbox)]
            if x2 <= x1 or y2 <= y1:
                recognition_logger.warning(f'Skipped detection: zero-size bbox=[{x1},{y1},{x2},{y2}]')
                continue

            matched = det.get('matched', False)
            checkin = det.get('checkin_created', False)

            if not matched:
                color = (0, 0, 255)        # 红
                status = '未匹配'
            elif checkin:
                color = (0, 255, 0)        # 绿
                status = '已打卡'
            else:
                color = (0, 215, 255)      # 黄
                reason = det.get('failure_reason', '')
                status_map = {'cooldown_not_reached': '冷却中', 'liveness_failed': '活体失败',
                              'checkin_failed': '打卡失败', 'confidence_too_low': '低置信'}
                status = status_map.get(reason, '已识别')

            recognition_logger.debug(f'Draw bbox={[x1,y1,x2,y2]} name={det.get("member_name","?")} matched={matched} color={color}')

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)

            name = det.get('member_name', '')
            eid = det.get('employee_id', '')
            conf = det.get('confidence', 0)
            lines = [f'{name}({eid})' if (name and eid) else (name or '陌生人'),
                     f'置信:{conf*100:.1f}%', status]

            bw, lh = 240, 22
            bh = len(lines) * lh + 10
            bx, by = x1, max(0, y1 - bh - 6)
            if by + bh > h: by = min(h - bh - 1, y2 + 6)
            overlay = frame.copy()
            cv2.rectangle(overlay, (bx, by), (min(bx+bw, w-1), min(by+bh, h-1)), (0, 0, 0), -1)
            frame = cv2.addWeighted(overlay, 0.55, frame, 0.45, 0)

            ty = by + 18
            for line in lines:
                cv2.putText(frame, line, (bx+6, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
                ty += lh
            drawn += 1

        recognition_logger.info(f'_draw_detections: input_dets={len(detections)} drawn={drawn} total')
        return frame
    except Exception:
        recognition_logger.exception('draw detections failed')
        return frame


# ========== 活体检测 ==========
_last_liveness_data = {'embedding': None, 'positions': [], 'blink_frames': []}

def _basic_liveness(embedding, bbox):
    global _last_liveness_data
    try:
        cx, cy = (bbox[0] + bbox[2]) // 2, (bbox[1] + bbox[3]) // 2
        if _last_liveness_data['embedding'] is None:
            _last_liveness_data = {'embedding': embedding, 'positions': [(cx, cy)], 'blink_frames': []}
            return None, 0.0, 'initial_frame'
        if float(np.dot(embedding, _last_liveness_data['embedding'])) < 0.7:
            _last_liveness_data = {'embedding': embedding, 'positions': [(cx, cy)], 'blink_frames': []}
            return None, 0.0, 'face_changed'
        _last_liveness_data['embedding'] = embedding
        _last_liveness_data['positions'].append((cx, cy))
        if len(_last_liveness_data['positions']) > 10: _last_liveness_data['positions'].pop(0)
        if len(_last_liveness_data['positions']) >= 5:
            pos = _last_liveness_data['positions']
            dx, dy = abs(pos[-1][0] - pos[0][0]), abs(pos[-1][1] - pos[0][1])
            if dx > 10 or dy > 10:
                return True, min(1.0, (dx + dy) / 100), 'movement_detected'
        return None, 0.0, 'insufficient_motion'
    except Exception:
        return None, 0.0, 'liveness_error'
