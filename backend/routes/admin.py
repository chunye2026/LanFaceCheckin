"""
统一后台管理路由
"""
import csv
import io
from datetime import datetime
from flask import Blueprint, request, jsonify, g, Response
from models import db, Admin, Member, FaceSample, FaceEmbedding, CameraDevice, RecognitionEvent, CheckinRecord, OperationLog, write_operation_log
from security import admin_required, hash_password, verify_password, validate_image_upload, generate_random_password
from face_service import extract_embedding, embedding_to_json, is_model_available, verify_face_image
from storage import save_upload, delete_file
from logger import app_logger, security_logger
from config import MIN_FACE_SAMPLES, MAX_FACE_SAMPLES, UPLOAD_FOLDER

admin_bp = Blueprint('admin', __name__)


# ========== 认证 ==========

@admin_bp.route('/api/admin/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    if not username or not password:
        return jsonify({'code': 400, 'message': '用户名和密码不能为空'})
    admin = Admin.query.filter_by(username=username, active=True).first()
    if not admin or not admin.check_password(password):
        security_logger.warning(f'Login failed: {username}')
        return jsonify({'code': 401, 'message': '用户名或密码错误'})
    from security import generate_token
    token = generate_token(admin.id, admin.username)
    security_logger.info(f'Login success: {username}')
    return jsonify({
        'code': 200, 'message': '登录成功',
        'data': {'token': token, 'username': admin.username, 'must_change_password': admin.must_change_password}
    })


@admin_bp.route('/api/admin/change-password', methods=['POST'])
@admin_required
def change_password():
    data = request.get_json()
    old_pw = data.get('old_password', '')
    new_pw = data.get('new_password', '')
    if not new_pw or len(new_pw) < 6:
        return jsonify({'code': 400, 'message': '新密码至少6位'})
    admin = Admin.query.get(g.admin_id)
    if not admin.check_password(old_pw):
        return jsonify({'code': 400, 'message': '旧密码错误'})
    admin.set_password(new_pw)
    admin.must_change_password = False
    db.session.commit()
    write_operation_log('CHANGE_PASSWORD', target_name=admin.username)
    security_logger.info(f'Password changed: {admin.username}')
    return jsonify({'code': 200, 'message': '密码修改成功'})


@admin_bp.route('/api/admin/info', methods=['GET'])
@admin_required
def get_info():
    admin = Admin.query.get(g.admin_id)
    return jsonify({'code': 200, 'data': {'username': admin.username, 'must_change_password': admin.must_change_password}})


# ========== 成员管理 ==========

@admin_bp.route('/api/admin/members', methods=['GET'])
@admin_required
def list_members():
    keyword = request.args.get('keyword', '').strip()
    query = Member.query
    if keyword:
        query = query.filter(db.or_(Member.name.like(f'%{keyword}%'), Member.employee_id.like(f'%{keyword}%'), Member.department.like(f'%{keyword}%')))
    members = query.order_by(Member.created_at.desc()).all()
    return jsonify({'code': 200, 'data': [m.to_dict() for m in members]})


@admin_bp.route('/api/admin/members', methods=['POST'])
@admin_required
def create_member():
    data = request.get_json()
    name = data.get('name', '').strip()
    eid = data.get('employee_id', '').strip()
    if not name: return jsonify({'code': 400, 'message': '姓名不能为空'})
    if not eid: return jsonify({'code': 400, 'message': '工号不能为空'})
    if Member.query.filter_by(employee_id=eid).first():
        return jsonify({'code': 400, 'message': '工号已存在'})
    m = Member(name=name, employee_id=eid, department=data.get('department', '').strip(), phone=data.get('phone', '').strip(), email=data.get('email', '').strip())
    db.session.add(m)
    db.session.flush()
    write_operation_log('CREATE_MEMBER', 'member', m.id, name, f'创建成员: {name}({eid})')
    db.session.commit()
    return jsonify({'code': 200, 'message': '创建成功', 'data': m.to_dict()})


@admin_bp.route('/api/admin/members/<int:mid>', methods=['PUT'])
@admin_required
def update_member(mid):
    m = Member.query.get(mid)
    if not m: return jsonify({'code': 404, 'message': '成员不存在'})
    data = request.get_json()
    if 'name' in data and data['name'].strip(): m.name = data['name'].strip()
    if 'department' in data: m.department = data['department'].strip()
    if 'phone' in data: m.phone = data['phone'].strip()
    if 'email' in data: m.email = data['email'].strip()
    if 'active' in data: m.active = bool(data['active'])
    write_operation_log('UPDATE_MEMBER', 'member', m.id, m.name, f'更新成员信息')
    db.session.commit()
    return jsonify({'code': 200, 'message': '更新成功', 'data': m.to_dict()})


@admin_bp.route('/api/admin/members/<int:mid>', methods=['DELETE'])
@admin_required
def delete_member(mid):
    m = Member.query.get(mid)
    if not m: return jsonify({'code': 404, 'message': '成员不存在'})
    # 删除关联数据
    for s in m.face_samples.all():
        delete_file(s.image_path)
    FaceEmbedding.query.filter_by(member_id=mid).delete()
    FaceSample.query.filter_by(member_id=mid).delete()
    CheckinRecord.query.filter_by(member_id=mid).delete()
    # 识别事件解除关联
    for event in RecognitionEvent.query.filter_by(member_id=mid).all():
        event.member_id = None
    name = m.name
    write_operation_log('DELETE_MEMBER', 'member', mid, name, f'删除成员: {name}')
    db.session.delete(m)
    db.session.commit()
    return jsonify({'code': 200, 'message': '已删除'})


# ========== 人脸样本管理 ==========

@admin_bp.route('/api/admin/members/<int:mid>/face-samples', methods=['POST'])
@admin_required
def upload_face_sample(mid):
    m = Member.query.get(mid)
    if not m: return jsonify({'code': 404, 'message': '成员不存在'})
    if m.sample_count >= MAX_FACE_SAMPLES:
        return jsonify({'code': 400, 'message': f'最多{MAX_FACE_SAMPLES}张人脸样本'})
    if 'file' not in request.files:
        return jsonify({'code': 400, 'message': '请上传图片'})
    file = request.files['file']
    valid, msg = validate_image_upload(file)
    if not valid: return jsonify({'code': 400, 'message': msg})
    valid, msg = verify_face_image(file)
    if not valid: return jsonify({'code': 400, 'message': msg})
    filename, filepath = save_upload(file, 'face')
    sample = FaceSample(member_id=m.id, image_path=filename)
    db.session.add(sample)
    db.session.flush()
    import cv2, numpy as np
    img = cv2.imread(filepath)
    emb, emb_msg = extract_embedding(img)
    if emb is None:
        db.session.delete(sample)
        db.session.commit()
        delete_file(filename)
        return jsonify({'code': 400, 'message': emb_msg})
    fe = FaceEmbedding(member_id=m.id, face_sample_id=sample.id, embedding_json=embedding_to_json(emb))
    db.session.add(fe)
    write_operation_log('UPLOAD_FACE', 'member', m.id, m.name, f'上传人脸样本 #{sample.id}')
    db.session.commit()
    return jsonify({'code': 200, 'message': '人脸样本上传成功', 'data': sample.to_dict()})


@admin_bp.route('/api/admin/members/<int:mid>/face-samples', methods=['GET'])
@admin_required
def list_face_samples(mid):
    samples = FaceSample.query.filter_by(member_id=mid).order_by(FaceSample.created_at.desc()).all()
    return jsonify({'code': 200, 'data': [s.to_dict() for s in samples]})


@admin_bp.route('/api/admin/face-samples/<int:sid>', methods=['DELETE'])
@admin_required
def delete_face_sample(sid):
    s = FaceSample.query.get(sid)
    if not s: return jsonify({'code': 404, 'message': '样本不存在'})
    mid = s.member_id
    delete_file(s.image_path)
    FaceEmbedding.query.filter_by(face_sample_id=sid).delete()
    write_operation_log('DELETE_FACE', 'face_sample', s.id, '', f'删除人脸样本: member_id={mid}')
    db.session.delete(s)
    db.session.commit()
    return jsonify({'code': 200, 'message': '已删除'})


# ========== 摄像头控制 ==========

@admin_bp.route('/api/admin/camera/start', methods=['POST'])
@admin_required
def camera_start():
    from camera_service import start
    ok, msg = start()
    cam = CameraDevice.query.first()
    if not cam:
        cam = CameraDevice(name='Default Camera', device_index=0)
        db.session.add(cam)
        db.session.flush()
    cam.status = 'running' if ok else 'error'
    cam.last_error = '' if ok else msg
    db.session.commit()
    return jsonify({'code': 200 if ok else 400, 'message': msg})


@admin_bp.route('/api/admin/camera/stop', methods=['POST'])
@admin_required
def camera_stop():
    from camera_service import stop
    stop()
    cam = CameraDevice.query.first()
    if cam:
        cam.status = 'stopped'
        db.session.commit()
    return jsonify({'code': 200, 'message': 'Camera stopped'})


@admin_bp.route('/api/admin/camera/status', methods=['GET'])
def camera_status():
    from camera_service import get_status
    from face_service import is_model_available
    s = get_status()
    s['model_available'] = is_model_available()
    return jsonify({'code': 200, 'data': s})


@admin_bp.route('/api/admin/camera/snapshot', methods=['GET'])
def camera_snapshot():
    from camera_service import get_frame
    import cv2
    frame = get_frame()
    if frame is None:
        return jsonify({'code': 400, 'message': 'Camera not running'})
    _, buf = cv2.imencode('.jpg', frame)
    return Response(buf.tobytes(), mimetype='image/jpeg')


@admin_bp.route('/api/admin/camera/stream', methods=['GET'])
def camera_stream():
    """MJPEG 实时视频流"""
    from camera_service import get_frame
    import cv2

    def generate():
        while True:
            frame = get_frame()
            if frame is None:
                # 返回占位图
                placeholder = cv2.imencode('.jpg', cv2.zeros((480, 640, 3), dtype=cv2.uint8))[0]
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + placeholder.tobytes() + b'\r\n')
            else:
                _, buf = cv2.imencode('.jpg', frame)
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')
            import time
            time.sleep(0.1)

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')


