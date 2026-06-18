"""
电动车配件行业插件
提供配件管理、订单处理、库存管理、维修记录等功能
"""
from .models import *
from .service import EvPartsService
from .api import evparts_bp

PLUGIN_NAME = 'evparts'

EVPARTS_COMMANDS = [
    {
        'command_name': 'parts_query',
        'keywords': ['配件', '电池', '充电器', '轮胎', '找配件', '型号'],
        'patterns': [
            r'(?:配件|电池|充电器|轮胎).*(?:查询|有什么|找)',
            r'(?:什么|哪个).*(?:型号|规格|配件)',
            r'(?:适合|匹配).*(?:什么|哪个)'
        ],
        'response_template': 'evparts:parts_query',
        'description': '电动车配件查询和匹配',
        'examples': ['配件查询 电池', '找充电器', '什么型号的轮胎'],
        'param_schema': {'text': '配件名称/型号'},
        'is_active': 1
    },
    {
        'command_name': 'order_query',
        'keywords': ['订单', '发货', '快递', '单号', '物流'],
        'patterns': [
            r'(?:订单|发货|物流).*(?:查询|状态|到哪)',
            r'(?:快递|单号).*(?:查询|跟踪)',
            r'(?:什么).*(?:时候|到了)'
        ],
        'response_template': 'evparts:order_query',
        'description': '配件订单查询和物流跟踪',
        'examples': ['订单查询', '快递到哪了', '物流单号'],
        'param_schema': {'order_no': '订单号'},
        'is_active': 1
    },
    {
        'command_name': 'inventory_query',
        'keywords': ['库存', '缺货', '备货', '到货', '有货吗'],
        'patterns': [
            r'(?:库存|缺货|备货|到货).*(?:查询|多少|哪些)',
            r'(?:还有|有).*(?:多少|货)',
            r'(?:什么).*(?:缺货|没货)'
        ],
        'response_template': 'evparts:inventory_query',
        'description': '配件库存查询',
        'examples': ['库存查询', '电池有货吗', '哪些配件缺货'],
        'param_schema': {},
        'is_active': 1
    },
    {
        'command_name': 'repair_record',
        'keywords': ['维修', '故障', '修理', '保养', '坏了'],
        'patterns': [
            r'(?:维修|故障|修理|保养).*(?:记录|登记|报修)',
            r'(?:坏了|故障).*(?:什么|怎么)',
            r'(?:需要).*(?:维修|保养)'
        ],
        'response_template': 'evparts:repair_record',
        'description': '维修记录管理和报修',
        'examples': ['报修 电池故障', '维修记录', '需要保养'],
        'param_schema': {'text': '故障描述', 'name': '客户姓名'},
        'is_active': 1
    },
    {
        'command_name': 'price_query',
        'keywords': ['价格', '多少钱', '报价', '优惠', '批发价'],
        'patterns': [
            r'(?:价格|多少钱|报价|批发价).*(?:查询|多少)',
            r'(?:这个|那个).*(?:多少|价格)',
            r'(\d+)\s*(?:元|块)'
        ],
        'response_template': 'evparts:price_query',
        'description': '配件价格查询',
        'examples': ['电池多少钱', '价格查询', '批发价'],
        'param_schema': {'text': '配件名称', 'quantity': '数量'},
        'is_active': 1
    }
]


def register_plugin(app):
    app.register_blueprint(evparts_bp)
    _register_commands()


def _register_commands():
    try:
        from services.command_config_service import command_config_service
        result = command_config_service.register_plugin_commands(PLUGIN_NAME, EVPARTS_COMMANDS)
        if result['success']:
            print(f"✓ 电动车配件插件指令注册成功: 创建{result['created_count']}条, 更新{result['updated_count']}条")
        else:
            print(f"✗ 电动车配件插件指令注册失败: {result['error']}")
    except ImportError:
        print("! 全局指令服务未加载，跳过指令注册")
    except Exception as e:
        print(f"✗ 电动车配件插件指令注册异常: {str(e)}")


def unregister_plugin(app):
    try:
        from services.command_config_service import command_config_service
        result = command_config_service.unregister_plugin_commands(PLUGIN_NAME)
        if result['success']:
            print(f"✓ 电动车配件插件指令已卸载: 禁用{result['deleted_count']}条")
    except Exception as e:
        print(f"✗ 电动车配件插件指令卸载异常: {str(e)}")