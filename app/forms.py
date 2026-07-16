from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, DateField, SelectField, HiddenField
from wtforms.validators import DataRequired, Optional, NumberRange


class UserCreateForm(FlaskForm):
    username = StringField("用户名", validators=[DataRequired("请输入用户名")])


class ProjectForm(FlaskForm):
    name = StringField("项目名称", validators=[DataRequired("请输入项目名称")])
    description = TextAreaField("描述", validators=[Optional()])


class TaskForm(FlaskForm):
    name = StringField("任务名称", validators=[DataRequired("请输入任务名称")])
    description = TextAreaField("描述", validators=[Optional()])


class TimeEntryForm(FlaskForm):
    entry_date = DateField("日期", validators=[DataRequired("请选择日期")])
    project_id = SelectField("项目", coerce=int, validators=[DataRequired("请选择项目")])
    task_id = SelectField("任务", coerce=int, validators=[DataRequired("请选择任务")])
    start_time = StringField("开始时间", default="09:00", validators=[DataRequired("请选择开始时间")])
    end_time = StringField("结束时间", default="18:00", validators=[DataRequired("请选择结束时间")])
    minutes = IntegerField(
        "工时（分钟）",
        validators=[Optional(), NumberRange(min=1, message="工时必须大于0")],
    )


class ExportForm(FlaskForm):
    start_date = DateField("起始日期", validators=[DataRequired("请选择起始日期")])
    end_date = DateField("结束日期", validators=[DataRequired("请选择结束日期")])
