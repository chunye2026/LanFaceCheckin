"""
打卡路由（人脸识别签到/签退）
"""
import os
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify
from models import db, Member, CheckRecord
from face_service import find_matching_member
from routes.auth import write_checkin_log
from config import UPLOAD_FOLDER

checkin_bp = Blueprint('checkin', __name__)


@checkin_bp.route('/api/checkin/verify', methods=['POST'])
def verify_face():
    """
    接收前端拍摄的人脸照片，进行人脸识别打卡
    请求: multipart/form-data, 字段: file
    返回: 匹配到的成员信息
    """
    if 'file' not in request.files:
        return jsonify({'code': 400, 'message': '请拍摄人脸照片'})

    file = request.files['file']
    if not file.filename:
        return jsonify({'code': 400, 'message': '未接收到图片'})

    # 保存临时图片
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'jpg'
    temp_filename = f"checkin_temp_{uuid.uuid4().hex}.{ext}"
    temp_path = os.path.join(UPLOAD_FOLDER, temp_filename)
    file.save(temp_path)

    try:
        # 获取所有已录脸的活跃成员
        members = Member.query.filter_by(status=1).filter(Member.face_encoding != '').all()
        if not members:
            os.remove(temp_path)
            return jsonify({'code': 400, 'message': '系统中暂无已录脸的成员，请联系管理员'})

        # 构建编码列表
        known_encodings = [(m.id, m.face_encoding) for m in members]

        # 人脸匹配
        matched_id, confidence, msg = find_matching_member(known_encodings, temp_path)
    finally:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.remove(temp_path)

    if matched_id is None:
        return jsonify({'code': 400, 'message': msg})

    member = Member.query.get(matched_id)
    return jsonify({
        'code': 200,
        'data': {
            'member': member.to_dict(),
            'confidence': confidence
        }
    })


@checkin_bp.route('/api/checkin/do', methods=['POST'])
def do_checkin():
    """
    执行打卡（签到或签退）
    请求JSON: { member_id, check_type: 'in'|'out', confidence }
    """
    data = request.get_json()
    member_id = data.get('member_id')
    check_type = data.get('check_type')
    confidence = data.get('confidence', 0.0)

    if check_type not in ('in', 'out'):
        return jsonify({'code': 400, 'message': '打卡类型错误'})

    member = Member.query.get(member_id)
    if not member:
        return jsonify({'code': 404, 'message': '成员不存在'})
    if member.status != 1:
        return jsonify({'code': 400, 'message': '该成员已被禁用，无法打卡'})

    # 创建打卡记录
    record = CheckRecord(
        member_id=member.id,
        member_name=member.name,
        employee_id=member.employee_id,
        check_type=check_type,
        ip_address=request.remote_addr or '',
        confidence=confidence
    )
    db.session.add(record)
    db.session.flush()

    type_name = '签到' if check_type == 'in' else '签退'
    write_checkin_log(
        action='CHECK_' + check_type.upper(),
        target_type='checkin',
        target_id=record.id,
        target_name=member.name,
        detail=f'{member.name}({member.employee_id}) {type_name}成功 (置信度:{confidence})'
    )
    db.session.commit()

    return jsonify({
        'code': 200,
        'message': f'{type_name}成功',
        'data': {
            'record': record.to_dict(),
            'member': member.to_dict()
        }
    })


@checkin_bp.route('/api/checkin/records', methods=['GET'])
def get_records():
    """查询打卡记录"""
    member_id = request.args.get('member_id', type=int)
    check_type = request.args.get('check_type')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    query = CheckRecord.query

    if member_id:
        query = query.filter_by(member_id=member_id)
    if check_type:
        query = query.filter_by(check_type=check_type)
    if date_from:
        query = query.filter(CheckRecord.check_time >= f'{date_from} 00:00:00')
    if date_to:
        query = query.filter(CheckRecord.check_time <= f'{date_to} 23:59:59')

    total = query.count()
    records = query.order_by(CheckRecord.check_time.desc()) \
        .offset((page - 1) * per_page).limit(per_page).all()

    return jsonify({
        'code': 200,
        'data': {
            'list': [r.to_dict() for r in records],
            'total': total,
            'page': page,
            'per_page': per_page
        }
    })


@checkin_bp.route('/api/checkin/today-status/<int:member_id>', methods=['GET'])
def today_status(member_id):
    """获取成员今日打卡状态"""
    today = datetime.now().strftime('%Y-%m-%d')
    records = CheckRecord.query.filter(
        CheckRecord.member_id == member_id,
        CheckRecord.check_time >= f'{today} 00:00:00',
        CheckRecord.check_time <= f'{today} 23:59:59'
    ).order_by(CheckRecord.check_time.asc()).all()

    has_in = any(r.check_type == 'in' for r in records)
    has_out = any(r.check_type == 'out' for r in records)

    last_in = next((r for r in reversed(records) if r.check_type == 'in'), None)
    last_out = next((r for r in reversed(records) if r.check_type == 'out'), None)

    return jsonify({
        'code': 200,
        'data': {
            'has_in': has_in,
            'has_out': has_out,
            'last_in_time': last_in.check_time.isoformat() if last_in else None,
            'last_out_time': last_out.check_time.isoformat() if last_out else None,
            'records': [r.to_dict() for r in records]
        }
    })
