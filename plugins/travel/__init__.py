"""
旅游服务行业插件
提供线路管理、订单处理、客户管理、行程安排等功能
"""
from .models import *
from .service import TravelService
from .api import travel_bp

PLUGIN_NAME = 'travel'

TRAVEL_COMMANDS = [
    {
        'command_name': 'route_query',
        'keywords': ['线路', '旅游', '行程', '景点', '去哪里', '有什么'],
        'patterns': [
            r'(?:线路|旅游|行程).*(?:查询|有什么|推荐)',
            r'(?:哪里|去哪).*(?:好玩|旅游|玩)',
            r'(?:什么|有).*(?:线路|行程|景点)'
        ],
        'response_template': 'travel:route_query',
        'description': '旅游线路查询和推荐',
        'examples': ['有什么线路', '去哪里玩', '推荐行程'],
        'param_schema': {},
        'is_active': 1
    },
    {
        'command_name': 'order_query',
        'keywords': ['订单', '预订', '行程', '时间', '确认'],
        'patterns': [
            r'(?:订单|预订).*(?:查询|确认|状态)',
            r'(?:行程|时间).*(?:确认|改|调整)',
            r'(?:我).*(?:订|预订).*(?:什么|哪个)'
        ],
        'response_template': 'travel:order_query',
        'description': '旅游订单查询和行程确认',
        'examples': ['订单查询', '行程确认', '我的预订'],
        'param_schema': {'order_no': '订单号'},
        'is_active': 1
    },
    {
        'command_name': 'customer_query',
        'keywords': ['客户', '游客', '报名', '人数', '信息'],
        'patterns': [
            r'(?:客户|游客).*(?:查询|报名|信息)',
            r'(?:报名|参加).*(?:多少人|谁)',
            r'(?:谁|哪些).*(?:报名|参加)'
        ],
        'response_template': 'travel:customer_query',
        'description': '游客信息和报名管理',
        'examples': ['游客查询', '报名人数', '谁参加了'],
        'param_schema': {'name': '游客姓名'},
        'is_active': 1
    },
    {
        'command_name': 'schedule_query',
        'keywords': ['安排', '行程', '住宿', '交通', '酒店'],
        'patterns': [
            r'(?:安排|行程|住宿|交通|酒店).*(?:查询|什么|怎么)',
            r'(?:住|睡).*(?:哪里|什么)',
            r'(?:交通|出行).*(?:什么|怎么)'
        ],
        'response_template': 'travel:schedule_query',
        'description': '行程安排查询：住宿、交通、景点',
        'examples': ['行程安排', '住什么酒店', '交通怎么解决'],
        'param_schema': {'text': '行程/团编号'},
        'is_active': 1
    },
    {
        'command_name': 'price_query',
        'keywords': ['价格', '多少钱', '报价', '优惠', '团价'],
        'patterns': [
            r'(?:价格|多少钱|报价|团价).*(?:查询|多少)',
            r'(?:这个|那个).*(?:多少|报价)',
            r'(\d+)\s*(?:元|块)'
        ],
        'response_template': 'travel:price_query',
        'description': '旅游线路价格查询',
        'examples': ['多少钱', '报价查询', '优惠活动'],
        'param_schema': {'text': '线路名称'},
        'is_active': 1
    }
]


def register_plugin(app):
    app.register_blueprint(travel_bp)
    _register_commands()


def _register_commands():
    try:
        from services.command_config_service import command_config_service
        result = command_config_service.register_plugin_commands(PLUGIN_NAME, TRAVEL_COMMANDS)
        if result['success']:
            print(f"✓ 旅游服务插件指令注册成功: 创建{result['created_count']}条, 更新{result['updated_count']}条")
        else:
            print(f"✗ 旅游服务插件指令注册失败: {result['error']}")
    except ImportError:
        print("! 全局指令服务未加载，跳过指令注册")
    except Exception as e:
        print(f"✗ 旅游服务插件指令注册异常: {str(e)}")


def unregister_plugin(app):
    try:
        from services.command_config_service import command_config_service
        result = command_config_service.unregister_plugin_commands(PLUGIN_NAME)
        if result['success']:
            print(f"✓ 旅游服务插件指令已卸载: 禁用{result['deleted_count']}条")
    except Exception as e:
        print(f"✗ 旅游服务插件指令卸载异常: {str(e)}")