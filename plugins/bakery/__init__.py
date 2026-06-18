"""
烘焙甜品行业插件
提供烘焙产品管理、订单处理、原料库存、会员管理、蛋糕定制等功能
"""
from .models import *
from .service import BakeryService
from .api import bakery_bp

PLUGIN_NAME = 'bakery'

BAKERY_COMMANDS = [
    {
        'command_name': 'order_query',
        'keywords': ['订单', '蛋糕', '面包', '定制', '订了', '什么时候好'],
        'patterns': [
            r'(?:订单|蛋糕|面包).*(?:查询|状态|好了吗)',
            r'(?:定制|订购).*(?:蛋糕|面包|甜品)',
            r'(?:我的|我).*(?:订了|定制)'
        ],
        'response_template': 'bakery:order_query',
        'description': '查询蛋糕/面包订单状态',
        'examples': ['我的蛋糕好了吗', '订单查询', '定制进度'],
        'param_schema': {'order_no': '订单号', 'phone': '手机号'},
        'is_active': 1
    },
    {
        'command_name': 'inventory_query',
        'keywords': ['原料', '库存', '面粉', '奶油', '缺货', '黄油'],
        'patterns': [
            r'(?:原料|库存|面粉|奶油|黄油).*(?:多少|查询|还有)',
            r'(?:面粉|奶油|黄油|酵母).*(?:还有|够)',
            r'(?:缺|不够).*(?:什么|哪些)'
        ],
        'response_template': 'bakery:inventory_query',
        'description': '原料库存查询与预警',
        'examples': ['面粉还有多少', '原料库存', '奶油够吗'],
        'param_schema': {},
        'is_active': 1
    },
    {
        'command_name': 'member_query',
        'keywords': ['会员', '积分', '余额', '折扣', '储值', '卡'],
        'patterns': [
            r'(?:会员|积分|余额|储值|卡).*(?:多少|查询|还有)',
            r'(?:查询|看看).*(?:会员|积分)',
            r'(?:折扣).*(?:多少)'
        ],
        'response_template': 'bakery:member_query',
        'description': '会员信息查询，积分和余额',
        'examples': ['会员积分多少', '查余额', '我的会员卡'],
        'param_schema': {'phone': '手机号'},
        'is_active': 1
    },
    {
        'command_name': 'product_query',
        'keywords': ['新品', '蛋糕', '面包', '甜点', '今天有什么', '出炉'],
        'patterns': [
            r'(?:新品|蛋糕|面包|甜点).*(?:有什么|推荐|出炉)',
            r'(?:今天|今日).*(?:有什么|出炉|新品)',
            r'(?:新鲜).*(?:出炉|什么)'
        ],
        'response_template': 'bakery:product_query',
        'description': '查询今日产品和新鲜出炉',
        'examples': ['今天有什么蛋糕', '新品推荐', '新鲜出炉'],
        'param_schema': {},
        'is_active': 1
    },
    {
        'command_name': 'custom_cake',
        'keywords': ['定制', '生日蛋糕', '纪念日', '尺寸', '祝福语', '图案'],
        'patterns': [
            r'(?:定制|定做).*(?:蛋糕)',
            r'(?:生日|纪念日|婚礼).*(?:蛋糕)',
            r'(?:蛋糕).*(?:尺寸|图案|祝福)'
        ],
        'response_template': 'bakery:custom_cake',
        'description': '定制生日蛋糕/纪念蛋糕',
        'examples': ['定制生日蛋糕 8寸', '纪念日蛋糕', '定制 水果蛋糕 10寸'],
        'param_schema': {'text': '定制需求描述', 'quantity': '尺寸/数量'},
        'is_active': 1
    }
]


def register_plugin(app):
    app.register_blueprint(bakery_bp)
    _register_commands()


def _register_commands():
    try:
        from services.command_config_service import command_config_service
        result = command_config_service.register_plugin_commands(PLUGIN_NAME, BAKERY_COMMANDS)
        if result['success']:
            print(f"✓ 烘焙甜品插件指令注册成功: 创建{result['created_count']}条, 更新{result['updated_count']}条")
        else:
            print(f"✗ 烘焙甜品插件指令注册失败: {result['error']}")
    except ImportError:
        print("! 全局指令服务未加载，跳过指令注册")
    except Exception as e:
        print(f"✗ 烘焙甜品插件指令注册异常: {str(e)}")


def unregister_plugin(app):
    try:
        from services.command_config_service import command_config_service
        result = command_config_service.unregister_plugin_commands(PLUGIN_NAME)
        if result['success']:
            print(f"✓ 烘焙甜品插件指令已卸载: 禁用{result['deleted_count']}条")
    except Exception as e:
        print(f"✗ 烘焙甜品插件指令卸载异常: {str(e)}")