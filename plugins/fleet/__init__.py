"""
车队管理行业插件
提供车辆管理、司机管理、调度安排、油耗统计、维修保养等功能
"""
from .models import *
from .service import FleetService
from .api import fleet_bp

PLUGIN_NAME = 'fleet'

FLEET_COMMANDS = [
    {
        'command_name': 'vehicle_query',
        'keywords': ['车辆', '车', '位置', '状态', '在哪', '跑哪了'],
        'patterns': [
            r'(?:车辆|车).*(?:查询|状态|位置|在哪|跑哪)',
            r'(?:车牌|车号).*(?:多少|查询)',
            r'(?:哪个|哪辆).*(?:车|车辆)'
        ],
        'response_template': 'fleet:vehicle_query',
        'description': '车辆位置和状态查询',
        'examples': ['车辆查询 京A12345', '车在哪', '车辆状态'],
        'param_schema': {'text': '车牌号'},
        'is_active': 1
    },
    {
        'command_name': 'driver_query',
        'keywords': ['司机', '驾驶员', '排班', '出勤', '谁开车'],
        'patterns': [
            r'(?:司机|驾驶员).*(?:查询|排班|谁|出勤)',
            r'(?:谁).*(?:开车|排班|出车)',
            r'(?:司机|驾驶员).*(?:今天|明天)'
        ],
        'response_template': 'fleet:driver_query',
        'description': '司机排班和出勤查询',
        'examples': ['司机排班', '今天谁开车', '司机查询'],
        'param_schema': {'name': '司机姓名', 'date': '日期'},
        'is_active': 1
    },
    {
        'command_name': 'dispatch',
        'keywords': ['调度', '派车', '任务', '路线', '安排'],
        'patterns': [
            r'(?:调度|派车|安排).*(?:任务|路线|车辆)',
            r'(?:需要|要).*(?:派|安排).*(?:车|车辆)',
            r'(?:任务).*(?:分配|安排)'
        ],
        'response_template': 'fleet:dispatch',
        'description': '车辆调度和任务分配',
        'examples': ['派车 明天去城东', '调度 运送钢材', '安排车辆'],
        'param_schema': {'text': '任务描述', 'date': '时间', 'site_name': '目的地'},
        'is_active': 1
    },
    {
        'command_name': 'fuel_query',
        'keywords': ['油耗', '加油', '油费', '统计', '用了多少油'],
        'patterns': [
            r'(?:油耗|加油|油费).*(?:多少|统计|查询)',
            r'(?:用了|加了).*(?:多少|油)',
            r'(?:油).*(?:多少|还剩)'
        ],
        'response_template': 'fleet:fuel_query',
        'description': '油耗统计和油费管理',
        'examples': ['油耗统计', '今天用了多少油', '加油记录'],
        'param_schema': {'text': '车牌号', 'date': '日期'},
        'is_active': 1
    },
    {
        'command_name': 'maintenance',
        'keywords': ['保养', '维修', '故障', '年检', '检修'],
        'patterns': [
            r'(?:保养|维修|故障|年检|检修).*(?:记录|安排|什么|预约)',
            r'(?:车).*(?:坏了|故障|需要修)',
            r'(?:什么).*(?:时候|保养|年检)'
        ],
        'response_template': 'fleet:maintenance',
        'description': '车辆维修保养管理',
        'examples': ['保养记录', '年检到期', '安排维修'],
        'param_schema': {'text': '车牌号', 'date': '时间'},
        'is_active': 1
    }
]


def register_plugin(app):
    app.register_blueprint(fleet_bp)
    _register_commands()


def _register_commands():
    try:
        from services.command_config_service import command_config_service
        result = command_config_service.register_plugin_commands(PLUGIN_NAME, FLEET_COMMANDS)
        if result['success']:
            print(f"✓ 车队管理插件指令注册成功: 创建{result['created_count']}条, 更新{result['updated_count']}条")
        else:
            print(f"✗ 车队管理插件指令注册失败: {result['error']}")
    except ImportError:
        print("! 全局指令服务未加载，跳过指令注册")
    except Exception as e:
        print(f"✗ 车队管理插件指令注册异常: {str(e)}")


def unregister_plugin(app):
    try:
        from services.command_config_service import command_config_service
        result = command_config_service.unregister_plugin_commands(PLUGIN_NAME)
        if result['success']:
            print(f"✓ 车队管理插件指令已卸载: 禁用{result['deleted_count']}条")
    except Exception as e:
        print(f"✗ 车队管理插件指令卸载异常: {str(e)}")