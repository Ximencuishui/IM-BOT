"""
教育培训行业插件API接口
"""
import logging
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from database.db_config import get_db_session
from services.auth_service import login_required, get_current_user_from_request
from plugins.education.service import EducationService

logger = logging.getLogger(__name__)

education_bp = Blueprint('education', __name__, url_prefix='/api/education')
education_service = EducationService()


@education_bp.route('/courses', methods=['GET', 'POST'])
@login_required
def courses():
    if request.method == 'GET':
        category = request.args.get('category', None)
        db: Session = get_db_session()
        courses = education_service.list_courses(db, category)
        db.close()
        return jsonify({'success': True, 'count': len(courses), 'courses': courses}), 200

    data = request.get_json()
    if not data or 'course_name' not in data:
        return jsonify({'success': False, 'error': '缺少课程名称'}), 400

    db: Session = get_db_session()
    result = education_service.create_course(db, data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@education_bp.route('/students', methods=['GET', 'POST'])
@login_required
def students():
    if request.method == 'GET':
        db: Session = get_db_session()
        students = education_service.list_students(db)
        db.close()
        return jsonify({'success': True, 'count': len(students), 'students': students}), 200

    data = request.get_json()
    if not data or 'student_name' not in data or 'phone' not in data:
        return jsonify({'success': False, 'error': '缺少学员名称或手机号'}), 400

    db: Session = get_db_session()
    result = education_service.create_student(db, data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@education_bp.route('/teachers', methods=['GET', 'POST'])
@login_required
def teachers():
    if request.method == 'GET':
        db: Session = get_db_session()
        teachers = education_service.list_teachers(db)
        db.close()
        return jsonify({'success': True, 'count': len(teachers), 'teachers': teachers}), 200

    data = request.get_json()
    if not data or 'teacher_name' not in data or 'phone' not in data:
        return jsonify({'success': False, 'error': '缺少教师名称或手机号'}), 400

    db: Session = get_db_session()
    result = education_service.create_teacher(db, data)
    db.close()
    return jsonify(result), 201 if result['success'] else 400


@education_bp.route('/enroll', methods=['POST'])
@login_required
def enroll():
    data = request.get_json()
    if not data or 'student_id' not in data or 'course_id' not in data:
        return jsonify({'success': False, 'error': '缺少学员ID或课程ID'}), 400

    db: Session = get_db_session()
    result = education_service.enroll(db, data['student_id'], data['course_id'], data)
    db.close()
    return jsonify(result), 200 if result['success'] else 400


@education_bp.route('/progress', methods=['POST'])
@login_required
def progress():
    data = request.get_json()
    if not data or 'student_id' not in data or 'course_id' not in data or 'progress_percent' not in data:
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400

    db: Session = get_db_session()
    result = education_service.update_progress(db, data['student_id'], data['course_id'], data['progress_percent'])
    db.close()
    return jsonify(result), 200


@education_bp.route('/assignment', methods=['POST'])
@login_required
def assignment():
    data = request.get_json()
    if not data or 'student_id' not in data or 'course_id' not in data or 'content' not in data:
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400

    db: Session = get_db_session()
    result = education_service.submit_assignment(db, data['student_id'], data['course_id'], data['content'])
    db.close()
    return jsonify(result), 201


@education_bp.route('/assignment/<int:assignment_id>/grade', methods=['POST'])
@login_required
def grade_assignment(assignment_id):
    data = request.get_json()
    if not data or 'score' not in data:
        return jsonify({'success': False, 'error': '缺少分数'}), 400

    db: Session = get_db_session()
    result = education_service.grade_assignment(db, assignment_id, data['score'], data.get('feedback'))
    db.close()
    return jsonify(result), 200 if result['success'] else 400


@education_bp.route('/attendance', methods=['POST'])
@login_required
def attendance():
    data = request.get_json()
    if not data or 'student_id' not in data or 'course_id' not in data:
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400

    db: Session = get_db_session()
    result = education_service.record_attendance(db, data['student_id'], data['course_id'], data.get('status', 'attended'))
    db.close()
    return jsonify(result), 200


@education_bp.route('/report', methods=['GET'])
@login_required
def report():
    report_type = request.args.get('type', 'student_progress')
    db: Session = get_db_session()
    result = education_service.generate_report(db, report_type)
    db.close()
    return jsonify(result), 200 if result['success'] else 400