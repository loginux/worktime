from datetime import date, datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from app.forms import TimeEntryForm
from app.models import (
    get_time_entry_by_id,
    create_time_entry,
    update_time_entry,
    delete_time_entry,
    get_projects_by_user,
    get_tasks_by_project,
    get_project_by_id,
    get_task_by_id,
)


def _parse_time(time_str):
    """解析 HH:MM 格式字符串，返回 (小时, 分钟)"""
    try:
        parts = time_str.strip().split(":")
        return int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return None


def _calc_minutes(start_time, end_time):
    """计算两个时间之间的分钟数"""
    start = _parse_time(start_time)
    end = _parse_time(end_time)
    if start is None or end is None:
        return None
    return (end[0] * 60 + end[1]) - (start[0] * 60 + start[1])

time_entries_bp = Blueprint("time_entries", __name__, url_prefix="/time_entries")


def _get_project_choices(user_id):
    """获取当前用户的项目列表，格式为 SelectField 的 choices"""
    projects = get_projects_by_user(user_id)
    return [(p["id"], p["name"]) for p in projects]


def _get_task_choices(project_id):
    """获取某项目下的任务列表"""
    tasks = get_tasks_by_project(project_id)
    return [(t["id"], t["name"]) for t in tasks]


@time_entries_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    form = TimeEntryForm()
    form.project_id.choices = _get_project_choices(current_user.id)

    # 根据提交的项目 ID 加载任务下拉选项
    selected_project_id = form.project_id.data or request.args.get("project_id", type=int)
    if selected_project_id:
        form.task_id.choices = _get_task_choices(selected_project_id)
    else:
        form.task_id.choices = []

    # 如果指定了日期参数，预填（转为 date 对象）
    date_param = request.args.get("date", "")
    if date_param and not form.is_submitted():
        try:
            form.entry_date.data = date.fromisoformat(date_param)
        except ValueError:
            form.entry_date.data = date.today()

    if form.validate_on_submit():
        entry_date = form.entry_date.data
        if entry_date > date.today():
            flash("日期不可晚于今天", "error")
            return render_template("time_entries/form.html", form=form, title="录入工时")

        # 计算分钟数：优先用表单提交的分钟数，否则从起止时间计算
        minutes = form.minutes.data
        if not minutes:
            calc = _calc_minutes(form.start_time.data, form.end_time.data)
            if calc and calc > 0:
                minutes = calc
            else:
                flash("请填写工时分钟数，或确保结束时间晚于开始时间", "error")
                return render_template("time_entries/form.html", form=form, title="录入工时")

        # 验证项目和任务属于当前用户
        proj = get_project_by_id(form.project_id.data)
        if not proj or proj["user_id"] != current_user.id:
            flash("项目不存在", "error")
            return render_template("time_entries/form.html", form=form, title="录入工时")

        create_time_entry(
            current_user.id,
            form.project_id.data,
            form.task_id.data,
            entry_date,
            minutes,
            form.content.data or "",
        )
        flash("工时记录成功", "success")
        return redirect(url_for("views.day_view", date=entry_date.isoformat()))

    return render_template("time_entries/form.html", form=form, title="录入工时")


@time_entries_bp.route("/<int:entry_id>/edit", methods=["GET", "POST"])
@login_required
def edit(entry_id):
    entry = get_time_entry_by_id(entry_id)
    if not entry or entry["user_id"] != current_user.id:
        flash("记录不存在", "error")
        return redirect(url_for("views.day_view"))

    form = TimeEntryForm()
    form.project_id.choices = _get_project_choices(current_user.id)

    # 根据提交或已有项目 ID 加载任务下拉选项
    selected_project_id = form.project_id.data or entry["project_id"]
    form.task_id.choices = _get_task_choices(selected_project_id)

    if form.validate_on_submit():
        entry_date = form.entry_date.data
        if entry_date > date.today():
            flash("日期不可晚于今天", "error")
            return render_template("time_entries/form.html", form=form, title="编辑工时", entry=entry)

        # 计算分钟数
        minutes = form.minutes.data
        if not minutes:
            calc = _calc_minutes(form.start_time.data, form.end_time.data)
            if calc and calc > 0:
                minutes = calc
            else:
                flash("请填写工时分钟数，或确保结束时间晚于开始时间", "error")
                return render_template("time_entries/form.html", form=form, title="编辑工时", entry=entry)

        update_time_entry(
            entry_id,
            form.project_id.data,
            form.task_id.data,
            entry_date,
            minutes,
            form.content.data or "",
        )
        flash("工时记录已更新", "success")
        return redirect(url_for("views.day_view", date=entry_date.isoformat()))

    # 预填表单
    form.entry_date.data = entry["entry_date"]
    form.project_id.data = entry["project_id"]
    form.task_id.choices = _get_task_choices(entry["project_id"])
    form.task_id.data = entry["task_id"]
    form.minutes.data = entry["minutes"]
    form.content.data = entry["content"]
    return render_template("time_entries/form.html", form=form, title="编辑工时", entry=entry)


@time_entries_bp.route("/<int:entry_id>/delete", methods=["POST"])
@login_required
def delete(entry_id):
    entry = get_time_entry_by_id(entry_id)
    if not entry or entry["user_id"] != current_user.id:
        return jsonify({"error": "记录不存在"}), 404

    delete_time_entry(entry_id)
    flash("工时记录已删除", "success")
    return jsonify({"ok": True})


@time_entries_bp.route("/tasks_for_project")
@login_required
def tasks_for_project():
    """获取某项目下的任务列表（API，用于前端动态加载）"""
    project_id = request.args.get("project_id", type=int)
    if not project_id:
        return jsonify([])

    tasks = get_tasks_by_project(project_id)
    return jsonify([{"id": t["id"], "name": t["name"]} for t in tasks])
