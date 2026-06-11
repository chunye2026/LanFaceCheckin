"""
人脸识别服务模块
支持双引擎:
- InsightFace (RetinaFace + ArcFace) — 高精度，需下载模型 (~140MB)
- OpenCV (Haar Cascade + LBPH) — 降级方案，无需额外下载

优先级: InsightFace 可用则用，否则自动回退 OpenCV
"""
import cv2
import numpy as np
import json
import os
import base64
from config import FACE_TOLERANCE, BASE_DIR

# ============================================================
# InsightFace 引擎
# ============================================================

INSIGHTFACE_ROOT = os.path.join(BASE_DIR, 'models', 'insightface')
INSIGHTFACE_MODEL = os.path.join(INSIGHTFACE_ROOT, 'models', 'buffalo_s')

_insightface_handler = None
_insightface_checked = False
_insightface_available = False


def _check_insightface():
    global _insightface_checked, _insightface_available
    if not _insightface_checked:
        # 检查 buffalo_s 目录是否有 .onnx 模型文件
        if os.path.isdir(INSIGHTFACE_MODEL):
            onnx_files = [f for f in os.listdir(INSIGHTFACE_MODEL) if f.endswith('.onnx')]
            _insightface_available = len(onnx_files) > 0
        else:
            _insightface_available = False
        _insightface_checked = True
    return _insightface_available


def _get_insightface():
    global _insightface_handler
    if _insightface_handler is None and _check_insightface():
        import insightface
        _insightface_handler = insightface.app.FaceAnalysis(
            name='buffalo_s', root=INSIGHTFACE_ROOT, providers=['CPUExecutionProvider']
        )
        _insightface_handler.prepare(ctx_id=-1, det_size=(640, 640))
        print(f'[FaceService] InsightFace loaded (buffalo_s)')
    return _insightface_handler


def _insightface_encode(img):
    handler = _get_insightface()
    faces = handler.get(img)
    if len(faces) == 0:
        return None, '未检测到人脸'
    if len(faces) > 1:
        return None, f'检测到{len(faces)}张人脸'
    return faces[0].normed_embedding, 'OK'


def _insightface_similarity(emb1, emb2):
    return round(float(np.dot(emb1, emb2)), 6)


# ============================================================
# OpenCV 降级引擎
# ============================================================

_opencv_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)


