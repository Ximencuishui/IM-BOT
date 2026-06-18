from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Date, Time, Text, ForeignKey, JSON
from sqlalchemy.types import SMALLINT as TinyInteger
from database.db_config import Base


class Livestock(Base):
    __tablename__ = 't_farm_livestock'

    id = Column(Integer, primary_key=True, autoincrement=True)
    livestock_no = Column(String(50), unique=True)
    breed = Column(String(100), nullable=False)
    breed_name = Column(String(100))
    category = Column(String(50))
    batch = Column(String(50))
    source = Column(String(200))
    entry_date = Column(Date)
    birth_date = Column(Date)
    gender = Column(String(10))
    initial_weight = Column(Numeric(10, 2))
    current_weight = Column(Numeric(10, 2))
    pen_no = Column(String(50))
    status = Column(String(20), default='active')
    remark = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'livestock_no': self.livestock_no,
            'breed': self.breed,
            'breed_name': self.breed_name,
            'category': self.category,
            'batch': self.batch,
            'source': self.source,
            'entry_date': self.entry_date.isoformat() if self.entry_date else None,
            'birth_date': self.birth_date.isoformat() if self.birth_date else None,
            'gender': self.gender,
            'initial_weight': float(self.initial_weight) if self.initial_weight else 0.00,
            'current_weight': float(self.current_weight) if self.current_weight else 0.00,
            'pen_no': self.pen_no,
            'status': self.status,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class LivestockEntry(Base):
    __tablename__ = 't_farm_livestock_entry'

    id = Column(Integer, primary_key=True, autoincrement=True)
    breed = Column(String(100), nullable=False)
    breed_name = Column(String(100))
    quantity = Column(Integer, nullable=False)
    unit = Column(String(20), default='头')
    source = Column(String(200))
    purchase_price = Column(Numeric(10, 2), default=0.00)
    total_amount = Column(Numeric(12, 2), default=0.00)
    batch = Column(String(50))
    entry_date = Column(Date, default=datetime.now().date())
    operator = Column(String(100))
    remark = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'breed': self.breed,
            'breed_name': self.breed_name,
            'quantity': self.quantity,
            'unit': self.unit,
            'source': self.source,
            'purchase_price': float(self.purchase_price) if self.purchase_price else 0.00,
            'total_amount': float(self.total_amount) if self.total_amount else 0.00,
            'batch': self.batch,
            'entry_date': self.entry_date.isoformat() if self.entry_date else None,
            'operator': self.operator,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class LivestockBirth(Base):
    __tablename__ = 't_farm_livestock_birth'

    id = Column(Integer, primary_key=True, autoincrement=True)
    mother_id = Column(Integer)
    breed = Column(String(100), nullable=False)
    breed_name = Column(String(100))
    quantity = Column(Integer, nullable=False)
    unit = Column(String(20), default='只')
    birth_date = Column(Date, default=datetime.now().date())
    survival_count = Column(Integer, default=0)
    operator = Column(String(100))
    remark = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'mother_id': self.mother_id,
            'breed': self.breed,
            'breed_name': self.breed_name,
            'quantity': self.quantity,
            'unit': self.unit,
            'birth_date': self.birth_date.isoformat() if self.birth_date else None,
            'survival_count': self.survival_count,
            'operator': self.operator,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class LivestockDeath(Base):
    __tablename__ = 't_farm_livestock_death'

    id = Column(Integer, primary_key=True, autoincrement=True)
    breed = Column(String(100), nullable=False)
    breed_name = Column(String(100))
    quantity = Column(Integer, nullable=False)
    unit = Column(String(20), default='头')
    death_date = Column(Date, default=datetime.now().date())
    cause = Column(String(200))
    processing_method = Column(String(200))
    operator = Column(String(100))
    remark = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'breed': self.breed,
            'breed_name': self.breed_name,
            'quantity': self.quantity,
            'unit': self.unit,
            'death_date': self.death_date.isoformat() if self.death_date else None,
            'cause': self.cause,
            'processing_method': self.processing_method,
            'operator': self.operator,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class LivestockSale(Base):
    __tablename__ = 't_farm_livestock_sale'

    id = Column(Integer, primary_key=True, autoincrement=True)
    breed = Column(String(100), nullable=False)
    breed_name = Column(String(100))
    quantity = Column(Integer, nullable=False)
    unit = Column(String(20), default='头')
    weight = Column(Numeric(10, 2), default=0.00)
    weight_unit = Column(String(20), default='公斤')
    unit_price = Column(Numeric(10, 2), default=0.00)
    total_amount = Column(Numeric(12, 2), default=0.00)
    customer_id = Column(Integer)
    customer_name = Column(String(100))
    sale_date = Column(Date, default=datetime.now().date())
    slaughter = Column(TinyInteger, default=0)
    logistics = Column(String(100))
    logistics_no = Column(String(100))
    operator = Column(String(100))
    remark = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'breed': self.breed,
            'breed_name': self.breed_name,
            'quantity': self.quantity,
            'unit': self.unit,
            'weight': float(self.weight) if self.weight else 0.00,
            'weight_unit': self.weight_unit,
            'unit_price': float(self.unit_price) if self.unit_price else 0.00,
            'total_amount': float(self.total_amount) if self.total_amount else 0.00,
            'customer_id': self.customer_id,
            'customer_name': self.customer_name,
            'sale_date': self.sale_date.isoformat() if self.sale_date else None,
            'slaughter': self.slaughter,
            'logistics': self.logistics,
            'logistics_no': self.logistics_no,
            'operator': self.operator,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class LivestockWeightRecord(Base):
    __tablename__ = 't_farm_livestock_weight'

    id = Column(Integer, primary_key=True, autoincrement=True)
    livestock_id = Column(Integer, ForeignKey('t_farm_livestock.id'))
    record_date = Column(Date, default=datetime.now().date())
    weight = Column(Numeric(10, 2), nullable=False)
    operator = Column(String(100))
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'livestock_id': self.livestock_id,
            'record_date': self.record_date.isoformat() if self.record_date else None,
            'weight': float(self.weight) if self.weight else 0.00,
            'operator': self.operator,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Feed(Base):
    __tablename__ = 't_farm_feed'

    id = Column(Integer, primary_key=True, autoincrement=True)
    feed_name = Column(String(200), nullable=False)
    feed_code = Column(String(50))
    feed_type = Column(String(50))
    spec = Column(String(200))
    unit = Column(String(20), nullable=False)
    price = Column(Numeric(10, 2), default=0.00)
    stock = Column(Numeric(10, 2), default=0.00)
    min_stock = Column(Numeric(10, 2), default=0.00)
    status = Column(String(20), default='active')
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'feed_name': self.feed_name,
            'feed_code': self.feed_code,
            'feed_type': self.feed_type,
            'spec': self.spec,
            'unit': self.unit,
            'price': float(self.price) if self.price else 0.00,
            'stock': float(self.stock) if self.stock else 0.00,
            'min_stock': float(self.min_stock) if self.min_stock else 0.00,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class FeedPurchase(Base):
    __tablename__ = 't_farm_feed_purchase'

    id = Column(Integer, primary_key=True, autoincrement=True)
    feed_id = Column(Integer, ForeignKey('t_farm_feed.id'), nullable=False)
    feed_name = Column(String(200))
    quantity = Column(Numeric(10, 2), nullable=False)
    unit = Column(String(20), default='吨')
    unit_price = Column(Numeric(10, 2), default=0.00)
    total_amount = Column(Numeric(12, 2), default=0.00)
    supplier = Column(String(200))
    purchase_date = Column(Date, default=datetime.now().date())
    operator = Column(String(100))
    remark = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'feed_id': self.feed_id,
            'feed_name': self.feed_name,
            'quantity': float(self.quantity) if self.quantity else 0.00,
            'unit': self.unit,
            'unit_price': float(self.unit_price) if self.unit_price else 0.00,
            'total_amount': float(self.total_amount) if self.total_amount else 0.00,
            'supplier': self.supplier,
            'purchase_date': self.purchase_date.isoformat() if self.purchase_date else None,
            'operator': self.operator,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class FeedUsage(Base):
    __tablename__ = 't_farm_feed_usage'

    id = Column(Integer, primary_key=True, autoincrement=True)
    feed_id = Column(Integer, ForeignKey('t_farm_feed.id'), nullable=False)
    feed_name = Column(String(200))
    quantity = Column(Numeric(10, 2), nullable=False)
    unit = Column(String(20), default='公斤')
    usage_date = Column(Date, default=datetime.now().date())
    pen_no = Column(String(50))
    breed = Column(String(100))
    operator = Column(String(100))
    remark = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'feed_id': self.feed_id,
            'feed_name': self.feed_name,
            'quantity': float(self.quantity) if self.quantity else 0.00,
            'unit': self.unit,
            'usage_date': self.usage_date.isoformat() if self.usage_date else None,
            'pen_no': self.pen_no,
            'breed': self.breed,
            'operator': self.operator,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Customer(Base):
    __tablename__ = 't_farm_customer'

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_name = Column(String(200), nullable=False)
    phone = Column(String(20))
    wechat = Column(String(100))
    address = Column(String(500))
    customer_type = Column(String(50))
    purchase_preference = Column(String(500))
    remark = Column(String(1000))
    status = Column(String(20), default='active')
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'customer_name': self.customer_name,
            'phone': self.phone,
            'wechat': self.wechat,
            'address': self.address,
            'customer_type': self.customer_type,
            'purchase_preference': self.purchase_preference,
            'remark': self.remark,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class CustomerAppointment(Base):
    __tablename__ = 't_farm_customer_appointment'

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey('t_farm_customer.id'), nullable=False)
    customer_name = Column(String(200))
    phone = Column(String(20))
    appointment_date = Column(Date, nullable=False)
    appointment_time = Column(Time)
    purpose = Column(String(200))
    breed = Column(String(100))
    quantity = Column(Integer)
    host = Column(String(100))
    status = Column(String(20), default='pending')
    remark = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'customer_name': self.customer_name,
            'phone': self.phone,
            'appointment_date': self.appointment_date.isoformat() if self.appointment_date else None,
            'appointment_time': str(self.appointment_time) if self.appointment_time else None,
            'purpose': self.purpose,
            'breed': self.breed,
            'quantity': self.quantity,
            'host': self.host,
            'status': self.status,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class CustomerFollowup(Base):
    __tablename__ = 't_farm_customer_followup'

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey('t_farm_customer.id'), nullable=False)
    followup_date = Column(Date, default=datetime.now().date())
    followup_content = Column(Text)
    followup_result = Column(String(200))
    next_followup_date = Column(Date)
    operator = Column(String(100))
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'followup_date': self.followup_date.isoformat() if self.followup_date else None,
            'followup_content': self.followup_content,
            'followup_result': self.followup_result,
            'next_followup_date': self.next_followup_date.isoformat() if self.next_followup_date else None,
            'operator': self.operator,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class FarmOrder(Base):
    __tablename__ = 't_farm_order'

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(50), unique=True)
    customer_id = Column(Integer, ForeignKey('t_farm_customer.id'))
    customer_name = Column(String(200))
    phone = Column(String(20))
    breed = Column(String(100), nullable=False)
    breed_name = Column(String(100))
    quantity = Column(Integer, nullable=False)
    unit = Column(String(20), default='头')
    weight = Column(Numeric(10, 2), default=0.00)
    weight_unit = Column(String(20), default='公斤')
    unit_price = Column(Numeric(10, 2), default=0.00)
    total_amount = Column(Numeric(12, 2), default=0.00)
    slaughter = Column(TinyInteger, default=0)
    slaughter_date = Column(Date)
    logistics = Column(String(100))
    logistics_no = Column(String(100))
    status = Column(String(20), default='pending')
    order_date = Column(Date, default=datetime.now().date())
    delivery_date = Column(Date)
    received_amount = Column(Numeric(12, 2), default=0.00)
    unpaid_amount = Column(Numeric(12, 2), default=0.00)
    operator = Column(String(100))
    remark = Column(String(1000))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'order_no': self.order_no,
            'customer_id': self.customer_id,
            'customer_name': self.customer_name,
            'phone': self.phone,
            'breed': self.breed,
            'breed_name': self.breed_name,
            'quantity': self.quantity,
            'unit': self.unit,
            'weight': float(self.weight) if self.weight else 0.00,
            'weight_unit': self.weight_unit,
            'unit_price': float(self.unit_price) if self.unit_price else 0.00,
            'total_amount': float(self.total_amount) if self.total_amount else 0.00,
            'slaughter': self.slaughter,
            'slaughter_date': self.slaughter_date.isoformat() if self.slaughter_date else None,
            'logistics': self.logistics,
            'logistics_no': self.logistics_no,
            'status': self.status,
            'order_date': self.order_date.isoformat() if self.order_date else None,
            'delivery_date': self.delivery_date.isoformat() if self.delivery_date else None,
            'received_amount': float(self.received_amount) if self.received_amount else 0.00,
            'unpaid_amount': float(self.unpaid_amount) if self.unpaid_amount else 0.00,
            'operator': self.operator,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class FarmEmployee(Base):
    __tablename__ = 't_farm_employee'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20))
    id_card = Column(String(20))
    position = Column(String(100))
    department = Column(String(100))
    join_date = Column(Date)
    leave_date = Column(Date)
    status = Column(String(20), default='active')
    remark = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'id_card': self.id_card,
            'position': self.position,
            'department': self.department,
            'join_date': self.join_date.isoformat() if self.join_date else None,
            'leave_date': self.leave_date.isoformat() if self.leave_date else None,
            'status': self.status,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class EmployeeAttendance(Base):
    __tablename__ = 't_farm_employee_attendance'

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey('t_farm_employee.id'), nullable=False)
    date = Column(Date, nullable=False)
    check_in_time = Column(Time)
    check_out_time = Column(Time)
    work_hours = Column(Numeric(5, 2), default=0.00)
    status = Column(String(20), default='normal')
    remark = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'date': self.date.isoformat() if self.date else None,
            'check_in_time': str(self.check_in_time) if self.check_in_time else None,
            'check_out_time': str(self.check_out_time) if self.check_out_time else None,
            'work_hours': float(self.work_hours) if self.work_hours else 0.00,
            'status': self.status,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class EmployeeSalary(Base):
    __tablename__ = 't_farm_employee_salary'

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey('t_farm_employee.id'), nullable=False)
    salary_standard = Column(Numeric(10, 2), nullable=False)
    salary_type = Column(String(20), default='monthly')
    position = Column(String(100))
    effective_date = Column(Date, nullable=False)
    end_date = Column(Date)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'salary_standard': float(self.salary_standard) if self.salary_standard else 0.00,
            'salary_type': self.salary_type,
            'position': self.position,
            'effective_date': self.effective_date.isoformat() if self.effective_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class SalaryCalculation(Base):
    __tablename__ = 't_farm_salary_calc'

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey('t_farm_employee.id'), nullable=False)
    calc_period = Column(String(20), nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    base_salary = Column(Numeric(10, 2), default=0.00)
    overtime_salary = Column(Numeric(10, 2), default=0.00)
    bonus = Column(Numeric(10, 2), default=0.00)
    deduction = Column(Numeric(10, 2), default=0.00)
    total_salary = Column(Numeric(10, 2), default=0.00)
    paid_status = Column(String(20), default='unpaid')
    paid_date = Column(Date)
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'calc_period': self.calc_period,
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
            'base_salary': float(self.base_salary) if self.base_salary else 0.00,
            'overtime_salary': float(self.overtime_salary) if self.overtime_salary else 0.00,
            'bonus': float(self.bonus) if self.bonus else 0.00,
            'deduction': float(self.deduction) if self.deduction else 0.00,
            'total_salary': float(self.total_salary) if self.total_salary else 0.00,
            'paid_status': self.paid_status,
            'paid_date': self.paid_date.isoformat() if self.paid_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class ExpenseCategory(Base):
    __tablename__ = 't_farm_expense_category'

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_name = Column(String(100), nullable=False)
    category_code = Column(String(50), unique=True)
    parent_id = Column(Integer, ForeignKey('t_farm_expense_category.id'))
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
    __tablename__ = 't_farm_expense_record'

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(Integer, ForeignKey('t_farm_expense_category.id'), nullable=False)
    category_name = Column(String(100))
    amount = Column(Numeric(10, 2), nullable=False)
    expense_date = Column(Date, default=datetime.now().date())
    description = Column(String(1000))
    receipt_image = Column(String(500))
    operator = Column(String(100))
    remark = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'category_id': self.category_id,
            'category_name': self.category_name,
            'amount': float(self.amount) if self.amount else 0.00,
            'expense_date': self.expense_date.isoformat() if self.expense_date else None,
            'description': self.description,
            'receipt_image': self.receipt_image,
            'operator': self.operator,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Vaccine(Base):
    __tablename__ = 't_farm_vaccine'

    id = Column(Integer, primary_key=True, autoincrement=True)
    vaccine_name = Column(String(200), nullable=False)
    vaccine_code = Column(String(50))
    spec = Column(String(200))
    unit = Column(String(20), nullable=False)
    stock = Column(Numeric(10, 2), default=0.00)
    min_stock = Column(Numeric(10, 2), default=0.00)
    expiry_date = Column(Date)
    manufacturer = Column(String(200))
    status = Column(String(20), default='active')
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'vaccine_name': self.vaccine_name,
            'vaccine_code': self.vaccine_code,
            'spec': self.spec,
            'unit': self.unit,
            'stock': float(self.stock) if self.stock else 0.00,
            'min_stock': float(self.min_stock) if self.min_stock else 0.00,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'manufacturer': self.manufacturer,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ImmunizationRecord(Base):
    __tablename__ = 't_farm_immunization_record'

    id = Column(Integer, primary_key=True, autoincrement=True)
    vaccine_id = Column(Integer, ForeignKey('t_farm_vaccine.id'), nullable=False)
    vaccine_name = Column(String(200))
    breed = Column(String(100))
    batch = Column(String(50))
    quantity = Column(Integer, nullable=False)
    immunization_date = Column(Date, default=datetime.now().date())
    next_immunization_date = Column(Date)
    operator = Column(String(100))
    remark = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'vaccine_id': self.vaccine_id,
            'vaccine_name': self.vaccine_name,
            'breed': self.breed,
            'batch': self.batch,
            'quantity': self.quantity,
            'immunization_date': self.immunization_date.isoformat() if self.immunization_date else None,
            'next_immunization_date': self.next_immunization_date.isoformat() if self.next_immunization_date else None,
            'operator': self.operator,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class DiseaseRecord(Base):
    __tablename__ = 't_farm_disease_record'

    id = Column(Integer, primary_key=True, autoincrement=True)
    breed = Column(String(100))
    batch = Column(String(50))
    symptom = Column(Text)
    diagnosis = Column(String(200))
    treatment = Column(Text)
    quantity = Column(Integer, default=1)
    onset_date = Column(Date, default=datetime.now().date())
    recovery_date = Column(Date)
    status = Column(String(20), default='treatment')
    operator = Column(String(100))
    remark = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'breed': self.breed,
            'batch': self.batch,
            'symptom': self.symptom,
            'diagnosis': self.diagnosis,
            'treatment': self.treatment,
            'quantity': self.quantity,
            'onset_date': self.onset_date.isoformat() if self.onset_date else None,
            'recovery_date': self.recovery_date.isoformat() if self.recovery_date else None,
            'status': self.status,
            'operator': self.operator,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class FarmInstruction(Base):
    __tablename__ = 't_farm_instruction'

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


class PricingRule(Base):
    __tablename__ = 't_farm_pricing_rule'

    id = Column(Integer, primary_key=True, autoincrement=True)
    breed = Column(String(100), nullable=False)
    breed_name = Column(String(100))
    unit = Column(String(20), default='斤')
    base_price = Column(Numeric(10, 2), default=0.00)
    min_quantity = Column(Integer, default=0)
    discount_rate = Column(Numeric(5, 2), default=1.00)
    effective_date = Column(Date)
    expire_date = Column(Date)
    status = Column(String(20), default='active')
    remark = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'breed': self.breed,
            'breed_name': self.breed_name,
            'unit': self.unit,
            'base_price': float(self.base_price) if self.base_price else 0.00,
            'min_quantity': self.min_quantity,
            'discount_rate': float(self.discount_rate) if self.discount_rate else 1.00,
            'effective_date': self.effective_date.isoformat() if self.effective_date else None,
            'expire_date': self.expire_date.isoformat() if self.expire_date else None,
            'status': self.status,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
