"""
操作日志路由
"""
from flask import Blueprint, request, jsonify
from models import AuditLog
from routes.auth import admin_required

log_bp = Blueprint('log', __name__)


@log_bp.route('/api/logs', methods=['GET'])
@admin_required
def list_logs():
    """查询操作日志"""
    admin_name = request.args.get('admin_name', '').strip()
    action = request.args.get('action', '').strip()
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    query = AuditLog.query

    if admin_name:
        query = query.filter(AuditLog.admin_name.like(f'%{admin_name}%'))
    if action:
        query = query.filter_by(action=action)
    if date_from:
        query = query.filter(AuditLog.created_at >= f'{date_from} 00:00:00')
    if date_to:
        query = query.filter(AuditLog.created_at <= f'{date_to} 23:59:59')

    total = query.count()
    logs = query.order_by(AuditLog.created_at.desc()) \
        .offset((page - 1) * per_page).limit(per_page).all()

    return jsonify({
        'code': 200,
        'data': {
            'list': [l.to_dict() for l in logs],
            'total': total,
            'page': page,
            'per_page': per_page
        }
    })


@log_bp.route('/api/logs/action-types', methods=['GET'])
@admin_required
def action_types():
    """获取所有操作类型列表"""
    types = [
        'LOGIN', 'LOGIN_FAILED',
        'CREATE_MEMBER', 'UPDATE_MEMBER', 'DELETE_MEMBER',
        'UPLOAD_FACE', 'DELETE_FACE',
        'CHECK_IN', 'CHECK_OUT',
    ]
    return jsonify({'code': 200, 'data': types})
