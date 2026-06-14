"""
教育培训行业插件数据模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from database.db_config import Base


class EducationCourse(Base):
    """课程表"""
    __tablename__ = 't_education_course'

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_name = Column(String(100), nullable=False, index=True)
    category = Column(String(50), index=True)
    price = Column(Float, default=0.0)
    duration = Column(Integer, comment='课时数')
    description = Column(String(500))
    cover_image = Column(String(500))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    enrollments = relationship('EducationEnrollment', back_populates='course')
    progress_records = relationship('EducationProgress', back_populates='course')
    assignments = relationship('EducationAssignment', back_populates='course')

    def to_dict(self):
        return {
            'id': self.id,
            'course_name': self.course_name,
            'category': self.category,
            'price': float(self.price) if self.price else 0.0,
            'duration': self.duration,
            'description': self.description,
            'cover_image': self.cover_image,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class EducationStudent(Base):
    """学员表"""
    __tablename__ = 't_education_student'

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, index=True)
    wechat_id = Column(String(100))
    level = Column(String(20), default='beginner')
    avatar = Column(String(500))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    enrollments = relationship('EducationEnrollment', back_populates='student')
    progress_records = relationship('EducationProgress', back_populates='student')
    assignments = relationship('EducationAssignment', back_populates='student')

    def to_dict(self):
        return {
            'id': self.id,
            'student_name': self.student_name,
            'phone': self.phone,
            'wechat_id': self.wechat_id,
            'level': self.level,
            'avatar': self.avatar,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class EducationTeacher(Base):
    """教师表"""
    __tablename__ = 't_education_teacher'

    id = Column(Integer, primary_key=True, autoincrement=True)
    teacher_name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, index=True)
    specialty = Column(String(100))
    experience = Column(Integer, comment='教学经验(年)')
    bio = Column(String(500))
    avatar = Column(String(500))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'teacher_name': self.teacher_name,
            'phone': self.phone,
            'specialty': self.specialty,
            'experience': self.experience,
            'bio': self.bio,
            'avatar': self.avatar,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class EducationEnrollment(Base):
    """报名表"""
    __tablename__ = 't_education_enrollment'

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey('t_education_student.id'), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey('t_education_course.id'), nullable=False, index=True)
    enroll_date = Column(DateTime, default=datetime.now)
    status = Column(String(20), default='active')
    payment_amount = Column(Float, default=0.0)

    student = relationship('EducationStudent', back_populates='enrollments')
    course = relationship('EducationCourse', back_populates='enrollments')

    __table_args__ = (Index('idx_student_course', 'student_id', 'course_id', unique=True),)

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'course_id': self.course_id,
            'enroll_date': self.enroll_date.isoformat() if self.enroll_date else None,
            'status': self.status,
            'payment_amount': float(self.payment_amount) if self.payment_amount else 0.0
        }


class EducationProgress(Base):
    """学习进度表"""
    __tablename__ = 't_education_progress'

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey('t_education_student.id'), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey('t_education_course.id'), nullable=False, index=True)
    progress_percent = Column(Float, default=0.0)
    last_learned_at = Column(DateTime)
    completed_lessons = Column(Integer, default=0)

    student = relationship('EducationStudent', back_populates='progress_records')
    course = relationship('EducationCourse', back_populates='progress_records')

    __table_args__ = (Index('idx_progress_student_course', 'student_id', 'course_id', unique=True),)

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'course_id': self.course_id,
            'progress_percent': float(self.progress_percent) if self.progress_percent else 0.0,
            'last_learned_at': self.last_learned_at.isoformat() if self.last_learned_at else None,
            'completed_lessons': self.completed_lessons
        }


class EducationAssignment(Base):
    """作业表"""
    __tablename__ = 't_education_assignment'

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey('t_education_student.id'), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey('t_education_course.id'), nullable=False, index=True)
    content = Column(Text)
    submitted_at = Column(DateTime)
    score = Column(Float, comment='分数')
    feedback = Column(Text, comment='评语')

    student = relationship('EducationStudent', back_populates='assignments')
    course = relationship('EducationCourse', back_populates='assignments')

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'course_id': self.course_id,
            'content': self.content,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'score': float(self.score) if self.score else None,
            'feedback': self.feedback
        }


class EducationAttendance(Base):
    """考勤表"""
    __tablename__ = 't_education_attendance'

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey('t_education_student.id'), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey('t_education_course.id'), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)
    status = Column(String(20), default='attended')

    __table_args__ = (Index('idx_attendance_date', 'date'),)

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'course_id': self.course_id,
            'date': self.date.isoformat() if self.date else None,
            'status': self.status
        }