def _opencv_get_face(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = _opencv_cascade.detectMultiScale(gray, 1.1, 5, minSize=(80, 80))
    if len(faces) == 0:
        return None
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    roi = gray[y:y+h, x:x+w]
    return cv2.resize(roi, (150, 150))


def _opencv_encode(img):
    roi = _opencv_get_face(img)
    if roi is None:
        return None, '未检测到人脸'
    roi = cv2.equalizeHist(roi)
    _, buf = cv2.imencode('.jpg', roi)
    return base64.b64encode(buf).decode('utf-8'), 'OK'


def _opencv_similarity(data1, data2):
    b1 = base64.b64decode(data1)
    f1 = cv2.imdecode(np.frombuffer(b1, np.uint8), cv2.IMREAD_GRAYSCALE)
    b2 = base64.b64decode(data2)
    f2 = cv2.imdecode(np.frombuffer(b2, np.uint8), cv2.IMREAD_GRAYSCALE)
    f1 = cv2.resize(f1, (150, 150))
    f2 = cv2.resize(f2, (150, 150))

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train([f1], np.array([0]))
    _, conf = recognizer.predict(f2)
    return round(max(0.0, min(1.0, 1.0 - conf / 100.0)), 4)


# ============================================================
# 统一接口
# ============================================================

def engine_name():
    return 'InsightFace' if _check_insightface() else 'OpenCV'


def detect_and_encode_face(image_path):
    """检测人脸并提取特征。返回 (success, data, message)"""
    try:
        if not os.path.exists(image_path):
            return False, None, '图片文件不存在'
        img = cv2.imread(image_path)
        if img is None:
            return False, None, '无法读取图片'

        if _check_insightface():
            data, msg = _insightface_encode(img)
            if data is not None:
                return True, data, f'特征提取成功 (InsightFace ArcFace 512-D)'
            return False, None, msg
        else:
            data, msg = _opencv_encode(img)
            if data is not None:
                return True, data, f'特征提取成功 (OpenCV LBPH)'
            return False, None, msg
    except Exception as e:
        return False, None, f'检测失败: {str(e)}'


def encoding_to_json(data):
    if data is None:
        return ''
    if isinstance(data, np.ndarray):
        return json.dumps(data.tolist())
    return str(data)


def json_to_encoding(json_str):
    if not json_str:
        return None
    try:
        arr = np.array(json.loads(json_str), dtype=np.float32)
        norm = np.linalg.norm(arr)
        return arr / norm if norm > 0 else arr
    except (json.JSONDecodeError, ValueError):
        return json_str


def compare_faces(known_encoding_json, face_image_path):
    """1:1 比对"""
    try:
        known = json_to_encoding(known_encoding_json)
        if known is None:
            return False, False, 0.0, '已知人脸数据为空'

        success, unknown, msg = detect_and_encode_face(face_image_path)
        if not success:
            return False, False, 0.0, msg

        if isinstance(known, np.ndarray) and isinstance(unknown, np.ndarray):
            sim = _insightface_similarity(known, unknown)
        else:
            sim = _opencv_similarity(str(known), str(unknown))

        match = sim >= FACE_TOLERANCE
        return True, match, sim, '比对成功' if match else f'不匹配 (相似度:{sim:.4f})'
    except Exception as e:
        return False, False, 0.0, f'比对失败: {str(e)}'


def find_matching_member(known_encodings, face_image_path):
    """1:N 匹配。known_encodings: [(member_id, encoding_json), ...]"""
    try:
        img = cv2.imread(face_image_path)
        if img is None:
            return None, 0.0, '无法读取图片'

        if _check_insightface():
            handler = _get_insightface()
            faces = handler.get(img)
            if len(faces) == 0:
                return None, 0.0, '未检测到人脸'
            unknown = faces[0].normed_embedding
        else:
            roi = _opencv_get_face(img)
            if roi is None:
                return None, 0.0, '未检测到人脸'
            roi = cv2.equalizeHist(roi)
            _, buf = cv2.imencode('.jpg', roi)
            unknown = base64.b64encode(buf).decode('utf-8')

        best_id, best_sim = None, 0.0

        for mid, enc_json in known_encodings:
            if not enc_json:
                continue
            known = json_to_encoding(enc_json)
            if known is None:
                continue

            if isinstance(known, np.ndarray) and isinstance(unknown, np.ndarray):
                sim = _insightface_similarity(known, unknown)
            else:
                sim = _opencv_similarity(str(known), str(unknown))

            if sim >= FACE_TOLERANCE and sim > best_sim:
                best_sim, best_id = sim, mid

        eng = engine_name()
        if best_id:
            return best_id, best_sim, f'匹配成功 ({eng}, 相似度:{best_sim:.4f})'
        return None, best_sim, f'未匹配 ({eng}, 最高:{best_sim:.4f}, 阈值:{FACE_TOLERANCE})'
    except Exception as e:
        return None, 0.0, f'匹配失败: {str(e)}'


def download_instructions():
    return {
        'engine': engine_name(),
        'available': _check_insightface(),
        'model_path': INSIGHTFACE_MODEL,
        'download_url': 'https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_s.zip',
        'instructions': [
            '1. 下载 buffalo_s.zip (~140MB)',
            '   https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_s.zip',
            f'2. 解压到: {INSIGHTFACE_MODEL}',
            f'3. 确保存在: {INSIGHTFACE_MODEL}/det_10g.onnx',
            f'4. 重启后端自动切换为 InsightFace',
        ]
    }
