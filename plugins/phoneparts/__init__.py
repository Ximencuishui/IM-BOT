"""
手机配件行业插件
提供手机配件管理、订单处理、库存管理、维修服务等功能
"""
from .models import *
from .service import PhonePartsService
from .api import phoneparts_bp

PLUGIN_NAME = 'phoneparts'

PHONEPARTS_COMMANDS = [
    {
        'command_name': 'parts_query',
        'keywords': ['配件', '屏幕', '电池', '壳', '膜', '手机'],
        'patterns': [
            r'(?:配件|屏幕|电池|壳|膜).*(?:查询|有什么|找)',
            r'(?:什么|哪个).*(?:型号|手机)',
            r'(?:手机|iPhone).*(?:配件|屏幕|电池)'
        ],
        'response_template': 'phoneparts:parts_query',
        'description': '手机配件查询，支持机型匹配',
        'examples': ['配件查询 iPhone15', '屏幕多少钱', '电池有吗'],
        'param_schema': {'text': '机型/配件名称'},
        'is_active': 1
    },
    {
        'command_name': 'order_query',
        'keywords': ['订单', '发货', '快递', '单号', '到哪'],
        'patterns': [
            r'(?:订单|发货|快递).*(?:查询|状态|到哪)',
            r'(?:单号|编号).*(?:查询)',
            r'(?:什么).*(?:时候|发货|到)'
        ],
        'response_template': 'phoneparts:order_query',
        'description': '手机配件订单查询',
        'examples': ['订单查询', '快递到哪了', '什么时候发货'],
        'param_schema': {'order_no': '订单号'},
        'is_active': 1
    },
    {
        'command_name': 'inventory_query',
        'keywords': ['库存', '缺货', '备货', '到货', '有货吗'],
        'patterns': [
            r'(?:库存|缺货|备货|到货).*(?:查询|多少)',
            r'(?:还有|有).*(?:多少|货)',
            r'(?:什么).*(?:缺|没)'
        ],
        'response_template': 'phoneparts:inventory_query',
        'description': '手机配件库存查询',
        'examples': ['库存查询', '屏幕有货吗', '哪些缺货'],
        'param_schema': {},
        'is_active': 1
    },
    {
        'command_name': 'repair_service',
        'keywords': ['维修', '换屏', '换电池', '故障', '坏了', '碎屏'],
        'patterns': [
            r'(?:维修|换屏|换电池|修理).*(?:报价|预约|登记)',
            r'(?:坏了|碎屏|故障).*(?:修|换|怎么办)',
            r'(?:手机).*(?:坏了|碎|故障)'
        ],
        'response_template': 'phoneparts:repair_service',
        'description': '手机维修服务登记和报价',
        'examples': ['换屏 多少钱', '手机坏了', '维修 iPhone换电池'],
        'param_schema': {'text': '故障描述/型号', 'amount': '预算金额'},
        'is_active': 1
    },
    {
        'command_name': 'price_query',
        'keywords': ['价格', '多少钱', '报价', '优惠', '批发'],
        'patterns': [
            r'(?:价格|多少钱|报价).*(?:查询|多少)',
            r'(?:这个|那个).*(?:多少|价格)',
            r'(\d+)\s*(?:元|块)'
        ],
        'response_template': 'phoneparts:price_query',
        'description': '手机配件价格查询',
        'examples': ['多少钱', '报价单', '批发行情'],
        'param_schema': {'text': '配件名称', 'quantity': '数量'},
        'is_active': 1
    }
]


def register_plugin(app):
    app.register_blueprint(phoneparts_bp)
    _register_commands()


def _register_commands():
    try:
        from services.command_config_service import command_config_service
        result = command_config_service.register_plugin_commands(PLUGIN_NAME, PHONEPARTS_COMMANDS)
        if result['success']:
            print(f"✓ 手机配件插件指令注册成功: 创建{result['created_count']}条, 更新{result['updated_count']}条")
        else:
            print(f"✗ 手机配件插件指令注册失败: {result['error']}")
    except ImportError:
        print("! 全局指令服务未加载，跳过指令注册")
    except Exception as e:
        print(f"✗ 手机配件插件指令注册异常: {str(e)}")


def unregister_plugin(app):
    try:
        from services.command_config_service import command_config_service
        result = command_config_service.unregister_plugin_commands(PLUGIN_NAME)
        if result['success']:
            print(f"✓ 手机配件插件指令已卸载: 禁用{result['deleted_count']}条")
    except Exception as e:
        print(f"✗ 手机配件插件指令卸载异常: {str(e)}")