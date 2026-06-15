"""
工地管理服务模块
实现工人打卡、天气工期管理、工作面记录、工程量记录等功能
"""
import json
import logging
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional

import requests

from database.db_config import get_db_session
from models.construction_models import (
    Worker, AttendanceRecord, LeaveRecord, WeatherRecord, ProjectSchedule,
    WorkArea, WorkAreaAssignment, WorkAreaProgress, WorkVolumeRecord,
    Material, MaterialRecord, SafetyCheck, SafetyIssue, QualityCheck
)

logger = logging.getLogger(__name__)


class ConstructionService:
    """工地管理服务类"""

    def create_worker(self, worker_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建工人"""
        db = get_db_session()
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
            db.add(worker)
            db.commit()
            db.refresh(worker)
            logger.info(f"工人创建成功: {worker.name}")
            return {'success': True, 'data': worker.to_dict()}
        except Exception as e:
            db.rollback()
            logger.error(f"创建工人失败: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            db.close()

    def get_worker(self, worker_id: int) -> Optional[Worker]:
        """获取工人信息"""
        db = get_db_session()
        try:
            return db.query(Worker).filter(Worker.id == worker_id).first()
        finally:
            db.close()

    def get_workers(self, team: Optional[str] = None, position: Optional[str] = None) -> List[Worker]:
        """获取工人列表"""
        db = get_db_session()
        try:
            query = db.query(Worker).filter(Worker.status == 'active')
            if team:
                query = query.filter(Worker.team == team)
            if position:
                query = query.filter(Worker.position == position)
            return query.all()
        finally:
            db.close()

    def check_in(self, worker_id: int, location: Optional[str] = None) -> Dict[str, Any]:
        """上班打卡"""
        db = get_db_session()
        try:
            worker = db.query(Worker).filter(Worker.id == worker_id).first()
            if not worker:
                return {'success': False, 'error': '工人不存在'}

            today = date.today()
            existing_record = db.query(AttendanceRecord).filter(
                AttendanceRecord.worker_id == worker_id,
                AttendanceRecord.date == today
            ).first()

            now = datetime.now().time()
            status = 'normal'
            if now.hour > 8:
                status = 'late'

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
                db.add(record)

            db.commit()
            logger.info(f"工人打卡成功: {worker.name}")
            return {'success': True, 'message': '打卡成功'}
        except Exception as e:
            db.rollback()
            logger.error(f"打卡失败: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            db.close()

    def check_out(self, worker_id: int, location: Optional[str] = None) -> Dict[str, Any]:
        """下班打卡"""
        db = get_db_session()
        try:
            worker = db.query(Worker).filter(Worker.id == worker_id).first()
            if not worker:
                return {'success': False, 'error': '工人不存在'}

            today = date.today()
            record = db.query(AttendanceRecord).filter(
                AttendanceRecord.worker_id == worker_id,
                AttendanceRecord.date == today
            ).first()

            if not record:
                return {'success': False, 'error': '未找到今日打卡记录'}

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

            db.commit()
            logger.info(f"工人下班成功: {worker.name}")
            return {'success': True, 'message': '下班成功'}
        except Exception as e:
            db.rollback()
            logger.error(f"下班打卡失败: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            db.close()

    def get_attendance(self, worker_id: Optional[int] = None, date_str: Optional[str] = None) -> List[AttendanceRecord]:
        """获取考勤记录"""
        db = get_db_session()
        try:
            query = db.query(AttendanceRecord)
            if worker_id:
                query = query.filter(AttendanceRecord.worker_id == worker_id)
            if date_str:
                query = query.filter(AttendanceRecord.date == date_str)
            return query.order_by(AttendanceRecord.date.desc()).all()
        finally:
            db.close()

    def apply_leave(self, leave_data: Dict[str, Any]) -> Dict[str, Any]:
        """申请请假"""
        db = get_db_session()
        try:
            leave = LeaveRecord(
                worker_id=leave_data['worker_id'],
                start_date=leave_data['start_date'],
                end_date=leave_data['end_date'],
                leave_type=leave_data.get('leave_type', 'personal'),
                reason=leave_data.get('reason', ''),
            )
            db.add(leave)
            db.commit()
            db.refresh(leave)
            return {'success': True, 'data': leave.to_dict()}
        except Exception as e:
            db.rollback()
            logger.error(f"申请请假失败: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            db.close()

    def approve_leave(self, leave_id: int, approved: bool, approved_by: str) -> Dict[str, Any]:
        """审批请假"""
        db = get_db_session()
        try:
            leave = db.query(LeaveRecord).filter(LeaveRecord.id == leave_id).first()
            if not leave:
                return {'success': False, 'error': '请假记录不存在'}

            leave.status = 'approved' if approved else 'rejected'
            leave.approved_by = approved_by
            leave.approved_at = datetime.now()
            db.commit()
            db.refresh(leave)
            return {'success': True, 'data': leave.to_dict()}
        except Exception as e:
            db.rollback()
            logger.error(f"审批请假失败: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            db.close()

    def fetch_weather(self, project_id: int, city: str) -> Dict[str, Any]:
        """获取天气信息"""
        try:
            api_url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid=demo"
            response = requests.get(api_url, timeout=10)
            data = response.json()

            weather_record = WeatherRecord(
                project_id=project_id,
                date=date.today(),
                weather=data.get('weather', [{}])[0].get('description', ''),
                temperature=f"{data.get('main', {}).get('temp', 0) - 273.15:.1f}°C",
                humidity=f"{data.get('main', {}).get('humidity', 0)}%",
                wind=f"{data.get('wind', {}).get('speed', 0)}m/s",
            )

            db = get_db_session()
            db.add(weather_record)
            db.commit()
            db.refresh(weather_record)
            db.close()

            return {'success': True, 'data': weather_record.to_dict()}
        except Exception as e:
            logger.error(f"获取天气失败: {e}")
            return {'success': False, 'error': str(e)}

    def get_weather(self, project_id: int, date_str: Optional[str] = None) -> List[WeatherRecord]:
        """获取天气记录"""
        db = get_db_session()
        try:
            query = db.query(WeatherRecord).filter(WeatherRecord.project_id == project_id)
            if date_str:
                query = query.filter(WeatherRecord.date == date_str)
            return query.order_by(WeatherRecord.date.desc()).all()
        finally:
            db.close()

    def create_schedule(self, schedule_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建工期计划"""
        db = get_db_session()
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
            db.add(schedule)
            db.commit()
            db.refresh(schedule)
            return {'success': True, 'data': schedule.to_dict()}
        except Exception as e:
            db.rollback()
            logger.error(f"创建工期计划失败: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            db.close()

    def update_schedule_progress(self, schedule_id: int, progress: float, actual_start_date: Optional[str] = None,
                                 actual_end_date: Optional[str] = None) -> Dict[str, Any]:
        """更新进度"""
        db = get_db_session()
        try:
            schedule = db.query(ProjectSchedule).filter(ProjectSchedule.id == schedule_id).first()
            if not schedule:
                return {'success': False, 'error': '计划不存在'}

            schedule.progress = progress
            if actual_start_date:
                schedule.actual_start_date = actual_start_date
            if actual_end_date:
                schedule.actual_end_date = actual_end_date

            if progress >= 100:
                schedule.status = 'completed'
            elif progress > 0:
                schedule.status = 'in_progress'

            db.commit()
            db.refresh(schedule)
            return {'success': True, 'data': schedule.to_dict()}
        except Exception as e:
            db.rollback()
            logger.error(f"更新进度失败: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            db.close()

    def get_schedules(self, project_id: int) -> List[ProjectSchedule]:
        """获取工期计划列表"""
        db = get_db_session()
        try:
            return db.query(ProjectSchedule).filter(
                ProjectSchedule.project_id == project_id
            ).order_by(ProjectSchedule.start_date).all()
        finally:
            db.close()

    def create_work_area(self, area_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建工作面"""
        db = get_db_session()
        try:
            area = WorkArea(
                project_id=area_data['project_id'],
                area_name=area_data['area_name'],
                area_code=area_data.get('area_code', ''),
                location=area_data.get('location', ''),
            )
            db.add(area)
            db.commit()
            db.refresh(area)
            return {'success': True, 'data': area.to_dict()}
        except Exception as e:
            db.rollback()
            logger.error(f"创建工作面失败: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            db.close()

    def assign_worker(self, work_area_id: int, worker_id: int, date_str: str, task: str) -> Dict[str, Any]:
        """安排工人到工作面"""
        db = get_db_session()
        try:
            assignment = WorkAreaAssignment(
                work_area_id=work_area_id,
                worker_id=worker_id,
                date=date_str,
                task=task,
            )
            db.add(assignment)
            db.commit()
            db.refresh(assignment)
            return {'success': True, 'data': assignment.to_dict()}
        except Exception as e:
            db.rollback()
            logger.error(f"安排工人失败: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            db.close()

    def record_progress(self, work_area_id: int, date_str: str, progress: float,
                        completed_amount: float, unit: str) -> Dict[str, Any]:
        """记录工作面进度"""
        db = get_db_session()
        try:
            progress_record = WorkAreaProgress(
                work_area_id=work_area_id,
                date=date_str,
                progress=progress,
                completed_amount=completed_amount,
                unit=unit,
            )
            db.add(progress_record)
            db.commit()
            db.refresh(progress_record)
            return {'success': True, 'data': progress_record.to_dict()}
        except Exception as e:
            db.rollback()
            logger.error(f"记录进度失败: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            db.close()

    def create_work_volume(self, volume_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建工程量记录"""
        db = get_db_session()
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
            db.add(volume)
            db.commit()
            db.refresh(volume)
            return {'success': True, 'data': volume.to_dict()}
        except Exception as e:
            db.rollback()
            logger.error(f"创建工程量记录失败: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            db.close()

    def get_work_volume(self, project_id: int, work_type: Optional[str] = None,
                        date_str: Optional[str] = None) -> List[WorkVolumeRecord]:
        """获取工程量记录"""
        db = get_db_session()
        try:
            query = db.query(WorkVolumeRecord).filter(WorkVolumeRecord.project_id == project_id)
            if work_type:
                query = query.filter(WorkVolumeRecord.work_type == work_type)
            if date_str:
                query = query.filter(WorkVolumeRecord.date == date_str)
            return query.order_by(WorkVolumeRecord.date.desc()).all()
        finally:
            db.close()

    def create_material(self, material_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建材料"""
        db = get_db_session()
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
            db.add(material)
            db.commit()
            db.refresh(material)
            return {'success': True, 'data': material.to_dict()}
        except Exception as e:
            db.rollback()
            logger.error(f"创建材料失败: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            db.close()

    def material_in(self, material_id: int, project_id: int, quantity: float,
                    price: float, operator: str) -> Dict[str, Any]:
        """材料入库"""
        db = get_db_session()
        try:
            material = db.query(Material).filter(Material.id == material_id).first()
            if not material:
                return {'success': False, 'error': '材料不存在'}

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

            db.add(record)
            db.commit()
            db.refresh(record)
            return {'success': True, 'data': record.to_dict()}
        except Exception as e:
            db.rollback()
            logger.error(f"材料入库失败: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            db.close()

    def material_out(self, material_id: int, project_id: int, quantity: float,
                     operator: str) -> Dict[str, Any]:
        """材料出库"""
        db = get_db_session()
        try:
            material = db.query(Material).filter(Material.id == material_id).first()
            if not material:
                return {'success': False, 'error': '材料不存在'}

            if material.stock < quantity:
                return {'success': False, 'error': '库存不足'}

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

            db.add(record)
            db.commit()
            db.refresh(record)
            return {'success': True, 'data': record.to_dict()}
        except Exception as e:
            db.rollback()
            logger.error(f"材料出库失败: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            db.close()

    def create_safety_check(self, check_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建安全检查"""
        db = get_db_session()
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
            db.add(check)
            db.commit()
            db.refresh(check)
            return {'success': True, 'data': check.to_dict()}
        except Exception as e:
            db.rollback()
            logger.error(f"创建安全检查失败: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            db.close()

    def create_safety_issue(self, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建安全隐患"""
        db = get_db_session()
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
            db.add(issue)
            db.commit()
            db.refresh(issue)
            return {'success': True, 'data': issue.to_dict()}
        except Exception as e:
            db.rollback()
            logger.error(f"创建安全隐患失败: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            db.close()

    def create_quality_check(self, check_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建质量检查"""
        db = get_db_session()
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

            db.add(check)
            db.commit()
            db.refresh(check)
            return {'success': True, 'data': check.to_dict()}
        except Exception as e:
            db.rollback()
            logger.error(f"创建质量检查失败: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            db.close()

    def generate_daily_report(self, project_id: int, date_str: Optional[str] = None) -> Dict[str, Any]:
        """生成日报"""
        if not date_str:
            date_str = date.today().isoformat()

        db = get_db_session()
        try:
            attendance_records = db.query(AttendanceRecord).filter(
                AttendanceRecord.date == date_str
            ).all()

            weather_record = db.query(WeatherRecord).filter(
                WeatherRecord.project_id == project_id,
                WeatherRecord.date == date_str
            ).first()

            progress_records = db.query(WorkAreaProgress).filter(
                WorkAreaProgress.date == date_str
            ).all()

            volume_records = db.query(WorkVolumeRecord).filter(
                WorkVolumeRecord.project_id == project_id,
                WorkVolumeRecord.date == date_str
            ).all()

            schedule_records = db.query(ProjectSchedule).filter(
                ProjectSchedule.project_id == project_id
            ).all()

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
        finally:
            db.close()


construction_service = ConstructionService()