# ========== 识别事件 ==========

@admin_bp.route('/api/admin/recognition-events', methods=['GET'])
@admin_required
def list_recognition_events():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    q = RecognitionEvent.query.order_by(RecognitionEvent.created_at.desc())
    total = q.count()
    events = q.offset((page-1)*per_page).limit(per_page).all()
    return jsonify({'code': 200, 'data': {'list': [e.to_dict() for e in events], 'total': total, 'page': page, 'per_page': per_page}})


# ========== 考勤记录 ==========

@admin_bp.route('/api/admin/checkin-records', methods=['GET'])
@admin_required
def list_checkin_records():
    mid = request.args.get('member_id', type=int)
    ctype = request.args.get('check_type')
    source = request.args.get('source')
    df = request.args.get('date_from')
    dt_ = request.args.get('date_to')
    page = request.args.get('page', 1, type=int)
    pp = request.args.get('per_page', 50, type=int)
    fmt = request.args.get('format', 'json')

    q = CheckinRecord.query
    if mid: q = q.filter_by(member_id=mid)
    if ctype: q = q.filter_by(check_type=ctype)
    if source: q = q.filter_by(source=source)
    if df: q = q.filter(CheckinRecord.check_time >= f'{df} 00:00:00')
    if dt_: q = q.filter(CheckinRecord.check_time <= f'{dt_} 23:59:59')
    total = q.count()
    records = q.order_by(CheckinRecord.check_time.desc()).offset((page-1)*pp).limit(pp).all()

    if fmt == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', '姓名', '工号', '类型', '时间', '置信度', '来源', '识别事件ID'])
        for r in records:
            writer.writerow([r.id, r.member_name, r.employee_id, r.check_type, r.check_time.isoformat(), r.confidence, r.source, r.recognition_event_id])
        return Response(output.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment;filename=checkin_records.csv'})

    return jsonify({'code': 200, 'data': {'list': [r.to_dict() for r in records], 'total': total, 'page': page, 'per_page': pp}})


@admin_bp.route('/api/admin/checkin-records/manual', methods=['POST'])
@admin_required
def manual_checkin():
    data = request.get_json()
    mid = data.get('member_id')
    ctype = data.get('check_type')
    if not mid or ctype not in ('in', 'out'):
        return jsonify({'code': 400, 'message': '参数错误'})
    from attendance_service import manual_checkin
    ok, msg = manual_checkin(mid, ctype, g.admin_name)
    return jsonify({'code': 200 if ok else 400, 'message': msg})


# ========== 系统状态 ==========

@admin_bp.route('/api/dashboard/status', methods=['GET'])
def dashboard_status():
    """公开 Dashboard 聚合接口，无需登录"""
    from camera_service import get_status as camera_get_status
    from face_service import is_model_available

    cam = camera_get_status()
    cam['model_available'] = is_model_available()

    member_count = Member.query.filter_by(active=True).count()
    today = datetime.now().strftime('%Y-%m-%d')
    today_in = CheckinRecord.query.filter(CheckinRecord.check_time >= f'{today} 00:00:00', CheckinRecord.check_type == 'in').count()
    today_out = CheckinRecord.query.filter(CheckinRecord.check_time >= f'{today} 00:00:00', CheckinRecord.check_type == 'out').count()

    events = RecognitionEvent.query.order_by(RecognitionEvent.created_at.desc()).limit(10).all()
    records = CheckinRecord.query.order_by(CheckinRecord.check_time.desc()).limit(10).all()

    return jsonify({'code': 200, 'data': {
        'camera': cam,
        'system': {
            'member_count': member_count,
            'today_checkin': today_in,
            'today_checkout': today_out,
            'model_available': is_model_available(),
        },
        'recent_events': [e.to_dict() for e in events],
        'recent_records': [r.to_dict() for r in records],
    }})


@admin_bp.route('/api/admin/operation-logs', methods=['GET'])
@admin_required
def list_operation_logs():
    page = request.args.get('page', 1, type=int)
    pp = request.args.get('per_page', 50, type=int)
    aname = request.args.get('admin_name', '').strip()
    action = request.args.get('action', '').strip()
    q = OperationLog.query
    if aname: q = q.filter(OperationLog.admin_name.like(f'%{aname}%'))
    if action: q = q.filter_by(action=action)
    total = q.count()
    logs = q.order_by(OperationLog.created_at.desc()).offset((page-1)*pp).limit(pp).all()
    return jsonify({'code': 200, 'data': {'list': [l.to_dict() for l in logs], 'total': total, 'page': page, 'per_page': pp}})

@admin_bp.route('/api/admin/system/status', methods=['GET'])
def system_status():
    from face_service import is_model_available
    member_count = Member.query.filter_by(active=True).count()
    today = datetime.now().strftime('%Y-%m-%d')
    today_in = CheckinRecord.query.filter(CheckinRecord.check_time >= f'{today} 00:00:00', CheckinRecord.check_type == 'in').count()
    today_out = CheckinRecord.query.filter(CheckinRecord.check_time >= f'{today} 00:00:00', CheckinRecord.check_type == 'out').count()
    return jsonify({'code': 200, 'data': {
        'model_available': is_model_available(),
        'member_count': member_count,
        'today_checkin': today_in,
        'today_checkout': today_out,
    }})
