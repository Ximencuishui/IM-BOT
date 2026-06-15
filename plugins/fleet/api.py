"""
车队调度插件API接口
"""
from flask import Blueprint, request, jsonify
from database.db_config import get_db_session
from .service import FleetService

fleet_bp = Blueprint('fleet', __name__, url_prefix='/api/fleet')


def get_user_id():
    return 1


@fleet_bp.route('/drivers', methods=['GET'])
def get_drivers():
    user_id = get_user_id()
    status = request.args.get('status')
    db = get_db_session()
    service = FleetService(db)
    drivers = service.get_drivers(user_id, status)
    db.close()
    return jsonify({'success': True, 'data': drivers})


@fleet_bp.route('/drivers/<int:driver_id>', methods=['GET'])
def get_driver(driver_id):
    user_id = get_user_id()
    db = get_db_session()
    service = FleetService(db)
    driver = service.get_driver(user_id, driver_id)
    db.close()
    if driver:
        return jsonify({'success': True, 'data': driver})
    return jsonify({'success': False, 'error': '司机不存在'}), 404


@fleet_bp.route('/drivers', methods=['POST'])
def create_driver():
    user_id = get_user_id()
    data = request.get_json()
    data['user_id'] = user_id
    db = get_db_session()
    service = FleetService(db)
    result = service.create_driver(data)
    db.close()
    if result['success']:
        return jsonify(result), 201
    return jsonify(result), 400


@fleet_bp.route('/drivers/<int:driver_id>', methods=['PUT'])
def update_driver(driver_id):
    user_id = get_user_id()
    data = request.get_json()
    db = get_db_session()
    service = FleetService(db)
    result = service.update_driver(user_id, driver_id, data)
    db.close()
    if result['success']:
        return jsonify(result)
    return jsonify(result), 400


@fleet_bp.route('/drivers/<int:driver_id>', methods=['DELETE'])
def delete_driver(driver_id):
    user_id = get_user_id()
    db = get_db_session()
    service = FleetService(db)
    result = service.delete_driver(user_id, driver_id)
    db.close()
    if result['success']:
        return jsonify(result)
    return jsonify(result), 400


@fleet_bp.route('/mud-trucks', methods=['GET'])
def get_mud_trucks():
    user_id = get_user_id()
    status = request.args.get('status')
    db = get_db_session()
    service = FleetService(db)
    trucks = service.get_mud_trucks(user_id, status)
    db.close()
    return jsonify({'success': True, 'data': trucks})


@fleet_bp.route('/mud-trucks/<int:truck_id>', methods=['GET'])
def get_mud_truck(truck_id):
    user_id = get_user_id()
    db = get_db_session()
    service = FleetService(db)
    truck = service.get_mud_truck(user_id, truck_id)
    db.close()
    if truck:
        return jsonify({'success': True, 'data': truck})
    return jsonify({'success': False, 'error': '泥土车不存在'}), 404


@fleet_bp.route('/mud-trucks', methods=['POST'])
def create_mud_truck():
    user_id = get_user_id()
    data = request.get_json()
    data['user_id'] = user_id
    db = get_db_session()
    service = FleetService(db)
    result = service.create_mud_truck(data)
    db.close()
    if result['success']:
        return jsonify(result), 201
    return jsonify(result), 400


@fleet_bp.route('/mud-trucks/<int:truck_id>', methods=['PUT'])
def update_mud_truck(truck_id):
    user_id = get_user_id()
    data = request.get_json()
    db = get_db_session()
    service = FleetService(db)
    result = service.update_mud_truck(user_id, truck_id, data)
    db.close()
    if result['success']:
        return jsonify(result)
    return jsonify(result), 400


@fleet_bp.route('/mud-trucks/<int:truck_id>', methods=['DELETE'])
def delete_mud_truck(truck_id):
    user_id = get_user_id()
    db = get_db_session()
    service = FleetService(db)
    result = service.delete_mud_truck(user_id, truck_id)
    db.close()
    if result['success']:
        return jsonify(result)
    return jsonify(result), 400


