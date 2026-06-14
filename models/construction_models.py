"""
工地管理数据模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Date, Time, Text, ForeignKey, JSON
from sqlalchemy.types import SMALLINT as TinyInteger
from database.db_config import Base


class Worker(Base):
    """工人表"""
    __tablename__ = 't_construction_worker'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True, comment='工人ID')
    name = Column(String(100), nullable=False, comment='工人姓名')
    phone = Column(String(20), comment='联系电话')
    id_card = Column(String(20), comment='身份证号')
    face_image = Column(String(500), comment='人脸图片路径')
    team = Column(String(100), comment='所属班组')
    position = Column(String(100), comment='工种')
    status = Column(String(20), default='active', comment='状态：active/inactive/leave')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

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
    """考勤记录表"""
    __tablename__ = 't_construction_attendance'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True, comment='记录ID')
    worker_id = Column(Integer, ForeignKey('t_construction_worker.id'), nullable=False, comment='工人ID')
    date = Column(Date, nullable=False, comment='日期')
    check_in_time = Column(Time, comment='上班时间')
    check_out_time = Column(Time, comment='下班时间')
    work_hours = Column(Numeric(5, 2), default=0.00, comment='工作时长')
    overtime_hours = Column(Numeric(5, 2), default=0.00, comment='加班时长')
    check_in_location = Column(String(200), comment='上班打卡位置')
    check_out_location = Column(String(200), comment='下班打卡位置')
    status = Column(String(20), default='normal', comment='状态：normal/late/early/absent')
    remark = Column(String(500), comment='备注')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')

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
    """请假记录表"""
    __tablename__ = 't_construction_leave'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True, comment='请假ID')
    worker_id = Column(Integer, ForeignKey('t_construction_worker.id'), nullable=False, comment='工人ID')
    start_date = Column(Date, nullable=False, comment='开始日期')
    end_date = Column(Date, nullable=False, comment='结束日期')
    leave_days = Column(Integer, default=1, comment='请假天数')
    leave_type = Column(String(20), default='personal', comment='类型：personal/sick/other')
    reason = Column(String(500), comment='请假原因')
    status = Column(String(20), default='pending', comment='状态：pending/approved/rejected')
    approved_by = Column(String(100), comment='审批人')
    approved_at = Column(DateTime, comment='审批时间')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')

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
    """天气记录表"""
    __tablename__ = 't_construction_weather'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True, comment='记录ID')
    project_id = Column(Integer, nullable=False, comment='项目ID')
    date = Column(Date, nullable=False, comment='日期')
    weather = Column(String(100), comment='天气状况')
    temperature = Column(String(50), comment='温度')
    humidity = Column(String(20), comment='湿度')
    wind = Column(String(100), comment='风力风向')
    rain = Column(String(20), comment='降雨量')
    warning = Column(String(100), comment='预警信息')
    impact = Column(String(500), comment='对施工的影响')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')

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
    """项目工期计划表"""
    __tablename__ = 't_construction_schedule'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True, comment='计划ID')
    project_id = Column(Integer, nullable=False, comment='项目ID')
    task_name = Column(String(200), nullable=False, comment='任务名称')
    start_date = Column(Date, nullable=False, comment='计划开始日期')
    end_date = Column(Date, nullable=False, comment='计划结束日期')
    actual_start_date = Column(Date, comment='实际开始日期')
    actual_end_date = Column(Date, comment='实际结束日期')
    progress = Column(Numeric(5, 2), default=0.00, comment='进度百分比')
    status = Column(String(20), default='pending', comment='状态：pending/in_progress/completed/delayed')
    is_critical = Column(TinyInteger, default=0, comment='是否关键节点')
    responsible = Column(String(100), comment='负责人')
    remark = Column(String(500), comment='备注')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

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
    """工作面表"""
    __tablename__ = 't_construction_work_area'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True, comment='工作面ID')
    project_id = Column(Integer, nullable=False, comment='项目ID')
    area_name = Column(String(200), nullable=False, comment='工作面名称')
    area_code = Column(String(50), comment='工作面编号')
    location = Column(String(200), comment='位置')
    status = Column(String(20), default='active', comment='状态：active/inactive/completed')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

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
    """工作面人员安排表"""
    __tablename__ = 't_construction_work_assignment'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True, comment='安排ID')
    work_area_id = Column(Integer, ForeignKey('t_construction_work_area.id'), nullable=False, comment='工作面ID')
    worker_id = Column(Integer, ForeignKey('t_construction_worker.id'), nullable=False, comment='工人ID')
    date = Column(Date, nullable=False, comment='日期')
    task = Column(String(500), comment='任务描述')
    status = Column(String(20), default='assigned', comment='状态：assigned/started/completed')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')

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
    """工作面进度记录表"""
    __tablename__ = 't_construction_work_progress'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True, comment='进度ID')
    work_area_id = Column(Integer, ForeignKey('t_construction_work_area.id'), nullable=False, comment='工作面ID')
    date = Column(Date, nullable=False, comment='日期')
    progress = Column(Numeric(5, 2), default=0.00, comment='进度百分比')
    completed_amount = Column(Numeric(10, 2), default=0.00, comment='完成量')
    unit = Column(String(20), comment='单位')
    remark = Column(String(500), comment='备注')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')

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
    """工程量记录表"""
    __tablename__ = 't_construction_work_volume'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True, comment='记录ID')
    project_id = Column(Integer, nullable=False, comment='项目ID')
    work_type = Column(String(50), nullable=False, comment='工程类型：earthwork/concrete/rebar/brickwork')
    work_type_name = Column(String(100), comment='工程类型名称')
    date = Column(Date, nullable=False, comment='日期')
    area_id = Column(Integer, comment='工作面ID')
    quantity = Column(Numeric(10, 2), nullable=False, comment='工程量')
    unit = Column(String(20), nullable=False, comment='单位')
    loss = Column(Numeric(10, 2), default=0.00, comment='损耗量')
    loss_rate = Column(Numeric(5, 2), default=0.00, comment='损耗率')
    remark = Column(String(500), comment='备注')
    created_by = Column(String(100), comment='记录人')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')

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
    """材料表"""
    __tablename__ = 't_construction_material'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True, comment='材料ID')
    material_name = Column(String(200), nullable=False, comment='材料名称')
    material_code = Column(String(50), comment='材料编码')
    unit = Column(String(20), nullable=False, comment='单位')
    spec = Column(String(200), comment='规格型号')
    price = Column(Numeric(10, 2), default=0.00, comment='单价')
    stock = Column(Numeric(10, 2), default=0.00, comment='库存量')
    min_stock = Column(Numeric(10, 2), default=0.00, comment='最低库存')
    status = Column(String(20), default='active', comment='状态：active/inactive')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

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
    """材料出入库记录表"""
    __tablename__ = 't_construction_material_record'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True, comment='记录ID')
    material_id = Column(Integer, ForeignKey('t_construction_material.id'), nullable=False, comment='材料ID')
    project_id = Column(Integer, nullable=False, comment='项目ID')
    record_type = Column(String(20), nullable=False, comment='类型：in/out')
    quantity = Column(Numeric(10, 2), nullable=False, comment='数量')
    price = Column(Numeric(10, 2), default=0.00, comment='单价')
    total_amount = Column(Numeric(12, 2), default=0.00, comment='总金额')
    warehouse = Column(String(100), comment='仓库')
    operator = Column(String(100), comment='操作人')
    remark = Column(String(500), comment='备注')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')

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
    """安全检查表"""
    __tablename__ = 't_construction_safety_check'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True, comment='检查ID')
    project_id = Column(Integer, nullable=False, comment='项目ID')
    check_date = Column(Date, nullable=False, comment='检查日期')
    check_type = Column(String(50), comment='检查类型：daily/weekly/monthly/special')
    area_id = Column(Integer, comment='工作面ID')
    check_items = Column(JSON, comment='检查项目')
    found_issues = Column(Integer, default=0, comment='发现问题数')
    status = Column(String(20), default='pending', comment='状态：pending/processing/completed')
    checker = Column(String(100), comment='检查人')
    remark = Column(String(500), comment='备注')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')

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
    """安全隐患表"""
    __tablename__ = 't_construction_safety_issue'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True, comment='隐患ID')
    check_id = Column(Integer, ForeignKey('t_construction_safety_check.id'), comment='检查ID')
    project_id = Column(Integer, nullable=False, comment='项目ID')
    area_id = Column(Integer, comment='工作面ID')
    issue_type = Column(String(50), comment='隐患类型')
    severity = Column(String(20), default='medium', comment='严重程度：low/medium/high/critical')
    description = Column(Text, comment='隐患描述')
    location = Column(String(200), comment='位置')
    status = Column(String(20), default='pending', comment='状态：pending/processing/completed')
    rectify_deadline = Column(Date, comment='整改期限')
    rectify_by = Column(String(100), comment='整改责任人')
    rectify_result = Column(Text, comment='整改结果')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

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
    """质量检查表"""
    __tablename__ = 't_construction_quality_check'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True, comment='检查ID')
    project_id = Column(Integer, nullable=False, comment='项目ID')
    check_date = Column(Date, nullable=False, comment='检查日期')
    check_type = Column(String(50), comment='检查类型：inspection/acceptance')
    area_id = Column(Integer, comment='工作面ID')
    work_stage = Column(String(100), comment='施工阶段')
    check_items = Column(JSON, comment='检查项目')
    pass_count = Column(Integer, default=0, comment='合格项数')
    fail_count = Column(Integer, default=0, comment='不合格项数')
    status = Column(String(20), default='pending', comment='状态：pending/passed/failed')
    checker = Column(String(100), comment='检查人')
    remark = Column(String(500), comment='备注')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')

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
