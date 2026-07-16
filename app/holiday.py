"""法定节假日模块

从 app/holiday/ 目录加载年度节假日配置（格式：holiday-cn 标准）。
文件命名：{年份}.json，如 2026.json、2027.json
"""

import json
import os
import sys
from datetime import date, timedelta

def _get_holiday_dirs():
    """获取节假日目录列表（优先找 exe 同级的 holiday/，再找打包内的）"""
    dirs = []
    # exe 模式：优先读 exe 同级的 holiday/
    if getattr(sys, "frozen", False):
        external = os.path.join(os.path.dirname(sys.executable), "holiday")
        if os.path.isdir(external):
            dirs.append(external)
    # 源码模式 / 打包内 fallback
    bundled = os.path.join(os.path.dirname(__file__), "holiday")
    if os.path.isdir(bundled):
        dirs.append(bundled)
    return dirs
_cache = None


def _load_all():
    """扫描 holiday 目录，加载所有年份的节假日
    返回: { "2026-01-01": {"name": "元旦", "is_off_day": True} }
    """
    result = {}
    holiday_dirs = _get_holiday_dirs()

    for holiday_dir in holiday_dirs:
        for fname in os.listdir(holiday_dir):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(holiday_dir, fname)
        try:
            with open(fpath, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        days = data.get("days", []) if isinstance(data, dict) else data
        for entry in days:
            if isinstance(entry, dict):
                name = entry.get("name", "")
                day_str = entry.get("date", "")
                is_off = entry.get("isOffDay", True)
                if day_str and name:
                    result[day_str] = {"name": name, "is_off_day": is_off}
    return result


def _get_cache():
    global _cache
    if _cache is None:
        _cache = _load_all()
    return _cache


def get_holiday_for(date_obj):
    """获取某天的节日名称，非节日返回 None"""
    info = _get_cache().get(date_obj.isoformat())
    return info["name"] if info else None


def get_holiday_info(date_obj):
    """获取某天的完整节日信息
    返回: {"name": str, "is_off_day": bool} 或 None
    """
    return _get_cache().get(date_obj.isoformat())


def reload():
    """重新加载（修改了 holiday 目录下的文件后调用）"""
    global _cache
    _cache = None
