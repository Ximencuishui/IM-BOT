"""
火锅食材行业插件
提供食材分类管理、锅底识别、订单处理、配送管理等功能
"""
from .models import *
from .service import HotpotService
from .api import hotpot_bp

PLUGIN_NAME = 'hotpot'

HOTPOT_COMMANDS = [
    {
        'command_name': 'food_query',
        'keywords': ['食材', '菜品', '毛肚', '肥牛', '虾滑', '有什么菜'],
        'patterns': [
            r'(?:食材|菜品|菜).*(?:查询|有什么|还有)',
            r'(?:毛肚|肥牛|虾滑|牛百叶).*(?:还有|多少)',
            r'(?:今天|今日).*(?:什么菜|有哪些)'
        ],
        'response_template': 'hotpot:food_query',
        'description': '查询火锅食材库存和推荐',
        'examples': ['今天有什么食材', '毛肚还有吗', '菜品查询'],
        'param_schema': {},
        'is_active': 1
    },
    {
        'command_name': 'soup_base',
        'keywords': ['锅底', '汤', '麻辣', '番茄', '菌汤', '清汤'],
        'patterns': [
            r'(?:锅底|汤底).*(?:有什么|推荐|选择)',
            r'(?:麻辣|番茄|菌汤|清汤|鸳鸯).*(?:锅底|汤)',
            r'(?:推荐).*(?:锅底|汤底)'
        ],
        'response_template': 'hotpot:soup_base',
        'description': '锅底选择和推荐',
        'examples': ['推荐锅底', '麻辣锅底', '有什么汤底'],
        'param_schema': {'text': '锅底偏好'},
        'is_active': 1
    },
    {
        'command_name': 'order_query',
        'keywords': ['订单', '点单', '下单', '上了吗', '还没上'],
        'patterns': [
            r'(?:订单|点单|下单).*(?:查询|状态|好了吗)',
            r'(?:菜).*(?:上了|上了吗|还没)',
            r'(?:等).*(?:菜|很久)'
        ],
        'response_template': 'hotpot:order_query',
        'description': '查询火锅订单状态和上菜进度',
        'examples': ['订单查询', '我的菜还没上', '点单状态'],
        'param_schema': {'order_no': '订单号'},
        'is_active': 1
    },
    {
        'command_name': 'delivery_query',
        'keywords': ['配送', '外卖', '送到哪', '多久到', '火锅外卖'],
        'patterns': [
            r'(?:配送|外卖).*(?:状态|多久到|送到哪)',
            r'(?:火锅).*(?:外卖|配送)',
            r'(?:送).*(?:到哪|多久)'
        ],
        'response_template': 'hotpot:delivery_query',
        'description': '火锅外卖配送查询',
        'examples': ['外卖到哪了', '配送多久到', '火锅外卖进度'],
        'param_schema': {'order_no': '订单号'},
        'is_active': 1
    },
    {
        'command_name': 'inventory_warning',
        'keywords': ['库存', '缺货', '补货', '冻品', '鲜货'],
        'patterns': [
            r'(?:库存|缺货|冻品|鲜货).*(?:查询|预警|还有)',
            r'(?:什么|哪些).*(?:缺|不够|需要补)',
            r'(?:冻品|鲜货).*(?:还有|多久)'
        ],
        'response_template': 'hotpot:inventory_warning',
        'description': '火锅食材库存预警和补货提醒',
        'examples': ['库存查询', '哪些缺货了', '需要补货'],
        'param_schema': {},
        'is_active': 1
    }
]


def register_plugin(app):
    app.register_blueprint(hotpot_bp)
    _register_commands()


def _register_commands():
    try:
        from services.command_config_service import command_config_service
        result = command_config_service.register_plugin_commands(PLUGIN_NAME, HOTPOT_COMMANDS)
        if result['success']:
            print(f"✓ 火锅食材插件指令注册成功: 创建{result['created_count']}条, 更新{result['updated_count']}条")
        else:
            print(f"✗ 火锅食材插件指令注册失败: {result['error']}")
    except ImportError:
        print("! 全局指令服务未加载，跳过指令注册")
    except Exception as e:
        print(f"✗ 火锅食材插件指令注册异常: {str(e)}")


def unregister_plugin(app):
    try:
        from services.command_config_service import command_config_service
        result = command_config_service.unregister_plugin_commands(PLUGIN_NAME)
        if result['success']:
            print(f"✓ 火锅食材插件指令已卸载: 禁用{result['deleted_count']}条")
    except Exception as e:
        print(f"✗ 火锅食材插件指令卸载异常: {str(e)}")