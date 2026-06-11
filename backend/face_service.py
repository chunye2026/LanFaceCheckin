"""
人脸识别服务 - InsightFace (ArcFace) 多向量比对
"""
import cv2
import numpy as np
import json
import os
import base64
from config import FACE_MATCH_THRESHOLD, BASE_DIR
from logger import recognition_logger

# InsightFace 模型路径
MODEL_ROOT = os.path.join(BASE_DIR, 'models', 'insightface')
MODEL_DIR = os.path.join(MODEL_ROOT, 'models', 'buffalo_s')

_handler = None
_checked = None


def is_model_available():
    global _checked
    if _checked is None:
        _checked = os.path.isdir(MODEL_DIR) and any(f.endswith('.onnx') for f in os.listdir(MODEL_DIR) if os.path.isfile(os.path.join(MODEL_DIR, f)))
    return _checked


def _get_handler():
    global _handler
    if _handler is None and is_model_available():
        import insightface
        _handler = insightface.app.FaceAnalysis(name='buffalo_s', root=MODEL_ROOT, providers=['CPUExecutionProvider'])
        _handler.prepare(ctx_id=-1, det_size=(640, 640))
        recognition_logger.info('InsightFace model loaded')
    return _handler


def detect_faces(img_bgr):
    """检测图片中所有人脸，返回 face 对象列表"""
    handler = _get_handler()
    if handler is None:
        return []
    return handler.get(img_bgr)


def extract_embedding(img_bgr):
    """从图片提取单个人脸 embedding"""
    faces = detect_faces(img_bgr)
    if len(faces) == 0:
        return None, '未检测到人脸'
    if len(faces) > 1:
        return None, f'检测到{len(faces)}张人脸'
    return faces[0].normed_embedding, 'OK'


def embedding_to_json(emb):
    if emb is None:
        return ''
    return json.dumps(emb.tolist())


def json_to_embedding(json_str):
    if not json_str:
        return None
    arr = np.array(json.loads(json_str), dtype=np.float32)
    norm = np.linalg.norm(arr)
    return arr / norm if norm > 0 else arr


def match_member(candidate_embedding, known_embeddings, threshold=None):
    """
    将候选 embedding 与多组已知 embedding 比对。
    known_embeddings: [(member_id, member_name, embedding_json), ...]
    返回最佳匹配
    """
    if threshold is None:
        threshold = FACE_MATCH_THRESHOLD

    if candidate_embedding is None:
        return None

    best = {'matched': False, 'member_id': None, 'member_name': '', 'confidence': 0.0, 'distance': 0.0}

    for mid, mname, emb_json in known_embeddings:
        known_emb = json_to_embedding(emb_json)
        if known_emb is None:
            continue
        sim = float(np.dot(candidate_embedding, known_emb))
        dist = 1.0 - sim
        if sim > best['confidence']:
            best['confidence'] = round(sim, 6)
            best['distance'] = round(dist, 6)
            best['member_id'] = mid
            best['member_name'] = mname

    if best['confidence'] >= threshold:
        best['matched'] = True

    return best


def verify_face_image(file_storage):
    """校验上传人脸图片：检测到且只检测到一张人脸"""
    import cv2, numpy as np
    try:
        file_bytes = np.frombuffer(file_storage.read(), np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        file_storage.seek(0)
        if img is None:
            return False, '无法解析图片'

        # InsightFace 检测
        handler = _get_handler()
        if handler is not None:
            faces = handler.get(img)
            if len(faces) == 0:
                return False, '未检测到人脸'
            if len(faces) > 1:
                return False, f'检测到{len(faces)}张人脸，请上传单人照片'
            return True, 'OK'

        # OpenCV 降级检测
        cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        opencv_faces = cascade.detectMultiScale(gray, 1.1, 5, minSize=(80, 80))
        if len(opencv_faces) == 0:
            return False, '未检测到人脸'
        if len(opencv_faces) > 1:
            return False, f'检测到{len(opencv_faces)}张人脸，请上传单人照片'
        return True, 'OK'
    except Exception as e:
        recognition_logger.exception('verify_face_image error')
        return False, str(e)
