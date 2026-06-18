import json
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional

from plugins.base.base_service import BaseService
from plugins.construction.models import (
    Worker, AttendanceRecord, LeaveRecord, WeatherRecord, ProjectSchedule,
    WorkArea, WorkAreaAssignment, WorkAreaProgress, WorkVolumeRecord,
    Material, MaterialRecord, SafetyCheck, SafetyIssue, QualityCheck,
    ConstructionSite, WorkerSalary, SalaryCalculation, PlanWorkVolume,
    DailyWorkVolume, ExpenseCategory, ExpenseRecord, Consumable,
    ConsumableRecord, EquipmentLease, FinancialRecord, MessageInstruction,
    OperationLog
)

logger = logging.getLogger(__name__)


class ConstructionService(BaseService):

    def create_worker(self, worker_data: Dict) -> Dict:
        try:
            worker = Worker(
                name=worker_data['name'],
                phone=worker_data.get('phone', ''),
                id_card=worker_data.get('id_card', ''),
                face_image=worker_data.get('face_image', ''),
                team=worker_data.get('team', ''),
                position=worker_data.get('position', ''),
                status=worker_data.get('status', 'active'),
            )
            self.db.add(worker)
            self.db.commit()
            self.db.refresh(worker)
            return {'success': True, 'data': worker.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def list_workers(self, team: Optional[str] = None, position: Optional[str] = None) -> List[Dict]:
        query = self.db.query(Worker).filter(Worker.status == 'active')
        if team:
            query = query.filter(Worker.team == team)
        if position:
            query = query.filter(Worker.position == position)
        return [w.to_dict() for w in query.all()]

    def check_in(self, worker_id: int, location: Optional[str] = None) -> Dict:
        worker = self.db.query(Worker).filter(Worker.id == worker_id).first()
        if not worker:
            return {'success': False, 'error': '工人不存在'}

        today = date.today()
        existing_record = self.db.query(AttendanceRecord).filter(
            AttendanceRecord.worker_id == worker_id,
            AttendanceRecord.date == today
        ).first()

        now = datetime.now().time()
        status = 'normal'
        if now.hour > 8:
            status = 'late'

        try:
            if existing_record:
                existing_record.check_in_time = now
                existing_record.check_in_location = location
                existing_record.status = status
            else:
                record = AttendanceRecord(
                    worker_id=worker_id,
                    date=today,
                    check_in_time=now,
                    check_in_location=location,
                    status=status,
                )
                self.db.add(record)

            self.db.commit()
            return {'success': True, 'message': '打卡成功'}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def check_out(self, worker_id: int, location: Optional[str] = None) -> Dict:
        worker = self.db.query(Worker).filter(Worker.id == worker_id).first()
        if not worker:
            return {'success': False, 'error': '工人不存在'}

        today = date.today()
        record = self.db.query(AttendanceRecord).filter(
            AttendanceRecord.worker_id == worker_id,
            AttendanceRecord.date == today
        ).first()

        if not record:
            return {'success': False, 'error': '未找到今日打卡记录'}

        try:
            now = datetime.now().time()
            record.check_out_time = now
            record.check_out_location = location

            if record.check_in_time:
                check_in = datetime.combine(date.today(), record.check_in_time)
                check_out = datetime.combine(date.today(), now)
                work_hours = (check_out - check_in).total_seconds() / 3600
                record.work_hours = work_hours

                if work_hours > 8:
                    record.overtime_hours = work_hours - 8

            self.db.commit()
            return {'success': True, 'message': '下班成功'}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def list_attendance(self, worker_id: Optional[int] = None, date_str: Optional[str] = None) -> List[Dict]:
        query = self.db.query(AttendanceRecord)
        if worker_id:
            query = query.filter(AttendanceRecord.worker_id == worker_id)
        if date_str:
            query = query.filter(AttendanceRecord.date == date_str)
        return [a.to_dict() for a in query.order_by(AttendanceRecord.date.desc()).all()]

    def apply_leave(self, leave_data: Dict) -> Dict:
        try:
            leave = LeaveRecord(
                worker_id=leave_data['worker_id'],
                start_date=leave_data['start_date'],
                end_date=leave_data['end_date'],
                leave_type=leave_data.get('leave_type', 'personal'),
                reason=leave_data.get('reason', ''),
            )
            self.db.add(leave)
            self.db.commit()
            self.db.refresh(leave)
            return {'success': True, 'data': leave.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def approve_leave(self, leave_id: int, approved: bool, approved_by: str) -> Dict:
        leave = self.db.query(LeaveRecord).filter(LeaveRecord.id == leave_id).first()
        if not leave:
            return {'success': False, 'error': '请假记录不存在'}

        try:
            leave.status = 'approved' if approved else 'rejected'
            leave.approved_by = approved_by
            leave.approved_at = datetime.now()
            self.db.commit()
            self.db.refresh(leave)
            return {'success': True, 'data': leave.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def create_weather(self, weather_data: Dict) -> Dict:
        try:
            weather = WeatherRecord(
                project_id=weather_data['project_id'],
                date=weather_data.get('date', date.today()),
                weather=weather_data.get('weather', ''),
                temperature=weather_data.get('temperature', ''),
                humidity=weather_data.get('humidity', ''),
                wind=weather_data.get('wind', ''),
                rain=weather_data.get('rain', ''),
                warning=weather_data.get('warning', ''),
                impact=weather_data.get('impact', ''),
            )
            self.db.add(weather)
            self.db.commit()
            self.db.refresh(weather)
            return {'success': True, 'data': weather.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def list_weather(self, project_id: int, date_str: Optional[str] = None) -> List[Dict]:
        query = self.db.query(WeatherRecord).filter(WeatherRecord.project_id == project_id)
        if date_str:
            query = query.filter(WeatherRecord.date == date_str)
        return [w.to_dict() for w in query.order_by(WeatherRecord.date.desc()).all()]

    def create_schedule(self, schedule_data: Dict) -> Dict:
        try:
            schedule = ProjectSchedule(
                project_id=schedule_data['project_id'],
                task_name=schedule_data['task_name'],
                start_date=schedule_data['start_date'],
                end_date=schedule_data['end_date'],
                is_critical=schedule_data.get('is_critical', 0),
                responsible=schedule_data.get('responsible', ''),
                remark=schedule_data.get('remark', ''),
            )
            self.db.add(schedule)
            self.db.commit()
            self.db.refresh(schedule)
            return {'success': True, 'data': schedule.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def update_schedule_progress(self, schedule_id: int, progress: float,
                                 actual_start_date: Optional[str] = None,
                                 actual_end_date: Optional[str] = None) -> Dict:
        schedule = self.db.query(ProjectSchedule).filter(ProjectSchedule.id == schedule_id).first()
        if not schedule:
            return {'success': False, 'error': '计划不存在'}

        try:
            schedule.progress = progress
            if actual_start_date:
                schedule.actual_start_date = actual_start_date
            if actual_end_date:
                schedule.actual_end_date = actual_end_date

            if progress >= 100:
                schedule.status = 'completed'
            elif progress > 0:
                schedule.status = 'in_progress'

            self.db.commit()
            self.db.refresh(schedule)
            return {'success': True, 'data': schedule.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def list_schedules(self, project_id: int) -> List[Dict]:
        return [s.to_dict() for s in self.db.query(ProjectSchedule).filter(
            ProjectSchedule.project_id == project_id
        ).order_by(ProjectSchedule.start_date).all()]

    def create_work_area(self, area_data: Dict) -> Dict:
        try:
            area = WorkArea(
                project_id=area_data['project_id'],
                area_name=area_data['area_name'],
                area_code=area_data.get('area_code', ''),
                location=area_data.get('location', ''),
            )
            self.db.add(area)
            self.db.commit()
            self.db.refresh(area)
            return {'success': True, 'data': area.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def assign_worker(self, work_area_id: int, worker_id: int, date_str: str, task: str) -> Dict:
        try:
            assignment = WorkAreaAssignment(
                work_area_id=work_area_id,
                worker_id=worker_id,
                date=date_str,
                task=task,
            )
            self.db.add(assignment)
            self.db.commit()
            self.db.refresh(assignment)
            return {'success': True, 'data': assignment.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def record_progress(self, work_area_id: int, date_str: str, progress: float,
                        completed_amount: float, unit: str) -> Dict:
        try:
            progress_record = WorkAreaProgress(
                work_area_id=work_area_id,
                date=date_str,
                progress=progress,
                completed_amount=completed_amount,
                unit=unit,
            )
            self.db.add(progress_record)
            self.db.commit()
            self.db.refresh(progress_record)
            return {'success': True, 'data': progress_record.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def create_work_volume(self, volume_data: Dict) -> Dict:
        try:
            volume = WorkVolumeRecord(
                project_id=volume_data['project_id'],
                work_type=volume_data['work_type'],
                work_type_name=volume_data.get('work_type_name', ''),
                date=volume_data.get('date', date.today()),
                area_id=volume_data.get('area_id'),
                quantity=volume_data['quantity'],
                unit=volume_data['unit'],
                loss=volume_data.get('loss', 0),
                loss_rate=volume_data.get('loss_rate', 0),
                remark=volume_data.get('remark', ''),
                created_by=volume_data.get('created_by', ''),
            )
            self.db.add(volume)
            self.db.commit()
            self.db.refresh(volume)
            return {'success': True, 'data': volume.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def list_work_volume(self, project_id: int, work_type: Optional[str] = None,
                         date_str: Optional[str] = None) -> List[Dict]:
        query = self.db.query(WorkVolumeRecord).filter(WorkVolumeRecord.project_id == project_id)
        if work_type:
            query = query.filter(WorkVolumeRecord.work_type == work_type)
        if date_str:
            query = query.filter(WorkVolumeRecord.date == date_str)
        return [v.to_dict() for v in query.order_by(WorkVolumeRecord.date.desc()).all()]

    def create_material(self, material_data: Dict) -> Dict:
        try:
            material = Material(
                material_name=material_data['material_name'],
                material_code=material_data.get('material_code', ''),
                unit=material_data['unit'],
                spec=material_data.get('spec', ''),
                price=material_data.get('price', 0),
                stock=material_data.get('stock', 0),
                min_stock=material_data.get('min_stock', 0),
            )
            self.db.add(material)
            self.db.commit()
            self.db.refresh(material)
            return {'success': True, 'data': material.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def material_in(self, material_id: int, project_id: int, quantity: float,
                    price: float, operator: str) -> Dict:
        material = self.db.query(Material).filter(Material.id == material_id).first()
        if not material:
            return {'success': False, 'error': '材料不存在'}

        try:
            record = MaterialRecord(
                material_id=material_id,
                project_id=project_id,
                record_type='in',
                quantity=quantity,
                price=price,
                total_amount=quantity * price,
                operator=operator,
            )
            material.stock += quantity

            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
            return {'success': True, 'data': record.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def material_out(self, material_id: int, project_id: int, quantity: float,
                     operator: str) -> Dict:
        material = self.db.query(Material).filter(Material.id == material_id).first()
        if not material:
            return {'success': False, 'error': '材料不存在'}

        if material.stock < quantity:
            return {'success': False, 'error': '库存不足'}

        try:
            record = MaterialRecord(
                material_id=material_id,
                project_id=project_id,
                record_type='out',
                quantity=quantity,
                price=material.price,
                total_amount=quantity * material.price,
                operator=operator,
            )
            material.stock -= quantity

            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
            return {'success': True, 'data': record.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def create_safety_check(self, check_data: Dict) -> Dict:
        try:
            check = SafetyCheck(
                project_id=check_data['project_id'],
                check_date=check_data.get('check_date', date.today()),
                check_type=check_data.get('check_type', 'daily'),
                area_id=check_data.get('area_id'),
                check_items=json.dumps(check_data.get('check_items', [])),
                found_issues=check_data.get('found_issues', 0),
                checker=check_data.get('checker', ''),
                remark=check_data.get('remark', ''),
            )
            self.db.add(check)
            self.db.commit()
            self.db.refresh(check)
            return {'success': True, 'data': check.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def create_safety_issue(self, issue_data: Dict) -> Dict:
        try:
            issue = SafetyIssue(
                check_id=issue_data.get('check_id'),
                project_id=issue_data['project_id'],
                area_id=issue_data.get('area_id'),
                issue_type=issue_data.get('issue_type', ''),
                severity=issue_data.get('severity', 'medium'),
                description=issue_data['description'],
                location=issue_data.get('location', ''),
                rectify_deadline=issue_data.get('rectify_deadline'),
                rectify_by=issue_data.get('rectify_by', ''),
            )
            self.db.add(issue)
            self.db.commit()
            self.db.refresh(issue)
            return {'success': True, 'data': issue.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def create_quality_check(self, check_data: Dict) -> Dict:
        try:
            check = QualityCheck(
                project_id=check_data['project_id'],
                check_date=check_data.get('check_date', date.today()),
                check_type=check_data.get('check_type', 'inspection'),
                area_id=check_data.get('area_id'),
                work_stage=check_data.get('work_stage', ''),
                check_items=json.dumps(check_data.get('check_items', [])),
                pass_count=check_data.get('pass_count', 0),
                fail_count=check_data.get('fail_count', 0),
                checker=check_data.get('checker', ''),
                remark=check_data.get('remark', ''),
            )

            total = check.pass_count + check.fail_count
            if total > 0:
                check.status = 'passed' if check.pass_count == total else 'failed'

            self.db.add(check)
            self.db.commit()
            self.db.refresh(check)
            return {'success': True, 'data': check.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def generate_report(self, report_type: str, date_range: Optional[str] = None) -> Dict:
        if not date_range:
            date_str = date.today().isoformat()
        else:
            date_str = date_range

        attendance_records = self.db.query(AttendanceRecord).filter(
            AttendanceRecord.date == date_str
        ).all()

        weather_record = self.db.query(WeatherRecord).filter(
            WeatherRecord.date == date_str
        ).first()

        progress_records = self.db.query(WorkAreaProgress).filter(
            WorkAreaProgress.date == date_str
        ).all()

        volume_records = self.db.query(WorkVolumeRecord).filter(
            WorkVolumeRecord.date == date_str
        ).all()

        schedule_records = self.db.query(ProjectSchedule).all()

        report = {
            'date': date_str,
            'attendance': {
                'total': len(attendance_records),
                'checked_in': len([r for r in attendance_records if r.check_in_time]),
                'checked_out': len([r for r in attendance_records if r.check_out_time]),
            },
            'weather': weather_record.to_dict() if weather_record else None,
            'progress': [p.to_dict() for p in progress_records],
            'work_volume': [v.to_dict() for v in volume_records],
            'schedule': {
                'total': len(schedule_records),
                'completed': len([s for s in schedule_records if s.status == 'completed']),
                'in_progress': len([s for s in schedule_records if s.status == 'in_progress']),
            },
        }

        return {'success': True, 'data': report}

    def get_stats(self, period: str = 'today') -> Dict:
        today = datetime.now().date()
        start_date = today

        if period == 'week':
            start_date = today - timedelta(days=7)
        elif period == 'month':
            start_date = today - timedelta(days=30)

        attendance_records = self.db.query(AttendanceRecord).filter(
            AttendanceRecord.date >= start_date
        ).all()

        safety_issues = self.db.query(SafetyIssue).filter(
            SafetyIssue.status == 'pending'
        ).all()

        work_volume_records = self.db.query(WorkVolumeRecord).filter(
            WorkVolumeRecord.date >= start_date
        ).all()

        return {
            'period': period,
            'total_workers': len(self.db.query(Worker).filter(Worker.status == 'active').all()),
            'attendance_count': len(attendance_records),
            'pending_safety_issues': len(safety_issues),
            'work_volume_count': len(work_volume_records),
        }

    def create_site(self, site_data: Dict) -> Dict:
        try:
            site = ConstructionSite(
                site_name=site_data['site_name'],
                location=site_data.get('location', ''),
                contract_no=site_data['contract_no'],
                contract_unit_price=site_data.get('contract_unit_price', 0),
                contract_total_amount=site_data.get('contract_total_amount', 0),
                contract_total_volume=site_data.get('contract_total_volume', 0),
                forecast_volume=site_data.get('forecast_volume', 0),
                start_date=site_data.get('start_date'),
                end_date=site_data.get('end_date'),
                status=site_data.get('status', 'in_progress'),
                remark=site_data.get('remark', ''),
            )
            self.db.add(site)
            self.db.commit()
            self.db.refresh(site)
            return {'success': True, 'data': site.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def list_sites(self, status: Optional[str] = None) -> List[Dict]:
        query = self.db.query(ConstructionSite)
        if status:
            query = query.filter(ConstructionSite.status == status)
        return [s.to_dict() for s in query.order_by(ConstructionSite.created_at.desc()).all()]

    def get_site(self, site_id: int) -> Dict:
        site = self.db.query(ConstructionSite).filter(ConstructionSite.id == site_id).first()
        if not site:
            return {'success': False, 'error': '工地不存在'}
        return {'success': True, 'data': site.to_dict()}

    def update_site(self, site_id: int, site_data: Dict) -> Dict:
        site = self.db.query(ConstructionSite).filter(ConstructionSite.id == site_id).first()
        if not site:
            return {'success': False, 'error': '工地不存在'}

        try:
            if 'site_name' in site_data:
                site.site_name = site_data['site_name']
            if 'location' in site_data:
                site.location = site_data['location']
            if 'contract_unit_price' in site_data:
                site.contract_unit_price = site_data['contract_unit_price']
            if 'contract_total_amount' in site_data:
                site.contract_total_amount = site_data['contract_total_amount']
            if 'contract_total_volume' in site_data:
                site.contract_total_volume = site_data['contract_total_volume']
            if 'forecast_volume' in site_data:
                site.forecast_volume = site_data['forecast_volume']
            if 'status' in site_data:
                site.status = site_data['status']
            if 'remark' in site_data:
                site.remark = site_data['remark']

            self.db.commit()
            self.db.refresh(site)
            return {'success': True, 'data': site.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def delete_site(self, site_id: int) -> Dict:
        site = self.db.query(ConstructionSite).filter(ConstructionSite.id == site_id).first()
        if not site:
            return {'success': False, 'error': '工地不存在'}

        try:
            self.db.delete(site)
            self.db.commit()
            return {'success': True, 'message': '删除成功'}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def set_worker_salary(self, salary_data: Dict) -> Dict:
        try:
            salary = WorkerSalary(
                worker_id=salary_data['worker_id'],
                salary_standard=salary_data['salary_standard'],
                salary_type=salary_data.get('salary_type', 'daily'),
                position=salary_data.get('position', ''),
                join_date=salary_data['join_date'],
                leave_date=salary_data.get('leave_date'),
                site_id=salary_data.get('site_id'),
            )
            self.db.add(salary)
            self.db.commit()
            self.db.refresh(salary)
            return {'success': True, 'data': salary.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def update_worker_salary(self, salary_id: int, salary_data: Dict) -> Dict:
        salary = self.db.query(WorkerSalary).filter(WorkerSalary.id == salary_id).first()
        if not salary:
            return {'success': False, 'error': '薪资记录不存在'}

        try:
            if 'salary_standard' in salary_data:
                salary.salary_standard = salary_data['salary_standard']
            if 'salary_type' in salary_data:
                salary.salary_type = salary_data['salary_type']
            if 'position' in salary_data:
                salary.position = salary_data['position']
            if 'site_id' in salary_data:
                salary.site_id = salary_data['site_id']
            if 'leave_date' in salary_data:
                salary.leave_date = salary_data['leave_date']

            self.db.commit()
            self.db.refresh(salary)
            return {'success': True, 'data': salary.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def calculate_salary(self, worker_id: int, period_start: date, period_end: date) -> Dict:
        salary_info = self.db.query(WorkerSalary).filter(
            WorkerSalary.worker_id == worker_id,
            WorkerSalary.leave_date.is_(None) | (WorkerSalary.leave_date >= period_start)
        ).order_by(WorkerSalary.id.desc()).first()

        if not salary_info:
            return {'success': False, 'error': '未找到薪资信息'}

        attendance_records = self.db.query(AttendanceRecord).filter(
            AttendanceRecord.worker_id == worker_id,
            AttendanceRecord.date >= period_start,
            AttendanceRecord.date <= period_end
        ).all()

        leave_records = self.db.query(LeaveRecord).filter(
            LeaveRecord.worker_id == worker_id,
            LeaveRecord.status == 'approved',
            LeaveRecord.start_date <= period_end,
            LeaveRecord.end_date >= period_start
        ).all()

        work_days = len(attendance_records)
        overtime_hours = sum(float(r.overtime_hours or 0) for r in attendance_records)

        leave_days = 0
        for leave in leave_records:
            overlap_start = max(leave.start_date, period_start)
            overlap_end = min(leave.end_date, period_end)
            if overlap_start <= overlap_end:
                leave_days += (overlap_end - overlap_start).days + 1

        base_salary = float(salary_info.salary_standard) * work_days
        overtime_salary = float(salary_info.salary_standard) * overtime_hours / 8 * 1.5
        leave_deduction = float(salary_info.salary_standard) * leave_days
        total_salary = base_salary + overtime_salary - leave_deduction

        try:
            calc_record = SalaryCalculation(
                worker_id=worker_id,
                calc_period='monthly',
                period_start=period_start,
                period_end=period_end,
                base_salary=base_salary,
                overtime_salary=overtime_salary,
                leave_deduction=leave_deduction,
                total_salary=total_salary,
            )
            self.db.add(calc_record)
            self.db.commit()
            self.db.refresh(calc_record)
            return {'success': True, 'data': calc_record.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def get_salary_report(self, period_start: date, period_end: date) -> Dict:
        records = self.db.query(SalaryCalculation).filter(
            SalaryCalculation.period_start >= period_start,
            SalaryCalculation.period_end <= period_end
        ).all()

        total_salary = sum(float(r.total_salary or 0) for r in records)
        total_workers = len(set(r.worker_id for r in records))

        return {
            'success': True,
            'data': {
                'period_start': period_start.isoformat(),
                'period_end': period_end.isoformat(),
                'total_workers': total_workers,
                'total_salary': round(total_salary, 2),
                'details': [r.to_dict() for r in records]
            }
        }

    def set_plan_volume(self, plan_data: Dict) -> Dict:
        try:
            plan = PlanWorkVolume(
                site_id=plan_data['site_id'],
                work_type=plan_data['work_type'],
                period_type=plan_data.get('period_type', 'daily'),
                period_start=plan_data['period_start'],
                period_end=plan_data.get('period_end'),
                plan_volume=plan_data['plan_volume'],
                unit=plan_data['unit'],
            )
            self.db.add(plan)
            self.db.commit()
            self.db.refresh(plan)
            return {'success': True, 'data': plan.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def report_daily_volume(self, volume_data: Dict) -> Dict:
        try:
            daily = DailyWorkVolume(
                site_id=volume_data['site_id'],
                work_type=volume_data['work_type'],
                work_date=volume_data.get('work_date', date.today()),
                actual_volume=volume_data['actual_volume'],
                unit=volume_data['unit'],
                reporter_id=volume_data.get('reporter_id'),
                remark=volume_data.get('remark', ''),
            )
            self.db.add(daily)
            self.db.commit()
            self.db.refresh(daily)
            return {'success': True, 'data': daily.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def get_work_volume_stats(self, site_id: int, period_start: date, period_end: date) -> Dict:
        plan_records = self.db.query(PlanWorkVolume).filter(
            PlanWorkVolume.site_id == site_id,
            PlanWorkVolume.period_start >= period_start,
            PlanWorkVolume.period_end <= period_end
        ).all()

        daily_records = self.db.query(DailyWorkVolume).filter(
            DailyWorkVolume.site_id == site_id,
            DailyWorkVolume.work_date >= period_start,
            DailyWorkVolume.work_date <= period_end
        ).all()

        plan_total = sum(float(p.plan_volume or 0) for p in plan_records)
        actual_total = sum(float(d.actual_volume or 0) for d in daily_records)

        deviation = 0
        if plan_total > 0:
            deviation = (actual_total - plan_total) / plan_total * 100

        work_types = {}
        for daily in daily_records:
            work_types[daily.work_type] = work_types.get(daily.work_type, 0) + float(daily.actual_volume or 0)

        return {
            'success': True,
            'data': {
                'site_id': site_id,
                'period_start': period_start.isoformat(),
                'period_end': period_end.isoformat(),
                'plan_total': round(plan_total, 2),
                'actual_total': round(actual_total, 2),
                'deviation': round(deviation, 2),
                'work_types': work_types,
                'details': [d.to_dict() for d in daily_records]
            }
        }

    def create_expense_category(self, category_data: Dict) -> Dict:
        try:
            category = ExpenseCategory(
                category_name=category_data['category_name'],
                category_code=category_data['category_code'],
                parent_id=category_data.get('parent_id'),
                sort_order=category_data.get('sort_order', 0),
                status=category_data.get('status', 'active'),
            )
            self.db.add(category)
            self.db.commit()
            self.db.refresh(category)
            return {'success': True, 'data': category.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def list_expense_categories(self) -> List[Dict]:
        return [c.to_dict() for c in self.db.query(ExpenseCategory).filter(
            ExpenseCategory.status == 'active'
        ).order_by(ExpenseCategory.sort_order).all()]

    def report_expense(self, expense_data: Dict) -> Dict:
        try:
            expense = ExpenseRecord(
                site_id=expense_data['site_id'],
                category_id=expense_data['category_id'],
                amount=expense_data['amount'],
                expense_date=expense_data.get('expense_date', date.today()),
                reporter_id=expense_data.get('reporter_id'),
                remark=expense_data.get('remark', ''),
                receipt_image=expense_data.get('receipt_image'),
            )
            self.db.add(expense)
            self.db.commit()
            self.db.refresh(expense)
            return {'success': True, 'data': expense.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def get_expense_report(self, site_id: int, period_start: date, period_end: date) -> Dict:
        records = self.db.query(ExpenseRecord).filter(
            ExpenseRecord.site_id == site_id,
            ExpenseRecord.expense_date >= period_start,
            ExpenseRecord.expense_date <= period_end
        ).all()

        total_amount = sum(float(r.amount or 0) for r in records)

        categories = {}
        for record in records:
            categories[record.category_id] = categories.get(record.category_id, 0) + float(record.amount or 0)

        return {
            'success': True,
            'data': {
                'site_id': site_id,
                'period_start': period_start.isoformat(),
                'period_end': period_end.isoformat(),
                'total_amount': round(total_amount, 2),
                'categories': categories,
                'details': [r.to_dict() for r in records]
            }
        }

    def create_consumable(self, consumable_data: Dict) -> Dict:
        try:
            consumable = Consumable(
                consumable_name=consumable_data['consumable_name'],
                consumable_type=consumable_data.get('consumable_type'),
                spec=consumable_data.get('spec', ''),
                unit=consumable_data['unit'],
                stock=consumable_data.get('stock', 0),
                min_stock=consumable_data.get('min_stock', 0),
                status=consumable_data.get('status', 'active'),
            )
            self.db.add(consumable)
            self.db.commit()
            self.db.refresh(consumable)
            return {'success': True, 'data': consumable.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def consumable_in(self, consumable_id: int, site_id: int, quantity: float, operator_id: int = None) -> Dict:
        consumable = self.db.query(Consumable).filter(Consumable.id == consumable_id).first()
        if not consumable:
            return {'success': False, 'error': '耗材不存在'}

        try:
            record = ConsumableRecord(
                consumable_id=consumable_id,
                site_id=site_id,
                record_type='in',
                quantity=quantity,
                operator_id=operator_id,
            )
            consumable.stock += quantity

            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
            return {'success': True, 'data': record.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def consumable_out(self, consumable_id: int, site_id: int, quantity: float, operator_id: int = None, remark: str = '') -> Dict:
        consumable = self.db.query(Consumable).filter(Consumable.id == consumable_id).first()
        if not consumable:
            return {'success': False, 'error': '耗材不存在'}

        if consumable.stock < quantity:
            return {'success': False, 'error': '库存不足'}

        try:
            record = ConsumableRecord(
                consumable_id=consumable_id,
                site_id=site_id,
                record_type='out',
                quantity=quantity,
                operator_id=operator_id,
                remark=remark,
            )
            consumable.stock -= quantity

            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
            return {'success': True, 'data': record.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def get_consumable_stats(self, period_start: date, period_end: date) -> Dict:
        records = self.db.query(ConsumableRecord).filter(
            ConsumableRecord.created_at >= period_start,
            ConsumableRecord.created_at <= period_end
        ).all()

        in_total = sum(float(r.quantity or 0) for r in records if r.record_type == 'in')
        out_total = sum(float(r.quantity or 0) for r in records if r.record_type == 'out')

        consumables = {}
        for record in records:
            key = record.consumable_id
            if key not in consumables:
                consumables[key] = {'in': 0, 'out': 0}
            if record.record_type == 'in':
                consumables[key]['in'] += float(record.quantity or 0)
            else:
                consumables[key]['out'] += float(record.quantity or 0)

        low_stock_items = self.db.query(Consumable).filter(
            Consumable.stock <= Consumable.min_stock,
            Consumable.status == 'active'
        ).all()

        return {
            'success': True,
            'data': {
                'period_start': period_start.isoformat(),
                'period_end': period_end.isoformat(),
                'in_total': round(in_total, 2),
                'out_total': round(out_total, 2),
                'consumables': consumables,
                'low_stock_items': [c.to_dict() for c in low_stock_items]
            }
        }

    def create_equipment_lease(self, lease_data: Dict) -> Dict:
        try:
            lease = EquipmentLease(
                equipment_name=lease_data['equipment_name'],
                equipment_type=lease_data.get('equipment_type'),
                equipment_no=lease_data.get('equipment_no'),
                site_id=lease_data['site_id'],
                lessor=lease_data.get('lessor', ''),
                lease_start_date=lease_data['lease_start_date'],
                lease_end_date=lease_data['lease_end_date'],
                lease_unit_price=lease_data.get('lease_unit_price', 0),
                lease_total_amount=lease_data.get('lease_total_amount', 0),
                paid_amount=lease_data.get('paid_amount', 0),
                unpaid_amount=lease_data.get('unpaid_amount', 0),
                status=lease_data.get('status', 'leasing'),
                remark=lease_data.get('remark', ''),
            )
            self.db.add(lease)
            self.db.commit()
            self.db.refresh(lease)
            return {'success': True, 'data': lease.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def get_lease_expiring(self, days_before: int = 7) -> List[Dict]:
        today = date.today()
        expire_date = today + timedelta(days=days_before)

        leases = self.db.query(EquipmentLease).filter(
            EquipmentLease.lease_end_date <= expire_date,
            EquipmentLease.lease_end_date >= today,
            EquipmentLease.status == 'leasing'
        ).all()

        return [l.to_dict() for l in leases]

    def get_lease_cost_report(self, site_id: int, period_start: date, period_end: date) -> Dict:
        records = self.db.query(EquipmentLease).filter(
            EquipmentLease.site_id == site_id,
            EquipmentLease.lease_start_date <= period_end,
            EquipmentLease.lease_end_date >= period_start,
            EquipmentLease.status != 'returned'
        ).all()

        total_cost = sum(float(r.lease_total_amount or 0) for r in records)
        unpaid_total = sum(float(r.unpaid_amount or 0) for r in records)

        equipment_types = {}
        for record in records:
            equipment_types[record.equipment_type] = equipment_types.get(record.equipment_type, 0) + float(record.lease_total_amount or 0)

        return {
            'success': True,
            'data': {
                'site_id': site_id,
                'period_start': period_start.isoformat(),
                'period_end': period_end.isoformat(),
                'total_cost': round(total_cost, 2),
                'unpaid_total': round(unpaid_total, 2),
                'equipment_types': equipment_types,
                'details': [r.to_dict() for r in records]
            }
        }

    def create_financial_record(self, record_data: Dict) -> Dict:
        try:
            record = FinancialRecord(
                record_type=record_data['record_type'],
                income_source=record_data.get('income_source'),
                expense_category=record_data.get('expense_category'),
                amount=record_data['amount'],
                record_date=record_data.get('record_date', date.today()),
                site_id=record_data.get('site_id'),
                contract_no=record_data.get('contract_no'),
                receivable_amount=record_data.get('receivable_amount', 0),
                received_amount=record_data.get('received_amount', 0),
                unpaid_amount=record_data.get('unpaid_amount', 0),
                overdue_days=record_data.get('overdue_days', 0),
                remark=record_data.get('remark', ''),
            )
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
            return {'success': True, 'data': record.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def get_financial_report(self, period_start: date, period_end: date) -> Dict:
        records = self.db.query(FinancialRecord).filter(
            FinancialRecord.record_date >= period_start,
            FinancialRecord.record_date <= period_end
        ).all()

        income_total = sum(float(r.amount or 0) for r in records if r.record_type == 'income')
        expense_total = sum(float(r.amount or 0) for r in records if r.record_type == 'expense')
        profit = income_total - expense_total

        receivable_total = sum(float(r.receivable_amount or 0) for r in records)
        received_total = sum(float(r.received_amount or 0) for r in records)
        unpaid_total = sum(float(r.unpaid_amount or 0) for r in records)

        return {
            'success': True,
            'data': {
                'period_start': period_start.isoformat(),
                'period_end': period_end.isoformat(),
                'income_total': round(income_total, 2),
                'expense_total': round(expense_total, 2),
                'profit': round(profit, 2),
                'profit_rate': round(profit / income_total * 100, 2) if income_total > 0 else 0,
                'receivable_total': round(receivable_total, 2),
                'received_total': round(received_total, 2),
                'unpaid_total': round(unpaid_total, 2),
                'recovery_rate': round(received_total / receivable_total * 100, 2) if receivable_total > 0 else 0,
                'details': [r.to_dict() for r in records]
            }
        }

    def parse_message(self, message_text: str) -> Dict:
        try:
            from services.command_config_service import command_config_service

            match_result = command_config_service.match_command(message_text)

            if match_result:
                command_name = match_result['command_name']

                if ':' in command_name:
                    plugin_name, action = command_name.split(':', 1)
                    if plugin_name == 'construction':
                        return {
                            'instruction_type': action,
                            'keyword': match_result.get('matched_type'),
                            'template': match_result.get('response_template'),
                            'raw_text': message_text,
                            'command_name': command_name,
                            'confidence': match_result.get('confidence'),
                        }

                return {
                    'instruction_type': command_name,
                    'keyword': match_result.get('matched_type'),
                    'template': match_result.get('response_template'),
                    'raw_text': message_text,
                    'command_name': command_name,
                    'confidence': match_result.get('confidence'),
                }

            instructions = self.db.query(MessageInstruction).filter(
                MessageInstruction.enabled == 1
            ).all()

            for instr in instructions:
                if instr.keyword in message_text:
                    return {
                        'instruction_type': instr.instruction_type,
                        'keyword': instr.keyword,
                        'template': instr.template,
                        'raw_text': message_text,
                    }

            return {'instruction_type': 'unknown', 'raw_text': message_text}

        except ImportError:
            instructions = self.db.query(MessageInstruction).filter(
                MessageInstruction.enabled == 1
            ).all()

            for instr in instructions:
                if instr.keyword in message_text:
                    return {
                        'instruction_type': instr.instruction_type,
                        'keyword': instr.keyword,
                        'template': instr.template,
                        'raw_text': message_text,
                    }

            return {'instruction_type': 'unknown', 'raw_text': message_text}
        except Exception as e:
            logger.error(f"消息解析失败: {e}", exc_info=True)
            return {'instruction_type': 'unknown', 'raw_text': message_text, 'error': str(e)}

    def add_operation_log(self, operator_id: int, operator_name: str, operation_type: str,
                           operation_object: str, operation_content: str, ip_address: str = '') -> Dict:
        try:
            log = OperationLog(
                operator_id=operator_id,
                operator_name=operator_name,
                operation_type=operation_type,
                operation_object=operation_object,
                operation_content=operation_content,
                ip_address=ip_address,
            )
            self.db.add(log)
            self.db.commit()
            return {'success': True}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}