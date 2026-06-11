"""
管理员认证路由
"""
import jwt
import datetime
from functools import wraps
from flask import Blueprint, request, jsonify, g
from models import db, Admin, AuditLog
from config import SECRET_KEY, JWT_EXPIRATION_HOURS

auth_bp = Blueprint('auth', __name__)


def generate_token(admin_id: int, username: str) -> str:
    """生成JWT Token"""
    payload = {
        'admin_id': admin_id,
        'username': username,
        'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.datetime.now(datetime.timezone.utc)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')


def admin_required(f):
    """管理员鉴权装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'code': 401, 'message': '未登录，请先登录'}), 401
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            g.admin_id = payload['admin_id']
            g.admin_name = payload['username']
        except jwt.ExpiredSignatureError:
            return jsonify({'code': 401, 'message': '登录已过期，请重新登录'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'code': 401, 'message': '无效的登录凭证'}), 401
        return f(*args, **kwargs)
    return decorated


def write_audit_log(action: str, target_type: str = '', target_id: int = 0,
                    target_name: str = '', detail: str = ''):
    """写入操作日志"""
    try:
        log = AuditLog(
            admin_id=getattr(g, 'admin_id', None),
            admin_name=getattr(g, 'admin_name', ''),
            action=action,
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            detail=detail,
            ip_address=request.remote_addr or ''
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        pass


def write_checkin_log(action: str, target_type: str = '', target_id: int = 0,
                      target_name: str = '', detail: str = ''):
    """写入打卡系统操作日志（无需管理员登录）"""
    try:
        log = AuditLog(
            admin_id=None,
            admin_name='SYSTEM',
            action=action,
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            detail=detail,
            ip_address=request.remote_addr or ''
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        pass


@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    """管理员登录"""
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'code': 400, 'message': '用户名和密码不能为空'})

    admin = Admin.query.filter_by(username=username).first()
    if not admin or not admin.check_password(password):
        write_audit_log(action='LOGIN_FAILED', target_name=username,
                        detail='登录失败：用户名或密码错误')
        return jsonify({'code': 401, 'message': '用户名或密码错误'})

    token = generate_token(admin.id, admin.username)
    write_audit_log(action='LOGIN', target_name=username, detail='管理员登录成功')
    return jsonify({
        'code': 200,
        'message': '登录成功',
        'data': {
            'token': token,
            'username': admin.username
        }
    })


@auth_bp.route('/api/auth/info', methods=['GET'])
@admin_required
def get_info():
    """获取当前管理员信息"""
    return jsonify({
        'code': 200,
        'data': {
            'username': g.admin_name
        }
    })
