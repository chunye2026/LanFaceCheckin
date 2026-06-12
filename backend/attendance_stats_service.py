"""
考勤统计服务 - 本周/本月综合考勤汇总
"""
import datetime
from config import WORKDAY_WEEKDAYS, DASHBOARD_TOP_N, DASHBOARD_MASK_PHONE, DASHBOARD_MASK_EMAIL


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


def get_workdays(start_date, end_date):
    """返回指定区间内的工作日列表"""
    days = []
    cur = start_date
    while cur <= end_date:
        if cur.weekday() in WORKDAY_WEEKDAYS:
            days.append(cur)
        cur += datetime.timedelta(days=1)
    return days


def build_period_summary(start_date, end_date, label_type='date'):
    """统计指定日期区间的出勤情况"""
    from models import Member, CheckinRecord
    from datetime import datetime as dt

    members = Member.query.filter_by(active=True).all()
    workdays = get_workdays(start_date, end_date)
    work_day_count = len(workdays)

    if not members or work_day_count == 0:
        return {
            'work_days': work_day_count,
            'expected_person_days': len(members) * work_day_count,
            'actual_person_days': 0,
            'attendance_rate': 0,
            'absent_person_days': 0,
            'absent_members': 0,
            'trend': [{'date': d.strftime('%Y-%m-%d'), 'label': _weekday_label(d), 'attended': 0, 'absent': len(members)} for d in workdays],
            'ranking': [],
        }

    # 统计每个成员每天的考勤
    today = dt.now().date()
    ranking_data = {}
    trend_data = {d: {'attended': 0, 'absent': 0} for d in workdays}

    for m in members:
        recs = CheckinRecord.query.filter(
            CheckinRecord.member_id == m.id,
            CheckinRecord.check_time >= start_date,
            CheckinRecord.check_time <= end_date + datetime.timedelta(days=1)
        ).all()

        attended_days = set()
        for r in recs:
            if r.check_time:
                d = r.check_time.date() if hasattr(r.check_time, 'date') else r.check_time
                if hasattr(d, 'date'): d = d.date()
                attended_days.add(d)

        last_check = max((r.check_time for r in recs if r.check_time), default=None)

        rank_data = {
            'member_id': m.id, 'name': m.name, 'employee_id': m.employee_id,
            'department': m.department or '', 'attended_days': 0,
            'absent_days': work_day_count, 'work_days': work_day_count,
            'last_check_time': last_check.isoformat() if last_check else None,
        }

        for wd in workdays:
            if wd in attended_days:
                rank_data['attended_days'] += 1
                rank_data['absent_days'] -= 1
                if wd <= today:
                    trend_data[wd]['attended'] += 1

        # 只有已过去的日期才算缺席
        actual_absent = 0
        for wd in workdays:
            if wd <= today and wd not in attended_days:
                actual_absent += 1
                trend_data[wd]['absent'] += 1
        rank_data['absent_days'] = actual_absent

        ranking_data[m.id] = rank_data

    # 排行榜排序
    ranking = sorted(ranking_data.values(), key=lambda x: (
        -x['absent_days'],
        x['attended_days'],
        0 if x['last_check_time'] else -1,
        x['last_check_time'] or '0000',
        x['name']
    ))[:DASHBOARD_TOP_N]

    # 统计数据
    total_expected = len(members) * work_day_count
    total_attended = sum(r['attended_days'] for r in ranking_data.values())
    total_absent = total_expected - total_attended
    absent_count = sum(1 for r in ranking_data.values() if r['absent_days'] > 0)
    rate = round(total_attended / total_expected * 100, 1) if total_expected > 0 else 0

    trend = []
    for wd in workdays:
        if wd <= today:
            trend.append({
                'date': wd.strftime('%Y-%m-%d'),
                'label': _weekday_label(wd),
                'attended': trend_data[wd]['attended'],
                'absent': trend_data[wd]['absent'],
            })

    return {
        'work_days': work_day_count,
        'expected_person_days': total_expected,
        'actual_person_days': total_attended,
        'attendance_rate': rate,
        'absent_person_days': total_absent,
        'absent_members': absent_count,
        'trend': trend,
        'ranking': ranking,
    }


def get_dashboard_attendance_summary():
    """返回本周和本月综合考勤统计"""
    from datetime import datetime as dt

    now = dt.now()
    today = now.date()

    # 本周: 周一到今天
    monday = today - datetime.timedelta(days=today.weekday())
    week_summary = build_period_summary(
        datetime.datetime.combine(monday, dt.min.time()),
        datetime.datetime.combine(today, dt.max.time()),
    )

    # 本月: 1日到今天
    month_start = today.replace(day=1)
    month_summary = build_period_summary(
        datetime.datetime.combine(month_start, dt.min.time()),
        datetime.datetime.combine(today, dt.max.time()),
    )

    return {'week': week_summary, 'month': month_summary}


def _weekday_label(d):
    labels = ['一', '二', '三', '四', '五', '六', '日']
    return '周' + labels[d.weekday()]
