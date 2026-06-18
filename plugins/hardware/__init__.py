"""
五金建材行业插件
提供五金产品管理、订单处理、库存管理、供应商管理等功能
"""
from .models import *
from .service import HardwareService
from .api import hardware_bp

PLUGIN_NAME = 'hardware'

HARDWARE_COMMANDS = [
    {
        'command_name': 'product_query',
        'keywords': ['五金', '螺丝', '工具', '建材', '找产品'],
        'patterns': [
            r'(?:五金|螺丝|工具|建材).*(?:查询|有什么|找)',
            r'(?:什么).*(?:规格|尺寸|型号)',
            r'(?:找|查).*(?:五金|工具|建材)'
        ],
        'response_template': 'hardware:product_query',
        'description': '五金建材产品查询',
        'examples': ['五金查询 螺丝', '找建材', '什么规格'],
        'param_schema': {'text': '产品名称/规格'},
        'is_active': 1
    },
    {
        'command_name': 'order_query',
        'keywords': ['订单', '发货', '物流', '单号', '到哪了'],
        'patterns': [
            r'(?:订单|发货|物流).*(?:查询|状态|到哪)',
            r'(?:单号|编号).*(?:查询|跟踪)',
            r'(?:什么).*(?:时候|发货|到)'
        ],
        'response_template': 'hardware:order_query',
        'description': '五金订单查询和物流跟踪',
        'examples': ['订单查询', '发货到哪了', '物流单号'],
        'param_schema': {'order_no': '订单号'},
        'is_active': 1
    },
    {
        'command_name': 'inventory_query',
        'keywords': ['库存', '备货', '缺货', '到货', '有多少'],
        'patterns': [
            r'(?:库存|备货|缺货|到货).*(?:查询|多少|哪些)',
            r'(?:还有|有).*(?:多少|库存)',
            r'(?:什么).*(?:缺|不够)'
        ],
        'response_template': 'hardware:inventory_query',
        'description': '五金库存查询',
        'examples': ['库存查询', '螺丝还有多少', '哪些缺货'],
        'param_schema': {},
        'is_active': 1
    },
    {
        'command_name': 'supplier_query',
        'keywords': ['供应商', '进货', '价格', '报价', '厂家'],
        'patterns': [
            r'(?:供应商|厂家).*(?:查询|联系|信息)',
            r'(?:进货|采购).*(?:价格|哪里)',
            r'(?:谁|哪个).*(?:供应商|厂家)'
        ],
        'response_template': 'hardware:supplier_query',
        'description': '供应商信息查询',
        'examples': ['供应商查询', '螺丝厂家', '进货价格'],
        'param_schema': {'text': '供应商/产品名称'},
        'is_active': 1
    },
    {
        'command_name': 'quote_request',
        'keywords': ['询价', '报价', '多少钱', '价格', '批价'],
        'patterns': [
            r'(?:询价|报价).*(?:多少|查询|请求)',
            r'(?:这个|那个).*(?:多少|价格)',
            r'(?:批价|批发).*(?:多少)'
        ],
        'response_template': 'hardware:quote_request',
        'description': '产品询价和报价',
        'examples': ['询价 螺丝 M6x20', '多少钱 一箱', '报价单'],
        'param_schema': {'text': '产品名称', 'quantity': '数量'},
        'is_active': 1
    }
]


def register_plugin(app):
    app.register_blueprint(hardware_bp)
    _register_commands()


def _register_commands():
    try:
        from services.command_config_service import command_config_service
        result = command_config_service.register_plugin_commands(PLUGIN_NAME, HARDWARE_COMMANDS)
        if result['success']:
            print(f"✓ 五金建材插件指令注册成功: 创建{result['created_count']}条, 更新{result['updated_count']}条")
        else:
            print(f"✗ 五金建材插件指令注册失败: {result['error']}")
    except ImportError:
        print("! 全局指令服务未加载，跳过指令注册")
    except Exception as e:
        print(f"✗ 五金建材插件指令注册异常: {str(e)}")


def unregister_plugin(app):
    try:
        from services.command_config_service import command_config_service
        result = command_config_service.unregister_plugin_commands(PLUGIN_NAME)
        if result['success']:
            print(f"✓ 五金建材插件指令已卸载: 禁用{result['deleted_count']}条")
    except Exception as e:
        print(f"✗ 五金建材插件指令卸载异常: {str(e)}")