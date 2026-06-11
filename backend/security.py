"""
安全模块
- JWT 鉴权
- CORS 白名单
- 操作审计
- 密码策略
"""
import os
import jwt
import datetime
import secrets
import bcrypt
from functools import wraps
from flask import request, jsonify, g
from logger import security_logger

_jwt_secret = None

def init_security(app_config):
    global _jwt_secret
    _jwt_secret = app_config.get('SECRET_KEY') or os.environ.get('SECRET_KEY')
    if not _jwt_secret:
        raise RuntimeError('SECRET_KEY 未配置！请在 .env 中设置 SECRET_KEY=<强随机字符串>')
    security_logger.info('Security module initialized')

def get_jwt_secret():
    if not _jwt_secret:
        raise RuntimeError('Security module not initialized')
    return _jwt_secret

def generate_token(admin_id, username):
    payload = {
        'admin_id': admin_id,
        'username': username,
        'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24),
        'iat': datetime.datetime.now(datetime.timezone.utc)
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm='HS256')

def decode_token(token):
    return jwt.decode(token, get_jwt_secret(), algorithms=['HS256'])

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'code': 401, 'message': '未登录'}), 401
        try:
            payload = decode_token(token)
            g.admin_id = payload['admin_id']
            g.admin_name = payload['username']
        except jwt.ExpiredSignatureError:
            return jsonify({'code': 401, 'message': '登录已过期'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'code': 401, 'message': '无效令牌'}), 401
        return f(*args, **kwargs)
    return decorated

def generate_random_password(length=12):
    return secrets.token_urlsafe(length)

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def validate_image_upload(file_storage, max_size_mb=10):
    if not file_storage or not file_storage.filename:
        return False, '未选择文件'
    ext = file_storage.filename.rsplit('.', 1)[-1].lower() if '.' in file_storage.filename else ''
    if ext not in ('jpg', 'jpeg', 'png', 'bmp'):
        return False, f'不支持的文件类型: .{ext}'
    from PIL import Image
    try:
        img = Image.open(file_storage.stream)
        img.verify()
    except Exception:
        return False, '文件不是有效的图片'
    file_storage.stream.seek(0)
    return True, 'OK'
