from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from app.forms import TaskForm
from app.models import (
    get_tasks_by_project,
    get_task_by_id,
    get_project_by_id,
    get_default_task,
    get_default_task_global,
    get_default_project,
    create_task,
    update_task,
    soft_delete_task,
    count_entries_by_task,
    transfer_entries_to_task,
)

tasks_bp = Blueprint("tasks", __name__, url_prefix="/tasks")


@tasks_bp.route("/")
@login_required
def list_tasks():
    project_id = request.args.get("project_id", type=int)
    if not project_id:
        flash("请选择项目", "error")
        return redirect(url_for("projects.list_projects"))

    proj = get_project_by_id(project_id)
    if not proj or proj["user_id"] != current_user.id:
        flash("项目不存在", "error")
        return redirect(url_for("projects.list_projects"))

    tasks = get_tasks_by_project(project_id)
    return render_template("tasks/list.html", tasks=tasks, proj=proj)


@tasks_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    project_id = request.args.get("project_id", type=int)
    proj = get_project_by_id(project_id)
    if not proj or proj["user_id"] != current_user.id:
        flash("项目不存在", "error")
        return redirect(url_for("projects.list_projects"))

    form = TaskForm()
    if form.validate_on_submit():
        create_task(
            project_id,
            form.name.data.strip(),
            form.description.data.strip() if form.description.data else "",
        )
        flash("任务创建成功", "success")
        return redirect(url_for("tasks.list_tasks", project_id=project_id))

    return render_template("tasks/form.html", form=form, title="创建任务", proj=proj)


@tasks_bp.route("/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
def edit(task_id):
    task = get_task_by_id(task_id)
    if not task:
        flash("任务不存在", "error")
        return redirect(url_for("projects.list_projects"))

    # 验证任务所属项目属于当前用户
    proj = get_project_by_id(task["project_id"])
    if not proj or proj["user_id"] != current_user.id:
        flash("任务不存在", "error")
        return redirect(url_for("projects.list_projects"))

    form = TaskForm()
    if form.validate_on_submit():
        update_task(task_id, form.name.data.strip(), form.description.data.strip() or "")
        flash("任务更新成功", "success")
        return redirect(url_for("tasks.list_tasks", project_id=task["project_id"]))

    form.name.data = task["name"]
    form.description.data = task["description"]
    return render_template("tasks/form.html", form=form, title="编辑任务", proj=proj, task=task)


@tasks_bp.route("/<int:task_id>/delete", methods=["GET", "POST"])
@login_required
def delete(task_id):
    task = get_task_by_id(task_id)
    if not task:
        return jsonify({"error": "任务不存在"}), 404
    if task["is_default"]:
        return jsonify({"error": "不能删除默认任务"}), 400

    proj = get_project_by_id(task["project_id"])
    if not proj or proj["user_id"] != current_user.id:
        return jsonify({"error": "任务不存在"}), 404

    # GET 请求：仅返回工时记录数（供前端弹窗提示）
    if request.method == "GET":
        entry_count = count_entries_by_task(task_id)
        return jsonify({"entry_count": entry_count})

    # POST 请求：执行删除
    entry_count = count_entries_by_task(task_id)

    if entry_count > 0:
        # 转移到同项目默认任务
        default_task = get_default_task(task["project_id"])
        if not default_task:
            # 兜底：转移到全局默认项目的默认任务
            default_task = get_default_task_global(current_user.id)
        if default_task:
            transfer_entries_to_task(task_id, default_task["id"])

    # 软删除任务
    soft_delete_task(task_id)

    flash("任务已删除", "success")
    return jsonify({"ok": True, "entry_count": entry_count})
