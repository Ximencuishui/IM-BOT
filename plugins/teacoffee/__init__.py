"""
茶饮咖啡行业插件
提供饮品管理、订单处理、原料库存、会员管理等功能
"""
from .models import *
from .service import TeaCoffeeService
from .api import teacoffee_bp

PLUGIN_NAME = 'teacoffee'

TEACOFFEE_COMMANDS = [
    {
        'command_name': 'menu_query',
        'keywords': ['菜单', '奶茶', '咖啡', '饮品', '有什么', '推荐'],
        'patterns': [
            r'(?:菜单|奶茶|咖啡|饮品).*(?:查询|有什么|推荐)',
            r'(?:今天|今日).*(?:推荐|新品|特价)',
            r'(?:什么).*(?:好喝|推荐|新品)'
        ],
        'response_template': 'teacoffee:menu_query',
        'description': '查询茶饮菜单和今日推荐',
        'examples': ['今天推荐什么', '菜单', '有什么新品'],
        'param_schema': {},
        'is_active': 1
    },
    {
        'command_name': 'order_query',
        'keywords': ['订单', '下单', '取餐', '等待', '好了吗', '取餐号'],
        'patterns': [
            r'(?:订单|下单).*(?:查询|状态|好了)',
            r'(?:取餐).*(?:号|码|好了)',
            r'(\d+)\s*号\s*(?:取餐|订单)'
        ],
        'response_template': 'teacoffee:order_query',
        'description': '查询茶饮订单和取餐状态',
        'examples': ['订单查询', '取餐号123', '做好了吗'],
        'param_schema': {'order_no': '订单号/取餐号'},
        'is_active': 1
    },
    {
        'command_name': 'inventory_query',
        'keywords': ['原料', '茶叶', '牛奶', '库存', '缺货', '不够了'],
        'patterns': [
            r'(?:原料|茶叶|牛奶|库存).*(?:查询|还有|多少)',
            r'(?:什么).*(?:缺|不够|需要补)',
            r'(?:茶叶|牛奶|糖浆).*(?:还有|多少)'
        ],
        'response_template': 'teacoffee:inventory_query',
        'description': '茶饮原料库存查询',
        'examples': ['原料库存', '牛奶还有多少', '茶叶够吗'],
        'param_schema': {},
        'is_active': 1
    },
    {
        'command_name': 'member_query',
        'keywords': ['会员', '积分', '优惠', '折扣', '储值', '余额'],
        'patterns': [
            r'(?:会员|积分|储值|余额).*(?:查询|多少|还有)',
            r'(?:优惠|折扣).*(?:多少|有什么)',
            r'(?:看看|查).*(?:积分|余额)'
        ],
        'response_template': 'teacoffee:member_query',
        'description': '会员积分和储值查询',
        'examples': ['会员查询', '积分多少', '余额查询'],
        'param_schema': {'phone': '手机号'},
        'is_active': 1
    },
    {
        'command_name': 'custom_order',
        'keywords': ['定制', '少糖', '去冰', '加料', '调整', '口味'],
        'patterns': [
            r'(?:定制|少糖|去冰|加料|调整).*(?:下单|饮品|口味)',
            r'(?:甜度|冰量|温度).*(?:调整|多少)',
            r'(?:口味|口感).*(?:调整|定制)'
        ],
        'response_template': 'teacoffee:custom_order',
        'description': '定制饮品：甜度、冰量、加料',
        'examples': ['少糖去冰', '加珍珠', '半糖奶茶'],
        'param_schema': {'text': '定制需求描述'},
        'is_active': 1
    }
]


def register_plugin(app):
    app.register_blueprint(teacoffee_bp)
    _register_commands()


def _register_commands():
    try:
        from services.command_config_service import command_config_service
        result = command_config_service.register_plugin_commands(PLUGIN_NAME, TEACOFFEE_COMMANDS)
        if result['success']:
            print(f"✓ 茶饮咖啡插件指令注册成功: 创建{result['created_count']}条, 更新{result['updated_count']}条")
        else:
            print(f"✗ 茶饮咖啡插件指令注册失败: {result['error']}")
    except ImportError:
        print("! 全局指令服务未加载，跳过指令注册")
    except Exception as e:
        print(f"✗ 茶饮咖啡插件指令注册异常: {str(e)}")


def unregister_plugin(app):
    try:
        from services.command_config_service import command_config_service
        result = command_config_service.unregister_plugin_commands(PLUGIN_NAME)
        if result['success']:
            print(f"✓ 茶饮咖啡插件指令已卸载: 禁用{result['deleted_count']}条")
    except Exception as e:
        print(f"✗ 茶饮咖啡插件指令卸载异常: {str(e)}")