# 薪酬管理系统

一个基于 Flask 的简单薪酬管理系统，用于管理员工信息和薪资记录。

## 功能特点

- 员工管理（添加、查看员工信息）
- 薪资管理（添加薪资记录、查看薪资历史）
- 薪资趋势分析（可视化图表、部门对比）
- 用户认证（管理员登录）
- 响应式界面设计

## 技术栈

- 后端：Python Flask
- 数据库：SQLite
- 前端：Bootstrap 5, Axios, Chart.js
- 认证：Flask-Login

## 依赖项

以下是项目所需的主要依赖项：

- Flask==2.3.3
- Flask-SQLAlchemy==3.0.5
- Flask-Login==0.6.2
- Flask-Migrate==4.0.4
- python-dotenv==1.0.0
- werkzeug==2.3.7
- numpy==1.26.4
- pandas==2.2.2
- xlsxwriter==3.1.2
- openpyxl==3.1.2

请确保在安装依赖项时使用正确的版本。

## 安装步骤

1. 创建虚拟环境（推荐）：
```bash
python -m venv venv
venv\Scripts\activate
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 运行应用：
```bash
python app.py
```

4. 访问应用：
打开浏览器访问 http://localhost:5000

## 初始用户

系统启动时会自动创建一个管理员账户：
- 用户名：admin
- 密码：admin123

请在生产环境中修改这些凭据。

## 系统结构

```
project-root
│   app.py              # 主应用程序文件
│   requirements.txt    # 依赖项列表
│   README.md           # 项目说明文档
│
├───instance           # Flask 实例文件夹
│
├───migrations         # 数据库迁移文件夹
│
├───static             # 静态文件
│   └───js             # JavaScript 文件
│       ├── bootstrap.bundle.min.js
│       ├── jquery.min.js
│       └── salaries.js
│
├───templates          # 模板文件
│   ├── base.html
│   ├── departments.html
│   ├── employees.html
│   ├── index.html
│   ├── login.html
│   ├── my_salary.html
│   ├── salaries.html
│   ├── salary_stats.html
│   └── salary_trends.html
│
└───venv               # 虚拟环境
```

## 开发说明

1. 数据库模型：
- **User**：用户表，存储管理员信息
   - `id`: 主键
   - `username`: 用户名，唯一且不能为空
   - `password_hash`: 密码哈希
   - `is_admin`: 是否为管理员
   - `created_at`: 创建时间

- **Department**：部门表，存储部门信息
   - `id`: 主键
   - `name`: 部门名称，唯一且不能为空
   - `description`: 描述
   - `created_at`: 创建时间

- **Employee**：员工表，存储员工基本信息
   - `id`: 主键
   - `name`: 员工姓名
   - `employee_id`: 工号，唯一且不能为空
   - `department_id`: 部门ID，外键
   - `position`: 职位
   - `entry_date`: 入职日期
   - `status`: 状态（active, resigned, suspended）
   - `created_at`: 创建时间

- **Salary**：薪资表，存储薪资记录
   - `id`: 主键
   - `employee_id`: 员工ID，外键
   - `year`: 年份
   - `month`: 月份
   - `base_salary`: 基本工资
   - `bonus`: 奖金
   - `overtime_pay`: 加班费
   - `deductions`: 扣除项
   - `insurance`: 保险
   - `tax`: 税收
   - `total`: 总额
   - `payment_status`: 支付状态（pending, paid）
   - `payment_date`: 支付日期
   - `created_at`: 创建时间
   - `remarks`: 备注

2. 主要路由：
- `/`：主页面，显示概览信息。
- `/login`：登录页面，用户可以在此登录。
- `/logout`：登出功能，用户可以在此登出。
- `/departments`：部门管理页面，管理员可以在此添加和查看部门信息。
- `/employees`：员工管理页面，管理员可以在此添加和查看员工信息。
- `/salaries`：薪资管理页面，管理员可以在此添加和查看薪资记录。
- `/employees/<int:emp_id>`：获取单个员工信息。
- `/employees/<int:emp_id>/update`：更新员工信息。
- `/employees/<int:emp_id>/delete`：删除员工。
- `/salaries/<int:salary_id>/update`：更新薪资记录。
- `/salaries/<int:salary_id>/delete`：删除薪资记录。
- `/my_salary`：查看个人薪资。
- `/salary_stats`：查看薪资统计和报表。
- `/export_salary_report`：导出薪资报表。
- `/salary_trends`：查看薪资趋势数据。

## 薪资分析功能

### 数据可视化

系统提供多个交互式图表用于薪资数据分析：
- 月度薪资趋势图
- 部门薪资对比图
- 同比增长率分析
- 部门人数分布图

### 统计分析

系统自动计算并展示以下统计数据：
- 总体统计：员工总数、部门数量、平均薪资等
- 部门统计：各部门平均薪资、最高/最低薪资、人数等
- 月度统计：月度总薪资、平均薪资、同比增长率
- 部门排名：基于平均薪资的部门TOP5排名

### 筛选功能

可以通过以下条件筛选数据：
- 年份筛选：查看不同年份的薪资数据
- 部门筛选：查看特定部门的薪资情况
- 支持多条件组合筛选

### 使用说明

1. 在导航菜单中选择"薪资趋势"
2. 使用筛选条件选择要分析的年份和部门
3. 查看各类统计图表和数据分析
4. 可以通过图表交互功能查看详细数据

## 注意事项

1. 本系统使用 SQLite 数据库，数据文件将保存在 salary.db
2. 请在生产环境中修改 SECRET_KEY
3. 建议添加更多的安全措施，如密码加密等
