from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Date, Time, Text, ForeignKey, JSON
from sqlalchemy.types import SMALLINT as TinyInteger
from database.db_config import Base


class Worker(Base):
    __tablename__ = 't_construction_worker'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20))
    id_card = Column(String(20))
    face_image = Column(String(500))
    team = Column(String(100))
    position = Column(String(100))
    status = Column(String(20), default='active')
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'id_card': self.id_card,
            'face_image': self.face_image,
            'team': self.team,
            'position': self.position,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class AttendanceRecord(Base):
    __tablename__ = 't_construction_attendance'

    id = Column(Integer, primary_key=True, autoincrement=True)
    worker_id = Column(Integer, ForeignKey('t_construction_worker.id'), nullable=False)
    date = Column(Date, nullable=False)
    check_in_time = Column(Time)
    check_out_time = Column(Time)
    work_hours = Column(Numeric(5, 2), default=0.00)
    overtime_hours = Column(Numeric(5, 2), default=0.00)
    check_in_location = Column(String(200))
    check_out_location = Column(String(200))
    status = Column(String(20), default='normal')
    remark = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'worker_id': self.worker_id,
            'date': self.date.isoformat() if self.date else None,
            'check_in_time': str(self.check_in_time) if self.check_in_time else None,
            'check_out_time': str(self.check_out_time) if self.check_out_time else None,
            'work_hours': float(self.work_hours) if self.work_hours else 0.00,
            'overtime_hours': float(self.overtime_hours) if self.overtime_hours else 0.00,
            'check_in_location': self.check_in_location,
            'check_out_location': self.check_out_location,
            'status': self.status,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class LeaveRecord(Base):
    __tablename__ = 't_construction_leave'

    id = Column(Integer, primary_key=True, autoincrement=True)
    worker_id = Column(Integer, ForeignKey('t_construction_worker.id'), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    leave_days = Column(Integer, default=1)
    leave_type = Column(String(20), default='personal')
    reason = Column(String(500))
    status = Column(String(20), default='pending')
    approved_by = Column(String(100))
    approved_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'worker_id': self.worker_id,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'leave_days': self.leave_days or 0,
            'leave_type': self.leave_type,
            'reason': self.reason,
            'status': self.status,
            'approved_by': self.approved_by,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class WeatherRecord(Base):
    __tablename__ = 't_construction_weather'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, nullable=False)
    date = Column(Date, nullable=False)
    weather = Column(String(100))
    temperature = Column(String(50))
    humidity = Column(String(20))
    wind = Column(String(100))
    rain = Column(String(20))
    warning = Column(String(100))
    impact = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'date': self.date.isoformat() if self.date else None,
            'weather': self.weather,
            'temperature': self.temperature,
            'humidity': self.humidity,
            'wind': self.wind,
            'rain': self.rain,
            'warning': self.warning,
            'impact': self.impact,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class ProjectSchedule(Base):
    __tablename__ = 't_construction_schedule'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, nullable=False)
    task_name = Column(String(200), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    actual_start_date = Column(Date)
    actual_end_date = Column(Date)
    progress = Column(Numeric(5, 2), default=0.00)
    status = Column(String(20), default='pending')
    is_critical = Column(TinyInteger, default=0)
    responsible = Column(String(100))
    remark = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'task_name': self.task_name,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'actual_start_date': self.actual_start_date.isoformat() if self.actual_start_date else None,
            'actual_end_date': self.actual_end_date.isoformat() if self.actual_end_date else None,
            'progress': float(self.progress) if self.progress else 0.00,
            'status': self.status,
            'is_critical': self.is_critical,
            'responsible': self.responsible,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class WorkArea(Base):
    __tablename__ = 't_construction_work_area'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, nullable=False)
    area_name = Column(String(200), nullable=False)
    area_code = Column(String(50))
    location = Column(String(200))
    status = Column(String(20), default='active')
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'area_name': self.area_name,
            'area_code': self.area_code,
            'location': self.location,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class WorkAreaAssignment(Base):
    __tablename__ = 't_construction_work_assignment'

    id = Column(Integer, primary_key=True, autoincrement=True)
    work_area_id = Column(Integer, ForeignKey('t_construction_work_area.id'), nullable=False)
    worker_id = Column(Integer, ForeignKey('t_construction_worker.id'), nullable=False)
    date = Column(Date, nullable=False)
    task = Column(String(500))
    status = Column(String(20), default='assigned')
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'work_area_id': self.work_area_id,
            'worker_id': self.worker_id,
            'date': self.date.isoformat() if self.date else None,
            'task': self.task,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class WorkAreaProgress(Base):
    __tablename__ = 't_construction_work_progress'

    id = Column(Integer, primary_key=True, autoincrement=True)
    work_area_id = Column(Integer, ForeignKey('t_construction_work_area.id'), nullable=False)
    date = Column(Date, nullable=False)
    progress = Column(Numeric(5, 2), default=0.00)
    completed_amount = Column(Numeric(10, 2), default=0.00)
    unit = Column(String(20))
    remark = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'work_area_id': self.work_area_id,
            'date': self.date.isoformat() if self.date else None,
            'progress': float(self.progress) if self.progress else 0.00,
            'completed_amount': float(self.completed_amount) if self.completed_amount else 0.00,
            'unit': self.unit,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class WorkVolumeRecord(Base):
    __tablename__ = 't_construction_work_volume'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, nullable=False)
    work_type = Column(String(50), nullable=False)
    work_type_name = Column(String(100))
    date = Column(Date, nullable=False)
    area_id = Column(Integer)
    quantity = Column(Numeric(10, 2), nullable=False)
    unit = Column(String(20), nullable=False)
    loss = Column(Numeric(10, 2), default=0.00)
    loss_rate = Column(Numeric(5, 2), default=0.00)
    remark = Column(String(500))
    created_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'work_type': self.work_type,
            'work_type_name': self.work_type_name,
            'date': self.date.isoformat() if self.date else None,
            'area_id': self.area_id,
            'quantity': float(self.quantity) if self.quantity else 0.00,
            'unit': self.unit,
            'loss': float(self.loss) if self.loss else 0.00,
            'loss_rate': float(self.loss_rate) if self.loss_rate else 0.00,
            'remark': self.remark,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Material(Base):
    __tablename__ = 't_construction_material'

    id = Column(Integer, primary_key=True, autoincrement=True)
    material_name = Column(String(200), nullable=False)
    material_code = Column(String(50))
    unit = Column(String(20), nullable=False)
    spec = Column(String(200))
    price = Column(Numeric(10, 2), default=0.00)
    stock = Column(Numeric(10, 2), default=0.00)
    min_stock = Column(Numeric(10, 2), default=0.00)
    status = Column(String(20), default='active')
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'material_name': self.material_name,
            'material_code': self.material_code,
            'unit': self.unit,
            'spec': self.spec,
            'price': float(self.price) if self.price else 0.00,
            'stock': float(self.stock) if self.stock else 0.00,
            'min_stock': float(self.min_stock) if self.min_stock else 0.00,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class MaterialRecord(Base):
    __tablename__ = 't_construction_material_record'

    id = Column(Integer, primary_key=True, autoincrement=True)
    material_id = Column(Integer, ForeignKey('t_construction_material.id'), nullable=False)
    project_id = Column(Integer, nullable=False)
    record_type = Column(String(20), nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False)
    price = Column(Numeric(10, 2), default=0.00)
    total_amount = Column(Numeric(12, 2), default=0.00)
    warehouse = Column(String(100))
    operator = Column(String(100))
    remark = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'material_id': self.material_id,
            'project_id': self.project_id,
            'record_type': self.record_type,
            'quantity': float(self.quantity) if self.quantity else 0.00,
            'price': float(self.price) if self.price else 0.00,
            'total_amount': float(self.total_amount) if self.total_amount else 0.00,
            'warehouse': self.warehouse,
            'operator': self.operator,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class SafetyCheck(Base):
    __tablename__ = 't_construction_safety_check'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, nullable=False)
    check_date = Column(Date, nullable=False)
    check_type = Column(String(50))
    area_id = Column(Integer)
    check_items = Column(JSON)
    found_issues = Column(Integer, default=0)
    status = Column(String(20), default='pending')
    checker = Column(String(100))
    remark = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'check_date': self.check_date.isoformat() if self.check_date else None,
            'check_type': self.check_type,
            'area_id': self.area_id,
            'check_items': self.check_items,
            'found_issues': self.found_issues or 0,
            'status': self.status,
            'checker': self.checker,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class SafetyIssue(Base):
    __tablename__ = 't_construction_safety_issue'

    id = Column(Integer, primary_key=True, autoincrement=True)
    check_id = Column(Integer, ForeignKey('t_construction_safety_check.id'))
    project_id = Column(Integer, nullable=False)
    area_id = Column(Integer)
    issue_type = Column(String(50))
    severity = Column(String(20), default='medium')
    description = Column(Text)
    location = Column(String(200))
    status = Column(String(20), default='pending')
    rectify_deadline = Column(Date)
    rectify_by = Column(String(100))
    rectify_result = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'check_id': self.check_id,
            'project_id': self.project_id,
            'area_id': self.area_id,
            'issue_type': self.issue_type,
            'severity': self.severity,
            'description': self.description,
            'location': self.location,
            'status': self.status,
            'rectify_deadline': self.rectify_deadline.isoformat() if self.rectify_deadline else None,
            'rectify_by': self.rectify_by,
            'rectify_result': self.rectify_result,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class QualityCheck(Base):
    __tablename__ = 't_construction_quality_check'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, nullable=False)
    check_date = Column(Date, nullable=False)
    check_type = Column(String(50))
    area_id = Column(Integer)
    work_stage = Column(String(100))
    check_items = Column(JSON)
    pass_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)
    status = Column(String(20), default='pending')
    checker = Column(String(100))
    remark = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'check_date': self.check_date.isoformat() if self.check_date else None,
            'check_type': self.check_type,
            'area_id': self.area_id,
            'work_stage': self.work_stage,
            'check_items': self.check_items,
            'pass_count': self.pass_count or 0,
            'fail_count': self.fail_count or 0,
            'status': self.status,
            'checker': self.checker,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class ConstructionSite(Base):
    __tablename__ = 't_field_site'

    id = Column(Integer, primary_key=True, autoincrement=True)
    site_name = Column(String(200), nullable=False)
    location = Column(String(500))
    contract_no = Column(String(100), unique=True)
    contract_unit_price = Column(Numeric(10, 2), default=0.00)
    contract_total_amount = Column(Numeric(12, 2), default=0.00)
    contract_total_volume = Column(Numeric(12, 2), default=0.00)
    forecast_volume = Column(Numeric(12, 2), default=0.00)
    start_date = Column(Date)
    end_date = Column(Date)
    status = Column(String(20), default='in_progress')
    remark = Column(String(1000))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'site_name': self.site_name,
            'location': self.location,
            'contract_no': self.contract_no,
            'contract_unit_price': float(self.contract_unit_price) if self.contract_unit_price else 0.00,
            'contract_total_amount': float(self.contract_total_amount) if self.contract_total_amount else 0.00,
            'contract_total_volume': float(self.contract_total_volume) if self.contract_total_volume else 0.00,
            'forecast_volume': float(self.forecast_volume) if self.forecast_volume else 0.00,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'status': self.status,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class WorkerSalary(Base):
    __tablename__ = 't_field_worker_salary'

    id = Column(Integer, primary_key=True, autoincrement=True)
    worker_id = Column(Integer, ForeignKey('t_construction_worker.id'), nullable=False)
    salary_standard = Column(Numeric(10, 2), nullable=False)
    salary_type = Column(String(20), default='daily')
    position = Column(String(100))
    join_date = Column(Date, nullable=False)
    leave_date = Column(Date)
    site_id = Column(Integer, ForeignKey('t_field_site.id'))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'worker_id': self.worker_id,
            'salary_standard': float(self.salary_standard) if self.salary_standard else 0.00,
            'salary_type': self.salary_type,
            'position': self.position,
            'join_date': self.join_date.isoformat() if self.join_date else None,
            'leave_date': self.leave_date.isoformat() if self.leave_date else None,
            'site_id': self.site_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class SalaryCalculation(Base):
    __tablename__ = 't_field_salary_calc'

    id = Column(Integer, primary_key=True, autoincrement=True)
    worker_id = Column(Integer, ForeignKey('t_construction_worker.id'), nullable=False)
    calc_period = Column(String(20), nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    base_salary = Column(Numeric(10, 2), default=0.00)
    overtime_salary = Column(Numeric(10, 2), default=0.00)
    leave_deduction = Column(Numeric(10, 2), default=0.00)
    piecework_salary = Column(Numeric(10, 2), default=0.00)
    total_salary = Column(Numeric(10, 2), default=0.00)
    paid_status = Column(String(20), default='unpaid')
    paid_date = Column(Date)
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'worker_id': self.worker_id,
            'calc_period': self.calc_period,
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
            'base_salary': float(self.base_salary) if self.base_salary else 0.00,
            'overtime_salary': float(self.overtime_salary) if self.overtime_salary else 0.00,
            'leave_deduction': float(self.leave_deduction) if self.leave_deduction else 0.00,
            'piecework_salary': float(self.piecework_salary) if self.piecework_salary else 0.00,
            'total_salary': float(self.total_salary) if self.total_salary else 0.00,
            'paid_status': self.paid_status,
            'paid_date': self.paid_date.isoformat() if self.paid_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class PlanWorkVolume(Base):
    __tablename__ = 't_field_plan_volume'

    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(Integer, ForeignKey('t_field_site.id'), nullable=False)
    work_type = Column(String(50), nullable=False)
    period_type = Column(String(20), default='daily')
    period_start = Column(Date, nullable=False)
    period_end = Column(Date)
    plan_volume = Column(Numeric(12, 2), nullable=False)
    unit = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'site_id': self.site_id,
            'work_type': self.work_type,
            'period_type': self.period_type,
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
            'plan_volume': float(self.plan_volume) if self.plan_volume else 0.00,
            'unit': self.unit,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class DailyWorkVolume(Base):
    __tablename__ = 't_field_daily_volume'

    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(Integer, ForeignKey('t_field_site.id'), nullable=False)
    work_type = Column(String(50), nullable=False)
    work_date = Column(Date, nullable=False)
    actual_volume = Column(Numeric(12, 2), nullable=False)
    unit = Column(String(20), nullable=False)
    reporter_id = Column(Integer, ForeignKey('t_construction_worker.id'))
    remark = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'site_id': self.site_id,
            'work_type': self.work_type,
            'work_date': self.work_date.isoformat() if self.work_date else None,
            'actual_volume': float(self.actual_volume) if self.actual_volume else 0.00,
            'unit': self.unit,
            'reporter_id': self.reporter_id,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class ExpenseCategory(Base):
    __tablename__ = 't_field_expense_category'

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_name = Column(String(100), nullable=False)
    category_code = Column(String(50), unique=True)
    parent_id = Column(Integer, ForeignKey('t_field_expense_category.id'))
    sort_order = Column(Integer, default=0)
    status = Column(String(20), default='active')
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'category_name': self.category_name,
            'category_code': self.category_code,
            'parent_id': self.parent_id,
            'sort_order': self.sort_order,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class ExpenseRecord(Base):
    __tablename__ = 't_field_expense_record'

    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(Integer, ForeignKey('t_field_site.id'), nullable=False)
    category_id = Column(Integer, ForeignKey('t_field_expense_category.id'), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    expense_date = Column(Date, nullable=False)
    reporter_id = Column(Integer, ForeignKey('t_construction_worker.id'))
    remark = Column(String(1000))
    receipt_image = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'site_id': self.site_id,
            'category_id': self.category_id,
            'amount': float(self.amount) if self.amount else 0.00,
            'expense_date': self.expense_date.isoformat() if self.expense_date else None,
            'reporter_id': self.reporter_id,
            'remark': self.remark,
            'receipt_image': self.receipt_image,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Consumable(Base):
    __tablename__ = 't_field_consumable'

    id = Column(Integer, primary_key=True, autoincrement=True)
    consumable_name = Column(String(200), nullable=False)
    consumable_type = Column(String(50))
    spec = Column(String(200))
    unit = Column(String(20), nullable=False)
    stock = Column(Numeric(10, 2), default=0.00)
    min_stock = Column(Numeric(10, 2), default=0.00)
    status = Column(String(20), default='active')
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'consumable_name': self.consumable_name,
            'consumable_type': self.consumable_type,
            'spec': self.spec,
            'unit': self.unit,
            'stock': float(self.stock) if self.stock else 0.00,
            'min_stock': float(self.min_stock) if self.min_stock else 0.00,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ConsumableRecord(Base):
    __tablename__ = 't_field_consumable_record'

    id = Column(Integer, primary_key=True, autoincrement=True)
    consumable_id = Column(Integer, ForeignKey('t_field_consumable.id'), nullable=False)
    site_id = Column(Integer, ForeignKey('t_field_site.id'), nullable=False)
    record_type = Column(String(20), nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False)
    operator_id = Column(Integer, ForeignKey('t_construction_worker.id'))
    remark = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'consumable_id': self.consumable_id,
            'site_id': self.site_id,
            'record_type': self.record_type,
            'quantity': float(self.quantity) if self.quantity else 0.00,
            'operator_id': self.operator_id,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class EquipmentLease(Base):
    __tablename__ = 't_field_equipment_lease'

    id = Column(Integer, primary_key=True, autoincrement=True)
    equipment_name = Column(String(200), nullable=False)
    equipment_type = Column(String(50))
    equipment_no = Column(String(100))
    site_id = Column(Integer, ForeignKey('t_field_site.id'), nullable=False)
    lessor = Column(String(200))
    lease_start_date = Column(Date, nullable=False)
    lease_end_date = Column(Date, nullable=False)
    lease_unit_price = Column(Numeric(10, 2), default=0.00)
    lease_total_amount = Column(Numeric(12, 2), default=0.00)
    paid_amount = Column(Numeric(12, 2), default=0.00)
    unpaid_amount = Column(Numeric(12, 2), default=0.00)
    status = Column(String(20), default='leasing')
    remark = Column(String(1000))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'equipment_name': self.equipment_name,
            'equipment_type': self.equipment_type,
            'equipment_no': self.equipment_no,
            'site_id': self.site_id,
            'lessor': self.lessor,
            'lease_start_date': self.lease_start_date.isoformat() if self.lease_start_date else None,
            'lease_end_date': self.lease_end_date.isoformat() if self.lease_end_date else None,
            'lease_unit_price': float(self.lease_unit_price) if self.lease_unit_price else 0.00,
            'lease_total_amount': float(self.lease_total_amount) if self.lease_total_amount else 0.00,
            'paid_amount': float(self.paid_amount) if self.paid_amount else 0.00,
            'unpaid_amount': float(self.unpaid_amount) if self.unpaid_amount else 0.00,
            'status': self.status,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class FinancialRecord(Base):
    __tablename__ = 't_field_financial_record'

    id = Column(Integer, primary_key=True, autoincrement=True)
    record_type = Column(String(20), nullable=False)
    income_source = Column(String(50))
    expense_category = Column(String(50))
    amount = Column(Numeric(12, 2), nullable=False)
    record_date = Column(Date, nullable=False)
    site_id = Column(Integer, ForeignKey('t_field_site.id'))
    contract_no = Column(String(100))
    receivable_amount = Column(Numeric(12, 2), default=0.00)
    received_amount = Column(Numeric(12, 2), default=0.00)
    unpaid_amount = Column(Numeric(12, 2), default=0.00)
    overdue_days = Column(Integer, default=0)
    remark = Column(String(1000))
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'record_type': self.record_type,
            'income_source': self.income_source,
            'expense_category': self.expense_category,
            'amount': float(self.amount) if self.amount else 0.00,
            'record_date': self.record_date.isoformat() if self.record_date else None,
            'site_id': self.site_id,
            'contract_no': self.contract_no,
            'receivable_amount': float(self.receivable_amount) if self.receivable_amount else 0.00,
            'received_amount': float(self.received_amount) if self.received_amount else 0.00,
            'unpaid_amount': float(self.unpaid_amount) if self.unpaid_amount else 0.00,
            'overdue_days': self.overdue_days or 0,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class MessageInstruction(Base):
    __tablename__ = 't_field_message_instruction'

    id = Column(Integer, primary_key=True, autoincrement=True)
    instruction_type = Column(String(50), nullable=False)
    keyword = Column(String(100), nullable=False)
    template = Column(String(500))
    description = Column(String(500))
    enabled = Column(TinyInteger, default=1)
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'instruction_type': self.instruction_type,
            'keyword': self.keyword,
            'template': self.template,
            'description': self.description,
            'enabled': self.enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class OperationLog(Base):
    __tablename__ = 't_field_operation_log'

    id = Column(Integer, primary_key=True, autoincrement=True)
    operator_id = Column(Integer, ForeignKey('t_construction_worker.id'))
    operator_name = Column(String(100))
    operation_type = Column(String(50), nullable=False)
    operation_object = Column(String(200))
    operation_content = Column(String(1000))
    ip_address = Column(String(50))
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'operator_id': self.operator_id,
            'operator_name': self.operator_name,
            'operation_type': self.operation_type,
            'operation_object': self.operation_object,
            'operation_content': self.operation_content,
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }