from datetime import datetime, date
from sqlalchemy import and_, or_, func
from plugins.base.base_service import BaseService
from plugins.farm.models import *
import re
import uuid

class FarmService(BaseService):
    def __init__(self, db_session):
        super().__init__(db_session)

    def parse_message(self, message_text):
        patterns = {
            'livestock_entry': [(r'(?:进了|入栏)\s*(\d+)\s*(?:头|只)\s*(\S+)', ['quantity', 'breed'])],
            'livestock_birth': [(r'(?:生了|产仔)\s*(\d+)\s*(?:头|只)', ['quantity'])],
            'livestock_death': [(r'(?:死了|病死)\s*(\d+)\s*(?:头|只)', ['quantity'])],
            'livestock_sale': [(r'(?:卖了|出栏)\s*(\d+)\s*(?:头|只)', ['quantity'])],
            'feed_purchase': [(r'(?:采购|买)\s*(\S+)\s*(\d+)\s*(?:吨|袋)', ['feed_name', 'quantity'])],
            'feed_usage': [(r'(?:喂了|用了)\s*(\d+)\s*(?:公斤|斤)', ['quantity'])],
            'farm_expense': [(r'(维修费|水电费)\s*(\d+)', ['category', 'amount'])],
            'farm_order': [(r'(?:订单|预定|下单)\s*(\S+)\s*(\d+)\s*(?:头|只)', ['customer_name', 'quantity'])],
        }
        result = {"command_type": None, "params": {}}
        for cmd_type, cmd_patterns in patterns.items():
            for pattern, keys in cmd_patterns:
                match = re.search(pattern, message_text)
                if match:
                    result["command_type"] = cmd_type
                    for i, key in enumerate(keys):
                        result["params"][key] = match.group(i+1)
                    return result
        if "存栏" in message_text or "统计" in message_text or "多少" in message_text:
            result["command_type"] = "farm_stats"
        return result

    def add_livestock_entry(self, breed, quantity, unit="头", source=None, purchase_price=0.00, batch=None, operator=None, remark=None):
        entry = LivestockEntry(breed=breed, breed_name=self._get_breed_name(breed), quantity=int(quantity), unit=unit, source=source, purchase_price=float(purchase_price), total_amount=float(quantity)*float(purchase_price), batch=batch, operator=operator, remark=remark)
        self.db.add(entry)
        self.db.commit()
        return entry.to_dict()

    def add_livestock_birth(self, breed, quantity, unit="只", mother_id=None, survival_count=None, operator=None, remark=None):
        birth = LivestockBirth(mother_id=mother_id, breed=breed, breed_name=self._get_breed_name(breed), quantity=int(quantity), unit=unit, survival_count=int(survival_count) if survival_count else int(quantity), operator=operator, remark=remark)
        self.db.add(birth)
        self.db.commit()
        return birth.to_dict()

    def add_livestock_death(self, breed, quantity, unit="头", cause=None, processing_method=None, operator=None, remark=None):
        death = LivestockDeath(breed=breed, breed_name=self._get_breed_name(breed), quantity=int(quantity), unit=unit, cause=cause, processing_method=processing_method, operator=operator, remark=remark)
        self.db.add(death)
        self.db.commit()
        return death.to_dict()

    def add_livestock_sale(self, breed, quantity, unit="头", weight=0.00, unit_price=0.00, customer_id=None, customer_name=None, slaughter=0, logistics=None, logistics_no=None, operator=None, remark=None):
        sale = LivestockSale(breed=breed, breed_name=self._get_breed_name(breed), quantity=int(quantity), unit=unit, weight=float(weight), unit_price=float(unit_price), total_amount=float(quantity)*float(unit_price), customer_id=customer_id, customer_name=customer_name, slaughter=slaughter, logistics=logistics, logistics_no=logistics_no, operator=operator, remark=remark)
        self.db.add(sale)
        self.db.commit()
        return sale.to_dict()

    def get_livestock_stats(self, period=None):
        today = date.today()
        start_date = None
        end_date = today
        if period == "today": start_date = today
        elif period == "week": start_date = today - datetime.timedelta(days=7)
        elif period == "month": start_date = today.replace(day=1)
        entry_filter = [LivestockEntry.entry_date <= end_date]
        birth_filter = [LivestockBirth.birth_date <= end_date]
        death_filter = [LivestockDeath.death_date <= end_date]
        sale_filter = [LivestockSale.sale_date <= end_date]
        if start_date:
            entry_filter.append(LivestockEntry.entry_date >= start_date)
            birth_filter.append(LivestockBirth.birth_date >= start_date)
            death_filter.append(LivestockDeath.death_date >= start_date)
            sale_filter.append(LivestockSale.sale_date >= start_date)
        total_entry = self.db.query(func.sum(LivestockEntry.quantity)).filter(*entry_filter).scalar() or 0
        total_birth = self.db.query(func.sum(LivestockBirth.survival_count)).filter(*birth_filter).scalar() or 0
        total_death = self.db.query(func.sum(LivestockDeath.quantity)).filter(*death_filter).scalar() or 0
        total_sale = self.db.query(func.sum(LivestockSale.quantity)).filter(*sale_filter).scalar() or 0
        all_entry = self.db.query(func.sum(LivestockEntry.quantity)).scalar() or 0
        all_birth = self.db.query(func.sum(LivestockBirth.survival_count)).scalar() or 0
        all_death = self.db.query(func.sum(LivestockDeath.quantity)).scalar() or 0
        all_sale = self.db.query(func.sum(LivestockSale.quantity)).scalar() or 0
        inventory = all_entry + all_birth - all_death - all_sale
        return {"period": period or "all", "inventory": inventory, "total_entry": all_entry, "total_birth": all_birth, "total_death": all_death, "total_sale": all_sale, "period_entry": total_entry, "period_birth": total_birth, "period_death": total_death, "period_sale": total_sale, "date_range": {"start": start_date.isoformat() if start_date else None, "end": end_date.isoformat()}}

    def add_feed_purchase(self, feed_name, quantity, unit="吨", unit_price=0.00, supplier=None, operator=None, remark=None):
        feed = self.db.query(Feed).filter(Feed.feed_name == feed_name).first()
        if not feed:
            feed = Feed(feed_name=feed_name, unit=unit, price=float(unit_price), stock=0)
            self.db.add(feed)
            self.db.commit()
        purchase = FeedPurchase(feed_id=feed.id, feed_name=feed_name, quantity=float(quantity), unit=unit, unit_price=float(unit_price), total_amount=float(quantity)*float(unit_price), supplier=supplier, operator=operator, remark=remark)
        self.db.add(purchase)
        feed.stock = float(feed.stock or 0) + float(quantity)
        self.db.commit()
        return purchase.to_dict()

    def add_feed_usage(self, feed_name, quantity, unit="公斤", pen_no=None, breed=None, operator=None, remark=None):
        feed = self.db.query(Feed).filter(Feed.feed_name == feed_name).first()
        if not feed:
            feed = Feed(feed_name=feed_name, unit=unit, stock=0)
            self.db.add(feed)
        usage = FeedUsage(feed_id=feed.id, feed_name=feed_name, quantity=float(quantity), unit=unit, pen_no=pen_no, breed=breed, operator=operator, remark=remark)
        self.db.add(usage)
        feed.stock = max(0, (feed.stock or 0) - float(quantity))
        self.db.commit()
        return usage.to_dict()

    def get_feed_stats(self, period=None):
        today = date.today()
        start_date = None
        end_date = today
        if period == "today": start_date = today
        elif period == "week": start_date = today - datetime.timedelta(days=7)
        elif period == "month": start_date = today.replace(day=1)
        purchase_filter = [FeedPurchase.purchase_date <= end_date]
        usage_filter = [FeedUsage.usage_date <= end_date]
        if start_date:
            purchase_filter.append(FeedPurchase.purchase_date >= start_date)
            usage_filter.append(FeedUsage.usage_date >= start_date)
        total_purchase = self.db.query(func.sum(FeedPurchase.total_amount)).filter(*purchase_filter).scalar() or 0
        total_usage_qty = self.db.query(func.sum(FeedUsage.quantity)).filter(*usage_filter).scalar() or 0
        total_stock = self.db.query(func.sum(Feed.stock)).scalar() or 0
        return {"period": period or "all", "total_stock": float(total_stock), "period_purchase_amount": float(total_purchase), "period_usage_quantity": float(total_usage_qty), "date_range": {"start": start_date.isoformat() if start_date else None, "end": end_date.isoformat()}}

    def add_expense(self, category_name, amount, description=None, receipt_image=None, operator=None, remark=None):
        category = self.db.query(ExpenseCategory).filter(ExpenseCategory.category_name == category_name).first()
        if not category:
            category = ExpenseCategory(category_name=category_name, category_code=category_name[:10].upper())
            self.db.add(category)
            self.db.commit()
        expense = ExpenseRecord(category_id=category.id, category_name=category_name, amount=float(amount), description=description, receipt_image=receipt_image, operator=operator, remark=remark)
        self.db.add(expense)
        self.db.commit()
        return expense.to_dict()

    def get_expense_stats(self, period=None):
        today = date.today()
        start_date = None
        end_date = today
        if period == "today": start_date = today
        elif period == "week": start_date = today - datetime.timedelta(days=7)
        elif period == "month": start_date = today.replace(day=1)
        expense_filter = [ExpenseRecord.expense_date <= end_date]
        if start_date: expense_filter.append(ExpenseRecord.expense_date >= start_date)
        total_expense = self.db.query(func.sum(ExpenseRecord.amount)).filter(*expense_filter).scalar() or 0
        category_stats = self.db.query(ExpenseRecord.category_name, func.sum(ExpenseRecord.amount)).filter(*expense_filter).group_by(ExpenseRecord.category_name).all()
        return {"period": period or "all", "total_expense": float(total_expense), "category_stats": [{"category_name": name, "amount": float(amount)} for name, amount in category_stats], "date_range": {"start": start_date.isoformat() if start_date else None, "end": end_date.isoformat()}}

    def create_order(self, customer_name, breed, quantity, unit="头", phone=None, slaughter=0, logistics=None, unit_price=0.00, operator=None, remark=None):
        order_no = f"FD{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:6].upper()}"
        customer = self.db.query(Customer).filter(Customer.customer_name == customer_name).first()
        customer_id = customer.id if customer else None
        price = self._calculate_price(breed, quantity, float(unit_price))
        order = FarmOrder(order_no=order_no, customer_id=customer_id, customer_name=customer_name, phone=phone, breed=breed, breed_name=self._get_breed_name(breed), quantity=int(quantity), unit=unit, unit_price=price, total_amount=price*int(quantity), slaughter=slaughter, logistics=logistics, unpaid_amount=price*int(quantity), operator=operator, remark=remark)
        self.db.add(order)
        self.db.commit()
        return order.to_dict()

    def get_order_stats(self, period=None):
        today = date.today()
        start_date = None
        end_date = today
        if period == "today": start_date = today
        elif period == "week": start_date = today - datetime.timedelta(days=7)
        elif period == "month": start_date = today.replace(day=1)
        order_filter = [FarmOrder.order_date <= end_date]
        if start_date: order_filter.append(FarmOrder.order_date >= start_date)
        total_orders = self.db.query(func.count(FarmOrder.id)).filter(*order_filter).scalar() or 0
        total_amount = self.db.query(func.sum(FarmOrder.total_amount)).filter(*order_filter).scalar() or 0
        status_stats = self.db.query(FarmOrder.status, func.count(FarmOrder.id)).filter(*order_filter).group_by(FarmOrder.status).all()
        return {"period": period or "all", "total_orders": total_orders, "total_amount": float(total_amount), "status_stats": [{"status": status, "count": count} for status, count in status_stats], "date_range": {"start": start_date.isoformat() if start_date else None, "end": end_date.isoformat()}}

    def add_customer(self, customer_name, phone=None, wechat=None, address=None, customer_type=None, purchase_preference=None, remark=None):
        customer = Customer(customer_name=customer_name, phone=phone, wechat=wechat, address=address, customer_type=customer_type, purchase_preference=purchase_preference, remark=remark)
        self.db.add(customer)
        self.db.commit()
        return customer.to_dict()

    def add_customer_appointment(self, customer_name, appointment_date, purpose=None, breed=None, quantity=None, host=None, remark=None):
        customer = self.db.query(Customer).filter(Customer.customer_name == customer_name).first()
        customer_id = customer.id if customer else None
        appointment = CustomerAppointment(customer_id=customer_id, customer_name=customer_name, phone=customer.phone if customer else None, appointment_date=appointment_date, purpose=purpose, breed=breed, quantity=int(quantity) if quantity else None, host=host, remark=remark)
        self.db.add(appointment)
        self.db.commit()
        return appointment.to_dict()

    def add_employee(self, name, phone=None, id_card=None, position=None, department=None, join_date=None, remark=None):
        employee = FarmEmployee(name=name, phone=phone, id_card=id_card, position=position, department=department, join_date=join_date, remark=remark)
        self.db.add(employee)
        self.db.commit()
        return employee.to_dict()

    def add_attendance(self, employee_id, date, check_in_time=None, check_out_time=None, work_hours=0.00, remark=None):
        attendance = EmployeeAttendance(employee_id=employee_id, date=date, check_in_time=check_in_time, check_out_time=check_out_time, work_hours=float(work_hours), remark=remark)
        self.db.add(attendance)
        self.db.commit()
        return attendance.to_dict()

    def add_salary(self, employee_id, salary_standard, salary_type="monthly", position=None, effective_date=None):
        salary = EmployeeSalary(employee_id=employee_id, salary_standard=float(salary_standard), salary_type=salary_type, position=position, effective_date=effective_date or date.today())
        self.db.add(salary)
        self.db.commit()
        return salary.to_dict()

    def add_vaccine(self, vaccine_name, spec=None, unit="瓶", stock=0.00, min_stock=0.00, expiry_date=None, manufacturer=None, remark=None):
        vaccine = Vaccine(vaccine_name=vaccine_name, spec=spec, unit=unit, stock=float(stock), min_stock=float(min_stock), expiry_date=expiry_date, manufacturer=manufacturer)
        self.db.add(vaccine)
        self.db.commit()
        return vaccine.to_dict()

    def add_immunization(self, vaccine_name, breed, quantity, batch=None, next_immunization_date=None, operator=None, remark=None):
        vaccine = self.db.query(Vaccine).filter(Vaccine.vaccine_name == vaccine_name).first()
        if not vaccine:
            vaccine = Vaccine(vaccine_name=vaccine_name, unit="瓶", stock=0)
            self.db.add(vaccine)
        immunization = ImmunizationRecord(vaccine_id=vaccine.id, vaccine_name=vaccine_name, breed=breed, batch=batch, quantity=int(quantity), next_immunization_date=next_immunization_date, operator=operator, remark=remark)
        self.db.add(immunization)
        vaccine.stock = max(0, (vaccine.stock or 0) - float(quantity))
        self.db.commit()
        return immunization.to_dict()

    def add_disease_record(self, breed, symptom, diagnosis=None, treatment=None, quantity=1, operator=None, remark=None):
        disease = DiseaseRecord(breed=breed, symptom=symptom, diagnosis=diagnosis, treatment=treatment, quantity=int(quantity), operator=operator, remark=remark)
        self.db.add(disease)
        self.db.commit()
        return disease.to_dict()

    def add_pricing_rule(self, breed, base_price, unit="斤", min_quantity=0, discount_rate=1.00, effective_date=None, expire_date=None, remark=None):
        rule = PricingRule(breed=breed, breed_name=self._get_breed_name(breed), unit=unit, base_price=float(base_price), min_quantity=int(min_quantity), discount_rate=float(discount_rate), effective_date=effective_date, expire_date=expire_date, remark=remark)
        self.db.add(rule)
        self.db.commit()
        return rule.to_dict()

    def _calculate_price(self, breed, quantity, default_price=0.00):
        today = date.today()
        rules = self.db.query(PricingRule).filter(PricingRule.breed == breed, PricingRule.status == "active", or_(PricingRule.effective_date.is_(None), PricingRule.effective_date <= today), or_(PricingRule.expire_date.is_(None), PricingRule.expire_date >= today)).order_by(PricingRule.min_quantity.desc()).all()
        for rule in rules:
            if int(quantity) >= rule.min_quantity:
                return rule.base_price * rule.discount_rate
        return default_price if default_price > 0 else 10.00

    def _get_breed_name(self, breed_code):
        breed_map = {"pig": "猪", "piglet": "仔猪", "sow": "母猪", "boar": "公猪", "chicken": "鸡", "chick": "鸡苗", "hen": "母鸡", "rooster": "公鸡", "duck": "鸭", "duckling": "鸭苗", "cow": "牛", "calf": "牛犊", "cow_milk": "奶牛", "sheep": "羊", "lamb": "羊羔", "goat": "山羊"}
        return breed_map.get(breed_code.lower(), breed_code)

    def get_farm_summary(self, period=None):
        return {"livestock": self.get_livestock_stats(period), "feed": self.get_feed_stats(period), "expense": self.get_expense_stats(period), "order": self.get_order_stats(period), "period": period or "all"}

    def process_message(self, message_data):
        cmd_type = message_data.get("command_type")
        params = message_data.get("params", {})
        handlers = {
            "livestock_entry": lambda: self.add_livestock_entry(**params),
            "livestock_birth": lambda: self.add_livestock_birth(**params),
            "livestock_death": lambda: self.add_livestock_death(**params),
            "livestock_sale": lambda: self.add_livestock_sale(**params),
            "feed_purchase": lambda: self.add_feed_purchase(**params),
            "feed_usage": lambda: self.add_feed_usage(**params),
            "farm_expense": lambda: self.add_expense(**params),
            "farm_order": lambda: self.create_order(**params),
            "farm_stats": lambda: self.get_farm_summary(params.get("period")),
        }
        handler = handlers.get(cmd_type)
        if handler:
            return {"success": True, "data": handler()}
        else:
            return {"success": False, "error": "Unknown command type"}

    def generate_report(self, report_type, date_range):
        if report_type == "daily": return self.get_farm_summary("today")
        elif report_type == "weekly": return self.get_farm_summary("week")
        elif report_type == "monthly": return self.get_farm_summary("month")
        elif report_type == "inventory": return self.get_livestock_stats()
        elif report_type == "expense": return self.get_expense_stats(date_range.get("period"))
        elif report_type == "sales": return self.get_order_stats(date_range.get("period"))
        else: return self.get_farm_summary()

    def get_stats(self, period):
        return self.get_farm_summary(period)