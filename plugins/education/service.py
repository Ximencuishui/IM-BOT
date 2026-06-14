"""
教育培训行业插件服务层
"""
from datetime import datetime
from sqlalchemy.orm import Session
from plugins.education.models import (
    EducationCourse, EducationStudent, EducationTeacher,
    EducationEnrollment, EducationProgress, EducationAssignment, EducationAttendance
)


class EducationService:
    """教育培训服务"""

    def list_courses(self, db: Session, category: str = None) -> list:
        query = db.query(EducationCourse).filter(EducationCourse.is_active == True)
        if category:
            query = query.filter(EducationCourse.category == category)
        return [c.to_dict() for c in query.all()]

    def create_course(self, db: Session, data: dict) -> dict:
        course = EducationCourse(
            course_name=data['course_name'],
            category=data.get('category', ''),
            price=data.get('price', 0.0),
            duration=data.get('duration'),
            description=data.get('description', ''),
            cover_image=data.get('cover_image', '')
        )
        db.add(course)
        db.commit()
        db.refresh(course)
        return {'success': True, 'course': course.to_dict()}

    def list_students(self, db: Session) -> list:
        return [s.to_dict() for s in db.query(EducationStudent).filter(EducationStudent.is_active == True).all()]

    def create_student(self, db: Session, data: dict) -> dict:
        student = EducationStudent(
            student_name=data['student_name'],
            phone=data['phone'],
            wechat_id=data.get('wechat_id', ''),
            level=data.get('level', 'beginner')
        )
        db.add(student)
        db.commit()
        db.refresh(student)
        return {'success': True, 'student': student.to_dict()}

    def list_teachers(self, db: Session) -> list:
        return [t.to_dict() for t in db.query(EducationTeacher).filter(EducationTeacher.is_active == True).all()]

    def create_teacher(self, db: Session, data: dict) -> dict:
        teacher = EducationTeacher(
            teacher_name=data['teacher_name'],
            phone=data['phone'],
            specialty=data.get('specialty', ''),
            experience=data.get('experience'),
            bio=data.get('bio', '')
        )
        db.add(teacher)
        db.commit()
        db.refresh(teacher)
        return {'success': True, 'teacher': teacher.to_dict()}

    def enroll(self, db: Session, student_id: int, course_id: int, data: dict = None) -> dict:
        existing = db.query(EducationEnrollment).filter(
            EducationEnrollment.student_id == student_id,
            EducationEnrollment.course_id == course_id
        ).first()
        if existing:
            return {'success': False, 'error': '已报名该课程'}

        enrollment = EducationEnrollment(
            student_id=student_id,
            course_id=course_id,
            payment_amount=data.get('payment_amount', 0.0) if data else 0.0
        )
        db.add(enrollment)

        progress = EducationProgress(
            student_id=student_id,
            course_id=course_id
        )
        db.add(progress)

        db.commit()
        return {'success': True, 'enrollment': enrollment.to_dict()}

    def update_progress(self, db: Session, student_id: int, course_id: int, progress_percent: float) -> dict:
        progress = db.query(EducationProgress).filter(
            EducationProgress.student_id == student_id,
            EducationProgress.course_id == course_id
        ).first()

        if not progress:
            progress = EducationProgress(
                student_id=student_id,
                course_id=course_id
            )
            db.add(progress)

        progress.progress_percent = progress_percent
        progress.last_learned_at = datetime.now()
        db.commit()
        db.refresh(progress)

        return {'success': True, 'progress': progress.to_dict()}

    def submit_assignment(self, db: Session, student_id: int, course_id: int, content: str) -> dict:
        assignment = EducationAssignment(
            student_id=student_id,
            course_id=course_id,
            content=content,
            submitted_at=datetime.now()
        )
        db.add(assignment)
        db.commit()
        db.refresh(assignment)
        return {'success': True, 'assignment': assignment.to_dict()}

    def grade_assignment(self, db: Session, assignment_id: int, score: float, feedback: str = None) -> dict:
        assignment = db.query(EducationAssignment).filter(EducationAssignment.id == assignment_id).first()
        if not assignment:
            return {'success': False, 'error': '作业不存在'}

        assignment.score = score
        assignment.feedback = feedback
        db.commit()
        db.refresh(assignment)
        return {'success': True, 'assignment': assignment.to_dict()}

    def record_attendance(self, db: Session, student_id: int, course_id: int, status: str = 'attended') -> dict:
        today = datetime.now().date()
        existing = db.query(EducationAttendance).filter(
            EducationAttendance.student_id == student_id,
            EducationAttendance.course_id == course_id,
            EducationAttendance.date >= datetime(today.year, today.month, today.day),
            EducationAttendance.date < datetime(today.year, today.month, today.day, 23, 59, 59)
        ).first()

        if existing:
            existing.status = status
        else:
            existing = EducationAttendance(
                student_id=student_id,
                course_id=course_id,
                date=datetime.now(),
                status=status
            )
            db.add(existing)

        db.commit()
        return {'success': True, 'attendance': existing.to_dict()}

    def generate_report(self, db: Session, report_type: str) -> dict:
        if report_type == 'student_progress':
            students = db.query(EducationStudent).all()
            progress_data = []
            for student in students:
                avg_progress = db.query(EducationProgress.progress_percent).filter(
                    EducationProgress.student_id == student.id
                ).all()
                if avg_progress:
                    avg = sum(p[0] for p in avg_progress) / len(avg_progress)
                else:
                    avg = 0
                progress_data.append({
                    'student_name': student.student_name,
                    'avg_progress': round(avg, 2),
                    'course_count': len(student.enrollments)
                })
            return {'success': True, 'data': progress_data}

        return {'success': False, 'error': '未知报表类型'}