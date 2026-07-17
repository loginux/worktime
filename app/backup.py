"""数据库备份模块

- 启动时备份
- 运行中每周六 03:00 自动备份
- 最多保留 6 个备份版本
- 备份文件存放在数据库同级目录
"""

import os
import shutil
import threading
import time
from datetime import datetime

BACKUP_PREFIX = "woktime.db.backup-"
MAX_BACKUPS = 6

# 调试模式下 reloader 会加载两次，用此标记避免重复启动备份
_startup_backup_done = False


def _backup_dir(db_path):
    """备份目录 = 数据库所在目录"""
    return os.path.dirname(db_path)


def _backup_path(db_path, timestamp=None):
    """生成备份文件路径，格式: woktime.db.backup-YYYYMMDD-HHMMSS"""
    ts = timestamp or datetime.now().strftime("%Y%m%d-%H%M%S")
    return os.path.join(_backup_dir(db_path), f"{BACKUP_PREFIX}{ts}")


def do_backup(db_path):
    """执行一次备份，返回备份文件路径；失败返回 None"""
    try:
        if not os.path.isfile(db_path):
            return None
        dest = _backup_path(db_path)
        shutil.copy2(db_path, dest)
        _cleanup(db_path)
        return dest
    except OSError:
        return None


def do_startup_backup(db_path):
    """启动时备份（带去重，防止 debug reloader 双次触发）"""
    global _startup_backup_done
    if _startup_backup_done:
        return None
    _startup_backup_done = True
    return do_backup(db_path)


def _cleanup(db_path):
    """清理多余备份，只保留最新的 MAX_BACKUPS 个"""
    backup_dir = _backup_dir(db_path)
    try:
        files = [
            os.path.join(backup_dir, f)
            for f in os.listdir(backup_dir)
            if f.startswith(BACKUP_PREFIX)
        ]
    except OSError:
        return

    # 按修改时间降序排列，保留最新的
    files.sort(key=os.path.getmtime, reverse=True)
    for old in files[MAX_BACKUPS:]:
        try:
            os.remove(old)
        except OSError:
            pass


def _weekly_scheduler(db_path, interval=3600):
    """后台线程：每小时检查一次，周六 03:00 执行备份"""
    while True:
        now = datetime.now()
        # 周六 weekday() == 5，凌晨 3 点
        if now.weekday() == 5 and now.hour == 3 and now.minute == 0:
            do_backup(db_path)
            # 执行后睡 61 秒，避免同一分钟重复触发
            time.sleep(61)
        else:
            time.sleep(interval)


def start_weekly_backup(app):
    """启动每周六 03:00 自动备份（守护线程）"""
    db_path = app.config["DATABASE"]
    thread = threading.Thread(
        target=_weekly_scheduler,
        args=(db_path,),
        daemon=True,
        name="db-backup-weekly",
    )
    thread.start()