@fleet_bp.route('/mud-trucks/<int:truck_id>/status', methods=['POST'])
def update_mud_truck_status(truck_id):
    user_id = get_user_id()
    data = request.get_json()
    db = get_db_session()
    service = FleetService(db)
    result = service.update_mud_truck_status(user_id, truck_id, data)
    db.close()
    if result['success']:
        return jsonify(result)
    return jsonify(result), 400


@fleet_bp.route('/logistics-trucks', methods=['GET'])
def get_logistics_trucks():
    user_id = get_user_id()
    status = request.args.get('status')
    db = get_db_session()
    service = FleetService(db)
    trucks = service.get_logistics_trucks(user_id, status)
    db.close()
    return jsonify({'success': True, 'data': trucks})


@fleet_bp.route('/logistics-trucks/<int:truck_id>', methods=['GET'])
def get_logistics_truck(truck_id):
    user_id = get_user_id()
    db = get_db_session()
    service = FleetService(db)
    truck = service.get_logistics_truck(user_id, truck_id)
    db.close()
    if truck:
        return jsonify({'success': True, 'data': truck})
    return jsonify({'success': False, 'error': '物流车不存在'}), 404


@fleet_bp.route('/logistics-trucks', methods=['POST'])
def create_logistics_truck():
    user_id = get_user_id()
    data = request.get_json()
    data['user_id'] = user_id
    db = get_db_session()
    service = FleetService(db)
    result = service.create_logistics_truck(data)
    db.close()
    if result['success']:
        return jsonify(result), 201
    return jsonify(result), 400


@fleet_bp.route('/logistics-trucks/<int:truck_id>', methods=['PUT'])
def update_logistics_truck(truck_id):
    user_id = get_user_id()
    data = request.get_json()
    db = get_db_session()
    service = FleetService(db)
    result = service.update_logistics_truck(user_id, truck_id, data)
    db.close()
    if result['success']:
        return jsonify(result)
    return jsonify(result), 400


@fleet_bp.route('/logistics-trucks/<int:truck_id>', methods=['DELETE'])
def delete_logistics_truck(truck_id):
    user_id = get_user_id()
    db = get_db_session()
    service = FleetService(db)
    result = service.delete_logistics_truck(user_id, truck_id)
    db.close()
    if result['success']:
        return jsonify(result)
    return jsonify(result), 400


@fleet_bp.route('/logistics-trucks/<int:truck_id>/status', methods=['POST'])
def update_logistics_truck_status(truck_id):
    user_id = get_user_id()
    data = request.get_json()
    db = get_db_session()
    service = FleetService(db)
    result = service.update_logistics_truck_status(user_id, truck_id, data)
    db.close()
    if result['success']:
        return jsonify(result)
    return jsonify(result), 400


@fleet_bp.route('/tasks', methods=['GET'])
def get_tasks():
    user_id = get_user_id()
    task_type = request.args.get('task_type')
    status = request.args.get('status')
    db = get_db_session()
    service = FleetService(db)
    tasks = service.get_tasks(user_id, task_type, status)
    db.close()
    return jsonify({'success': True, 'data': tasks})


