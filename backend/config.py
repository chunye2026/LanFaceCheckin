import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# 数据库配置
DATABASE_PATH = os.path.join(BASE_DIR, 'data', 'checkin.db')

# JWT配置
SECRET_KEY = 'lan-checkin-secret-key-change-in-production'
JWT_EXPIRATION_HOURS = 24

# 人脸识别配置 (InsightFace ArcFace)
FACE_TOLERANCE = 0.35  # 余弦相似度阈值(0~1)，越大越宽松。ArcFace建议0.3~0.4

# 上传配置
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp'}

# 默认管理员
DEFAULT_ADMIN_USERNAME = 'admin'
DEFAULT_ADMIN_PASSWORD = 'admin123'

# 确保目录存在
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
