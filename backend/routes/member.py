"""
成员管理路由
"""
import os
import uuid
from flask import Blueprint, request, jsonify, g
from models import db, Member, CheckRecord
from face_service import detect_and_encode_face, encoding_to_json, json_to_encoding
from routes.auth import admin_required, write_audit_log
from config import UPLOAD_FOLDER

member_bp = Blueprint('member', __name__)


@member_bp.route('/api/members', methods=['GET'])
@admin_required
def list_members():
    """获取所有成员列表"""
    keyword = request.args.get('keyword', '').strip()
    status = request.args.get('status', type=int)

    query = Member.query
    if keyword:
        query = query.filter(
            db.or_(
                Member.name.like(f'%{keyword}%'),
                Member.employee_id.like(f'%{keyword}%'),
                Member.department.like(f'%{keyword}%')
            )
        )
    if status is not None:
        query = query.filter_by(status=status)

    members = query.order_by(Member.created_at.desc()).all()
    return jsonify({
        'code': 200,
        'data': [m.to_dict() for m in members]
    })


@member_bp.route('/api/members/<int:member_id>', methods=['GET'])
@admin_required
def get_member(member_id):
    """获取单个成员详情"""
    member = Member.query.get(member_id)
    if not member:
        return jsonify({'code': 404, 'message': '成员不存在'})
    return jsonify({'code': 200, 'data': member.to_dict()})


@member_bp.route('/api/members', methods=['POST'])
@admin_required
def create_member():
    """新增成员"""
    data = request.get_json()
    name = data.get('name', '').strip()
    employee_id = data.get('employee_id', '').strip()

    if not name:
        return jsonify({'code': 400, 'message': '姓名不能为空'})
    if not employee_id:
        return jsonify({'code': 400, 'message': '工号不能为空'})

    existing = Member.query.filter_by(employee_id=employee_id).first()
    if existing:
        return jsonify({'code': 400, 'message': f'工号 {employee_id} 已存在'})

    member = Member(
        name=name,
        employee_id=employee_id,
        department=data.get('department', '').strip(),
        phone=data.get('phone', '').strip(),
        email=data.get('email', '').strip(),
    )
    db.session.add(member)
    db.session.flush()

    write_audit_log(action='CREATE_MEMBER', target_type='member',
                    target_id=member.id, target_name=name,
                    detail=f'新增成员: {name}({employee_id})')
    db.session.commit()

    return jsonify({'code': 200, 'message': '成员创建成功', 'data': member.to_dict()})


@member_bp.route('/api/members/<int:member_id>', methods=['PUT'])
@admin_required
def update_member(member_id):
    """更新成员信息"""
    member = Member.query.get(member_id)
    if not member:
        return jsonify({'code': 404, 'message': '成员不存在'})

    data = request.get_json()
    old_data = member.to_dict()

    if 'name' in data and data['name'].strip():
        member.name = data['name'].strip()
    if 'employee_id' in data and data['employee_id'].strip():
        existing = Member.query.filter_by(employee_id=data['employee_id']).first()
        if existing and existing.id != member_id:
            return jsonify({'code': 400, 'message': f'工号 {data["employee_id"]} 已存在'})
        member.employee_id = data['employee_id'].strip()
    if 'department' in data:
        member.department = data['department'].strip()
    if 'phone' in data:
        member.phone = data['phone'].strip()
    if 'email' in data:
        member.email = data['email'].strip()
    if 'status' in data:
        member.status = data['status']

    write_audit_log(
        action='UPDATE_MEMBER', target_type='member',
        target_id=member.id, target_name=member.name,
        detail=f'更新成员: 旧={old_data}, 新={member.to_dict()}'
    )
    db.session.commit()

    return jsonify({'code': 200, 'message': '成员信息更新成功', 'data': member.to_dict()})


