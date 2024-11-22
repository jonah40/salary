from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os
import io
import xlsxwriter
from flask import send_file
import pandas as pd

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_please_change_in_production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///salary.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# 用户模型
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# 部门模型
class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    employees = db.relationship('Employee', backref='department', lazy=True)

# 员工模型
class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    employee_id = db.Column(db.String(20), unique=True, nullable=False)  # 工号
    department_id = db.Column(db.Integer, db.ForeignKey('department.id', ondelete='SET NULL'), nullable=True)
    position = db.Column(db.String(80))
    entry_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='active')  # active, resigned, suspended
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    salaries = db.relationship('Salary', backref='employee', lazy=True)

# 薪资模型
class Salary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id', ondelete='CASCADE'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    base_salary = db.Column(db.Float, nullable=False)
    bonus = db.Column(db.Float, default=0)
    overtime_pay = db.Column(db.Float, default=0)
    deductions = db.Column(db.Float, default=0)
    insurance = db.Column(db.Float, default=0)
    tax = db.Column(db.Float, default=0)
    total = db.Column(db.Float, nullable=False)
    payment_status = db.Column(db.String(20), default='pending')  # pending, paid
    payment_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    remarks = db.Column(db.String(200))

    __table_args__ = (
        db.UniqueConstraint('employee_id', 'year', 'month', name='unique_monthly_salary'),
    )

# 薪资验证函数
def validate_salary_data(data):
    errors = []
    
    # 验证必填字段
    required_fields = ['employee_id', 'year', 'month', 'base_salary']
    for field in required_fields:
        if field not in data or not data[field]:
            errors.append(f'{field} 是必填项')
    
    # 验证数值范围
    try:
        if float(data.get('base_salary', 0)) < 0:
            errors.append('基本工资不能为负数')
        if float(data.get('bonus', 0)) < 0:
            errors.append('奖金不能为负数')
        if float(data.get('overtime_pay', 0)) < 0:
            errors.append('加班费不能为负数')
        if float(data.get('deductions', 0)) < 0:
            errors.append('扣除项不能为负数')
        if float(data.get('insurance', 0)) < 0:
            errors.append('保险不能为负数')
        if float(data.get('tax', 0)) < 0:
            errors.append('税收不能为负数')
    except ValueError:
        errors.append('薪资数据必须是有效的数字')
    
    # 验证日期
    try:
        year = int(data.get('year', 0))
        month = int(data.get('month', 0))
        if not (2000 <= year <= 2100):
            errors.append('年份必须在2000-2100之间')
        if not (1 <= month <= 12):
            errors.append('月份必须在1-12之间')
    except ValueError:
        errors.append('年份和月份必须是有效的数字')
    
    # 验证员工存在性
    if 'employee_id' in data:
        employee = Employee.query.get(data['employee_id'])
        if not employee:
            errors.append('选择的员工不存在')
    
    return errors

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 登录路由
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('登录成功！', 'success')
            return redirect(url_for('index'))
        flash('用户名或密码错误！', 'error')
    return render_template('login.html')

# 登出路由
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('已成功登出！', 'success')
    return redirect(url_for('login'))

# 首页
@app.route('/')
@login_required
def index():
    return render_template('index.html')

