from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.forms import UserCreateForm
from app.models import get_all_users, create_user, get_user_by_username

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/")
def index():
    """首页：已登录则跳转日视图，否则跳转用户选择"""
    if current_user.is_authenticated:
        return redirect(url_for("views.day_view"))
    return redirect(url_for("auth.user_select"))


@auth_bp.route("/user_select", methods=["GET", "POST"])
def user_select():
    form = UserCreateForm()
    users = get_all_users()

    if form.validate_on_submit():
        username = form.username.data.strip()
        if not username:
            flash("用户名不能为空", "error")
        elif get_user_by_username(username):
            flash("用户名已存在", "error")
        else:
            user_id = create_user(username)
            from app.models import get_user_by_id
            user = get_user_by_id(user_id)
            login_user(user)
            flash(f"用户 {username} 创建成功", "success")
            return redirect(url_for("views.day_view"))

    return render_template("auth/user_select.html", users=users, form=form)


@auth_bp.route("/login/<int:user_id>")
def login_as(user_id):
    """直接以某用户身份登录（无密码）"""
    from app.models import get_user_by_id

    user = get_user_by_id(user_id)
    if user is None:
        flash("用户不存在", "error")
        return redirect(url_for("auth.user_select"))
    login_user(user)
    flash(f"已切换至用户：{user.username}", "success")
    return redirect(url_for("views.day_view"))


@auth_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.user_select"))
