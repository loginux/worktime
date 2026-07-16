from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from app.forms import ProjectForm
from app.models import (
    get_projects_by_user,
    get_project_by_id,
    get_default_project,
    create_project,
    update_project,
    soft_delete_project,
    get_tasks_by_project_all,
    soft_delete_tasks_by_project,
    transfer_entries_to_default,
    get_default_task,
    get_default_task_global,
)

projects_bp = Blueprint("projects", __name__, url_prefix="/projects")


@projects_bp.route("/")
@login_required
def list_projects():
    projects = get_projects_by_user(current_user.id)
    return render_template("projects/list.html", projects=projects)


@projects_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    form = ProjectForm()
    if form.validate_on_submit():
        proj_id = create_project(
            current_user.id,
            form.name.data.strip(),
            form.description.data.strip() if form.description.data else "",
        )
        flash("项目创建成功", "success")
        return redirect(url_for("projects.list_projects"))
    return render_template("projects/form.html", form=form, title="创建项目")


@projects_bp.route("/<int:project_id>/edit", methods=["GET", "POST"])
@login_required
def edit(project_id):
    proj = get_project_by_id(project_id)
    if not proj or proj["user_id"] != current_user.id:
        flash("项目不存在", "error")
        return redirect(url_for("projects.list_projects"))

    form = ProjectForm(obj=proj)
    if form.validate_on_submit():
        update_project(project_id, form.name.data.strip(), form.description.data.strip() or "")
        flash("项目更新成功", "success")
        return redirect(url_for("projects.list_projects"))

    form.name.data = proj["name"]
    form.description.data = proj["description"]
    return render_template("projects/form.html", form=form, title="编辑项目", proj=proj)


@projects_bp.route("/<int:project_id>/delete", methods=["POST"])
@login_required
def delete(project_id):
    proj = get_project_by_id(project_id)
    if not proj or proj["user_id"] != current_user.id:
        return jsonify({"error": "项目不存在"}), 404
    if proj["is_default"]:
        return jsonify({"error": "不能删除默认项目"}), 400

    default_proj = get_default_project(current_user.id)
    default_task = get_default_task(default_proj["id"]) or get_default_task_global(current_user.id)
    if not default_task:
        return jsonify({"error": "系统错误：找不到默认任务"}), 500

    # 转移工时记录到默认项目的默认任务
    transfer_entries_to_default(project_id, default_proj["id"], default_task["id"])

    # 软删除项目下所有任务
    soft_delete_tasks_by_project(project_id)

    # 软删除项目
    soft_delete_project(project_id)

    flash("项目已删除，工时记录已转移", "success")
    return jsonify({"ok": True})
