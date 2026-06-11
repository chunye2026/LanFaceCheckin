"""
考勤决策引擎 - 自动签到/签退逻辑
禁止前端直接传入 member_id 打卡
"""
import datetime
from config import COOLDOWN_SECONDS
from logger import app_logger


def process_recognition(recognition_event):
    """
    根据识别事件 + 成员当天考勤状态，决定是否创建打卡记录
    返回 (created: bool, reason: str)
    """
    from models import db, Member, CheckinRecord

    member_id = recognition_event.member_id
    if not member_id:
        return False, 'no_member_id'

    member = Member.query.get(member_id)
    if not member or not member.active:
        return False, 'member_inactive'

    from config import MIN_FACE_SAMPLES
    if member.sample_count < MIN_FACE_SAMPLES:
        return False, 'insufficient_face_samples'

    now = datetime.datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # 查询今天的打卡记录
    today_records = CheckinRecord.query.filter(
        CheckinRecord.member_id == member_id,
        CheckinRecord.check_time >= today_start
    ).order_by(CheckinRecord.check_time.asc()).all()

    has_checkin = any(r.check_type == 'in' for r in today_records)
    has_checkout = any(r.check_type == 'out' for r in today_records)

    # 规则1: 今天没有签到 → 自动签到
    if not has_checkin:
        return _create_record(member, recognition_event, 'in', 'auto_checkin_success')

    # 规则2: 已签到、未签退、超时冷却 → 自动签退
    if has_checkin and not has_checkout:
        last_in = max((r for r in today_records if r.check_type == 'in'), key=lambda r: r.check_time)
        elapsed = (now - last_in.check_time).total_seconds()
        if elapsed >= COOLDOWN_SECONDS:
            return _create_record(member, recognition_event, 'out', 'auto_checkout_success')
        return False, 'cooldown_not_reached'

    # 规则3: 已签到且已签退 → 不重复
    if has_checkin and has_checkout:
        return False, 'already_checked_out'

    return False, 'unknown_rule'


def manual_checkin(member_id, check_type, admin_name=''):
    """管理员手工补录"""
    from models import db, Member, CheckinRecord

    member = Member.query.get(member_id)
    if not member:
        return False, 'member_not_found'
    if check_type not in ('in', 'out'):
        return False, 'invalid_check_type'

    record = CheckinRecord(
        member_id=member.id,
        member_name=member.name,
        employee_id=member.employee_id,
        check_type=check_type,
        check_time=datetime.datetime.now(),
        confidence=1.0,
        camera_id=0,
        source='manual_admin',
    )
    db.session.add(record)
    db.session.flush()

    from models import write_operation_log
    write_operation_log(
        action='MANUAL_CHECKIN',
        target_type='checkin',
        target_id=record.id,
        target_name=member.name,
        detail=f'管理员 {admin_name} 为 {member.name} 手工补录 {check_type}'
    )
    db.session.commit()
    app_logger.info(f'Manual checkin: {member.name} {check_type} by {admin_name}')
    return True, 'manual_checkin_created'


def _create_record(member, event, check_type, reason):
    from models import db, CheckinRecord

    record = CheckinRecord(
        member_id=member.id,
        member_name=member.name,
        employee_id=member.employee_id,
        check_type=check_type,
        check_time=datetime.datetime.now(),
        confidence=event.confidence,
        camera_id=event.camera_id,
        source='auto',
        recognition_event_id=event.id,
    )
    db.session.add(record)
    db.session.flush()

    # 更新事件的 checkin_created 标记
    event.checkin_created = True

    app_logger.info(f'Auto {check_type}: {member.name} confidence={event.confidence:.4f} event={event.id}')
    return True, reason
