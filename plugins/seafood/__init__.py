"""
海鲜水产行业插件
提供海鲜产品管理、订单处理、库存管理、供应商管理等功能
"""
from .models import *
from .service import SeafoodService
from .api import seafood_bp

PLUGIN_NAME = 'seafood'

SEAFOOD_COMMANDS = [
    {
        'command_name': 'product_query',
        'keywords': ['海鲜', '鱼', '虾', '蟹', '水产', '今天有什么'],
        'patterns': [
            r'(?:海鲜|鱼|虾|蟹|水产).*(?:查询|有什么|今天)',
            r'(?:今天|今日).*(?:什么|哪些).*(?:海鲜|鱼|虾)',
            r'(?:什么).*(?:新鲜|时令)'
        ],
        'response_template': 'seafood:product_query',
        'description': '海鲜产品查询和今日行情',
        'examples': ['今天有什么海鲜', '水产查询', '什么鱼新鲜'],
        'param_schema': {},
        'is_active': 1
    },
    {
        'command_name': 'order_query',
        'keywords': ['订单', '发货', '配送', '冷链', '到哪了'],
        'patterns': [
            r'(?:订单|发货|配送|冷链).*(?:查询|状态|到哪)',
            r'(?:什么).*(?:时候|发货|配送)',
            r'(?:送到).*(?:哪|多久)'
        ],
        'response_template': 'seafood:order_query',
        'description': '海鲜订单查询和冷链配送跟踪',
        'examples': ['订单查询', '冷链到哪了', '什么时候发货'],
        'param_schema': {'order_no': '订单号'},
        'is_active': 1
    },
    {
        'command_name': 'inventory_query',
        'keywords': ['库存', '鲜货', '缺货', '到货', '有没有'],
        'patterns': [
            r'(?:库存|鲜货|缺货|到货).*(?:查询|多少|哪些)',
            r'(?:还有|有).*(?:多少|鲜货)',
            r'(?:什么).*(?:缺|不够|没了)'
        ],
        'response_template': 'seafood:inventory_query',
        'description': '海鲜鲜货库存查询',
        'examples': ['库存查询', '鲜货还有多少', '哪些缺货'],
        'param_schema': {},
        'is_active': 1
    },
    {
        'command_name': 'supplier_query',
        'keywords': ['供应商', '产地', '进货', '报价', '哪来的'],
        'patterns': [
            r'(?:供应商|产地).*(?:查询|哪里|信息)',
            r'(?:进货|采购).*(?:哪里|价格)',
            r'(?:哪|谁).*(?:供|产).*(?:海鲜|鱼|虾)'
        ],
        'response_template': 'seafood:supplier_query',
        'description': '海鲜供应商和产地查询',
        'examples': ['供应商查询', '产地哪里', '进货报价'],
        'param_schema': {'text': '海鲜/产地名称'},
        'is_active': 1
    },
    {
        'command_name': 'fresh_check',
        'keywords': ['新鲜', '保鲜', '保质期', '冷冻', '检查'],
        'patterns': [
            r'(?:新鲜|保鲜|保质期|冷冻).*(?:检查|查询|多久)',
            r'(?:什么).*(?:时候|过期|不新鲜)',
            r'(?:还能).*(?:放|冻|保存)'
        ],
        'response_template': 'seafood:fresh_check',
        'description': '海鲜新鲜度检查和保质期预警',
        'examples': ['新鲜度检查', '保质期多久', '什么时候过期'],
        'param_schema': {},
        'is_active': 1
    }
]


def register_plugin(app):
    app.register_blueprint(seafood_bp)
    _register_commands()


def _register_commands():
    try:
        from services.command_config_service import command_config_service
        result = command_config_service.register_plugin_commands(PLUGIN_NAME, SEAFOOD_COMMANDS)
        if result['success']:
            print(f"✓ 海鲜水产插件指令注册成功: 创建{result['created_count']}条, 更新{result['updated_count']}条")
        else:
            print(f"✗ 海鲜水产插件指令注册失败: {result['error']}")
    except ImportError:
        print("! 全局指令服务未加载，跳过指令注册")
    except Exception as e:
        print(f"✗ 海鲜水产插件指令注册异常: {str(e)}")


def unregister_plugin(app):
    try:
        from services.command_config_service import command_config_service
        result = command_config_service.unregister_plugin_commands(PLUGIN_NAME)
        if result['success']:
            print(f"✓ 海鲜水产插件指令已卸载: 禁用{result['deleted_count']}条")
    except Exception as e:
        print(f"✗ 海鲜水产插件指令卸载异常: {str(e)}")