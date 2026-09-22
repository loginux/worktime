import csv
import io
from datetime import date
from urllib.parse import quote
from flask import Blueprint, render_template, request, flash, Response
from flask_login import login_required, current_user
from app.forms import ExportForm
from app.models import get_time_entries_by_date_range
from app.holiday import get_holiday_info


def _to_date(value):
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _is_off_day(d):
    """判断某天是否为休息日（法定节假日或周末，排除调休上班），与月视图逻辑一致"""
    info = get_holiday_info(d)
    if info is not None:
        return info["is_off_day"]
    return d.weekday() >= 5

export_bp = Blueprint("export", __name__, url_prefix="/export")


@export_bp.route("/", methods=["GET", "POST"])
@login_required
def export_csv():
    form = ExportForm()
    if not form.is_submitted():
        form.start_date.data = date(2020, 1, 1)
        form.end_date.data = date.today()
    if form.validate_on_submit():
        start_date = form.start_date.data
        end_date = form.end_date.data

        if start_date > end_date:
            flash("起始日期不能晚于结束日期", "error")
            return render_template("export/export.html", form=form)

        entries = get_time_entries_by_date_range(
            current_user.id, start_date.isoformat(), end_date.isoformat()
        )

        # 生成 CSV（含 BOM 头，兼容 Excel 中文）
        output = io.StringIO()
        output.write("\ufeff")  # BOM
        writer = csv.writer(output)
        writer.writerow(["日期", "项目名称", "任务名称", "工作内容", "工时(分钟)", "节假期加班", "记录ID"])

        for e in entries:
            entry_date = _to_date(e["entry_date"])
            holiday_ot = "是" if _is_off_day(entry_date) else ""
            writer.writerow([
                str(e["entry_date"]),
                e["project_name"],
                e["task_name"],
                e["content"] or "",
                e["minutes"],
                holiday_ot,
                e["id"],
            ])

        csv_content = output.getvalue()
        output.close()

        # 中文文件名做 URL 编码
        filename = f"woktime_{start_date.isoformat()}_{end_date.isoformat()}.csv"
        filename_encoded = quote(filename)

        return Response(
            csv_content,
            mimetype="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename={filename_encoded}; filename*=UTF-8''{filename_encoded}",
            },
        )

    return render_template("export/export.html", form=form)
