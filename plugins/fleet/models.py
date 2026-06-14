"""
车队调度插件数据模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, ForeignKey, Boolean
from database.db_config import Base


class FleetDriver(Base):
    __tablename__ = 't_fleet_driver'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    driver_name = Column(String(100), nullable=False)
    phone = Column(String(20))
    license_type = Column(String(20))
    license_number = Column(String(50))
    driving_years = Column(Integer)
    emergency_contact = Column(String(100))
    emergency_phone = Column(String(20))
    status = Column(String(20), default='active')
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'driver_name': self.driver_name,
            'phone': self.phone,
            'license_type': self.license_type,
            'license_number': self.license_number,
            'driving_years': self.driving_years,
            'emergency_contact': self.emergency_contact,
            'emergency_phone': self.emergency_phone,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class FleetMudTruck(Base):
    __tablename__ = 't_fleet_mud_truck'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    plate_number = Column(String(20), nullable=False, unique=True)
    vehicle_type = Column(String(50))
    capacity = Column(Float)
    load_weight = Column(Float)
    fuel_type = Column(String(20))
    mileage = Column(Float, default=0)
    driver_id = Column(Integer, ForeignKey('t_fleet_driver.id'))
    driver_name = Column(String(100))
    status = Column(String(20), default='available')
    current_location = Column(String(200))
    current_speed = Column(Float)
    current_load = Column(Float)
    last_report_time = Column(DateTime)
    next_maintenance_mileage = Column(Float)
    next_maintenance_date = Column(Date)
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'plate_number': self.plate_number,
            'vehicle_type': self.vehicle_type,
            'capacity': self.capacity,
            'load_weight': self.load_weight,
            'fuel_type': self.fuel_type,
            'mileage': self.mileage,
            'driver_id': self.driver_id,
            'driver_name': self.driver_name,
            'status': self.status,
            'current_location': self.current_location,
            'current_speed': self.current_speed,
            'current_load': self.current_load,
            'last_report_time': self.last_report_time.isoformat() if self.last_report_time else None,
            'next_maintenance_mileage': self.next_maintenance_mileage,
            'next_maintenance_date': self.next_maintenance_date.isoformat() if self.next_maintenance_date else None,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class FleetLogisticsTruck(Base):
    __tablename__ = 't_fleet_logistics_truck'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    plate_number = Column(String(20), nullable=False, unique=True)
    vehicle_type = Column(String(50))
    load_capacity = Column(Float)
    volume = Column(Float)
    fuel_type = Column(String(20))
    fuel_consumption = Column(Float)
    mileage = Column(Float, default=0)
    driver_id = Column(Integer, ForeignKey('t_fleet_driver.id'))
    driver_name = Column(String(100))
    status = Column(String(20), default='available')
    current_location = Column(String(200))
    current_speed = Column(Float)
    load_rate = Column(Float, default=0)
    last_report_time = Column(DateTime)
    next_maintenance_mileage = Column(Float)
    next_maintenance_date = Column(Date)
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'plate_number': self.plate_number,
            'vehicle_type': self.vehicle_type,
            'load_capacity': self.load_capacity,
            'volume': self.volume,
            'fuel_type': self.fuel_type,
            'fuel_consumption': self.fuel_consumption,
            'mileage': self.mileage,
            'driver_id': self.driver_id,
            'driver_name': self.driver_name,
            'status': self.status,
            'current_location': self.current_location,
            'current_speed': self.current_speed,
            'load_rate': self.load_rate,
            'last_report_time': self.last_report_time.isoformat() if self.last_report_time else None,
            'next_maintenance_mileage': self.next_maintenance_mileage,
            'next_maintenance_date': self.next_maintenance_date.isoformat() if self.next_maintenance_date else None,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class FleetTask(Base):
    __tablename__ = 't_fleet_task'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    task_no = Column(String(50), nullable=False, unique=True)
    task_type = Column(String(20), nullable=False)
    truck_id = Column(Integer)
    truck_type = Column(String(20))
    plate_number = Column(String(20))
    driver_id = Column(Integer)
    driver_name = Column(String(100))
    origin = Column(String(200), nullable=False)
    destination = Column(String(200), nullable=False)
    cargo_info = Column(Text)
    cargo_weight = Column(Float)
    cargo_volume = Column(Float)
    scheduled_departure = Column(DateTime)
    scheduled_arrival = Column(DateTime)
    actual_departure = Column(DateTime)
    actual_arrival = Column(DateTime)
    status = Column(String(20), default='pending')
    priority = Column(String(20), default='normal')
    dispatching_mode = Column(String(20), default='manual')
    route_info = Column(Text)
    distance = Column(Float)
    estimated_fuel = Column(Float)
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'task_no': self.task_no,
            'task_type': self.task_type,
            'truck_id': self.truck_id,
            'truck_type': self.truck_type,
            'plate_number': self.plate_number,
            'driver_id': self.driver_id,
            'driver_name': self.driver_name,
            'origin': self.origin,
            'destination': self.destination,
            'cargo_info': self.cargo_info,
            'cargo_weight': self.cargo_weight,
            'cargo_volume': self.cargo_volume,
            'scheduled_departure': self.scheduled_departure.isoformat() if self.scheduled_departure else None,
            'scheduled_arrival': self.scheduled_arrival.isoformat() if self.scheduled_arrival else None,
            'actual_departure': self.actual_departure.isoformat() if self.actual_departure else None,
            'actual_arrival': self.actual_arrival.isoformat() if self.actual_arrival else None,
            'status': self.status,
            'priority': self.priority,
            'dispatching_mode': self.dispatching_mode,
            'route_info': self.route_info,
            'distance': self.distance,
            'estimated_fuel': self.estimated_fuel,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class FleetRoute(Base):
    __tablename__ = 't_fleet_route'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    task_id = Column(Integer, ForeignKey('t_fleet_task.id'))
    origin = Column(String(200), nullable=False)
    destination = Column(String(200), nullable=False)
    waypoints = Column(Text)
    distance = Column(Float)
    estimated_time = Column(Float)
    estimated_fuel = Column(Float)
    route_coordinates = Column(Text)
    traffic_condition = Column(String(50))
    road_conditions = Column(Text)
    is_optimized = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'task_id': self.task_id,
            'origin': self.origin,
            'destination': self.destination,
            'waypoints': self.waypoints,
            'distance': self.distance,
            'estimated_time': self.estimated_time,
            'estimated_fuel': self.estimated_fuel,
            'route_coordinates': self.route_coordinates,
            'traffic_condition': self.traffic_condition,
            'road_conditions': self.road_conditions,
            'is_optimized': self.is_optimized,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class FleetMaintenance(Base):
    __tablename__ = 't_fleet_maintenance'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    truck_id = Column(Integer, nullable=False)
    truck_type = Column(String(20), nullable=False)
    plate_number = Column(String(20))
    maintenance_type = Column(String(50), nullable=False)
    maintenance_date = Column(Date, nullable=False)
    mileage_at_maintenance = Column(Float)
    description = Column(Text)
    parts_replaced = Column(Text)
    cost = Column(Float)
    maintenance_shop = Column(String(100))
    contact_person = Column(String(50))
    phone = Column(String(20))
    status = Column(String(20), default='completed')
    next_maintenance_mileage = Column(Float)
    next_maintenance_date = Column(Date)
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'truck_id': self.truck_id,
            'truck_type': self.truck_type,
            'plate_number': self.plate_number,
            'maintenance_type': self.maintenance_type,
            'maintenance_date': self.maintenance_date.isoformat() if self.maintenance_date else None,
            'mileage_at_maintenance': self.mileage_at_maintenance,
            'description': self.description,
            'parts_replaced': self.parts_replaced,
            'cost': self.cost,
            'maintenance_shop': self.maintenance_shop,
            'contact_person': self.contact_person,
            'phone': self.phone,
            'status': self.status,
            'next_maintenance_mileage': self.next_maintenance_mileage,
            'next_maintenance_date': self.next_maintenance_date.isoformat() if self.next_maintenance_date else None,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class FleetTransportRecord(Base):
    __tablename__ = 't_fleet_transport_record'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    task_id = Column(Integer, ForeignKey('t_fleet_task.id'))
    truck_id = Column(Integer, nullable=False)
    truck_type = Column(String(20), nullable=False)
    plate_number = Column(String(20))
    driver_id = Column(Integer)
    driver_name = Column(String(100))
    transport_date = Column(Date, nullable=False)
    origin = Column(String(200))
    destination = Column(String(200))
    route = Column(Text)
    distance = Column(Float)
    transport_weight = Column(Float)
    transport_volume = Column(Float)
    transport_time = Column(Float)
    fuel_used = Column(Float)
    average_speed = Column(Float)
    status = Column(String(20), default='completed')
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'task_id': self.task_id,
            'truck_id': self.truck_id,
            'truck_type': self.truck_type,
            'plate_number': self.plate_number,
            'driver_id': self.driver_id,
            'driver_name': self.driver_name,
            'transport_date': self.transport_date.isoformat() if self.transport_date else None,
            'origin': self.origin,
            'destination': self.destination,
            'route': self.route,
            'distance': self.distance,
            'transport_weight': self.transport_weight,
            'transport_volume': self.transport_volume,
            'transport_time': self.transport_time,
            'fuel_used': self.fuel_used,
            'average_speed': self.average_speed,
            'status': self.status,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class FleetDriverBehavior(Base):
    __tablename__ = 't_fleet_driver_behavior'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    driver_id = Column(Integer, ForeignKey('t_fleet_driver.id'))
    driver_name = Column(String(100))
    truck_id = Column(Integer)
    plate_number = Column(String(20))
    behavior_date = Column(Date, nullable=False)
    total_distance = Column(Float)
    total_time = Column(Float)
    average_speed = Column(Float)
    max_speed = Column(Float)
    speeding_count = Column(Integer, default=0)
    harsh_braking_count = Column(Integer, default=0)
    harsh_acceleration_count = Column(Integer, default=0)
    idle_time = Column(Float)
    fuel_efficiency = Column(Float)
    score = Column(Float)
    remarks = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'driver_id': self.driver_id,
            'driver_name': self.driver_name,
            'truck_id': self.truck_id,
            'plate_number': self.plate_number,
            'behavior_date': self.behavior_date.isoformat() if self.behavior_date else None,
            'total_distance': self.total_distance,
            'total_time': self.total_time,
            'average_speed': self.average_speed,
            'max_speed': self.max_speed,
            'speeding_count': self.speeding_count,
            'harsh_braking_count': self.harsh_braking_count,
            'harsh_acceleration_count': self.harsh_acceleration_count,
            'idle_time': self.idle_time,
            'fuel_efficiency': self.fuel_efficiency,
            'score': self.score,
            'remarks': self.remarks,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }