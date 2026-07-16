"""从 Clockify PDF 导出导入工时记录到 WokTime

用法:
    python import_clockify.py [pdf文件...]
    python import_clockify.py                          # 导入 data/ 下所有 PDF
    python import_clockify.py data/xxx.pdf             # 导入指定文件

PDF 格式 (每记录6行):
    日期        2026/04/24
    备注        修改后白盒
    项目-任务   融合RIOM - 白盒测试代码修改
    时长        11:06:43
    起止时间    08:43:11 - 19:54:14
    用户名      guangqiang99
"""

import re
import sys
import os
import glob

# 将项目根目录加入 path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db import init_db, query, execute
from flask import Flask
from config import Config


def parse_pdf(filepath):
    """解析 PDF 返回记录列表"""
    try:
        import pymupdf
    except ImportError:
        print("请先安装 pymupdf: pip install pymupdf")
        sys.exit(1)

    doc = pymupdf.open(filepath)
    records = []

    for page in doc:
        text = page.get_text("text")
        lines = [l.strip() for l in text.split("\n") if l.strip()]

        i = 0
        while i < len(lines):
            # 跳过页眉/页脚
            if lines[i] in ("Detailed report", "Total:", "Date", "Description", "Duration", "User"):
                i += 1
                continue
            if "Created with Clockify" in lines[i]:
                i += 1
                continue
            if re.match(r"\d{4}/\d{2}/\d{2} - \d{4}/\d{2}/\d{2}", lines[i]):
                i += 1
                continue
            if re.match(r"\d+:\d{2}:\d{2}", lines[i]) and "Total" in text and i < 3:
                i += 1
                continue

            # 检查是否是日期行（记录开始）
            if re.match(r"\d{4}/\d{2}/\d{2}", lines[i]):
                date_str = lines[i]

                # 后5行: 备注, 项目-任务, 时长, 起止时间, 用户名
                if i + 5 >= len(lines):
                    break

                desc = lines[i + 1]
                proj_task = lines[i + 2]
                duration_str = lines[i + 3]
                time_range = lines[i + 4]
                username = lines[i + 5]

                # 跳过异常用户名（页码、页脚等误解析）
                if not re.match(r'^[a-zA-Z0-9_\u4e00-\u9fff]+$', username):
                    i += 1
                    continue

                # 解析项目-任务
                pt = proj_task.split(" - ", 1)
                project = pt[0].strip() if len(pt) > 0 else ""
                task = pt[1].strip() if len(pt) > 1 else ""

                # 解析时长 HH:MM:SS → 分钟
                minutes = _parse_duration(duration_str)

                # 解析起止时间
                start_time, end_time = "", ""
                if " - " in time_range:
                    parts = time_range.split(" - ")
                    start_time = parts[0].strip()
                    end_time = parts[1].strip()

                records.append({
                    "date": date_str.replace("/", "-"),
                    "description": desc,
                    "project": project,
                    "task": task,
                    "minutes": minutes,
                    "start_time": start_time,
                    "end_time": end_time,
                    "username": username,
                })

                i += 6
            else:
                i += 1

    doc.close()
    return records


def _parse_duration(s):
    """HH:MM:SS → 分钟数"""
    m = re.match(r"(\d+):(\d{2}):(\d{2})", s)
    if m:
        h, mm, sec = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return h * 60 + mm + (1 if sec >= 30 else 0)  # 秒数四舍五入
    return 0


