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
    return None

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
    global _latest_raw_frame, _latest_annotated_frame
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

            # RGBA→BGR
            if len(frame.shape) == 3 and frame.shape[2] == 4:
                frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)

            _status['last_frame_time'] = datetime.datetime.now()
            _frame_count += 1

            # 保存原始帧
            with _frame_lock:
                _latest_raw_frame = frame.copy()

            should_detect = (_frame_count % DETECTION_EVERY_N_FRAMES == 0 and is_model_available())

            if should_detect:
                faces = detect_faces(frame)
                _status['detected_faces'] = len(faces)

                detections = []
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

                _status['current_detections'] = detections
                _status['last_recognition_result'] = detections[-1] if detections else None

            # 每一帧都绘制当前 detections
            current_dets = _status.get('current_detections', [])
            if DASHBOARD_DRAW_FACE_BOX:
                annotated = _draw_detections(frame.copy(), current_dets)
            else:
                annotated = frame.copy()

            with _frame_lock:
                _latest_annotated_frame = annotated.copy()

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
def _get_chinese_font(size=20):
    """加载支持中文的字体，找不到时写日志而非静默回退"""
    from PIL import ImageFont
    import os

    base_dir = os.path.abspath(os.path.dirname(__file__))

    font_paths = [
        os.path.join(base_dir, "assets", "fonts", "NotoSansCJK-Regular.otf"),
        os.path.join(base_dir, "assets", "fonts", "NotoSansCJK-Regular.ttc"),
        os.path.join(base_dir, "assets", "fonts", "SourceHanSansCN-Regular.otf"),
        os.path.join(base_dir, "assets", "fonts", "simhei.ttf"),
        os.path.join(base_dir, "assets", "fonts", "msyh.ttc"),
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\msyhbd.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\simsun.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.otf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.otf",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/arphic/ukai.ttc",
        "/usr/share/fonts/truetype/arphic/uming.ttc",
    ]

    for path in font_paths:
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, size)
                try:
                    recognition_logger.info(f"Chinese font loaded: {path}")
                except Exception:
                    pass
                return font
            except Exception as e:
                try:
                    recognition_logger.warning(f"Failed to load Chinese font {path}: {e}")
                except Exception:
                    pass

    try:
        recognition_logger.warning(
            "No Chinese font found. Fallback to PIL default font. Chinese text may display as question marks."
        )
    except Exception:
        pass

    return ImageFont.load_default()


def _draw_detections(frame, detections):
    """PIL中文绘制: 已录入/陌生人 人脸框+信息卡"""
    if frame is None or not detections:
        return frame
    try:
        import numpy as np
        from PIL import Image, ImageDraw

        if len(frame.shape) == 3 and frame.shape[2] == 4:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)
        draw = ImageDraw.Draw(image, "RGBA")
        font = _get_chinese_font(20)

        detections_sorted = sorted(detections, key=lambda d: (d.get('matched', False), d.get('checkin_created', False)))
        drawn = 0

        for det in detections_sorted:
            bbox = det.get('bbox') or []
            if len(bbox) != 4: continue
            x1, y1, x2, y2 = [max(0, min(int(v), (w-1) if i%2==0 else (h-1))) for i, v in enumerate(bbox)]
            if x2 <= x1 or y2 <= y1: continue

            matched = bool(det.get('matched', False))
            checkin = bool(det.get('checkin_created', False))

            if not matched:
                box_color = (255, 60, 60, 255)      # 红
            elif checkin:
                box_color = (60, 220, 80, 255)      # 绿
            else:
                box_color = (255, 210, 0, 255)      # 黄

            # 画框
            lw = 4
            for off in range(lw):
                draw.rectangle([x1-off, y1-off, x2+off, y2+off], outline=box_color)

            if matched:
                name = det.get("member_name", "")
                eid = det.get("employee_id", "")
                dept = det.get("department", "")

                lines = []
                if name:
                    lines.append(f"姓名：{name}")
                if eid:
                    lines.append(f"学号：{eid}")
                if dept:
                    lines.append(f"班级：{dept}")
            else:
                lines = ["陌生人"]

            if not lines: continue

            # 信息卡尺寸
            px, py, lh = 10, 8, 28
            text_widths = []
            for line in lines:
                try:
                    box = draw.textbbox((0, 0), line, font=font)
                    text_widths.append(box[2] - box[0])
                except Exception:
                    text_widths.append(len(line) * 22)
            tw = max(text_widths) if text_widths else 120
            cw = max(160, min(tw + px * 2 + 8, 360))
            ch = py*2 + lh * len(lines)
            cx, cy = x1, y1 - ch - 8
            if cy < 0: cy = y2 + 8
            if cy + ch > h: cy = max(0, h - ch - 2)
            if cx + cw > w: cx = max(0, w - cw - 2)

            draw.rectangle([cx, cy, cx+cw, cy+ch], fill=(0,0,0,170))
            draw.rectangle([cx, cy, cx+5, cy+ch], fill=box_color)

            text_color = (255, 230, 80, 255) if matched else (255, 80, 80, 255)
            ty = cy + py
            for line in lines:
                draw.text((cx + px, ty), line, font=font, fill=text_color)
                ty += lh
            drawn += 1

        result = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        recognition_logger.info(f'_draw_detections: input={len(detections)} drawn={drawn}')
        return result
    except Exception:
        recognition_logger.exception('_draw_detections PIL failed')
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
