import json
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional

from plugins.base.base_service import BaseService
from plugins.construction.models import (
    Worker, AttendanceRecord, LeaveRecord, WeatherRecord, ProjectSchedule,
    WorkArea, WorkAreaAssignment, WorkAreaProgress, WorkVolumeRecord,
    Material, MaterialRecord, SafetyCheck, SafetyIssue, QualityCheck
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