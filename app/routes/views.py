import calendar
from datetime import date, timedelta
import json
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from app.models import (
    get_time_entries_by_date,
    get_time_entries_by_date_range,
    get_project_task_summary,
    get_daily_summary,
    get_projects_by_user,
)
from app.holiday import get_holiday_for

views_bp = Blueprint("views", __name__, url_prefix="/views")


def _format_minutes(minutes):
    """将分钟数格式化为 X小时X分钟"""
    hours = minutes // 60
    mins = minutes % 60
    if hours > 0 and mins > 0:
        return f"{hours}小时{mins}分钟"
    elif hours > 0:
        return f"{hours}小时"
    else:
        return f"{mins}分钟"


def _shift_month(d, delta):
    """将日期向前/向后推一个月，自动处理月末边界"""
    total_months = d.year * 12 + d.month - 1 + delta
    year = total_months // 12
    month = total_months % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    day = min(d.day, last_day)
    return date(year, month, day)


@views_bp.route("/day")
@login_required
def day_view():
    """日视图：展示选定日期的明细"""
    date_str = request.args.get("date", date.today().isoformat())
    try:
        view_date = date.fromisoformat(date_str)
    except ValueError:
        view_date = date.today()

    entries = get_time_entries_by_date(current_user.id, view_date.isoformat())
    summary = get_project_task_summary(current_user.id, view_date.isoformat())

    total_minutes = sum(e["minutes"] for e in entries)
    prev_date = (view_date - timedelta(days=1)).isoformat()
    next_date = (view_date + timedelta(days=1)).isoformat()

    # ── 饼图数据 ─────────────────────────────────────────────
    # 按项目汇总
    proj_map = {}
    for s in summary:
        pname = s["project_name"]
        proj_map[pname] = proj_map.get(pname, 0) + s["total_minutes"]
    chart_proj_labels = json.dumps(list(proj_map.keys()), ensure_ascii=False)
    chart_proj_data = json.dumps(list(proj_map.values()))

    # 按项目-任务汇总
    chart_task_labels = json.dumps(
        [f"{s['project_name']}-{s['task_name']}" for s in summary], ensure_ascii=False
    )
    chart_task_data = json.dumps([s["total_minutes"] for s in summary])

    return render_template(
        "views/day.html",
        view_date=view_date,
        entries=entries,
        summary=summary,
        total_minutes=total_minutes,
        format_minutes=_format_minutes,
        today=date.today(),
        prev_date=prev_date,
        next_date=next_date,
        chart_proj_labels=chart_proj_labels,
        chart_proj_data=chart_proj_data,
        chart_task_labels=chart_task_labels,
        chart_task_data=chart_task_data,
    )


@views_bp.route("/week")
@login_required
def week_view():
    """周视图：展示选定周的每日汇总柱状图"""
    today = date.today()
    date_str = request.args.get("date", today.isoformat())

    try:
        base_date = date.fromisoformat(date_str)
    except ValueError:
        base_date = today

    # 计算周一
    monday = base_date - timedelta(days=base_date.weekday())
    sunday = monday + timedelta(days=6)

    entries = get_time_entries_by_date_range(current_user.id, monday.isoformat(), sunday.isoformat())

    # 按日汇总
    daily_data = {}
    for i in range(7):
        d = monday + timedelta(days=i)
        daily_data[d.isoformat()] = {"date": d, "total_minutes": 0, "label": f"周{'一二三四五六日'[i]}"}

    for e in entries:
        day_key = str(e["entry_date"])
        if day_key in daily_data:
            daily_data[day_key]["total_minutes"] += e["minutes"]

    week_days = list(daily_data.values())
    week_total = sum(d["total_minutes"] for d in week_days)

    return render_template(
        "views/week.html",
        monday=monday,
        sunday=sunday,
        week_days=week_days,
        week_total=week_total,
        format_minutes=_format_minutes,
        today=today,
        prev_week=(monday - timedelta(days=7)).isoformat(),
        next_week=(monday + timedelta(days=7)).isoformat(),
    )


@views_bp.route("/month")
@login_required
def month_view():
    """月视图：从起始日期起展示一个月（下个月同日 -1天）"""
    today = date.today()
    # 默认从当月1号开始
    default_start = today.replace(day=1).isoformat()
    date_str = request.args.get("date", default_start)

    try:
        base_date = date.fromisoformat(date_str)
    except ValueError:
        base_date = today

    # 起始日期 → 下个月同日 - 1天（例如 6/5→7/4, 1/31→2/28）
    next_month = _shift_month(base_date, 1)
    first_day = base_date
    last_day = next_month - timedelta(days=1)

    entries = get_time_entries_by_date_range(current_user.id, first_day.isoformat(), last_day.isoformat())

    # 按日汇总：记录总分钟数和涉及的项目名称
    daily_map = {}
    for e in entries:
        day_key = str(e["entry_date"])
        if day_key not in daily_map:
            daily_map[day_key] = {"minutes": 0, "projects": []}
        daily_map[day_key]["minutes"] += e["minutes"]
        pname = e["project_name"]
        if pname not in daily_map[day_key]["projects"]:
            daily_map[day_key]["projects"].append(pname)

    # 构建网格（按周排列，从 first_day 的星期几开始）
    start_weekday = first_day.weekday()
    calendar_days = []
    current_day = first_day
    for row in range(6):
        week = []
        for col in range(7):
            if current_day > last_day:
                week.append(None)
            elif row == 0 and col < start_weekday:
                week.append(None)
            else:
                info = daily_map.get(current_day.isoformat(), {"minutes": 0, "projects": []})
                holiday_name = get_holiday_for(current_day)
                week.append({
                    "day": current_day.day,
                    "date": current_day,
                    "total_minutes": info["minutes"],
                    "projects": info["projects"],
                    "is_today": current_day == today,
                    "holiday": holiday_name,
                })
                current_day += timedelta(days=1)
        if week and any(d is not None for d in week):
            calendar_days.append(week)
        if current_day > last_day:
            break

    month_total = sum(v["minutes"] for v in daily_map.values())

    prev_start = _shift_month(first_day, -1).isoformat()
    next_start = _shift_month(first_day, 1).isoformat()

    return render_template(
        "views/month.html",
        year=first_day.year,
        month=first_day.month,
        first_day=first_day,
        last_day=last_day,
        calendar_days=calendar_days,
        month_total=month_total,
        format_minutes=_format_minutes,
        today=today,
        prev_month=prev_start,
        next_month=next_start,
    )