@fleet_bp.route('/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    user_id = get_user_id()
    db = get_db_session()
    service = FleetService(db)
    task = service.get_task(user_id, task_id)
    db.close()
    if task:
        return jsonify({'success': True, 'data': task})
    return jsonify({'success': False, 'error': '任务不存在'}), 404


@fleet_bp.route('/tasks', methods=['POST'])
def create_task():
    user_id = get_user_id()
    data = request.get_json()
    data['user_id'] = user_id
    db = get_db_session()
    service = FleetService(db)
    result = service.create_task(data)
    db.close()
    if result['success']:
        return jsonify(result), 201
    return jsonify(result), 400


@fleet_bp.route('/tasks/<int:task_id>/assign', methods=['POST'])
def assign_task(task_id):
    user_id = get_user_id()
    data = request.get_json()
    db = get_db_session()
    service = FleetService(db)
    result = service.assign_task(user_id, task_id, data)
    db.close()
    if result['success']:
        return jsonify(result)
    return jsonify(result), 400


@fleet_bp.route('/tasks/<int:task_id>/auto-assign', methods=['POST'])
def auto_assign_task(task_id):
    user_id = get_user_id()
    db = get_db_session()
    service = FleetService(db)
    result = service.auto_assign_task(user_id, task_id)
    db.close()
    if result['success']:
        return jsonify(result)
    return jsonify(result), 400


@fleet_bp.route('/tasks/<int:task_id>/status', methods=['POST'])
def update_task_status(task_id):
    user_id = get_user_id()
    data = request.get_json()
    status = data.get('status')
    db = get_db_session()
    service = FleetService(db)
    result = service.update_task_status(user_id, task_id, status)
    db.close()
    if result['success']:
        return jsonify(result)
    return jsonify(result), 400


@fleet_bp.route('/route/calculate', methods=['POST'])
def calculate_route():
    user_id = get_user_id()
    data = request.get_json()
    origin = data.get('origin')
    destination = data.get('destination')
    waypoints = data.get('waypoints')
    db = get_db_session()
    service = FleetService(db)
    route = service.calculate_route(user_id, origin, destination, waypoints)
    db.close()
    return jsonify({'success': True, 'data': route})


@fleet_bp.route('/route/optimize', methods=['POST'])
def optimize_route():
    user_id = get_user_id()
    data = request.get_json()
    origin = data.get('origin')
    destination = data.get('destination')
    constraints = data.get('constraints')
    db = get_db_session()
    service = FleetService(db)
    route = service.optimize_route(user_id, origin, destination, constraints)
    db.close()
    return jsonify({'success': True, 'data': route})


@fleet_bp.route('/maintenance', methods=['GET'])
def get_maintenance_records():
    user_id = get_user_id()
    truck_id = request.args.get('truck_id', type=int)
    truck_type = request.args.get('truck_type')
    db = get_db_session()
    service = FleetService(db)
    records = service.get_maintenance_records(user_id, truck_id, truck_type)
    db.close()
    return jsonify({'success': True, 'data': records})


@fleet_bp.route('/maintenance', methods=['POST'])
def create_maintenance():
    user_id = get_user_id()
    data = request.get_json()
    data['user_id'] = user_id
    db = get_db_session()
    service = FleetService(db)
    result = service.create_maintenance(data)
    db.close()
    if result['success']:
        return jsonify(result), 201
    return jsonify(result), 400


@fleet_bp.route('/maintenance/alerts', methods=['GET'])
def get_maintenance_alerts():
    user_id = get_user_id()
    db = get_db_session()
    service = FleetService(db)
    alerts = service.get_maintenance_alerts(user_id)
    db.close()
    return jsonify({'success': True, 'data': alerts})


@fleet_bp.route('/transport-records', methods=['GET'])
def get_transport_records():
    user_id = get_user_id()
    truck_id = request.args.get('truck_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    date_range = {}
    if start_date:
        date_range['start_date'] = start_date
    if end_date:
        date_range['end_date'] = end_date
    db = get_db_session()
    service = FleetService(db)
    records = service.get_transport_records(user_id, truck_id, date_range if date_range else None)
    db.close()
    return jsonify({'success': True, 'data': records})


@fleet_bp.route('/driver-behavior', methods=['GET'])
def get_driver_behavior():
    user_id = get_user_id()
    driver_id = request.args.get('driver_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    date_range = {}
    if start_date:
        date_range['start_date'] = start_date
    if end_date:
        date_range['end_date'] = end_date
    db = get_db_session()
    service = FleetService(db)
    behavior = service.get_driver_behavior(user_id, driver_id, date_range if date_range else None)
    db.close()
    return jsonify({'success': True, 'data': behavior})


@fleet_bp.route('/stats', methods=['GET'])
def get_fleet_stats():
    user_id = get_user_id()
    db = get_db_session()
    service = FleetService(db)
    stats = service.get_fleet_stats(user_id)
    db.close()
    return jsonify({'success': True, 'data': stats})