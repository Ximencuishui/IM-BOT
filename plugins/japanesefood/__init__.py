"""
日式料理行业插件
提供日料产品管理、订单处理、食材库存、会员管理等功能
"""
from .models import *
from .service import JapaneseFoodService
from .api import japanesefood_bp

PLUGIN_NAME = 'japanesefood'

JAPANESEFOOD_COMMANDS = [
    {
        'command_name': 'menu_query',
        'keywords': ['菜单', '寿司', '刺身', '料理', '今日什么', '推荐什么'],
        'patterns': [
            r'(?:菜单|料理).*(?:查询|有什么|推荐)',
            r'(?:今天|今日).*(?:推荐|什么|菜单)',
            r'(?:什么).*(?:好吃|推荐|特别)'
        ],
        'response_template': 'japanesefood:menu_query',
        'description': '查询日料菜单和今日推荐',
        'examples': ['今日推荐', '菜单', '有什么好吃的'],
        'param_schema': {},
        'is_active': 1
    },
    {
        'command_name': 'order_query',
        'keywords': ['订单', '下单', '上菜', '等待', '还没来'],
        'patterns': [
            r'(?:订单|下单).*(?:查询|状态|好了)',
            r'(?:上菜|菜).*(?:还没|什么时候|多久)',
            r'(?:等).*(?:多久|半天|很久)'
        ],
        'response_template': 'japanesefood:order_query',
        'description': '查询日料订单和上菜状态',
        'examples': ['订单查询', '菜什么时候上', '等很久了'],
        'param_schema': {'order_no': '订单号'},
        'is_active': 1
    },
    {
        'command_name': 'inventory_query',
        'keywords': ['食材', '生鲜', '库存', '缺货', '鱼', '新鲜'],
        'patterns': [
            r'(?:食材|生鲜|鱼).*(?:查询|还有|新鲜)',
            r'(?:库存|缺货).*(?:多少|哪些)',
            r'(?:新鲜).*(?:程度|检查)'
        ],
        'response_template': 'japanesefood:inventory_query',
        'description': '日料食材库存和新鲜度查询',
        'examples': ['食材库存', '今天什么鱼新鲜', '缺货查询'],
        'param_schema': {},
        'is_active': 1
    },
    {
        'command_name': 'member_query',
        'keywords': ['会员', '积分', '优惠', '折扣', '储值'],
        'patterns': [
            r'(?:会员|积分|储值).*(?:查询|多少|还有)',
            r'(?:优惠|折扣).*(?:多少|有什么)',
            r'(?:查|看).*(?:积分|会员)'
        ],
        'response_template': 'japanesefood:member_query',
        'description': '会员积分和储值查询',
        'examples': ['会员查询', '积分多少', '有什么优惠'],
        'param_schema': {'phone': '手机号'},
        'is_active': 1
    },
    {
        'command_name': 'booking',
        'keywords': ['预约', '订位', '包间', '时间', '几位'],
        'patterns': [
            r'(?:预约|订位|预订).*(?:包间|时间|位置)',
            r'(?:明天|今天|这周).*(?:订|预约)',
            r'(\d+)\s*(?:位|人).*(?:订|预约)'
        ],
        'response_template': 'japanesefood:booking',
        'description': '预约订位，支持包间和时间选择',
        'examples': ['预订明天6位', '订包间', '预约 晚上7点'],
        'param_schema': {'date': '日期时间', 'quantity': '人数', 'text': '座位偏好'},
        'is_active': 1
    }
]


def register_plugin(app):
    app.register_blueprint(japanesefood_bp)
    _register_commands()


def _register_commands():
    try:
        from services.command_config_service import command_config_service
        result = command_config_service.register_plugin_commands(PLUGIN_NAME, JAPANESEFOOD_COMMANDS)
        if result['success']:
            print(f"✓ 日式料理插件指令注册成功: 创建{result['created_count']}条, 更新{result['updated_count']}条")
        else:
            print(f"✗ 日式料理插件指令注册失败: {result['error']}")
    except ImportError:
        print("! 全局指令服务未加载，跳过指令注册")
    except Exception as e:
        print(f"✗ 日式料理插件指令注册异常: {str(e)}")


def unregister_plugin(app):
    try:
        from services.command_config_service import command_config_service
        result = command_config_service.unregister_plugin_commands(PLUGIN_NAME)
        if result['success']:
            print(f"✓ 日式料理插件指令已卸载: 禁用{result['deleted_count']}条")
    except Exception as e:
        print(f"✗ 日式料理插件指令卸载异常: {str(e)}")