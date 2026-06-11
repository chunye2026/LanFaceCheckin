"""
考勤决策引擎 - 多次进出模式
基于最后一条记录决定下次行为（in→out→in→out 循环）
"""
import datetime
from config import COOLDOWN_SECONDS, ALLOW_MULTIPLE_IN_OUT
from logger import app_logger


def process_recognition(recognition_event):
    """
    根据识别事件 + 成员最后一条考勤记录，决定是否创建打卡
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

    # 获取该成员最后一条打卡记录
    last_record = CheckinRecord.query.filter_by(member_id=member_id)\
        .order_by(CheckinRecord.check_time.desc()).first()

    # 冷却检查
    if last_record:
        elapsed = (now - last_record.check_time).total_seconds()
        if elapsed < COOLDOWN_SECONDS:
            return False, 'cooldown_not_reached'

    # 多次进出模式：根据最后一条记录切换
    if ALLOW_MULTIPLE_IN_OUT:
        if last_record is None:
            next_type = 'in'
        elif last_record.check_type == 'in':
            next_type = 'out'
        else:
            next_type = 'in'
    else:
        # 旧模式：一天一次签到一次签退
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_records = CheckinRecord.query.filter(
            CheckinRecord.member_id == member_id,
            CheckinRecord.check_time >= today_start
        ).all()
        has_in = any(r.check_type == 'in' for r in today_records)
        has_out = any(r.check_type == 'out' for r in today_records)
        if not has_in:
            next_type = 'in'
        elif not has_out:
            next_type = 'out'
        else:
            return False, 'already_checked_out'

    return _create_record(member, recognition_event, next_type, f'auto_{next_type}_success')


def manual_checkin(member_id, check_type, admin_name=''):
    """管理员手工补录"""
    from models import db, Member, CheckinRecord

    member = Member.query.get(member_id)
    if not member:
        return False, 'member_not_found'
    if check_type not in ('in', 'out'):
        return False, 'invalid_check_type'

    record = CheckinRecord(
        member_id=member.id, member_name=member.name,
        employee_id=member.employee_id, check_type=check_type,
        check_time=datetime.datetime.now(), confidence=1.0,
        camera_id=0, source='manual_admin',
    )
    db.session.add(record)
    db.session.flush()

    from models import write_operation_log
    write_operation_log(
        action='MANUAL_CHECKIN', target_type='checkin',
        target_id=record.id, target_name=member.name,
        detail=f'管理员 {admin_name} 为 {member.name} 手工补录 {check_type}'
    )
    db.session.commit()
    app_logger.info(f'Manual checkin: {member.name} {check_type} by {admin_name}')
    return True, 'manual_checkin_created'


def _create_record(member, event, check_type, reason):
    from models import db, CheckinRecord

    record = CheckinRecord(
        member_id=member.id, member_name=member.name,
        employee_id=member.employee_id, check_type=check_type,
        check_time=datetime.datetime.now(), confidence=event.confidence,
        camera_id=event.camera_id, source='auto',
        recognition_event_id=event.id,
    )
    db.session.add(record)
    db.session.flush()

    event.checkin_created = True

    app_logger.info(f'Auto {check_type}: {member.name} conf={event.confidence:.4f}')
    return True, reason
