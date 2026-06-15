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