@member_bp.route('/api/members/<int:member_id>', methods=['DELETE'])
@admin_required
def delete_member(member_id):
    """删除成员"""
    member = Member.query.get(member_id)
    if not member:
        return jsonify({'code': 404, 'message': '成员不存在'})

    name = member.name
    eid = member.employee_id

    # 删除关联的打卡记录
    CheckRecord.query.filter_by(member_id=member_id).delete()

    # 删除人脸照片文件
    if member.face_image:
        img_path = os.path.join(UPLOAD_FOLDER, member.face_image)
        if os.path.exists(img_path):
            os.remove(img_path)

    write_audit_log(action='DELETE_MEMBER', target_type='member',
                    target_id=member.id, target_name=name,
                    detail=f'删除成员: {name}({eid})')
    db.session.delete(member)
    db.session.commit()

    return jsonify({'code': 200, 'message': '成员已删除'})


@member_bp.route('/api/members/<int:member_id>/face', methods=['POST'])
@admin_required
def upload_face(member_id):
    """上传成员人脸照片并提取特征"""
    member = Member.query.get(member_id)
    if not member:
        return jsonify({'code': 404, 'message': '成员不存在'})

    if 'file' not in request.files:
        return jsonify({'code': 400, 'message': '请上传人脸照片'})

    file = request.files['file']
    if not file.filename:
        return jsonify({'code': 400, 'message': '未选择文件'})

    # 保存文件
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'jpg'
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    # 提取人脸特征
    success, encoding, msg = detect_and_encode_face(filepath)
    if not success:
        os.remove(filepath)
        return jsonify({'code': 400, 'message': msg})

    # 删除旧照片
    if member.face_image:
        old_path = os.path.join(UPLOAD_FOLDER, member.face_image)
        if os.path.exists(old_path):
            os.remove(old_path)

    member.face_encoding = encoding_to_json(encoding)
    member.face_image = filename

    write_audit_log(action='UPLOAD_FACE', target_type='member',
                    target_id=member.id, target_name=member.name,
                    detail=f'上传人脸照片: {member.name}')
    db.session.commit()

    return jsonify({'code': 200, 'message': '人脸照片上传成功', 'data': member.to_dict()})


@member_bp.route('/api/members/<int:member_id>/face', methods=['DELETE'])
@admin_required
def delete_face(member_id):
    """删除成员人脸数据"""
    member = Member.query.get(member_id)
    if not member:
        return jsonify({'code': 404, 'message': '成员不存在'})

    if member.face_image:
        img_path = os.path.join(UPLOAD_FOLDER, member.face_image)
        if os.path.exists(img_path):
            os.remove(img_path)

    member.face_encoding = ''
    member.face_image = ''

    write_audit_log(action='DELETE_FACE', target_type='member',
                    target_id=member.id, target_name=member.name,
                    detail=f'删除人脸数据: {member.name}')
    db.session.commit()

    return jsonify({'code': 200, 'message': '人脸数据已删除'})


@member_bp.route('/api/members/active-for-checkin', methods=['GET'])
def get_active_members():
    """获取可用于打卡的活跃成员（无需管理员登录）"""
    members = Member.query.filter_by(status=1).filter(Member.face_encoding != '').all()
    return jsonify({
        'code': 200,
        'data': [m.to_dict() for m in members]
    })


@member_bp.route('/api/model/status', methods=['GET'])
def model_status():
    """检查人脸识别模型状态"""
    from face_service import download_instructions, engine_name
    info = download_instructions()
    eng = engine_name()
    return jsonify({
        'code': 200,
        'data': {
            'engine': eng,
            'available': info['available'],
            'model_path': info['model_path'],
            'download_url': info['download_url'],
            'instructions': info['instructions'],
            'algorithm': 'InsightFace (RetinaFace + ArcFace)' if eng == 'InsightFace' else 'OpenCV (Haar Cascade + LBPH)',
            'backend': 'ONNX Runtime (CPU)' if eng == 'InsightFace' else 'OpenCV (CPU)',
        }
    })
