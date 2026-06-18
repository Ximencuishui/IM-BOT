import logging
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from database.db_config import get_db_session
from services.auth_service import login_required
from plugins.construction.service import ConstructionService

logger = logging.getLogger(__name__)

construction_bp = Blueprint('construction', __name__, url_prefix='/api/construction')


@construction_bp.route('/workers', methods=['GET', 'POST'])
@login_required
def workers():
    db: Session = get_db_session()
    service = ConstructionService(db)

    if request.method == 'GET':
        team = request.args.get('team', None)
        position = request.args.get('position', None)
        workers = service.list_workers(team, position)
        db.close()
        return jsonify({'success': True, 'count': len(workers), 'workers': workers}), 200

    data = request.get_json()
    if not data or 'name' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少工人姓名'}), 400

    result = service.create_worker(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@construction_bp.route('/attendance/checkin', methods=['POST'])
@login_required
def checkin():
    db: Session = get_db_session()
    service = ConstructionService(db)

    data = request.get_json()
    if not data or 'worker_id' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少工人ID'}), 400

    result = service.check_in(data['worker_id'], data.get('location'))
    db.close()
    return jsonify(result), 200


@construction_bp.route('/attendance/checkout', methods=['POST'])
@login_required
def checkout():
    db: Session = get_db_session()
    service = ConstructionService(db)

    data = request.get_json()
    if not data or 'worker_id' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少工人ID'}), 400

    result = service.check_out(data['worker_id'], data.get('location'))
    db.close()
    return jsonify(result), 200


@construction_bp.route('/attendance', methods=['GET'])
@login_required
def attendance():
    db: Session = get_db_session()
    service = ConstructionService(db)

    worker_id = request.args.get('worker_id', None)
    date_str = request.args.get('date', None)
    records = service.list_attendance(worker_id, date_str)
    db.close()
    return jsonify({'success': True, 'count': len(records), 'records': records}), 200


@construction_bp.route('/leave', methods=['POST'])
@login_required
def leave():
    db: Session = get_db_session()
    service = ConstructionService(db)

    data = request.get_json()
    if not data or 'worker_id' not in data or 'start_date' not in data or 'end_date' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400

    result = service.apply_leave(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@construction_bp.route('/leave/<int:leave_id>/approve', methods=['POST'])
@login_required
def approve_leave(leave_id):
    db: Session = get_db_session()
    service = ConstructionService(db)

    data = request.get_json()
    approved = data.get('approved', False)
    approved_by = data.get('approved_by', '')

    result = service.approve_leave(leave_id, approved, approved_by)
    db.close()
    return jsonify(result), 200


@construction_bp.route('/weather', methods=['GET', 'POST'])
@login_required
def weather():
    db: Session = get_db_session()
    service = ConstructionService(db)

    if request.method == 'GET':
        project_id = request.args.get('project_id', None)
        date_str = request.args.get('date', None)
        records = service.list_weather(project_id, date_str)
        db.close()
        return jsonify({'success': True, 'count': len(records), 'weather': records}), 200

    data = request.get_json()
    if not data or 'project_id' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少项目ID'}), 400

    result = service.create_weather(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@construction_bp.route('/schedule', methods=['GET', 'POST'])
@login_required
def schedule():
    db: Session = get_db_session()
    service = ConstructionService(db)

    if request.method == 'GET':
        project_id = request.args.get('project_id', None)
        records = service.list_schedules(project_id)
        db.close()
        return jsonify({'success': True, 'count': len(records), 'schedules': records}), 200

    data = request.get_json()
    if not data or 'project_id' not in data or 'task_name' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400

    result = service.create_schedule(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@construction_bp.route('/schedule/<int:schedule_id>/progress', methods=['POST'])
@login_required
def update_schedule_progress(schedule_id):
    db: Session = get_db_session()
    service = ConstructionService(db)

    data = request.get_json()
    if not data or 'progress' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少进度'}), 400

    result = service.update_schedule_progress(
        schedule_id,
        data['progress'],
        data.get('actual_start_date'),
        data.get('actual_end_date')
    )
    db.close()
    return jsonify(result), 200


@construction_bp.route('/work_area', methods=['GET', 'POST'])
@login_required
def work_area():
    db: Session = get_db_session()
    service = ConstructionService(db)

    if request.method == 'GET':
        project_id = request.args.get('project_id', None)
        records = service.list_schedules(project_id)
        db.close()
        return jsonify({'success': True, 'count': len(records), 'work_areas': records}), 200

    data = request.get_json()
    if not data or 'project_id' not in data or 'area_name' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400

    result = service.create_work_area(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@construction_bp.route('/work_area/assign', methods=['POST'])
@login_required
def assign_worker():
    db: Session = get_db_session()
    service = ConstructionService(db)

    data = request.get_json()
    if not data or 'work_area_id' not in data or 'worker_id' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400

    result = service.assign_worker(
        data['work_area_id'],
        data['worker_id'],
        data.get('date'),
        data.get('task', '')
    )
    db.close()
    return jsonify(result), 200


@construction_bp.route('/work_area/progress', methods=['POST'])
@login_required
def record_progress():
    db: Session = get_db_session()
    service = ConstructionService(db)

    data = request.get_json()
    if not data or 'work_area_id' not in data or 'progress' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400

    result = service.record_progress(
        data['work_area_id'],
        data.get('date'),
        data['progress'],
        data.get('completed_amount', 0),
        data.get('unit', '')
    )
    db.close()
    return jsonify(result), 200


@construction_bp.route('/work_volume', methods=['GET', 'POST'])
@login_required
def work_volume():
    db: Session = get_db_session()
    service = ConstructionService(db)

    if request.method == 'GET':
        project_id = request.args.get('project_id', None)
        work_type = request.args.get('work_type', None)
        date_str = request.args.get('date', None)
        records = service.list_work_volume(project_id, work_type, date_str)
        db.close()
        return jsonify({'success': True, 'count': len(records), 'work_volume': records}), 200

    data = request.get_json()
    if not data or 'project_id' not in data or 'work_type' not in data or 'quantity' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400

    result = service.create_work_volume(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@construction_bp.route('/material', methods=['GET', 'POST'])
@login_required
def material():
    db: Session = get_db_session()
    service = ConstructionService(db)

    if request.method == 'POST':
        data = request.get_json()
        if not data or 'material_name' not in data or 'unit' not in data:
            db.close()
            return jsonify({'success': False, 'error': '缺少必要参数'}), 400

        result = service.create_material(data)
        db.close()
        return jsonify(result), 201 if result['success'] else 400

    db.close()
    return jsonify({'success': True}), 200


@construction_bp.route('/material/in', methods=['POST'])
@login_required
def material_in():
    db: Session = get_db_session()
    service = ConstructionService(db)

    data = request.get_json()
    if not data or 'material_id' not in data or 'quantity' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400

    result = service.material_in(
        data['material_id'],
        data.get('project_id', 0),
        data['quantity'],
        data.get('price', 0),
        data.get('operator', '')
    )
    db.close()
    return jsonify(result), 200


@construction_bp.route('/material/out', methods=['POST'])
@login_required
def material_out():
    db: Session = get_db_session()
    service = ConstructionService(db)

    data = request.get_json()
    if not data or 'material_id' not in data or 'quantity' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400

    result = service.material_out(
        data['material_id'],
        data.get('project_id', 0),
        data['quantity'],
        data.get('operator', '')
    )
    db.close()
    return jsonify(result), 200


@construction_bp.route('/safety/check', methods=['POST'])
@login_required
def safety_check():
    db: Session = get_db_session()
    service = ConstructionService(db)

    data = request.get_json()
    if not data or 'project_id' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少项目ID'}), 400

    result = service.create_safety_check(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@construction_bp.route('/safety/issue', methods=['POST'])
@login_required
def safety_issue():
    db: Session = get_db_session()
    service = ConstructionService(db)

    data = request.get_json()
    if not data or 'project_id' not in data or 'description' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400

    result = service.create_safety_issue(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@construction_bp.route('/quality/check', methods=['POST'])
@login_required
def quality_check():
    db: Session = get_db_session()
    service = ConstructionService(db)

    data = request.get_json()
    if not data or 'project_id' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少项目ID'}), 400

    result = service.create_quality_check(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@construction_bp.route('/report', methods=['GET'])
@login_required
def report():
    db: Session = get_db_session()
    service = ConstructionService(db)

    report_type = request.args.get('type', 'daily')
    date_range = request.args.get('date', None)
    result = service.generate_report(report_type, date_range)
    db.close()
    return jsonify(result), 200 if result['success'] else 400


@construction_bp.route('/stats', methods=['GET'])
@login_required
def stats():
    db: Session = get_db_session()
    service = ConstructionService(db)

    period = request.args.get('period', 'today')
    stats = service.get_stats(period)
    db.close()
    return jsonify({'success': True, 'stats': stats}), 200


@construction_bp.route('/sites', methods=['GET', 'POST'])
@login_required
def sites():
    db: Session = get_db_session()
    service = ConstructionService(db)

    if request.method == 'GET':
        status = request.args.get('status', None)
        sites = service.list_sites(status)
        db.close()
        return jsonify({'success': True, 'count': len(sites), 'sites': sites}), 200

    data = request.get_json()
    if not data or 'site_name' not in data or 'contract_no' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少工地名称或合同编号'}), 400

    result = service.create_site(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@construction_bp.route('/sites/<int:site_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def site_detail(site_id):
    db: Session = get_db_session()
    service = ConstructionService(db)

    if request.method == 'GET':
        result = service.get_site(site_id)
        db.close()
        return jsonify(result), 200 if result['success'] else 404

    if request.method == 'PUT':
        data = request.get_json()
        result = service.update_site(site_id, data)
        db.close()
        return jsonify(result), 200 if result['success'] else 400

    if request.method == 'DELETE':
        result = service.delete_site(site_id)
        db.close()
        return jsonify(result), 200 if result['success'] else 400


@construction_bp.route('/workers/salary', methods=['POST'])
@login_required
def set_worker_salary():
    db: Session = get_db_session()
    service = ConstructionService(db)

    data = request.get_json()
    if not data or 'worker_id' not in data or 'salary_standard' not in data or 'join_date' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400

    result = service.set_worker_salary(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@construction_bp.route('/workers/salary/<int:salary_id>', methods=['PUT'])
@login_required
def update_worker_salary(salary_id):
    db: Session = get_db_session()
    service = ConstructionService(db)

    data = request.get_json()
    result = service.update_worker_salary(salary_id, data)
    db.close()
    return jsonify(result), 200 if result['success'] else 400


@construction_bp.route('/salary/calculate', methods=['POST'])
@login_required
def calculate_salary():
    db: Session = get_db_session()
    service = ConstructionService(db)

    data = request.get_json()
    if not data or 'worker_id' not in data or 'period_start' not in data or 'period_end' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400

    from datetime import datetime
    period_start = datetime.strptime(data['period_start'], '%Y-%m-%d').date()
    period_end = datetime.strptime(data['period_end'], '%Y-%m-%d').date()

    result = service.calculate_salary(data['worker_id'], period_start, period_end)
    db.close()
    return jsonify(result), 200 if result['success'] else 400


@construction_bp.route('/salary/report', methods=['GET'])
@login_required
def salary_report():
    db: Session = get_db_session()
    service = ConstructionService(db)

    from datetime import datetime
    period_start = request.args.get('period_start')
    period_end = request.args.get('period_end')

    if not period_start or not period_end:
        db.close()
        return jsonify({'success': False, 'error': '缺少日期参数'}), 400

    start_date = datetime.strptime(period_start, '%Y-%m-%d').date()
    end_date = datetime.strptime(period_end, '%Y-%m-%d').date()

    result = service.get_salary_report(start_date, end_date)
    db.close()
    return jsonify(result), 200


@construction_bp.route('/work_volume/plan', methods=['POST'])
@login_required
def set_plan_volume():
    db: Session = get_db_session()
    service = ConstructionService(db)

    data = request.get_json()
    if not data or 'site_id' not in data or 'work_type' not in data or 'plan_volume' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400

    from datetime import datetime
    if 'period_start' in data:
        data['period_start'] = datetime.strptime(data['period_start'], '%Y-%m-%d').date()
    if 'period_end' in data:
        data['period_end'] = datetime.strptime(data['period_end'], '%Y-%m-%d').date()

    result = service.set_plan_volume(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@construction_bp.route('/work_volume/daily', methods=['POST'])
@login_required
def report_daily_volume():
    db: Session = get_db_session()
    service = ConstructionService(db)

    data = request.get_json()
    if not data or 'site_id' not in data or 'work_type' not in data or 'actual_volume' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400

    from datetime import datetime
    if 'work_date' in data:
        data['work_date'] = datetime.strptime(data['work_date'], '%Y-%m-%d').date()

    result = service.report_daily_volume(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@construction_bp.route('/work_volume/stats', methods=['GET'])
@login_required
def work_volume_stats():
    db: Session = get_db_session()
    service = ConstructionService(db)

    site_id = request.args.get('site_id', type=int)
    period_start = request.args.get('period_start')
    period_end = request.args.get('period_end')

    if not site_id or not period_start or not period_end:
        db.close()
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400

    from datetime import datetime
    start_date = datetime.strptime(period_start, '%Y-%m-%d').date()
    end_date = datetime.strptime(period_end, '%Y-%m-%d').date()

    result = service.get_work_volume_stats(site_id, start_date, end_date)
    db.close()
    return jsonify(result), 200


@construction_bp.route('/expense/categories', methods=['GET', 'POST'])
@login_required
def expense_categories():
    db: Session = get_db_session()
    service = ConstructionService(db)

    if request.method == 'GET':
        categories = service.list_expense_categories()
        db.close()
        return jsonify({'success': True, 'count': len(categories), 'categories': categories}), 200

    data = request.get_json()
    if not data or 'category_name' not in data or 'category_code' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400

    result = service.create_expense_category(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@construction_bp.route('/expense/report', methods=['POST'])
@login_required
def report_expense():
    db: Session = get_db_session()
    service = ConstructionService(db)

    data = request.get_json()
    if not data or 'site_id' not in data or 'category_id' not in data or 'amount' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400

    from datetime import datetime
    if 'expense_date' in data:
        data['expense_date'] = datetime.strptime(data['expense_date'], '%Y-%m-%d').date()

    result = service.report_expense(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@construction_bp.route('/expense/report/stats', methods=['GET'])
@login_required
def expense_report_stats():
    db: Session = get_db_session()
    service = ConstructionService(db)

    site_id = request.args.get('site_id', type=int)
    period_start = request.args.get('period_start')
    period_end = request.args.get('period_end')

    if not site_id or not period_start or not period_end:
        db.close()
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400

    from datetime import datetime
    start_date = datetime.strptime(period_start, '%Y-%m-%d').date()
    end_date = datetime.strptime(period_end, '%Y-%m-%d').date()

    result = service.get_expense_report(site_id, start_date, end_date)
    db.close()
    return jsonify(result), 200


@construction_bp.route('/consumable', methods=['POST'])
@login_required
def create_consumable():
    db: Session = get_db_session()
    service = ConstructionService(db)

    data = request.get_json()
    if not data or 'consumable_name' not in data or 'unit' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400

    result = service.create_consumable(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@construction_bp.route('/consumable/in', methods=['POST'])
@login_required
def consumable_in():
    db: Session = get_db_session()
    service = ConstructionService(db)

    data = request.get_json()
    if not data or 'consumable_id' not in data or 'site_id' not in data or 'quantity' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400

    result = service.consumable_in(data['consumable_id'], data['site_id'], data['quantity'], data.get('operator_id'))
    db.close()
    return jsonify(result), 200


@construction_bp.route('/consumable/out', methods=['POST'])
@login_required
def consumable_out():
    db: Session = get_db_session()
    service = ConstructionService(db)

    data = request.get_json()
    if not data or 'consumable_id' not in data or 'site_id' not in data or 'quantity' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400

    result = service.consumable_out(data['consumable_id'], data['site_id'], data['quantity'], data.get('operator_id'), data.get('remark', ''))
    db.close()
    return jsonify(result), 200


@construction_bp.route('/consumable/stats', methods=['GET'])
@login_required
def consumable_stats():
    db: Session = get_db_session()
    service = ConstructionService(db)

    period_start = request.args.get('period_start')
    period_end = request.args.get('period_end')

    if not period_start or not period_end:
        db.close()
        return jsonify({'success': False, 'error': '缺少日期参数'}), 400

    from datetime import datetime
    start_date = datetime.strptime(period_start, '%Y-%m-%d').date()
    end_date = datetime.strptime(period_end, '%Y-%m-%d').date()

    result = service.get_consumable_stats(start_date, end_date)
    db.close()
    return jsonify(result), 200


@construction_bp.route('/equipment/lease', methods=['POST'])
@login_required
def create_equipment_lease():
    db: Session = get_db_session()
    service = ConstructionService(db)

    data = request.get_json()
    if not data or 'equipment_name' not in data or 'site_id' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400

    from datetime import datetime
    if 'lease_start_date' in data:
        data['lease_start_date'] = datetime.strptime(data['lease_start_date'], '%Y-%m-%d').date()
    if 'lease_end_date' in data:
        data['lease_end_date'] = datetime.strptime(data['lease_end_date'], '%Y-%m-%d').date()

    result = service.create_equipment_lease(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@construction_bp.route('/equipment/lease/expiring', methods=['GET'])
@login_required
def lease_expiring():
    db: Session = get_db_session()
    service = ConstructionService(db)

    days_before = request.args.get('days_before', 7, type=int)
    leases = service.get_lease_expiring(days_before)
    db.close()
    return jsonify({'success': True, 'count': len(leases), 'leases': leases}), 200


@construction_bp.route('/equipment/lease/report', methods=['GET'])
@login_required
def lease_cost_report():
    db: Session = get_db_session()
    service = ConstructionService(db)

    site_id = request.args.get('site_id', type=int)
    period_start = request.args.get('period_start')
    period_end = request.args.get('period_end')

    if not site_id or not period_start or not period_end:
        db.close()
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400

    from datetime import datetime
    start_date = datetime.strptime(period_start, '%Y-%m-%d').date()
    end_date = datetime.strptime(period_end, '%Y-%m-%d').date()

    result = service.get_lease_cost_report(site_id, start_date, end_date)
    db.close()
    return jsonify(result), 200


@construction_bp.route('/financial/record', methods=['POST'])
@login_required
def create_financial_record():
    db: Session = get_db_session()
    service = ConstructionService(db)

    data = request.get_json()
    if not data or 'record_type' not in data or 'amount' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400

    from datetime import datetime
    if 'record_date' in data:
        data['record_date'] = datetime.strptime(data['record_date'], '%Y-%m-%d').date()

    result = service.create_financial_record(data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@construction_bp.route('/financial/report', methods=['GET'])
@login_required
def financial_report():
    db: Session = get_db_session()
    service = ConstructionService(db)

    period_start = request.args.get('period_start')
    period_end = request.args.get('period_end')

    if not period_start or not period_end:
        db.close()
        return jsonify({'success': False, 'error': '缺少日期参数'}), 400

    from datetime import datetime
    start_date = datetime.strptime(period_start, '%Y-%m-%d').date()
    end_date = datetime.strptime(period_end, '%Y-%m-%d').date()

    result = service.get_financial_report(start_date, end_date)
    db.close()
    return jsonify(result), 200


@construction_bp.route('/message/parse', methods=['POST'])
@login_required
def parse_message():
    db: Session = get_db_session()
    service = ConstructionService(db)

    data = request.get_json()
    if not data or 'message_text' not in data:
        db.close()
        return jsonify({'success': False, 'error': '缺少消息内容'}), 400

    result = service.parse_message(data['message_text'])
    db.close()
    return jsonify({'success': True, 'data': result}), 200