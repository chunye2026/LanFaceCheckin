"""
数据大屏考勤统计服务
统计本周、本月出勤情况和未考勤排行
"""

from datetime import datetime, date, timedelta, time
from models import Member, CheckinRecord
from config import WORKDAY_WEEKDAYS, DASHBOARD_TOP_N, DASHBOARD_MASK_PHONE, DASHBOARD_MASK_EMAIL


def get_dashboard_attendance_summary():
    """返回本周、本月综合考勤统计"""
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    return {
        "week": build_period_summary(week_start, today, label_type="weekday"),
        "month": build_period_summary(month_start, today, label_type="date"),
    }


def build_period_summary(start_date, end_date, label_type="date"):
    """统计指定日期区间内的考勤情况"""
    start_date = _to_date(start_date)
    end_date = _to_date(end_date)

    workdays = get_workdays(start_date, end_date)
    workday_set = set(workdays)

    members = Member.query.filter_by(active=True).order_by(Member.employee_id.asc()).all()

    if not members or not workdays:
        return {
            "work_days": len(workdays),
            "expected_person_days": 0,
            "actual_person_days": 0,
            "attendance_rate": 0,
            "absent_person_days": 0,
            "absent_members": 0,
            "trend": [],
            "ranking": [],
        }

    member_ids = [m.id for m in members]

    # 关键: CheckinRecord.check_time 是 datetime, 查询边界也必须用 datetime
    start_dt = datetime.combine(workdays[0], time.min)
    end_dt = datetime.combine(workdays[-1], time.max)

    records = (
        CheckinRecord.query
        .filter(CheckinRecord.member_id.in_(member_ids))
        .filter(CheckinRecord.check_time >= start_dt)
        .filter(CheckinRecord.check_time <= end_dt)
        .all()
    )

    attended_days_by_member = {m.id: set() for m in members}
    last_check_time_by_member = {}

    for record in records:
        if not record.check_time:
            continue
        check_day = record.check_time.date()
        if check_day not in workday_set:
            continue
        attended_days_by_member.setdefault(record.member_id, set()).add(check_day)

        old_last = last_check_time_by_member.get(record.member_id)
        if old_last is None or record.check_time > old_last:
            last_check_time_by_member[record.member_id] = record.check_time

    expected_person_days = len(workdays) * len(members)
    actual_person_days = sum(len(days) for days in attended_days_by_member.values())
    absent_person_days = expected_person_days - actual_person_days

    attendance_rate = 0
    if expected_person_days > 0:
        attendance_rate = round(actual_person_days * 100 / expected_person_days, 2)

    trend = []
    for d in workdays:
        attended = sum(1 for m in members if d in attended_days_by_member.get(m.id, set()))
        absent = len(members) - attended
        trend.append({
            "date": d.isoformat(),
            "label": _format_label(d, label_type),
            "attended": attended,
            "absent": absent,
        })

    ranking = []
    absent_members = 0

    for m in members:
        attended_days = len(attended_days_by_member.get(m.id, set()))
        absent_days = len(workdays) - attended_days
        last_check_time = last_check_time_by_member.get(m.id)

        if absent_days > 0:
            absent_members += 1

        ranking.append({
            "member_id": m.id,
            "name": m.name,
            "employee_id": m.employee_id,
            "department": m.department or "",
            "absent_days": absent_days,
            "attended_days": attended_days,
            "work_days": len(workdays),
            "last_check_time": last_check_time.isoformat() if last_check_time else "",
        })

    ranking.sort(key=lambda x: (
        -x["absent_days"],
        x["attended_days"],
        0 if not x["last_check_time"] else 1,
        x["last_check_time"] or "",
        x["employee_id"] or "",
        x["name"] or "",
    ))

    top_n = DASHBOARD_TOP_N if DASHBOARD_TOP_N > 0 else 10

    return {
        "work_days": len(workdays),
        "expected_person_days": expected_person_days,
        "actual_person_days": actual_person_days,
        "attendance_rate": attendance_rate,
        "absent_person_days": absent_person_days,
        "absent_members": absent_members,
        "trend": trend,
        "ranking": ranking[:top_n],
    }


def get_workdays(start_date, end_date):
    """根据 WORKDAY_WEEKDAYS 返回工作日列表 (0=周一, 6=周日)"""
    start_date = _to_date(start_date)
    end_date = _to_date(end_date)
    if start_date > end_date:
        return []
    days = []
    current = start_date
    while current <= end_date:
        if current.weekday() in WORKDAY_WEEKDAYS:
            days.append(current)
        current += timedelta(days=1)
    return days


def _to_date(value):
    """统一转换为 datetime.date"""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value[:10]).date()
    raise TypeError(f"Unsupported date value: {value!r}")


def _format_label(d, label_type="date"):
    if label_type == "weekday":
        labels = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        return labels[d.weekday()]
    return f"{d.month}-{d.day}"


def mask_phone(phone):
    if not phone or not DASHBOARD_MASK_PHONE: return phone or ''
    s = str(phone)
    return s[:3] + '****' + s[-4:] if len(s) >= 7 else s[:3] + '****'


def mask_email(email):
    if not email or not DASHBOARD_MASK_EMAIL: return email or ''
    s = str(email)
    if '@' in s:
        local, domain = s.split('@', 1)
        return local[:2] + '***@' + domain
    return s[:2] + '***'
