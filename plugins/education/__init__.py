"""
教育培训行业插件
提供课程管理、学员管理、课时统计、考勤管理、招生管理等功能
"""
from .models import *
from .service import EducationService
from .api import education_bp

PLUGIN_NAME = 'education'

EDUCATION_COMMANDS = [
    {
        'command_name': 'course_query',
        'keywords': ['课程', '上课', '课表', '课程表', '今天上什么'],
        'patterns': [
            r'(?:课程|课表|课程表).*(?:查询|有什么|安排)',
            r'(?:今天|明天).*(?:上课|课程|什么课)',
            r'(?:什么|哪些).*(?:课|课程)'
        ],
        'response_template': 'education:course_query',
        'description': '查询课程安排和课表',
        'examples': ['今天上什么课', '课程表', '明天有课吗'],
        'param_schema': {'date': '日期'},
        'is_active': 1
    },
    {
        'command_name': 'student_query',
        'keywords': ['学员', '学生', '报名', '出勤', '成绩', '学习进度'],
        'patterns': [
            r'(?:学员|学生).*(?:查询|名单|信息)',
            r'(?:出勤|成绩|学习).*(?:多少|怎么样|查询)',
            r'(?:找|查).*(?:学生|学员)'
        ],
        'response_template': 'education:student_query',
        'description': '学员信息查询和出勤统计',
        'examples': ['学员查询 张三', '出勤统计', '学生名单'],
        'param_schema': {'name': '学员姓名', 'text': '查询内容'},
        'is_active': 1
    },
    {
        'command_name': 'attendance_check',
        'keywords': ['打卡', '签到', '考勤', '请假', '缺勤'],
        'patterns': [
            r'(?:打卡|签到).*(?:成功|记录|查询)',
            r'(?:请假|缺勤|迟到).*(?:记录|申请)',
            r'(?:今天|今日).*(?:打卡|签到)'
        ],
        'response_template': 'education:attendance_check',
        'description': '考勤打卡和请假管理',
        'examples': ['打卡', '请假', '考勤记录'],
        'param_schema': {'name': '学员姓名', 'text': '考勤备注'},
        'is_active': 1
    },
    {
        'command_name': 'schedule_query',
        'keywords': ['排班', '上课时间', '老师', '教室', '调课'],
        'patterns': [
            r'(?:排班|上课时间|调课).*(?:查询|安排)',
            r'(?:老师|教室).*(?:安排|在哪|谁)',
            r'(?:什么).*(?:时间|老师|教室)'
        ],
        'response_template': 'education:schedule_query',
        'description': '排班查询和调课管理',
        'examples': ['排班查询', '老师是谁', '什么时间上课'],
        'param_schema': {'text': '排班信息', 'date': '日期'},
        'is_active': 1
    },
    {
        'command_name': 'enrollment_query',
        'keywords': ['招生', '报名', '咨询', '学费', '试听', '优惠'],
        'patterns': [
            r'(?:招生|报名|咨询|试听).*(?:什么|多少钱|优惠)',
            r'(?:学费|费用).*(?:多少|查询)',
            r'(?:想|要).*(?:报名|试听)'
        ],
        'response_template': 'education:enrollment_query',
        'description': '招生咨询和学费查询',
        'examples': ['学费多少', '报名咨询', '试听课程'],
        'param_schema': {'text': '咨询内容'},
        'is_active': 1
    }
]


def register_plugin(app):
    app.register_blueprint(education_bp)
    _register_commands()


def _register_commands():
    try:
        from services.command_config_service import command_config_service
        result = command_config_service.register_plugin_commands(PLUGIN_NAME, EDUCATION_COMMANDS)
        if result['success']:
            print(f"✓ 教育培训插件指令注册成功: 创建{result['created_count']}条, 更新{result['updated_count']}条")
        else:
            print(f"✗ 教育培训插件指令注册失败: {result['error']}")
    except ImportError:
        print("! 全局指令服务未加载，跳过指令注册")
    except Exception as e:
        print(f"✗ 教育培训插件指令注册异常: {str(e)}")


def unregister_plugin(app):
    try:
        from services.command_config_service import command_config_service
        result = command_config_service.unregister_plugin_commands(PLUGIN_NAME)
        if result['success']:
            print(f"✓ 教育培训插件指令已卸载: 禁用{result['deleted_count']}条")
    except Exception as e:
        print(f"✗ 教育培训插件指令卸载异常: {str(e)}")