"""法定节假日模块

从 app/holiday/ 目录加载年度节假日配置（格式：holiday-cn 标准）。
文件命名：{年份}.json，如 2026.json、2027.json
"""

import json
import os
from datetime import date, timedelta

_HOLIDAY_DIR = os.path.join(os.path.dirname(__file__), "holiday")
_cache = None


def _load_all():
    """扫描 holiday 目录，加载所有年份的节假日"""
    result = {}  # { "2026-01-01": "元旦" }

    if not os.path.isdir(_HOLIDAY_DIR):
        return result

    for fname in os.listdir(_HOLIDAY_DIR):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(_HOLIDAY_DIR, fname)
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
                # isOffDay=true 才是法定假日，false 是调休上班
                if day_str and name and is_off:
                    result[day_str] = name
            elif isinstance(entry, (list, tuple)) and len(entry) >= 2:
                # 兼容 [date, name] 格式
                result[entry[0]] = entry[1]
    return result


def _get_cache():
    global _cache
    if _cache is None:
        _cache = _load_all()
    return _cache


def get_holiday_for(date_obj):
    """获取某天的节日名称，非节日返回 None"""
    return _get_cache().get(date_obj.isoformat())


def reload():
    """重新加载（修改了 holiday 目录下的文件后调用）"""
    global _cache
    _cache = None
