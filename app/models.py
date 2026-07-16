from flask_login import UserMixin
from app.db import query, execute, execute_many


# ─── User ───────────────────────────────────────────────────────────────────


class User(UserMixin):
    def __init__(self, row):
        self.id = row["id"]
        self.username = row["username"]
        self.created_at = row["created_at"]


def get_user_by_id(user_id):
    row = query("SELECT * FROM users WHERE id = ?", (user_id,), one=True)
    return User(row) if row else None


def get_user_by_username(username):
    row = query(
        "SELECT * FROM users WHERE username = ?", (username,), one=True
    )
    return User(row) if row else None


def get_all_users():
    rows = query("SELECT * FROM users ORDER BY created_at ASC")
    return [User(r) for r in rows]


def create_user(username):
    """创建用户，同时自动创建默认项目和默认任务"""
    user_id = execute("INSERT INTO users (username) VALUES (?)", (username,))

    # 创建默认项目
    proj_id = execute(
        "INSERT INTO projects (user_id, name, description, is_default) VALUES (?, '默认项目', '', 1)",
        (user_id,),
    )
    # 创建默认任务
    execute(
        "INSERT INTO tasks (project_id, name, description, is_default) VALUES (?, '默认任务', '', 1)",
        (proj_id,),
    )
    return user_id


# ─── Project ────────────────────────────────────────────────────────────────


def get_projects_by_user(user_id):
    return query(
        "SELECT * FROM projects WHERE user_id = ? AND is_deleted = 0 ORDER BY is_default DESC, created_at ASC",
        (user_id,),
    )


def get_project_by_id(project_id):
    return query(
        "SELECT * FROM projects WHERE id = ? AND is_deleted = 0",
        (project_id,),
        one=True,
    )


def get_default_project(user_id):
    return query(
        "SELECT * FROM projects WHERE user_id = ? AND is_default = 1 AND is_deleted = 0",
        (user_id,),
        one=True,
    )


def create_project(user_id, name, description=""):
    proj_id = execute(
        "INSERT INTO projects (user_id, name, description) VALUES (?, ?, ?)",
        (user_id, name, description),
    )
    # 自动创建默认任务
    execute(
        "INSERT INTO tasks (project_id, name, description, is_default) VALUES (?, '默认任务', '', 1)",
        (proj_id,),
    )
    return proj_id


def update_project(project_id, name, description):
    execute(
        "UPDATE projects SET name = ?, description = ? WHERE id = ?",
        (name, description, project_id),
    )


def soft_delete_project(project_id):
    execute(
        "UPDATE projects SET is_deleted = 1 WHERE id = ?", (project_id,)
    )


# ─── Task ───────────────────────────────────────────────────────────────────


def get_tasks_by_project(project_id):
    return query(
        "SELECT * FROM tasks WHERE project_id = ? AND is_deleted = 0 ORDER BY is_default DESC, created_at ASC",
        (project_id,),
    )


def get_task_by_id(task_id):
    return query(
        "SELECT * FROM tasks WHERE id = ? AND is_deleted = 0",
        (task_id,),
        one=True,
    )


def get_default_task(project_id):
    return query(
        "SELECT * FROM tasks WHERE project_id = ? AND is_default = 1 AND is_deleted = 0",
        (project_id,),
        one=True,
    )


def get_default_task_global(user_id):
    """获取全局默认项目下的默认任务"""
    default_proj = get_default_project(user_id)
    if default_proj:
        return get_default_task(default_proj["id"])
    return None


def create_task(project_id, name, description=""):
    return execute(
        "INSERT INTO tasks (project_id, name, description) VALUES (?, ?, ?)",
        (project_id, name, description),
    )


def update_task(task_id, name, description):
    execute(
        "UPDATE tasks SET name = ?, description = ? WHERE id = ?",
        (name, description, task_id),
    )


def soft_delete_task(task_id):
    execute("UPDATE tasks SET is_deleted = 1 WHERE id = ?", (task_id,))


def get_tasks_by_project_all(project_id):
    """获取项目下所有任务（含已删除），用于删除项目时转移工时"""
    return query(
        "SELECT * FROM tasks WHERE project_id = ?", (project_id,)
    )


