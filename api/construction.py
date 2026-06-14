"""
工地管理API
提供工人管理、考勤打卡、天气工期、工作面记录、工程量记录等CRUD操作
"""
import logging
from flask import Blueprint, request, jsonify

from services.construction_service import construction_service

logger = logging.getLogger(__name__)

construction_bp = Blueprint('construction', __name__, url_prefix='/api/construction')


@construction_bp.route('/workers', methods=['POST'])
def create_worker():
    """创建工人"""
    try:
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({'success': False, 'error': '缺少必要参数: name'}), 400

        result = construction_service.create_worker(data)
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"创建工人失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@construction_bp.route('/workers', methods=['GET'])
def get_workers():
    """获取工人列表"""
    try:
        team = request.args.get('team', None)
        position = request.args.get('position', None)
        workers = construction_service.get_workers(team, position)
        return jsonify({
            'success': True,
            'count': len(workers),
            'workers': [worker.to_dict() for worker in workers],
        }), 200
    except Exception as e:
        logger.error(f"获取工人列表失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@construction_bp.route('/workers/<int:worker_id>', methods=['GET'])
def get_worker(worker_id):
    """获取工人详情"""
    try:
        worker = construction_service.get_worker(worker_id)
        if not worker:
            return jsonify({'success': False, 'error': '工人不存在'}), 404
        return jsonify({'success': True, 'data': worker.to_dict()}), 200
    except Exception as e:
        logger.error(f"获取工人详情失败: worker_id={worker_id}, error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@construction_bp.route('/attendance/check-in', methods=['POST'])
def check_in():
    """上班打卡"""
    try:
        data = request.get_json()
        if not data or 'worker_id' not in data:
            return jsonify({'success': False, 'error': '缺少必要参数: worker_id'}), 400

        result = construction_service.check_in(
            data['worker_id'],
            data.get('location', None)
        )
        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        logger.error(f"打卡失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@construction_bp.route('/attendance/check-out', methods=['POST'])
def check_out():
    """下班打卡"""
    try:
        data = request.get_json()
        if not data or 'worker_id' not in data:
            return jsonify({'success': False, 'error': '缺少必要参数: worker_id'}), 400

        result = construction_service.check_out(
            data['worker_id'],
            data.get('location', None)
        )
        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        logger.error(f"下班打卡失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@construction_bp.route('/attendance', methods=['GET'])
def get_attendance():
    """获取考勤记录"""
    try:
        worker_id = request.args.get('worker_id', None)
        date_str = request.args.get('date', None)

        records = construction_service.get_attendance(
            int(worker_id) if worker_id else None,
            date_str
        )
        return jsonify({
            'success': True,
            'count': len(records),
            'attendance': [r.to_dict() for r in records],
        }), 200
    except Exception as e:
        logger.error(f"获取考勤记录失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@construction_bp.route('/leave', methods=['POST'])
def apply_leave():
    """申请请假"""
    try:
        data = request.get_json()
        if not data or 'worker_id' not in data:
            return jsonify({'success': False, 'error': '缺少必要参数: worker_id'}), 400

        result = construction_service.apply_leave(data)
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"申请请假失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@construction_bp.route('/leave/<int:leave_id>/approve', methods=['POST'])
def approve_leave(leave_id):
    """审批请假"""
    try:
        data = request.get_json()
        if not data or 'approved' not in data:
            return jsonify({'success': False, 'error': '缺少必要参数: approved'}), 400

        result = construction_service.approve_leave(
            leave_id,
            data['approved'],
            data.get('approved_by', '')
        )
        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        logger.error(f"审批请假失败: leave_id={leave_id}, error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@construction_bp.route('/weather', methods=['POST'])
def fetch_weather():
    """获取天气信息"""
    try:
        data = request.get_json()
        if not data or 'project_id' not in data or 'city' not in data:
            return jsonify({'success': False, 'error': '缺少必要参数: project_id, city'}), 400

        result = construction_service.fetch_weather(data['project_id'], data['city'])
        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        logger.error(f"获取天气失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@construction_bp.route('/weather', methods=['GET'])
def get_weather():
    """获取天气记录"""
    try:
        project_id = request.args.get('project_id', None)
        date_str = request.args.get('date', None)

        if not project_id:
            return jsonify({'success': False, 'error': '缺少必要参数: project_id'}), 400

        records = construction_service.get_weather(int(project_id), date_str)
        return jsonify({
            'success': True,
            'count': len(records),
            'weather': [r.to_dict() for r in records],
        }), 200
    except Exception as e:
        logger.error(f"获取天气记录失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@construction_bp.route('/schedule', methods=['POST'])
def create_schedule():
    """创建工期计划"""
    try:
        data = request.get_json()
        if not data or 'project_id' not in data or 'task_name' not in data:
            return jsonify({'success': False, 'error': '缺少必要参数: project_id, task_name'}), 400

        result = construction_service.create_schedule(data)
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"创建工期计划失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@construction_bp.route('/schedule/<int:schedule_id>/progress', methods=['PUT'])
def update_schedule_progress(schedule_id):
    """更新进度"""
    try:
        data = request.get_json()
        if not data or 'progress' not in data:
            return jsonify({'success': False, 'error': '缺少必要参数: progress'}), 400

        result = construction_service.update_schedule_progress(
            schedule_id,
            data['progress'],
            data.get('actual_start_date'),
            data.get('actual_end_date')
        )
        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        logger.error(f"更新进度失败: schedule_id={schedule_id}, error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@construction_bp.route('/schedule', methods=['GET'])
def get_schedules():
    """获取工期计划列表"""
    try:
        project_id = request.args.get('project_id', None)
        if not project_id:
            return jsonify({'success': False, 'error': '缺少必要参数: project_id'}), 400

        schedules = construction_service.get_schedules(int(project_id))
        return jsonify({
            'success': True,
            'count': len(schedules),
            'schedules': [s.to_dict() for s in schedules],
        }), 200
    except Exception as e:
        logger.error(f"获取工期计划列表失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@construction_bp.route('/work-area', methods=['POST'])
def create_work_area():
    """创建工作面"""
    try:
        data = request.get_json()
        if not data or 'project_id' not in data or 'area_name' not in data:
            return jsonify({'success': False, 'error': '缺少必要参数: project_id, area_name'}), 400

        result = construction_service.create_work_area(data)
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"创建工作面失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@construction_bp.route('/work-area/assign', methods=['POST'])
def assign_worker():
    """安排工人到工作面"""
    try:
        data = request.get_json()
        required = ['work_area_id', 'worker_id', 'date', 'task']
        if not data or any(field not in data for field in required):
            return jsonify({'success': False, 'error': f'缺少必要参数: {", ".join(required)}'}), 400

        result = construction_service.assign_worker(
            data['work_area_id'],
            data['worker_id'],
            data['date'],
            data['task']
        )
        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        logger.error(f"安排工人失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@construction_bp.route('/work-area/progress', methods=['POST'])
def record_progress():
    """记录工作面进度"""
    try:
        data = request.get_json()
        required = ['work_area_id', 'date', 'progress', 'completed_amount', 'unit']
        if not data or any(field not in data for field in required):
            return jsonify({'success': False, 'error': f'缺少必要参数: {", ".join(required)}'}), 400

        result = construction_service.record_progress(
            data['work_area_id'],
            data['date'],
            data['progress'],
            data['completed_amount'],
            data['unit']
        )
        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        logger.error(f"记录进度失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@construction_bp.route('/work-volume', methods=['POST'])
def create_work_volume():
    """创建工程量记录"""
    try:
        data = request.get_json()
        if not data or 'project_id' not in data or 'work_type' not in data:
            return jsonify({'success': False, 'error': '缺少必要参数: project_id, work_type'}), 400

        result = construction_service.create_work_volume(data)
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"创建工程量记录失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@construction_bp.route('/work-volume', methods=['GET'])
def get_work_volume():
    """获取工程量记录"""
    try:
        project_id = request.args.get('project_id', None)
        work_type = request.args.get('work_type', None)
        date_str = request.args.get('date', None)

        if not project_id:
            return jsonify({'success': False, 'error': '缺少必要参数: project_id'}), 400

        records = construction_service.get_work_volume(int(project_id), work_type, date_str)
        return jsonify({
            'success': True,
            'count': len(records),
            'work_volume': [r.to_dict() for r in records],
        }), 200
    except Exception as e:
        logger.error(f"获取工程量记录失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@construction_bp.route('/material', methods=['POST'])
def create_material():
    """创建材料"""
    try:
        data = request.get_json()
        if not data or 'material_name' not in data or 'unit' not in data:
            return jsonify({'success': False, 'error': '缺少必要参数: material_name, unit'}), 400

        result = construction_service.create_material(data)
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"创建材料失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@construction_bp.route('/material/in', methods=['POST'])
def material_in():
    """材料入库"""
    try:
        data = request.get_json()
        required = ['material_id', 'project_id', 'quantity', 'price', 'operator']
        if not data or any(field not in data for field in required):
            return jsonify({'success': False, 'error': f'缺少必要参数: {", ".join(required)}'}), 400

        result = construction_service.material_in(
            data['material_id'],
            data['project_id'],
            data['quantity'],
            data['price'],
            data['operator']
        )
        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        logger.error(f"材料入库失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@construction_bp.route('/material/out', methods=['POST'])
def material_out():
    """材料出库"""
    try:
        data = request.get_json()
        required = ['material_id', 'project_id', 'quantity', 'operator']
        if not data or any(field not in data for field in required):
            return jsonify({'success': False, 'error': f'缺少必要参数: {", ".join(required)}'}), 400

        result = construction_service.material_out(
            data['material_id'],
            data['project_id'],
            data['quantity'],
            data['operator']
        )
        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        logger.error(f"材料出库失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@construction_bp.route('/safety-check', methods=['POST'])
def create_safety_check():
    """创建安全检查"""
    try:
        data = request.get_json()
        if not data or 'project_id' not in data:
            return jsonify({'success': False, 'error': '缺少必要参数: project_id'}), 400

        result = construction_service.create_safety_check(data)
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"创建安全检查失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@construction_bp.route('/safety-issue', methods=['POST'])
def create_safety_issue():
    """创建安全隐患"""
    try:
        data = request.get_json()
        if not data or 'project_id' not in data or 'description' not in data:
            return jsonify({'success': False, 'error': '缺少必要参数: project_id, description'}), 400

        result = construction_service.create_safety_issue(data)
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"创建安全隐患失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@construction_bp.route('/quality-check', methods=['POST'])
def create_quality_check():
    """创建质量检查"""
    try:
        data = request.get_json()
        if not data or 'project_id' not in data:
            return jsonify({'success': False, 'error': '缺少必要参数: project_id'}), 400

        result = construction_service.create_quality_check(data)
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"创建质量检查失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@construction_bp.route('/daily-report', methods=['GET'])
def get_daily_report():
    """获取日报"""
    try:
        project_id = request.args.get('project_id', None)
        date_str = request.args.get('date', None)

        if not project_id:
            return jsonify({'success': False, 'error': '缺少必要参数: project_id'}), 400

        result = construction_service.generate_daily_report(int(project_id), date_str)
        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        logger.error(f"获取日报失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
