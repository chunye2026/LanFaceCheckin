"""
摄像头常驻识别服务 - 后台线程持续读取摄像头、检测人脸、调用考勤引擎
"""
import cv2
import time
import threading
import datetime
import numpy as np
from config import CAMERA_INDEX, DETECTION_EVERY_N_FRAMES, ENABLE_LIVENESS
from logger import recognition_logger, app_logger

_status = {
    'running': False, 'last_frame_time': None, 'last_error': '',
    'fps': 0.0, 'detected_faces': 0, 'last_recognition_result': None,
}
_cap = None
_thread = None
_frame_count = 0
_last_recognized = {}
_flask_app = None


def init_app(app):
    """注入 Flask app 引用，避免循环导入"""
    global _flask_app
    _flask_app = app


def get_status():
    return dict(_status)


def start():
    global _cap, _thread, _status
    if _status['running']:
        return False, 'Camera already running'
    try:
        _cap = cv2.VideoCapture(CAMERA_INDEX)
        if not _cap.isOpened():
            _status['last_error'] = f'Cannot open camera index {CAMERA_INDEX}'
            return False, _status['last_error']
        _status['running'] = True
        _status['last_error'] = ''
        _thread = threading.Thread(target=_run_loop, daemon=True)
        _thread.start()
        app_logger.info(f'Camera service started (index={CAMERA_INDEX})')
        return True, 'OK'
    except Exception as e:
        _status['last_error'] = str(e)
        app_logger.exception('Camera start failed')
        return False, str(e)


def stop():
    global _cap, _thread, _status
    _status['running'] = False
    if _cap:
        _cap.release(); _cap = None
    if _thread:
        _thread.join(timeout=3); _thread = None
    _status['detected_faces'] = 0
    _status['last_recognition_result'] = None
    app_logger.info('Camera service stopped')
    return True, 'OK'


def get_frame():
    if _cap and _cap.isOpened():
        ret, frame = _cap.read()
        if ret:
            return frame
    return None


def _run_loop():
    global _frame_count, _status, _last_recognized
    from face_service import detect_faces, is_model_available
    frame_times = []

    while _status['running']:
        try:
            ret, frame = _cap.read()
            if not ret:
                _status['last_error'] = 'Failed to read camera frame'
                time.sleep(0.5)
                continue

            now = time.time()
            frame_times.append(now)
            if len(frame_times) > 30:
                frame_times.pop(0)
            if len(frame_times) >= 2:
                _status['fps'] = round(len(frame_times) / (frame_times[-1] - frame_times[0]), 1)
            _status['last_frame_time'] = datetime.datetime.now()
            _frame_count += 1

            if _frame_count % DETECTION_EVERY_N_FRAMES != 0:
                continue
            if not is_model_available():
                continue

            faces = detect_faces(frame)
            _status['detected_faces'] = len(faces)
            if len(faces) == 0:
                continue

            best_face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
            embedding = best_face.normed_embedding
            bbox = [int(v) for v in best_face.bbox]

            liveness_passed = None
            liveness_score = 0.0
            liveness_reason = ''
            if ENABLE_LIVENESS:
                liveness_passed, liveness_score, liveness_reason = _basic_liveness(embedding, bbox)

            if _flask_app:
                with _flask_app.app_context():
                    _do_recognition(embedding, bbox, liveness_passed, liveness_score, liveness_reason)

        except Exception as e:
            _status['last_error'] = str(e)
            recognition_logger.exception('Camera loop error')
            time.sleep(1)

    _status['running'] = False


def _do_recognition(embedding, bbox, liveness_passed, liveness_score, liveness_reason):
    from models import db, Member, FaceEmbedding, RecognitionEvent, CameraDevice
    from face_service import match_member
    from config import FACE_MATCH_THRESHOLD, MIN_FACE_SAMPLES, COOLDOWN_SECONDS
    import datetime as dt

    result = {'matched': False, 'member_id': None, 'member_name': '', 'confidence': 0.0, 'distance': 0.0, 'bbox': bbox}

    members = Member.query.filter_by(active=True).all()
    eligible = [m for m in members if m.can_participate]
    if not eligible:
        _status['last_recognition_result'] = result
        return

    all_embeddings = []
    for m in eligible:
        for emb in m.face_embeddings.all():
            if emb.embedding_json:
                all_embeddings.append((m.id, m.name, emb.embedding_json))
    if not all_embeddings:
        _status['last_recognition_result'] = result
        return

    match_result = match_member(embedding, all_embeddings, FACE_MATCH_THRESHOLD)
    match_result['bbox'] = bbox

    event = RecognitionEvent(
        camera_id=CAMERA_INDEX, matched=match_result['matched'],
        member_id=match_result['member_id'], member_name=match_result['member_name'],
        confidence=match_result['confidence'], distance=match_result['distance'],
        bbox=str(bbox), liveness_passed=liveness_passed,
        liveness_score=liveness_score, liveness_reason=liveness_reason,
    )

    if not match_result['matched']:
        event.failure_reason = 'confidence_too_low'
        db.session.add(event); db.session.commit()
        _status['last_recognition_result'] = match_result; return

    if ENABLE_LIVENESS and not liveness_passed:
        event.failure_reason = 'liveness_failed'
        db.session.add(event); db.session.commit()
        _status['last_recognition_result'] = match_result; return

    mid = match_result['member_id']
    now = dt.datetime.now()
    if mid in _last_recognized:
        if (now - _last_recognized[mid]).total_seconds() < COOLDOWN_SECONDS:
            event.failure_reason = 'cooldown_not_reached'
            db.session.add(event); db.session.commit()
            _status['last_recognition_result'] = match_result; return

    _last_recognized[mid] = now

    from attendance_service import process_recognition
    checkin_created, reason = process_recognition(event)
    event.checkin_created = checkin_created
    if not checkin_created:
        event.failure_reason = reason

    db.session.add(event); db.session.commit()
    _status['last_recognition_result'] = match_result

    cam = CameraDevice.query.first()
    if cam:
        cam.last_frame_time = now; cam.fps = _status.get('fps', 0.0)
        cam.last_error = _status.get('last_error', '')
        db.session.merge(cam); db.session.commit()


_last_liveness_data = {'embedding': None, 'positions': [], 'blink_frames': []}


def _basic_liveness(embedding, bbox):
    global _last_liveness_data
    try:
        cx, cy = (bbox[0] + bbox[2]) // 2, (bbox[1] + bbox[3]) // 2
        if _last_liveness_data['embedding'] is None:
            _last_liveness_data = {'embedding': embedding, 'positions': [(cx, cy)], 'blink_frames': []}
            return None, 0.0, 'initial_frame'
        prev_emb = _last_liveness_data['embedding']
        if float(np.dot(embedding, prev_emb)) < 0.7:
            _last_liveness_data = {'embedding': embedding, 'positions': [(cx, cy)], 'blink_frames': []}
            return None, 0.0, 'face_changed'
        _last_liveness_data['embedding'] = embedding
        _last_liveness_data['positions'].append((cx, cy))
        if len(_last_liveness_data['positions']) > 10:
            _last_liveness_data['positions'].pop(0)
        if len(_last_liveness_data['positions']) >= 5:
            pos = _last_liveness_data['positions']
            dx, dy = abs(pos[-1][0] - pos[0][0]), abs(pos[-1][1] - pos[0][1])
            if dx > 10 or dy > 10:
                return True, min(1.0, (dx + dy) / 100), 'movement_detected'
        return None, 0.0, 'insufficient_motion'
    except Exception:
        return None, 0.0, 'liveness_error'