def import_records(records):
    """将记录导入数据库"""
    # 缓存已创建的用户/项目/任务，避免重复查询
    user_cache = {}
    proj_cache = {}
    task_cache = {}
    imported = 0

    for rec in records:
        username = rec["username"]
        project_name = rec["project"]
        task_name = rec["task"]
        desc = rec["description"]

        # --- 用户 ---
        if username not in user_cache:
            user = query("SELECT * FROM users WHERE username = ?", (username,), one=True)
            if not user:
                uid = execute("INSERT INTO users (username) VALUES (?)", (username,))
                # 创建默认项目+默认任务
                default_proj_id = execute(
                    "INSERT INTO projects (user_id, name, description, is_default) VALUES (?, '默认项目', '', 1)",
                    (uid,),
                )
                execute(
                    "INSERT INTO tasks (project_id, name, description, is_default) VALUES (?, '默认任务', '', 1)",
                    (default_proj_id,),
                )
            else:
                uid = user["id"]
            user_cache[username] = uid
        uid = user_cache[username]

        # --- 项目（为空则用默认项目） ---
        if not project_name:
            proj = query(
                "SELECT * FROM projects WHERE user_id = ? AND is_default = 1 AND is_deleted = 0",
                (uid,),
                one=True,
            )
            if proj:
                pid = proj["id"]
            else:
                pid = execute(
                    "INSERT INTO projects (user_id, name, description, is_default) VALUES (?, '默认项目', '', 1)",
                    (uid,),
                )
                execute(
                    "INSERT INTO tasks (project_id, name, description, is_default) VALUES (?, '默认任务', '', 1)",
                    (pid,),
                )
            proj_cache[(uid, "")] = pid
        else:
            proj_key = (uid, project_name)
            if proj_key not in proj_cache:
                proj = query(
                    "SELECT * FROM projects WHERE user_id = ? AND name = ? AND is_deleted = 0",
                    (uid, project_name),
                    one=True,
                )
                if not proj:
                    pid = execute(
                        "INSERT INTO projects (user_id, name, description) VALUES (?, ?, '')",
                        (uid, project_name),
                    )
                    execute(
                        "INSERT INTO tasks (project_id, name, description, is_default) VALUES (?, '默认任务', '', 1)",
                        (pid,),
                    )
                else:
                    pid = proj["id"]
                proj_cache[proj_key] = pid
            pid = proj_cache[proj_key]

        # --- 任务（为空则用该项目的默认任务） ---
        if not task_name:
            t = query(
                "SELECT * FROM tasks WHERE project_id = ? AND is_default = 1 AND is_deleted = 0",
                (pid,),
                one=True,
            )
            tid = t["id"] if t else execute(
                "INSERT INTO tasks (project_id, name, description, is_default) VALUES (?, '默认任务', '', 1)",
                (pid,),
            )
        else:
            task_key = (pid, task_name)
            if task_key not in task_cache:
                t = query(
                    "SELECT * FROM tasks WHERE project_id = ? AND name = ? AND is_deleted = 0",
                    (pid, task_name),
                    one=True,
                )
                if not t:
                    tid = execute(
                        "INSERT INTO tasks (project_id, name, description) VALUES (?, ?, ?)",
                        (pid, task_name, desc),
                    )
                else:
                    tid = t["id"]
                    if desc and desc != "(Without Description)" and not t["description"]:
                        execute("UPDATE tasks SET description = ? WHERE id = ?", (desc, tid))
                task_cache[task_key] = tid
            tid = task_cache[task_key]

        # --- 工时记录 ---
        # 检查是否已存在（避免重复导入）
        existing = query(
            """SELECT id FROM time_entries
               WHERE user_id = ? AND project_id = ? AND task_id = ?
               AND entry_date = ? AND minutes = ?""",
            (uid, pid, tid, rec["date"], rec["minutes"]),
            one=True,
        )
        if not existing:
            execute(
                """INSERT INTO time_entries (user_id, project_id, task_id, entry_date, minutes)
                   VALUES (?, ?, ?, ?, ?)""",
                (uid, pid, tid, rec["date"], rec["minutes"]),
            )
            imported += 1

    return imported


def main():
    # 获取 PDF 文件列表
    if len(sys.argv) > 1:
        pdf_files = sys.argv[1:]
    else:
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        pdf_files = glob.glob(os.path.join(data_dir, "*.pdf"))

    if not pdf_files:
        print("未找到 PDF 文件。用法: python import_clockify.py <pdf文件>")
        sys.exit(1)

    # 初始化 Flask app 和数据库
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    with app.app_context():
        init_db(app)

        total_records = 0
        total_imported = 0

        for fpath in sorted(pdf_files):
            print(f"解析: {os.path.basename(fpath)} ...")
            records = parse_pdf(fpath)
            print(f"  找到 {len(records)} 条记录")
            if records:
                imported = import_records(records)
                total_records += len(records)
                total_imported += imported
                print(f"  导入 {imported} 条 (跳过 {len(records) - imported} 条重复)")

        print(f"\n完成! 共导入 {total_imported} 条工时记录 / {total_records} 条总记录")


if __name__ == "__main__":
    main()
