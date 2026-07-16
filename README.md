# ⏱ WokTime - 工时记录工具

一款轻量级的 Web 端工时记录工具，帮助用户精确回答 **"时间花在哪里"**。

---

## 目的与作用

在日常工作中，经常遇到以下问题：

- 一天下来不知道时间花在了哪里
- 汇报工作时说不出每个项目/任务花了多少时间
- 缺乏一个轻便的工具随手记录工时

**WokTime** 就是为了解决这些问题而生的。它让用户能够：

1. 快速记录每天在每个项目/任务上花费的时间（分钟级）
2. 通过**日/周/月**视图直观查看时间分布
3. 支持穿透查看——从周/月汇总点击某天直达该天明细
4. 导出 CSV 做进一步分析或汇报

---

## 功能特性

| 模块 | 功能 |
|------|------|
| **用户切换** | 多用户数据隔离，无密码，点击即切换 |
| **项目管理** | 创建/编辑/删除项目；自动创建默认项目（不可删） |
| **任务管理** | 在项目下创建/编辑/删除任务；自动创建默认任务（不可删） |
| **工时录入** | 起止时间自动计算分钟数，默认 09:00-18:00，也可手动填写 |
| **日视图** | 明细列表 + 按项目/项目-任务双饼图 + 汇总表格 |
| **周视图** | 柱状图（Chart.js，纵轴小时），每日卡片，点击穿透 |
| **月视图** | 自定义起始日期的月度滚动视图，工时色阶、项目标签、法定节假日 |
| **CSV导出** | 自定义日期范围，含 BOM 头兼容 Excel |
| **工时转移** | 删除任务/项目时自动将工时转移至默认实体，数据不丢失 |

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | **Flask** (Python) |
| 模板引擎 | **Jinja2** |
| 数据库 | **SQLite**（嵌入式，零配置） |
| 前端图表 | **Chart.js**（柱状图 + 饼图） |
| 表单处理 | **Flask-WTF** (WTForms) |
| 用户会话 | **Flask-Login** |
| CSS | 纯手写，无框架依赖 |

---

## 设计原理

### 数据模型

采用**项目-任务二级结构**，每个项目下可包含多个任务：

```
用户
 ├── 项目1（可多个）
 │    ├── 默认任务（自动创建，不可删）
 │    ├── 任务A
 │    └── 任务B
 └── 项目2
      ├── 默认任务
      └── ...
```

### 核心机制

- **软删除**：项目和任务删除时仅标记 `is_deleted=1`，数据保留在数据库中以供历史统计
- **工时转移**：删除非默认任务 → 工时自动转移至同项目的默认任务；删除非默认项目 → 工时转移至全局默认项目
- **物理删除**：工时记录可物理删除（唯一可彻底删除的数据）
- **默认实体保护**：每个用户有一个"默认项目"、每个项目有一个"默认任务"，可改名但不可删除，确保始终有兜底容器

### 视图逻辑

- **日视图**：按日期查询明细，按项目/任务分组汇总，双饼图可视化占比
- **周视图**：以周一~周日为一周，Chart.js 柱状图（纵轴小时），tooltip 显示 X小时X分钟
- **月视图**：以用户设置的起始日期为起点，范围到下个月同日 -1 天。日工时按 <9h / 9~9.5h / 9.5~10.5h / >10.5h 四档色阶显示，每天展示涉及的项目标签和法定节假日

---

## 目录结构

```
woktime/
├── run.py                    # 启动入口
├── config.py                 # 配置
├── requirements.txt          # Python 依赖
├── README.md
├── app/
│   ├── __init__.py           # Flask 应用工厂
│   ├── db.py                 # SQLite 连接管理 + 建表
│   ├── models.py             # 数据访问层
│   ├── forms.py              # WTForms 表单
│   ├── holiday.py            # 节假日加载模块
│   ├── holiday/              # 年度节假日 JSON（holiday-cn 格式）
│   ├── routes/
│   │   ├── auth.py           # 用户选择/创建/切换
│   │   ├── projects.py       # 项目 CRUD
│   │   ├── tasks.py          # 任务 CRUD
│   │   ├── time_entries.py   # 工时录入/编辑/删除
│   │   ├── views.py          # 日/周/月视图
│   │   └── export.py         # CSV 导出
│   ├── templates/            # Jinja2 模板
│   └── static/               # CSS / JS
└── instance/
    └── woktime.db            # SQLite 数据库（自动创建）
```

---

## 部署与运行

### 源码运行

```bash
cd woktime
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements.txt
python run.py
# 访问 http://127.0.0.1:5000

# 也可指定监听地址和端口：
python run.py --host 0.0.0.0 --port 8080
```

### 打包为 exe

```bash
pip install pyinstaller
# 清理旧缓存后打包
rm -rf dist build *.spec
pyinstaller --onefile --name WokTime ^
  --add-data "app/templates;app/templates" ^
  --add-data "app/static;app/static" ^
  --add-data "app/holiday;app/holiday" ^
  --hidden-import flask ^
  --hidden-import flask_login ^
  --hidden-import flask_wtf ^
  --hidden-import flask_wtf.csrf ^
  --hidden-import wtforms ^
  --hidden-import jinja2 ^
  --hidden-import markupsafe ^
  --hidden-import werkzeug ^
  --hidden-import itsdangerous ^
  --hidden-import click ^
  --hidden-import blinker ^
  run.py
```

打包后在 `dist/WokTime.exe`，双击即可启动。

---

## 交叉编译 ARM（OpenWrt 路由器）

项目内置了 GitHub Actions 工作流（`.github/workflows/build-arm.yml`），可在 ARM Linux（musl libc）上运行：

### 手动触发

1. 在 GitHub 仓库页面点击 **Actions** → **Build ARM (OpenWrt)** → **Run workflow**
2. 等待几分钟，下载 `WokTime-linux-armv7` 产物
3. 上传到路由器：

```bash
# 路由器上执行
scp user@host:/path/to/WokTime /root/
chmod +x /root/WokTime
/root/WokTime --host 0.0.0.0 --port 5000
```

### 自动触发

推送 git tag（如 `v1.0`）时自动构建并发布到 Releases：

```bash
git tag v1.0
git push origin v1.0
```

---

## 节假日配置

月视图支持显示法定节假日。数据按年份存放在 `app/holiday/` 目录下，遵循 [holiday-cn](https://github.com/NateScarlet/holiday-cn) 格式：

```json
{
  "year": 2026,
  "days": [
    {"name": "元旦", "date": "2026-01-01", "isOffDay": true}
  ]
}
```

- `isOffDay: true` — 法定假日（显示）
- `isOffDay: false` — 调休上班日（不显示）

---

## 开发背景

本项目基于 Python Flask 构建，数据库使用 SQLite（零配置嵌入式），前端采用服务端渲染（Jinja2 模板）+ 原生 JS + Chart.js，无需 Node.js 或前端构建工具，开箱即用。

