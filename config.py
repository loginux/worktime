import os
import sys


def _get_data_dir():
    """获取数据存储目录（exe 模式下放在 exe 同目录，源码模式在项目根目录）"""
    if getattr(sys, "frozen", False):
        # PyInstaller 打包的 exe：数据库放在 exe 所在目录
        return os.path.dirname(sys.executable)
    # 源码开发模式：放在项目根目录
    return os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    DATABASE = os.path.join(_get_data_dir(), "instance", "woktime.db")
    WTF_CSRF_ENABLED = True