def soft_delete_tasks_by_project(project_id):
    """软删除项目下所有任务"""
    execute(
        "UPDATE tasks SET is_deleted = 1 WHERE project_id = ?",
        (project_id,),
    )


# ─── Time Entry ─────────────────────────────────────────────────────────────


def get_time_entries_by_date(user_id, date):
    return query(
        """SELECT te.*, p.name AS project_name, t.name AS task_name
           FROM time_entries te
           JOIN projects p ON te.project_id = p.id
           JOIN tasks t ON te.task_id = t.id
           WHERE te.user_id = ? AND te.entry_date = ?
           ORDER BY te.created_at ASC""",
        (user_id, date),
    )


def get_time_entries_by_date_range(user_id, start_date, end_date):
    return query(
        """SELECT te.*, p.name AS project_name, t.name AS task_name
           FROM time_entries te
           JOIN projects p ON te.project_id = p.id
           JOIN tasks t ON te.task_id = t.id
           WHERE te.user_id = ? AND te.entry_date BETWEEN ? AND ?
           ORDER BY te.entry_date ASC, te.created_at ASC""",
        (user_id, start_date, end_date),
    )


def get_time_entry_by_id(entry_id):
    return query(
        "SELECT * FROM time_entries WHERE id = ?", (entry_id,), one=True
    )


def create_time_entry(user_id, project_id, task_id, entry_date, minutes, content=""):
    return execute(
        """INSERT INTO time_entries (user_id, project_id, task_id, entry_date, minutes, content)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, project_id, task_id, entry_date, minutes, content),
    )


def update_time_entry(entry_id, project_id, task_id, entry_date, minutes, content=""):
    execute(
        """UPDATE time_entries
           SET project_id = ?, task_id = ?, entry_date = ?, minutes = ?, content = ?, updated_at = CURRENT_TIMESTAMP
           WHERE id = ?""",
        (project_id, task_id, entry_date, minutes, content, entry_id),
    )


def delete_time_entry(entry_id):
    execute("DELETE FROM time_entries WHERE id = ?", (entry_id,))


def count_entries_by_task(task_id):
    row = query(
        "SELECT COUNT(*) AS cnt FROM time_entries WHERE task_id = ?",
        (task_id,),
        one=True,
    )
    return row["cnt"] if row else 0


def transfer_entries_to_task(from_task_id, to_task_id):
    """将某任务下的工时记录转移到另一任务"""
    execute(
        "UPDATE time_entries SET task_id = ?, updated_at = CURRENT_TIMESTAMP WHERE task_id = ?",
        (to_task_id, from_task_id),
    )


def transfer_entries_to_default(project_id, default_project_id, default_task_id):
    """将某项目下所有工时记录转移到默认项目的默认任务"""
    execute(
        """UPDATE time_entries
           SET project_id = ?, task_id = ?, updated_at = CURRENT_TIMESTAMP
           WHERE project_id = ?""",
        (default_project_id, default_task_id, project_id),
    )


def get_daily_summary(user_id, start_date, end_date):
    """获取日期范围内的每日汇总"""
    return query(
        """SELECT entry_date, SUM(minutes) AS total_minutes
           FROM time_entries te
           JOIN projects p ON te.project_id = p.id
           WHERE te.user_id = ? AND te.entry_date BETWEEN ? AND ? AND p.is_deleted = 0
           GROUP BY entry_date
           ORDER BY entry_date ASC""",
        (user_id, start_date, end_date),
    )


def get_project_task_summary(user_id, date):
    """获取某天按项目/任务的汇总"""
    return query(
        """SELECT te.project_id, te.task_id, p.name AS project_name, t.name AS task_name,
                  SUM(te.minutes) AS total_minutes
           FROM time_entries te
           JOIN projects p ON te.project_id = p.id
           JOIN tasks t ON te.task_id = t.id
           WHERE te.user_id = ? AND te.entry_date = ? AND p.is_deleted = 0 AND t.is_deleted = 0
           GROUP BY te.project_id, te.task_id
           ORDER BY p.name, t.name""",
        (user_id, date),
    )
