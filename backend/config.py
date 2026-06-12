"""
配置文件 - 所有配置从环境变量读取，无硬编码
"""
import os
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

# ====== 安全 (必填) ======
SECRET_KEY = os.environ.get('SECRET_KEY', '')
if not SECRET_KEY and not os.environ.get('FLASK_SKIP_SECRET_CHECK'):
    raise RuntimeError('SECRET_KEY 未配置！请复制 .env.example 为 .env 并设置 SECRET_KEY')

# ====== 管理员初始凭证 ======
ADMIN_INIT_USERNAME = os.environ.get('ADMIN_INIT_USERNAME', 'admin')
ADMIN_INIT_PASSWORD = os.environ.get('ADMIN_INIT_PASSWORD', '')

# ====== 数据库 ======
DATABASE_URL = os.environ.get('DATABASE_URL', f'sqlite:///{os.path.join(BASE_DIR, "data", "checkin.db")}')

# ====== CORS ======
_cors_raw = os.environ.get('CORS_ALLOWED_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173')
CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors_raw.split(',') if o.strip()]

# ====== 人脸识别 ======
FACE_MATCH_THRESHOLD = float(os.environ.get('FACE_MATCH_THRESHOLD', '0.65'))
CHECKIN_INTERVAL_SECONDS = int(os.environ.get('CHECKIN_INTERVAL_SECONDS', '300'))
CAMERA_INDEX = int(os.environ.get('CAMERA_INDEX', '0'))
ENABLE_LIVENESS = os.environ.get('ENABLE_LIVENESS', 'false').lower() == 'true'
MIN_FACE_SAMPLES = int(os.environ.get('MIN_FACE_SAMPLES', '3'))
MAX_FACE_SAMPLES = int(os.environ.get('MAX_FACE_SAMPLES', '5'))
DETECTION_EVERY_N_FRAMES = int(os.environ.get('DETECTION_EVERY_N_FRAMES', '5'))
COOLDOWN_SECONDS = int(os.environ.get('COOLDOWN_SECONDS', '300'))
ALLOW_MULTIPLE_IN_OUT = os.environ.get('ALLOW_MULTIPLE_IN_OUT', 'true').lower() == 'true'

# ====== Dashboard 大屏 ======
DASHBOARD_DRAW_FACE_BOX = os.environ.get('DASHBOARD_DRAW_FACE_BOX', 'true').lower() == 'true'
DASHBOARD_SHOW_PHONE = os.environ.get('DASHBOARD_SHOW_PHONE', 'true').lower() == 'true'
DASHBOARD_SHOW_EMAIL = os.environ.get('DASHBOARD_SHOW_EMAIL', 'true').lower() == 'true'
DASHBOARD_MASK_PHONE = os.environ.get('DASHBOARD_MASK_PHONE', 'true').lower() == 'true'
DASHBOARD_MASK_EMAIL = os.environ.get('DASHBOARD_MASK_EMAIL', 'true').lower() == 'true'
DASHBOARD_TOP_N = int(os.environ.get('DASHBOARD_TOP_N', '10'))
WORKDAY_WEEKDAYS = [int(x) for x in os.environ.get('WORKDAY_WEEKDAYS', '0,1,2,3,4').split(',') if x.strip() != '']
ATTENDANCE_DAY_RULE = os.environ.get('ATTENDANCE_DAY_RULE', 'any_record')

# ====== Flask ======
FLASK_DEBUG = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
FLASK_HOST = os.environ.get('FLASK_HOST', '0.0.0.0')
FLASK_PORT = int(os.environ.get('FLASK_PORT', '5000'))
FLASK_USE_SSL = os.environ.get('FLASK_USE_SSL', 'false').lower() == 'true'

# ====== 上传 ======
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
MAX_UPLOAD_SIZE_MB = 10

# ====== 路径 ======
if DATABASE_URL.startswith('sqlite:///'):
    _db_rel = DATABASE_URL.replace('sqlite:///', '')
    _db_abs = os.path.join(BASE_DIR, _db_rel)
    DATABASE_URL = f'sqlite:///{_db_abs}'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'data'), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)
