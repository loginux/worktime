import os
from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import Config

login_manager = LoginManager()
login_manager.login_view = "auth.user_select"
csrf = CSRFProtect()


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    # 确保 instance 目录存在
    os.makedirs(app.instance_path, exist_ok=True)

    # 初始化扩展
    login_manager.init_app(app)
    csrf.init_app(app)

    # 初始化数据库
    from app import db

    db.init_db(app)

    # 注册蓝图
    from app.routes.auth import auth_bp
    from app.routes.projects import projects_bp
    from app.routes.tasks import tasks_bp
    from app.routes.time_entries import time_entries_bp
    from app.routes.views import views_bp
    from app.routes.export import export_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(time_entries_bp)
    app.register_blueprint(views_bp)
    app.register_blueprint(export_bp)

    # Flask-Login user_loader
    from app.models import get_user_by_id

    @login_manager.user_loader
    def load_user(user_id):
        return get_user_by_id(int(user_id))

    return app
