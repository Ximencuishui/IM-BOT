"""
车队调度插件业务服务
"""
import json
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from .models import (
    FleetDriver,
    FleetMudTruck,
    FleetLogisticsTruck,
    FleetTask,
    FleetRoute,
    FleetMaintenance,
    FleetTransportRecord,
    FleetDriverBehavior
)


class FleetService:
    def __init__(self, db: Session):
        self.db = db

    def create_driver(self, data: Dict) -> Dict:
        try:
            driver = FleetDriver(
                user_id=data['user_id'],
                driver_name=data['driver_name'],
                phone=data.get('phone'),
                license_type=data.get('license_type'),
                license_number=data.get('license_number'),
                driving_years=data.get('driving_years'),
                emergency_contact=data.get('emergency_contact'),
                emergency_phone=data.get('emergency_phone'),
                status=data.get('status', 'active')
            )
            self.db.add(driver)
            self.db.commit()
            self.db.refresh(driver)
            return {'success': True, 'data': driver.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def get_drivers(self, user_id: int, status: str = None) -> List[Dict]:
        query = self.db.query(FleetDriver).filter(FleetDriver.user_id == user_id)
        if status:
            query = query.filter(FleetDriver.status == status)
        return [d.to_dict() for d in query.all()]

    def get_driver(self, user_id: int, driver_id: int) -> Optional[Dict]:
        driver = self.db.query(FleetDriver).filter(
            FleetDriver.user_id == user_id,
            FleetDriver.id == driver_id
        ).first()
        return driver.to_dict() if driver else None

    def update_driver(self, user_id: int, driver_id: int, data: Dict) -> Dict:
        try:
            driver = self.db.query(FleetDriver).filter(
                FleetDriver.user_id == user_id,
                FleetDriver.id == driver_id
            ).first()
            if not driver:
                return {'success': False, 'error': '司机不存在'}
            for key, value in data.items():
                if hasattr(driver, key):
                    setattr(driver, key, value)
            self.db.commit()
            self.db.refresh(driver)
            return {'success': True, 'data': driver.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def delete_driver(self, user_id: int, driver_id: int) -> Dict:
        try:
            driver = self.db.query(FleetDriver).filter(
                FleetDriver.user_id == user_id,
                FleetDriver.id == driver_id
            ).first()
            if not driver:
                return {'success': False, 'error': '司机不存在'}
            self.db.delete(driver)
            self.db.commit()
            return {'success': True, 'message': '删除成功'}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def create_mud_truck(self, data: Dict) -> Dict:
        try:
            truck = FleetMudTruck(
                user_id=data['user_id'],
                plate_number=data['plate_number'],
                vehicle_type=data.get('vehicle_type'),
                capacity=data.get('capacity'),
                load_weight=data.get('load_weight'),
                fuel_type=data.get('fuel_type'),
                driver_id=data.get('driver_id'),
                driver_name=data.get('driver_name'),
                remark=data.get('remark')
            )
            self.db.add(truck)
            self.db.commit()
            self.db.refresh(truck)
            return {'success': True, 'data': truck.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def get_mud_trucks(self, user_id: int, status: str = None) -> List[Dict]:
        query = self.db.query(FleetMudTruck).filter(FleetMudTruck.user_id == user_id)
        if status:
            query = query.filter(FleetMudTruck.status == status)
        return [t.to_dict() for t in query.all()]

    def get_mud_truck(self, user_id: int, truck_id: int) -> Optional[Dict]:
        truck = self.db.query(FleetMudTruck).filter(
            FleetMudTruck.user_id == user_id,
            FleetMudTruck.id == truck_id
        ).first()
        return truck.to_dict() if truck else None

    def update_mud_truck(self, user_id: int, truck_id: int, data: Dict) -> Dict:
        try:
            truck = self.db.query(FleetMudTruck).filter(
                FleetMudTruck.user_id == user_id,
                FleetMudTruck.id == truck_id
            ).first()
            if not truck:
                return {'success': False, 'error': '泥土车不存在'}
            for key, value in data.items():
                if hasattr(truck, key):
                    setattr(truck, key, value)
            self.db.commit()
            self.db.refresh(truck)
            return {'success': True, 'data': truck.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def delete_mud_truck(self, user_id: int, truck_id: int) -> Dict:
        try:
            truck = self.db.query(FleetMudTruck).filter(
                FleetMudTruck.user_id == user_id,
                FleetMudTruck.id == truck_id
            ).first()
            if not truck:
                return {'success': False, 'error': '泥土车不存在'}
            self.db.delete(truck)
            self.db.commit()
            return {'success': True, 'message': '删除成功'}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def update_mud_truck_status(self, user_id: int, truck_id: int, data: Dict) -> Dict:
        try:
            truck = self.db.query(FleetMudTruck).filter(
                FleetMudTruck.user_id == user_id,
                FleetMudTruck.id == truck_id
            ).first()
            if not truck:
                return {'success': False, 'error': '泥土车不存在'}
            
            truck.current_location = data.get('current_location', truck.current_location)
            truck.current_speed = data.get('current_speed', truck.current_speed)
            truck.current_load = data.get('current_load', truck.current_load)
            truck.status = data.get('status', truck.status)
            truck.mileage = data.get('mileage', truck.mileage)
            truck.last_report_time = datetime.now()
            
            self.db.commit()
            self.db.refresh(truck)
            return {'success': True, 'data': truck.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def create_logistics_truck(self, data: Dict) -> Dict:
        try:
            truck = FleetLogisticsTruck(
                user_id=data['user_id'],
                plate_number=data['plate_number'],
                vehicle_type=data.get('vehicle_type'),
                load_capacity=data.get('load_capacity'),
                volume=data.get('volume'),
                fuel_type=data.get('fuel_type'),
                fuel_consumption=data.get('fuel_consumption'),
                driver_id=data.get('driver_id'),
                driver_name=data.get('driver_name'),
                remark=data.get('remark')
            )
            self.db.add(truck)
            self.db.commit()
            self.db.refresh(truck)
            return {'success': True, 'data': truck.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def get_logistics_trucks(self, user_id: int, status: str = None) -> List[Dict]:
        query = self.db.query(FleetLogisticsTruck).filter(FleetLogisticsTruck.user_id == user_id)
        if status:
            query = query.filter(FleetLogisticsTruck.status == status)
        return [t.to_dict() for t in query.all()]

    def get_logistics_truck(self, user_id: int, truck_id: int) -> Optional[Dict]:
        truck = self.db.query(FleetLogisticsTruck).filter(
            FleetLogisticsTruck.user_id == user_id,
            FleetLogisticsTruck.id == truck_id
        ).first()
        return truck.to_dict() if truck else None

    def update_logistics_truck(self, user_id: int, truck_id: int, data: Dict) -> Dict:
        try:
            truck = self.db.query(FleetLogisticsTruck).filter(
                FleetLogisticsTruck.user_id == user_id,
                FleetLogisticsTruck.id == truck_id
            ).first()
            if not truck:
                return {'success': False, 'error': '物流车不存在'}
            for key, value in data.items():
                if hasattr(truck, key):
                    setattr(truck, key, value)
            self.db.commit()
            self.db.refresh(truck)
            return {'success': True, 'data': truck.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def delete_logistics_truck(self, user_id: int, truck_id: int) -> Dict:
        try:
            truck = self.db.query(FleetLogisticsTruck).filter(
                FleetLogisticsTruck.user_id == user_id,
                FleetLogisticsTruck.id == truck_id
            ).first()
            if not truck:
                return {'success': False, 'error': '物流车不存在'}
            self.db.delete(truck)
            self.db.commit()
            return {'success': True, 'message': '删除成功'}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def update_logistics_truck_status(self, user_id: int, truck_id: int, data: Dict) -> Dict:
        try:
            truck = self.db.query(FleetLogisticsTruck).filter(
                FleetLogisticsTruck.user_id == user_id,
                FleetLogisticsTruck.id == truck_id
            ).first()
            if not truck:
                return {'success': False, 'error': '物流车不存在'}
            
            truck.current_location = data.get('current_location', truck.current_location)
            truck.current_speed = data.get('current_speed', truck.current_speed)
            truck.load_rate = data.get('load_rate', truck.load_rate)
            truck.status = data.get('status', truck.status)
            truck.mileage = data.get('mileage', truck.mileage)
            truck.last_report_time = datetime.now()
            
            self.db.commit()
            self.db.refresh(truck)
            return {'success': True, 'data': truck.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def create_task(self, data: Dict) -> Dict:
        try:
            task_no = f"FLT{datetime.now().strftime('%Y%m%d%H%M%S')}"
            task = FleetTask(
                user_id=data['user_id'],
                task_no=task_no,
                task_type=data['task_type'],
                origin=data['origin'],
                destination=data['destination'],
                cargo_info=data.get('cargo_info'),
                cargo_weight=data.get('cargo_weight'),
                cargo_volume=data.get('cargo_volume'),
                scheduled_departure=data.get('scheduled_departure'),
                scheduled_arrival=data.get('scheduled_arrival'),
                priority=data.get('priority', 'normal'),
                dispatching_mode=data.get('dispatching_mode', 'manual'),
                remark=data.get('remark')
            )
            self.db.add(task)
            self.db.commit()
            self.db.refresh(task)
            return {'success': True, 'data': task.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def get_tasks(self, user_id: int, task_type: str = None, status: str = None) -> List[Dict]:
        query = self.db.query(FleetTask).filter(FleetTask.user_id == user_id)
        if task_type:
            query = query.filter(FleetTask.task_type == task_type)
        if status:
            query = query.filter(FleetTask.status == status)
        return [t.to_dict() for t in query.all()]

    def get_task(self, user_id: int, task_id: int) -> Optional[Dict]:
        task = self.db.query(FleetTask).filter(
            FleetTask.user_id == user_id,
            FleetTask.id == task_id
        ).first()
        return task.to_dict() if task else None

    def assign_task(self, user_id: int, task_id: int, data: Dict) -> Dict:
        try:
            task = self.db.query(FleetTask).filter(
                FleetTask.user_id == user_id,
                FleetTask.id == task_id
            ).first()
            if not task:
                return {'success': False, 'error': '任务不存在'}
            
            if task.status != 'pending':
                return {'success': False, 'error': '任务状态不允许分配'}

            truck_type = data.get('truck_type')
            truck_id = data.get('truck_id')
            driver_id = data.get('driver_id')

            if truck_type == 'mud':
                truck = self.db.query(FleetMudTruck).filter(
                    FleetMudTruck.user_id == user_id,
                    FleetMudTruck.id == truck_id
                ).first()
                if not truck:
                    return {'success': False, 'error': '泥土车不存在'}
                if truck.status != 'available':
                    return {'success': False, 'error': '泥土车不可用'}
                truck.status = 'working'
            else:
                truck = self.db.query(FleetLogisticsTruck).filter(
                    FleetLogisticsTruck.user_id == user_id,
                    FleetLogisticsTruck.id == truck_id
                ).first()
                if not truck:
                    return {'success': False, 'error': '物流车不存在'}
                if truck.status != 'available':
                    return {'success': False, 'error': '物流车不可用'}
                truck.status = 'working'

            driver = self.db.query(FleetDriver).filter(
                FleetDriver.user_id == user_id,
                FleetDriver.id == driver_id
            ).first() if driver_id else None

            task.truck_id = truck_id
            task.truck_type = truck_type
            task.plate_number = truck.plate_number
            task.driver_id = driver_id
            task.driver_name = driver.driver_name if driver else None
            task.status = 'assigned'
            task.dispatching_mode = data.get('dispatching_mode', 'manual')

            route = self.calculate_route(user_id, task.origin, task.destination)
            task.route_info = json.dumps(route) if route else None
            task.distance = route.get('distance') if route else None
            task.estimated_fuel = route.get('estimated_fuel') if route else None

            self.db.commit()
            self.db.refresh(task)
            return {'success': True, 'data': task.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def auto_assign_task(self, user_id: int, task_id: int) -> Dict:
        try:
            task = self.db.query(FleetTask).filter(
                FleetTask.user_id == user_id,
                FleetTask.id == task_id
            ).first()
            if not task:
                return {'success': False, 'error': '任务不存在'}

            if task.status != 'pending':
                return {'success': False, 'error': '任务状态不允许分配'}

            task_type = task.task_type
            query = self.db.query(FleetMudTruck) if task_type == 'mud' else self.db.query(FleetLogisticsTruck)
            available_trucks = query.filter(
                query.c.user_id == user_id,
                query.c.status == 'available'
            ).all()

            if not available_trucks:
                return {'success': False, 'error': '没有可用的车辆'}

            best_truck = None
            min_distance = float('inf')

            for truck in available_trucks:
                if task.cargo_weight and (task_type == 'mud' and truck.load_weight < task.cargo_weight):
                    continue
                if task.cargo_weight and (task_type == 'logistics' and truck.load_capacity < task.cargo_weight):
                    continue
                if task.cargo_volume and (task_type == 'logistics' and truck.volume < task.cargo_volume):
                    continue

                if truck.current_location:
                    distance = self._calculate_distance(truck.current_location, task.origin)
                    if distance < min_distance:
                        min_distance = distance
                        best_truck = truck

            best_truck = best_truck or available_trucks[0]

            assign_data = {
                'truck_type': task_type,
                'truck_id': best_truck.id,
                'driver_id': best_truck.driver_id,
                'dispatching_mode': 'auto'
            }

            return self.assign_task(user_id, task_id, assign_data)
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def _calculate_distance(self, loc1: str, loc2: str) -> float:
        import re
        coords1 = re.findall(r'[\d.]+', loc1)
        coords2 = re.findall(r'[\d.]+', loc2)
        if len(coords1) >= 2 and len(coords2) >= 2:
            lat1, lng1 = float(coords1[0]), float(coords1[1])
            lat2, lng2 = float(coords2[0]), float(coords2[1])
            from math import radians, sin, cos, sqrt, atan2
            R = 6371
            dlat = radians(lat2 - lat1)
            dlng = radians(lng2 - lng1)
            a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng/2)**2
            return R * (2 * atan2(sqrt(a), sqrt(1-a)))
        return 10.0

    def update_task_status(self, user_id: int, task_id: int, status: str) -> Dict:
        try:
            task = self.db.query(FleetTask).filter(
                FleetTask.user_id == user_id,
                FleetTask.id == task_id
            ).first()
            if not task:
                return {'success': False, 'error': '任务不存在'}

            task.status = status
            
            if status == 'in_progress':
                task.actual_departure = datetime.now()
            elif status == 'completed':
                task.actual_arrival = datetime.now()
                self._complete_task(task)

            self.db.commit()
            self.db.refresh(task)
            return {'success': True, 'data': task.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def _complete_task(self, task: FleetTask):
        try:
            record = FleetTransportRecord(
                user_id=task.user_id,
                task_id=task.id,
                truck_id=task.truck_id,
                truck_type=task.truck_type,
                plate_number=task.plate_number,
                driver_id=task.driver_id,
                driver_name=task.driver_name,
                transport_date=date.today(),
                origin=task.origin,
                destination=task.destination,
                route=task.route_info,
                distance=task.distance,
                transport_weight=task.cargo_weight,
                transport_volume=task.cargo_volume,
                fuel_used=task.estimated_fuel,
                status='completed'
            )
            self.db.add(record)

            if task.truck_type == 'mud':
                truck = self.db.query(FleetMudTruck).filter(FleetMudTruck.id == task.truck_id).first()
                if truck:
                    truck.status = 'available'
            else:
                truck = self.db.query(FleetLogisticsTruck).filter(FleetLogisticsTruck.id == task.truck_id).first()
                if truck:
                    truck.status = 'available'

            self.db.commit()
        except Exception:
            pass

    def calculate_route(self, user_id: int, origin: str, destination: str, waypoints: list = None) -> Dict:
        distance = self._calculate_distance(origin, destination)
        estimated_time = distance / 60 * 60
        estimated_fuel = distance * 0.3

        return {
            'origin': origin,
            'destination': destination,
            'distance': round(distance, 2),
            'estimated_time': round(estimated_time, 2),
            'estimated_fuel': round(estimated_fuel, 2),
            'traffic_condition': 'normal',
            'is_optimized': True
        }

    def optimize_route(self, user_id: int, origin: str, destination: str, constraints: Dict = None) -> Dict:
        base_route = self.calculate_route(user_id, origin, destination)
        
        if constraints:
            if constraints.get('priority') == 'fast':
                base_route['estimated_time'] *= 0.9
            elif constraints.get('priority') == 'fuel':
                base_route['estimated_fuel'] *= 0.9
        
        base_route['is_optimized'] = True
        return base_route

    def create_maintenance(self, data: Dict) -> Dict:
        try:
            maintenance = FleetMaintenance(
                user_id=data['user_id'],
                truck_id=data['truck_id'],
                truck_type=data['truck_type'],
                plate_number=data.get('plate_number'),
                maintenance_type=data['maintenance_type'],
                maintenance_date=data['maintenance_date'],
                mileage_at_maintenance=data.get('mileage_at_maintenance'),
                description=data.get('description'),
                parts_replaced=data.get('parts_replaced'),
                cost=data.get('cost'),
                maintenance_shop=data.get('maintenance_shop'),
                contact_person=data.get('contact_person'),
                phone=data.get('phone'),
                next_maintenance_mileage=data.get('next_maintenance_mileage'),
                next_maintenance_date=data.get('next_maintenance_date'),
                remark=data.get('remark')
            )
            self.db.add(maintenance)

            if data['truck_type'] == 'mud':
                truck = self.db.query(FleetMudTruck).filter(
                    FleetMudTruck.user_id == data['user_id'],
                    FleetMudTruck.id == data['truck_id']
                ).first()
                if truck:
                    truck.next_maintenance_mileage = data.get('next_maintenance_mileage')
                    truck.next_maintenance_date = data.get('next_maintenance_date')
            else:
                truck = self.db.query(FleetLogisticsTruck).filter(
                    FleetLogisticsTruck.user_id == data['user_id'],
                    FleetLogisticsTruck.id == data['truck_id']
                ).first()
                if truck:
                    truck.next_maintenance_mileage = data.get('next_maintenance_mileage')
                    truck.next_maintenance_date = data.get('next_maintenance_date')

            self.db.commit()
            self.db.refresh(maintenance)
            return {'success': True, 'data': maintenance.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def get_maintenance_records(self, user_id: int, truck_id: int = None, truck_type: str = None) -> List[Dict]:
        query = self.db.query(FleetMaintenance).filter(FleetMaintenance.user_id == user_id)
        if truck_id:
            query = query.filter(FleetMaintenance.truck_id == truck_id)
        if truck_type:
            query = query.filter(FleetMaintenance.truck_type == truck_type)
        return [m.to_dict() for m in query.all()]

    def get_maintenance_alerts(self, user_id: int) -> List[Dict]:
        alerts = []
        
        mud_trucks = self.db.query(FleetMudTruck).filter(FleetMudTruck.user_id == user_id).all()
        for truck in mud_trucks:
            if truck.next_maintenance_mileage and truck.mileage >= truck.next_maintenance_mileage * 0.9:
                alerts.append({
                    'truck_id': truck.id,
                    'truck_type': 'mud',
                    'plate_number': truck.plate_number,
                    'alert_type': 'mileage',
                    'message': f'泥土车 {truck.plate_number} 即将到达保养里程',
                    'current_mileage': truck.mileage,
                    'target_mileage': truck.next_maintenance_mileage
                })
            if truck.next_maintenance_date and truck.next_maintenance_date <= date.today() + timedelta(days=7):
                alerts.append({
                    'truck_id': truck.id,
                    'truck_type': 'mud',
                    'plate_number': truck.plate_number,
                    'alert_type': 'date',
                    'message': f'泥土车 {truck.plate_number} 即将到达保养日期',
                    'target_date': truck.next_maintenance_date.isoformat()
                })

        logistics_trucks = self.db.query(FleetLogisticsTruck).filter(FleetLogisticsTruck.user_id == user_id).all()
        for truck in logistics_trucks:
            if truck.next_maintenance_mileage and truck.mileage >= truck.next_maintenance_mileage * 0.9:
                alerts.append({
                    'truck_id': truck.id,
                    'truck_type': 'logistics',
                    'plate_number': truck.plate_number,
                    'alert_type': 'mileage',
                    'message': f'物流车 {truck.plate_number} 即将到达保养里程',
                    'current_mileage': truck.mileage,
                    'target_mileage': truck.next_maintenance_mileage
                })
            if truck.next_maintenance_date and truck.next_maintenance_date <= date.today() + timedelta(days=7):
                alerts.append({
                    'truck_id': truck.id,
                    'truck_type': 'logistics',
                    'plate_number': truck.plate_number,
                    'alert_type': 'date',
                    'message': f'物流车 {truck.plate_number} 即将到达保养日期',
                    'target_date': truck.next_maintenance_date.isoformat()
                })

        return alerts

    def get_transport_records(self, user_id: int, truck_id: int = None, date_range: Dict = None) -> List[Dict]:
        query = self.db.query(FleetTransportRecord).filter(FleetTransportRecord.user_id == user_id)
        if truck_id:
            query = query.filter(FleetTransportRecord.truck_id == truck_id)
        if date_range and date_range.get('start_date'):
            query = query.filter(FleetTransportRecord.transport_date >= date_range['start_date'])
        if date_range and date_range.get('end_date'):
            query = query.filter(FleetTransportRecord.transport_date <= date_range['end_date'])
        return [r.to_dict() for r in query.all()]

    def get_driver_behavior(self, user_id: int, driver_id: int = None, date_range: Dict = None) -> List[Dict]:
        query = self.db.query(FleetDriverBehavior).filter(FleetDriverBehavior.user_id == user_id)
        if driver_id:
            query = query.filter(FleetDriverBehavior.driver_id == driver_id)
        if date_range and date_range.get('start_date'):
            query = query.filter(FleetDriverBehavior.behavior_date >= date_range['start_date'])
        if date_range and date_range.get('end_date'):
            query = query.filter(FleetDriverBehavior.behavior_date <= date_range['end_date'])
        return [b.to_dict() for b in query.all()]

    def calculate_driver_score(self, user_id: int, driver_id: int, behavior_data: Dict) -> float:
        score = 100.0
        
        score -= behavior_data.get('speeding_count', 0) * 5
        score -= behavior_data.get('harsh_braking_count', 0) * 3
        score -= behavior_data.get('harsh_acceleration_count', 0) * 3
        
        idle_ratio = behavior_data.get('idle_time', 0) / (behavior_data.get('total_time', 1) + 0.001)
        if idle_ratio > 0.3:
            score -= (idle_ratio - 0.3) * 100
        
        if behavior_data.get('fuel_efficiency', 0) < 8:
            score -= (8 - behavior_data['fuel_efficiency']) * 2
        
        return max(0, min(100, score))

    def get_fleet_stats(self, user_id: int) -> Dict:
        mud_trucks = self.db.query(FleetMudTruck).filter(FleetMudTruck.user_id == user_id).all()
        logistics_trucks = self.db.query(FleetLogisticsTruck).filter(FleetLogisticsTruck.user_id == user_id).all()
        drivers = self.db.query(FleetDriver).filter(FleetDriver.user_id == user_id).all()
        tasks = self.db.query(FleetTask).filter(FleetTask.user_id == user_id).all()

        return {
            'total_mud_trucks': len(mud_trucks),
            'available_mud_trucks': len([t for t in mud_trucks if t.status == 'available']),
            'working_mud_trucks': len([t for t in mud_trucks if t.status == 'working']),
            'total_logistics_trucks': len(logistics_trucks),
            'available_logistics_trucks': len([t for t in logistics_trucks if t.status == 'available']),
            'working_logistics_trucks': len([t for t in logistics_trucks if t.status == 'working']),
            'total_drivers': len(drivers),
            'total_tasks': len(tasks),
            'pending_tasks': len([t for t in tasks if t.status == 'pending']),
            'assigned_tasks': len([t for t in tasks if t.status == 'assigned']),
            'in_progress_tasks': len([t for t in tasks if t.status == 'in_progress']),
            'completed_tasks': len([t for t in tasks if t.status == 'completed'])
        }