# 部门管理
@app.route('/departments', methods=['GET', 'POST'])
@login_required
def departments():
    if not current_user.is_admin:
        flash('权限不足！', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        if Department.query.filter_by(name=name).first():
            flash('部门名称已存在！', 'error')
        else:
            dept = Department(name=name, description=description)
            db.session.add(dept)
            try:
                db.session.commit()
                flash('部门创建成功！', 'success')
            except Exception as e:
                db.session.rollback()
                flash('部门创建失败！', 'error')
                
    departments = Department.query.all()
    return render_template('departments.html', departments=departments)

# 员工管理
@app.route('/employees', methods=['GET', 'POST'])
@login_required
def employees():
    if request.method == 'POST':
        if not current_user.is_admin:
            return jsonify({'error': '权限不足'}), 403

        data = request.json
        try:
            employee = Employee(
                name=data['name'],
                employee_id=data['employee_id'],
                department_id=data['department_id'],
                position=data['position'],
                entry_date=datetime.strptime(data['entry_date'], '%Y-%m-%d').date(),
                status=data.get('status', 'active')
            )
            db.session.add(employee)
            db.session.commit()
            return jsonify({'message': '员工添加成功'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400

    employees = Employee.query.all()
    departments = Department.query.all()
    return render_template('employees.html', employees=employees, departments=departments)

# 获取单个员工信息
@app.route('/employees/<int:emp_id>', methods=['GET'])
@login_required
def get_employee(emp_id):
    if not current_user.is_admin:
        return jsonify({'error': '权限不足'}), 403
    
    employee = Employee.query.get_or_404(emp_id)
    return jsonify({
        'id': employee.id,
        'name': employee.name,
        'employee_id': employee.employee_id,
        'department_id': employee.department_id,
        'position': employee.position,
        'entry_date': employee.entry_date.strftime('%Y-%m-%d'),
        'status': employee.status
    })

# 更新员工信息
@app.route('/employees/<int:emp_id>', methods=['PUT'])
@login_required
def update_employee(emp_id):
    if not current_user.is_admin:
        return jsonify({'error': '权限不足'}), 403

    employee = Employee.query.get_or_404(emp_id)
    data = request.json

    try:
        employee.name = data['name']
        employee.employee_id = data['employee_id']
        employee.department_id = data['department_id']
        employee.position = data['position']
        employee.entry_date = datetime.strptime(data['entry_date'], '%Y-%m-%d').date()
        employee.status = data['status']
        
        db.session.commit()
        return jsonify({'message': '员工信息更新成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# 删除员工
@app.route('/employees/<int:emp_id>', methods=['DELETE'])
@login_required
def delete_employee(emp_id):
    if not current_user.is_admin:
        return jsonify({'error': '权限不足'}), 403

    employee = Employee.query.get_or_404(emp_id)
    try:
        db.session.delete(employee)
        db.session.commit()
        return jsonify({'message': '员工删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# 薪资管理
@app.route('/salaries', methods=['GET', 'POST'])
@login_required
def salaries():
    if not current_user.is_admin:
        flash('权限不足！', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        data = request.json
        
        # 验证数据
        errors = validate_salary_data(data)
        if errors:
            return jsonify({'error': ' '.join(errors)}), 400
            
        try:
            # 检查是否已存在该月薪资记录
            existing_salary = Salary.query.filter_by(
                employee_id=data['employee_id'],
                year=data['year'],
                month=data['month']
            ).first()
            
            if existing_salary:
                return jsonify({'error': '该员工本月薪资记录已存在'}), 400
            
            # 计算总薪资
            total = (
                float(data['base_salary']) +
                float(data.get('bonus', 0)) +
                float(data.get('overtime_pay', 0)) -
                float(data.get('deductions', 0)) -
                float(data.get('insurance', 0)) -
                float(data.get('tax', 0))
            )
            
            salary = Salary(
                employee_id=data['employee_id'],
                year=data['year'],
                month=data['month'],
                base_salary=data['base_salary'],
                bonus=data.get('bonus', 0),
                overtime_pay=data.get('overtime_pay', 0),
                deductions=data.get('deductions', 0),
                insurance=data.get('insurance', 0),
                tax=data.get('tax', 0),
                total=total,
                remarks=data.get('remarks', '')
            )
            db.session.add(salary)
            db.session.commit()
            return jsonify({'message': '薪资记录添加成功'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'保存失败：{str(e)}'}), 400

    # 获取查询参数
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    search = request.args.get('search', '')
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    department_id = request.args.get('department_id', type=int)
    min_salary = request.args.get('min_salary', type=float)
    max_salary = request.args.get('max_salary', type=float)
    
    # 构建查询
    query = Salary.query.join(Employee)
    
    # 应用过滤条件
    if search:
        query = query.filter(Employee.name.ilike(f'%{search}%'))
    if year:
        query = query.filter(Salary.year == year)
    if month:
        query = query.filter(Salary.month == month)
    if department_id:
        query = query.filter(Employee.department_id == department_id)
    if min_salary is not None:
        query = query.filter(Salary.total >= min_salary)
    if max_salary is not None:
        query = query.filter(Salary.total <= max_salary)
    
    # 排序
    query = query.order_by(Salary.year.desc(), Salary.month.desc())
    
    # 执行分页查询
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    salaries = pagination.items
    
    # 获取所有部门和活跃员工（用于表单）
    departments = Department.query.all()
    employees = Employee.query.filter_by(status='active').all()
    
    # 获取年份和月份选项（用于过滤）
    years = db.session.query(db.distinct(Salary.year)).order_by(Salary.year.desc()).all()
    months = list(range(1, 13))
    
    return render_template('salaries.html',
                         salaries=salaries,
                         pagination=pagination,
                         employees=employees,
                         departments=departments,
                         years=years,
                         months=months,
                         current_filters={
                             'search': search,
                             'year': year,
                             'month': month,
                             'department_id': department_id,
                             'min_salary': min_salary,
                             'max_salary': max_salary
                         })

# 批量导入薪资
@app.route('/import-salaries', methods=['POST'])
@login_required
def import_salaries():
    if not current_user.is_admin:
        return jsonify({'error': '权限不足'}), 403
        
    if 'file' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
        
    if not file.filename.endswith('.xlsx'):
        return jsonify({'error': '只支持.xlsx格式的文件'}), 400
        
    try:
        # 读取Excel文件
        df = pd.read_excel(file)
        
        # 验证必要的列
        required_columns = ['员工ID', '年份', '月份', '基本工资']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return jsonify({'error': f'缺少必要的列：{", ".join(missing_columns)}'}), 400
            
        # 验证数据
        errors = []
        success_count = 0
        error_count = 0
        
        for index, row in df.iterrows():
            try:
                # 验证员工ID
                employee = Employee.query.get(row['员工ID'])
                if not employee:
                    errors.append(f'第{index+2}行：员工ID {row["员工ID"]} 不存在')
                    error_count += 1
                    continue
                    
                # 验证年月
                year = int(row['年份'])
                month = int(row['月份'])
                if not (2000 <= year <= 2100):
                    errors.append(f'第{index+2}行：年份必须在2000-2100之间')
                    error_count += 1
                    continue
                if not (1 <= month <= 12):
                    errors.append(f'第{index+2}行：月份必须在1-12之间')
                    error_count += 1
                    continue
                    
                # 检查是否已存在该月薪资记录
                existing_salary = Salary.query.filter_by(
                    employee_id=row['员工ID'],
                    year=year,
                    month=month
                ).first()
                
                if existing_salary:
                    errors.append(f'第{index+2}行：员工 {employee.name} 的 {year}年{month}月薪资记录已存在')
                    error_count += 1
                    continue
                    
                # 验证数值
                base_salary = float(row['基本工资'])
                bonus = float(row.get('奖金', 0))
                overtime_pay = float(row.get('加班费', 0))
                deductions = float(row.get('扣除项', 0))
                insurance = float(row.get('保险', 0))
                tax = float(row.get('税收', 0))
                
                if any(x < 0 for x in [base_salary, bonus, overtime_pay, deductions, insurance, tax]):
                    errors.append(f'第{index+2}行：薪资相关数值不能为负')
                    error_count += 1
                    continue
                    
                # 计算总薪资
                total = (
                    base_salary +
                    bonus +
                    overtime_pay -
                    deductions -
                    insurance -
                    tax
                )
                
                # 创建薪资记录
                salary = Salary(
                    employee_id=row['员工ID'],
                    year=year,
                    month=month,
                    base_salary=base_salary,
                    bonus=bonus,
                    overtime_pay=overtime_pay,
                    deductions=deductions,
                    insurance=insurance,
                    tax=tax,
                    total=total,
                    remarks=str(row.get('备注', ''))
                )
                db.session.add(salary)
                success_count += 1
                
            except (ValueError, TypeError) as e:
                errors.append(f'第{index+2}行：数据格式错误 - {str(e)}')
                error_count += 1
                continue
                
        # 提交事务
        if success_count > 0:
            db.session.commit()
            
        # 返回结果
        result = {
            'message': f'导入完成：成功 {success_count} 条，失败 {error_count} 条',
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors
        }
        
        if success_count > 0:
            result['status'] = 'success'
        elif error_count > 0:
            result['status'] = 'error'
        else:
            result['status'] = 'warning'
            result['message'] = '没有数据被导入'
            
        return jsonify(result)
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': '导入失败',
            'error': str(e)
        }), 400

# 更新薪资记录
@app.route('/salaries/<int:salary_id>', methods=['PUT'])
@login_required
def update_salary(salary_id):
    if not current_user.is_admin:
        return jsonify({'error': '权限不足'}), 403
    
    salary = Salary.query.get_or_404(salary_id)
    data = request.json
    
    # 验证数据
    errors = validate_salary_data(data)
    if errors:
        return jsonify({'error': ' '.join(errors)}), 400
        
    try:
        # 检查是否与其他记录冲突
        existing_salary = Salary.query.filter(
            Salary.employee_id == data['employee_id'],
            Salary.year == data['year'],
            Salary.month == data['month'],
            Salary.id != salary_id
        ).first()
        
        if existing_salary:
            return jsonify({'error': '该员工本月已有其他薪资记录'}), 400
            
        # 计算总薪资
        total = (
            float(data['base_salary']) +
            float(data.get('bonus', 0)) +
            float(data.get('overtime_pay', 0)) -
            float(data.get('deductions', 0)) -
            float(data.get('insurance', 0)) -
            float(data.get('tax', 0))
        )
        
        # 更新薪资记录
        salary.base_salary = data['base_salary']
        salary.bonus = data.get('bonus', 0)
        salary.overtime_pay = data.get('overtime_pay', 0)
        salary.deductions = data.get('deductions', 0)
        salary.insurance = data.get('insurance', 0)
        salary.tax = data.get('tax', 0)
        salary.total = total
        salary.remarks = data.get('remarks', '')
        
        db.session.commit()
        return jsonify({'message': '薪资记录更新成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'更新失败：{str(e)}'}), 400

# 删除薪资记录
@app.route('/salaries/<int:salary_id>', methods=['DELETE'])
@login_required
def delete_salary(salary_id):
    if not current_user.is_admin:
        return jsonify({'error': '权限不足'}), 403
    
    salary = Salary.query.get_or_404(salary_id)
    try:
        db.session.delete(salary)
        db.session.commit()
        return jsonify({'message': '薪资记录删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'删除失败：{str(e)}'}), 400

# 查看个人薪资
@app.route('/my-salary')
@login_required
def my_salary():
    # 通过员工工号查找对应的薪资记录
    employee = Employee.query.filter_by(employee_id=current_user.username).first()
    if not employee:
        flash('未找到您的员工信息', 'error')
        return redirect(url_for('index'))
    
    salaries = Salary.query.filter_by(employee_id=employee.id).order_by(
        Salary.year.desc(),
        Salary.month.desc()
    ).all()
    
    return render_template('my_salary.html', salaries=salaries, employee=employee)

# 薪资统计和报表
@app.route('/salary-stats')
@login_required
def salary_stats():
    if not current_user.is_admin:
        flash('权限不足！', 'error')
        return redirect(url_for('index'))
        
    # 获取查询参数
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', type=int)
    department_id = request.args.get('department_id', type=int)
    
    # 基础查询
    query = db.session.query(
        Employee.department_id,
        Department.name.label('department_name'),
        db.func.count(Salary.id).label('employee_count'),
        db.func.sum(Salary.base_salary).label('total_base_salary'),
        db.func.sum(Salary.bonus).label('total_bonus'),
        db.func.sum(Salary.overtime_pay).label('total_overtime'),
        db.func.sum(Salary.deductions).label('total_deductions'),
        db.func.sum(Salary.insurance).label('total_insurance'),
        db.func.sum(Salary.tax).label('total_tax'),
        db.func.sum(Salary.total).label('total_salary')
    ).join(Department).join(Salary)
    
    # 应用过滤条件
    if year:
        query = query.filter(Salary.year == year)
    if month:
        query = query.filter(Salary.month == month)
    if department_id:
        query = query.filter(Employee.department_id == department_id)
    
    # 按部门分组
    stats = query.group_by(Employee.department_id, Department.name).all()
    
    # 计算总计
    totals = {
        'employee_count': sum(s.employee_count for s in stats),
        'total_base_salary': sum(s.total_base_salary for s in stats),
        'total_bonus': sum(s.total_bonus for s in stats),
        'total_overtime': sum(s.total_overtime for s in stats),
        'total_deductions': sum(s.total_deductions for s in stats),
        'total_insurance': sum(s.total_insurance for s in stats),
        'total_tax': sum(s.total_tax for s in stats),
        'total_salary': sum(s.total_salary for s in stats)
    }
    
    # 获取年份和部门选项（用于过滤）
    years = db.session.query(db.distinct(Salary.year)).order_by(Salary.year.desc()).all()
    departments = Department.query.all()
    
    return render_template('salary_stats.html',
                         stats=stats,
                         totals=totals,
                         years=years,
                         departments=departments,
                         current_filters={
                             'year': year,
                             'month': month,
                             'department_id': department_id
                         })

# 导出薪资报表
@app.route('/export-salary-report')
@login_required
def export_salary_report():
    if not current_user.is_admin:
        flash('权限不足！', 'error')
        return redirect(url_for('index'))
        
    # 获取查询参数
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', type=int)
    department_id = request.args.get('department_id', type=int)
    
    # 构建查询
    query = db.session.query(
        Employee.name,
        Department.name.label('department'),
        Salary.year,
        Salary.month,
        Salary.base_salary,
        Salary.bonus,
        Salary.overtime_pay,
        Salary.deductions,
        Salary.insurance,
        Salary.tax,
        Salary.total,
        Salary.payment_status,
        Salary.payment_date,
        Salary.remarks
    ).join(Employee).join(Department)
    
    # 应用过滤条件
    if year:
        query = query.filter(Salary.year == year)
    if month:
        query = query.filter(Salary.month == month)
    if department_id:
        query = query.filter(Employee.department_id == department_id)
        
    # 排序
    records = query.order_by(Department.name, Employee.name, Salary.year.desc(), Salary.month.desc()).all()
    
    # 创建Excel文件
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet('薪资报表')
    
    # 设置表头样式
    header_format = workbook.add_format({
        'bold': True,
        'align': 'center',
        'valign': 'vcenter',
        'fg_color': '#D9EAD3',
        'border': 1
    })
    
    # 写入表头
    headers = [
        '员工姓名', '部门', '年份', '月份', '基本工资', '奖金', '加班费',
        '扣除项', '保险', '税收', '总计', '支付状态', '支付日期', '备注'
    ]
    for col, header in enumerate(headers):
        worksheet.write(0, col, header, header_format)
        
    # 设置数据格式
    date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
    number_format = workbook.add_format({'num_format': '#,##0.00'})
    
    # 写入数据
    for row, record in enumerate(records, 1):
        worksheet.write(row, 0, record.name)
        worksheet.write(row, 1, record.department)
        worksheet.write(row, 2, record.year)
        worksheet.write(row, 3, record.month)
        worksheet.write(row, 4, record.base_salary, number_format)
        worksheet.write(row, 5, record.bonus, number_format)
        worksheet.write(row, 6, record.overtime_pay, number_format)
        worksheet.write(row, 7, record.deductions, number_format)
        worksheet.write(row, 8, record.insurance, number_format)
        worksheet.write(row, 9, record.tax, number_format)
        worksheet.write(row, 10, record.total, number_format)
        worksheet.write(row, 11, record.payment_status)
        worksheet.write(row, 12, record.payment_date, date_format)
        worksheet.write(row, 13, record.remarks)
    
    # 调整列宽
    worksheet.set_column('A:N', 15)
    
    # 添加合计行
    total_row = len(records) + 1
    worksheet.write(total_row, 0, '合计', header_format)
    worksheet.write(total_row, 1, f'共{len(records)}条记录', header_format)
    for col in range(4, 11):
        worksheet.write_formula(
            total_row, col,
            f'=SUM({chr(65+col)}2:{chr(65+col)}{total_row})',
            number_format
        )
    
    workbook.close()
    
    # 设置响应头
    output.seek(0)
    filename = f'薪资报表_{year}年{month or "全年"}.xlsx'
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )

# 薪资趋势数据
@app.route('/salary-trends')
@login_required
def salary_trends():
    if not current_user.is_admin:
        flash('权限不足！', 'error')
        return redirect(url_for('index'))
        
    # 获取查询参数
    year = request.args.get('year', datetime.now().year, type=int)
    department_id = request.args.get('department_id', type=int)
    
    # 获取年份和部门选项（用于过滤）
    years = db.session.query(db.distinct(Salary.year)).order_by(Salary.year.desc()).all()
    departments = Department.query.all()
    
    # 基础查询
    base_query = db.session.query(
        Employee.id,
        Employee.name,
        Salary.total.label('salary'),
        Employee.entry_date,
        Department.name.label('department_name'),
        Department.id.label('department_id')
    ).select_from(Employee).join(Department).join(Salary)
    
    if department_id:
        base_query = base_query.filter(Department.id == department_id)
    if year:
        base_query = base_query.filter(Salary.year == year)
    
    # 计算整体统计数据
    overall_stats = {
        'total_employees': db.session.query(db.func.count(db.distinct(Employee.id))).scalar(),
        'department_count': Department.query.count(),
        'avg_salary': db.session.query(db.func.avg(Salary.total)).filter(Salary.year == year).scalar() or 0,
        'min_salary': db.session.query(db.func.min(Salary.total)).filter(Salary.year == year).scalar() or 0,
        'max_salary': db.session.query(db.func.max(Salary.total)).filter(Salary.year == year).scalar() or 0,
        'total_salary': db.session.query(db.func.sum(Salary.total)).filter(Salary.year == year).scalar() or 0
    }
    
    # 计算总体同比增长率
    current_year_total = db.session.query(db.func.sum(Salary.total))\
        .filter(Salary.year == year)
    last_year_total = db.session.query(db.func.sum(Salary.total))\
        .filter(Salary.year == year - 1)
        
    if department_id:
        current_year_total = current_year_total.join(Employee)\
            .filter(Employee.department_id == department_id)
        last_year_total = last_year_total.join(Employee)\
            .filter(Employee.department_id == department_id)
    
    current_year_total = current_year_total.scalar() or 0
    last_year_total = last_year_total.scalar() or 0
    
    yoy_growth = 0
    if last_year_total > 0:
        yoy_growth = ((current_year_total - last_year_total) / last_year_total) * 100
    
    # 按月份统计薪资总额
    monthly_totals = db.session.query(
        Salary.month,
        db.func.sum(Salary.total).label('total_salary'),
        db.func.avg(Salary.total).label('avg_salary'),
        db.func.count(Salary.id).label('salary_count')
    ).select_from(Salary).join(Employee)
    
    if year:
        monthly_totals = monthly_totals.filter(Salary.year == year)
    if department_id:
        monthly_totals = monthly_totals.filter(Employee.department_id == department_id)
        
    monthly_totals = monthly_totals.group_by(Salary.month).all()
    
    # 转换为图表数据
    months = [f"{i}月" for i in range(1, 13)]
    salary_data = [0] * 12
    avg_salary_data = [0] * 12
    salary_count_data = [0] * 12
    
    for month, total, avg, count in monthly_totals:
        salary_data[month-1] = float(total or 0)
        avg_salary_data[month-1] = float(avg or 0)
        salary_count_data[month-1] = int(count or 0)
    
    # 按部门统计平均薪资和人数
    dept_stats = db.session.query(
        Department.name,
        db.func.avg(Salary.total).label('avg_salary'),
        db.func.count(db.distinct(Employee.id)).label('emp_count'),
        db.func.sum(Salary.total).label('total_salary'),
        db.func.min(Salary.total).label('min_salary'),
        db.func.max(Salary.total).label('max_salary')
    ).select_from(Department).join(Employee).join(Salary)
    
    if year:
        dept_stats = dept_stats.filter(Salary.year == year)
        
    dept_stats = dept_stats.group_by(Department.name).all()
    
    # 转换为图表数据
    dept_names = [dept[0] for dept in dept_stats]
    dept_data = {
        'avg': [float(stats[1] or 0) for stats in dept_stats],
        'count': [int(stats[2] or 0) for stats in dept_stats],
        'total': [float(stats[3] or 0) for stats in dept_stats],
        'min': [float(stats[4] or 0) for stats in dept_stats],
        'max': [float(stats[5] or 0) for stats in dept_stats]
    }
    
    # 计算月度同比增长率
    growth_rates = []
    if year > 2000:
        for month in range(1, 13):
            current_month = db.session.query(db.func.sum(Salary.total))\
                .filter(Salary.year == year, Salary.month == month)
            last_year = db.session.query(db.func.sum(Salary.total))\
                .filter(Salary.year == year - 1, Salary.month == month)
            
            if department_id:
                current_month = current_month.join(Employee)\
                    .filter(Employee.department_id == department_id)
                last_year = last_year.join(Employee)\
                    .filter(Employee.department_id == department_id)
            
            current_value = current_month.scalar() or 0
            last_value = last_year.scalar() or 0
            
            if last_value > 0:
                growth = ((current_value - last_value) / last_value) * 100
            else:
                growth = 0
            growth_rates.append(float(growth))
    else:
        growth_rates = [0] * 12
    
    # 计算部门薪资排名
    dept_rankings = []
    for i, dept in enumerate(dept_stats):
        dept_rankings.append({
            'name': dept[0],
            'average': dept_data['avg'][i],
            'employee_count': dept_data['count'][i],
            'total': dept_data['total'][i],
            'min': dept_data['min'][i],
            'max': dept_data['max'][i]
        })
    
    dept_rankings.sort(key=lambda x: x['average'], reverse=True)
    
    return render_template('salary_trends.html',
        years=years,
        departments=departments,
        current_filters={'year': year, 'department_id': department_id},
        overall_stats=overall_stats,
        months=months,
        salary_data=salary_data,
        avg_salary_data=avg_salary_data,
        growth_rates=growth_rates,
        dept_names=dept_names,
        dept_data=dept_data,
        dept_rankings=dept_rankings[:5],  # Top 5 departments
        yoy_growth=yoy_growth  # Added overall year-over-year growth rate
    )

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # 创建管理员账户（如果不存在）
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', is_admin=True)
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
    app.run(debug=True)
