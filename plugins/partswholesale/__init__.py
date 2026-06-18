"""
配件批发行业插件
提供配件管理、订单处理、库存管理、客户管理等功能
"""
from .models import *
from .service import PartsWholesaleService
from .api import partswholesale_bp

PLUGIN_NAME = 'partswholesale'

PARTSWHOLESALE_COMMANDS = [
    {
        'command_name': 'product_query',
        'keywords': ['配件', '批发', '型号', '规格', '找货'],
        'patterns': [
            r'(?:配件|批发|型号).*(?:查询|有什么|找)',
            r'(?:什么|哪个).*(?:型号|规格)',
            r'(?:找|查).*(?:配件|型号)'
        ],
        'response_template': 'partswholesale:product_query',
        'description': '配件批发产品查询',
        'examples': ['配件查询', '批发有什么', '找型号'],
        'param_schema': {'text': '产品名称/型号'},
        'is_active': 1
    },
    {
        'command_name': 'order_query',
        'keywords': ['订单', '发货', '物流', '单号', '批货'],
        'patterns': [
            r'(?:订单|发货|批货).*(?:查询|状态|到哪)',
            r'(?:物流|单号).*(?:查询|跟踪)',
            r'(?:什么).*(?:时候|发货)'
        ],
        'response_template': 'partswholesale:order_query',
        'description': '批发订单查询和物流跟踪',
        'examples': ['订单查询', '发货了吗', '物流到哪了'],
        'param_schema': {'order_no': '订单号'},
        'is_active': 1
    },
    {
        'command_name': 'inventory_query',
        'keywords': ['库存', '备货', '缺货', '到货', '有没有'],
        'patterns': [
            r'(?:库存|备货|缺货|到货).*(?:查询|多少|哪些)',
            r'(?:还有|有).*(?:多少|库存)',
            r'(?:什么).*(?:缺|不够)'
        ],
        'response_template': 'partswholesale:inventory_query',
        'description': '批发库存查询',
        'examples': ['库存查询', '有没有货', '哪些缺货'],
        'param_schema': {},
        'is_active': 1
    },
    {
        'command_name': 'customer_query',
        'keywords': ['客户', '拿货', '欠款', '对账', '结账'],
        'patterns': [
            r'(?:客户|拿货).*(?:查询|对账|欠款)',
            r'(?:欠款|欠).*(?:多少|哪些)',
            r'(?:对账|结账).*(?:多少|查询)'
        ],
        'response_template': 'partswholesale:customer_query',
        'description': '客户对账和欠款管理',
        'examples': ['客户对账', '谁欠款了', '对账查询'],
        'param_schema': {'name': '客户名称'},
        'is_active': 1
    },
    {
        'command_name': 'price_query',
        'keywords': ['价格', '批发价', '多少钱', '报价', '拿货价'],
        'patterns': [
            r'(?:价格|批发价|拿货价|报价).*(?:查询|多少)',
            r'(?:这个|那个).*(?:多少|价格)',
            r'(\d+)\s*(?:元|块)'
        ],
        'response_template': 'partswholesale:price_query',
        'description': '批发价格查询',
        'examples': ['多少钱 一箱', '批发价查询', '拿货价'],
        'param_schema': {'text': '产品名称', 'quantity': '数量'},
        'is_active': 1
    }
]


def register_plugin(app):
    app.register_blueprint(partswholesale_bp)
    _register_commands()


def _register_commands():
    try:
        from services.command_config_service import command_config_service
        result = command_config_service.register_plugin_commands(PLUGIN_NAME, PARTSWHOLESALE_COMMANDS)
        if result['success']:
            print(f"✓ 配件批发插件指令注册成功: 创建{result['created_count']}条, 更新{result['updated_count']}条")
        else:
            print(f"✗ 配件批发插件指令注册失败: {result['error']}")
    except ImportError:
        print("! 全局指令服务未加载，跳过指令注册")
    except Exception as e:
        print(f"✗ 配件批发插件指令注册异常: {str(e)}")


def unregister_plugin(app):
    try:
        from services.command_config_service import command_config_service
        result = command_config_service.unregister_plugin_commands(PLUGIN_NAME)
        if result['success']:
            print(f"✓ 配件批发插件指令已卸载: 禁用{result['deleted_count']}条")
    except Exception as e:
        print(f"✗ 配件批发插件指令卸载异常: {str(e)}")