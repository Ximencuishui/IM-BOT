"""
餐饮配送行业插件
提供商品管理、订单处理、桌台管理、员工管理、促销活动、销售报表等功能
"""
from .models import *
from .service import FoodDeliveryService
from .api import fooddelivery_bp

PLUGIN_NAME = 'fooddelivery'

FOODDELIVERY_COMMANDS = [
    {
        'command_name': 'order_query',
        'keywords': ['订单', '查订单', '我的订单', '订单状态', '订了什么', '点了什么'],
        'patterns': [
            r'(?:订单|点单).*(?:查询|状态|多少|到哪)',
            r'(?:我的|本人).*(?:订单|订了什么|点了什么)',
            r'(\d+)\s*号\s*(?:订单|单)'
        ],
        'response_template': 'fooddelivery:order_query',
        'description': '查询订单状态和详情，支持订单号查询',
        'examples': ['查订单', '我的订单到哪了', '订单号12345'],
        'param_schema': {'order_no': '订单号', 'phone': '手机号'},
        'is_active': 1
    },
    {
        'command_name': 'delivery_status',
        'keywords': ['配送', '骑手', '多久到', '送到了吗', '还有多远', '外卖'],
        'patterns': [
            r'(?:配送|骑手|外卖|外卖员).*(?:状态|位置|多久到|到哪)',
            r'(?:送到|到了).*(?:吗|没)',
            r'(?:还要|还有).*(?:多久|多远)'
        ],
        'response_template': 'fooddelivery:delivery_status',
        'description': '查询外卖配送实时进度',
        'examples': ['配送到哪了', '骑手还有多久到', '外卖送到了吗'],
        'param_schema': {'order_no': '订单号'},
        'is_active': 1
    },
    {
        'command_name': 'menu_query',
        'keywords': ['菜单', '菜品', '有什么', '今日特价', '推荐', '招牌'],
        'patterns': [
            r'(?:菜单|菜品|有什么|推荐|招牌).*(?:查询|看看|介绍)',
            r'(?:今日|今天|本周).*(?:特价|优惠|推荐|新品)',
            r'(?:什么).*(?:好吃|推荐)'
        ],
        'response_template': 'fooddelivery:menu_query',
        'description': '查询菜单和今日特价菜品',
        'examples': ['今天有什么好吃的', '菜单', '推荐菜品'],
        'param_schema': {},
        'is_active': 1
    },
    {
        'command_name': 'inventory_warning',
        'keywords': ['库存', '缺货', '不够了', '补货', '没了', '售罄'],
        'patterns': [
            r'(?:库存|缺货|不够了|售罄).*(?:多少|查询|哪些)',
            r'(?:什么|哪些).*(?:缺货|没了|卖完了)',
            r'(?:补货|进货).*(?:提醒|通知)'
        ],
        'response_template': 'fooddelivery:inventory_warning',
        'description': '库存预警，查看哪些食材需要补货',
        'examples': ['库存还有多少', '哪些菜卖完了', '需要补货'],
        'param_schema': {},
        'is_active': 1
    },
    {
        'command_name': 'rush_order',
        'keywords': ['催单', '快点', '加急', '催一下', '着急', '等很久'],
        'patterns': [
            r'(?:催单|加急|快点|催一下|着急|等很久)',
            r'(?:麻烦|帮我).*(?:快点|催|加急)',
            r'(?:等).*(?:很久|半天)'
        ],
        'response_template': 'fooddelivery:rush_order',
        'description': '催单，通知后厨加急处理',
        'examples': ['催单', '快点，等很久了', '加急处理'],
        'param_schema': {'order_no': '订单号', 'text': '备注'},
        'is_active': 1
    }
]


def register_plugin(app):
    app.register_blueprint(fooddelivery_bp)
    _register_commands()


def _register_commands():
    try:
        from services.command_config_service import command_config_service
        result = command_config_service.register_plugin_commands(PLUGIN_NAME, FOODDELIVERY_COMMANDS)
        if result['success']:
            print(f"✓ 餐饮配送插件指令注册成功: 创建{result['created_count']}条, 更新{result['updated_count']}条")
        else:
            print(f"✗ 餐饮配送插件指令注册失败: {result['error']}")
    except ImportError:
        print("! 全局指令服务未加载，跳过指令注册")
    except Exception as e:
        print(f"✗ 餐饮配送插件指令注册异常: {str(e)}")


def unregister_plugin(app):
    try:
        from services.command_config_service import command_config_service
        result = command_config_service.unregister_plugin_commands(PLUGIN_NAME)
        if result['success']:
            print(f"✓ 餐饮配送插件指令已卸载: 禁用{result['deleted_count']}条")
    except Exception as e:
        print(f"✗ 餐饮配送插件指令卸载异常: {str(e)}")