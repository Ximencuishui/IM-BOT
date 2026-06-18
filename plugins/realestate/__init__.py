"""
房产中介行业插件
提供房源管理、客户管理、交易流程、智能匹配等功能
"""
from .models import *
from .service import RealEstateService
from .api import realestate_bp

PLUGIN_NAME = 'realestate'

REALESTATE_COMMANDS = [
    {
        'command_name': 'house_query',
        'keywords': ['房源', '房子', '买房', '租房', '二手房', '新房', '楼盘'],
        'patterns': [
            r'(?:房源|房子|楼盘).*(?:查询|有什么|推荐)',
            r'(?:买房|租房|二手房|新房).*(?:多少|价格|面积)',
            r'(\d+)\s*(?:万|平|室|厅)'
        ],
        'response_template': 'realestate:house_query',
        'description': '房源检索，按条件查询在售/在租房源',
        'examples': ['房源 100万', '买房 城东', '租房 两室一厅'],
        'param_schema': {'amount': '预算(万)', 'site_name': '区域', 'text': '户型需求'},
        'is_active': 1
    },
    {
        'command_name': 'customer_follow',
        'keywords': ['客户', '跟进', '意向', '需求', '看房意向'],
        'patterns': [
            r'(?:客户|意向).*(?:跟进|登记|录入)',
            r'(?:客户|有).*(?:兴趣|意向|想)',
            r'(?:需求|要求).*(?:登记|记录)'
        ],
        'response_template': 'realestate:customer_follow',
        'description': '客户跟进记录管理',
        'examples': ['客户跟进 李四', '意向登记', '客户需求 学区房'],
        'param_schema': {'name': '客户姓名', 'text': '需求描述'},
        'is_active': 1
    },
    {
        'command_name': 'transaction_progress',
        'keywords': ['交易', '进度', '过户', '贷款', '签约', '网签'],
        'patterns': [
            r'(?:交易|过户|贷款|签约|网签).*(?:进度|状态|到什么阶段)',
            r'(?:手续).*(?:办到哪|进度)',
            r'(?:房子).*(?:过完户|贷完款)'
        ],
        'response_template': 'realestate:transaction_progress',
        'description': '查询房屋交易进度',
        'examples': ['交易进度', '过户到哪了', '贷款审批进度'],
        'param_schema': {'order_no': '交易编号', 'text': '房源信息'},
        'is_active': 1
    },
    {
        'command_name': 'viewing_record',
        'keywords': ['带看', '看房', '记录', '约看', '安排看房'],
        'patterns': [
            r'(?:带看|看房).*(?:记录|安排|预约)',
            r'(?:明天|今天|这周).*(?:看房)',
            r'(?:约).*(?:看房|看)'
        ],
        'response_template': 'realestate:viewing_record',
        'description': '带看记录和预约管理',
        'examples': ['带看记录', '明天安排看房', '约看 城东小区'],
        'param_schema': {'name': '客户姓名', 'date': '看房日期', 'text': '房源信息'},
        'is_active': 1
    },
    {
        'command_name': 'price_estimate',
        'keywords': ['估价', '房价', '多少钱', '评估', '能卖多少', '值多少'],
        'patterns': [
            r'(?:估价|评估|房价).*(?:多少|查询)',
            r'(?:能卖|值).*(?:多少|多少钱)',
            r'(?:小区).*(?:多少|价格)'
        ],
        'response_template': 'realestate:price_estimate',
        'description': '房屋估价，提供市场参考价',
        'examples': ['估价 城东小区', '这个房子值多少', '房价评估'],
        'param_schema': {'text': '小区名称', 'quantity': '面积'},
        'is_active': 1
    }
]


def register_plugin(app):
    app.register_blueprint(realestate_bp)
    _register_commands()


def _register_commands():
    try:
        from services.command_config_service import command_config_service
        result = command_config_service.register_plugin_commands(PLUGIN_NAME, REALESTATE_COMMANDS)
        if result['success']:
            print(f"✓ 房产中介插件指令注册成功: 创建{result['created_count']}条, 更新{result['updated_count']}条")
        else:
            print(f"✗ 房产中介插件指令注册失败: {result['error']}")
    except ImportError:
        print("! 全局指令服务未加载，跳过指令注册")
    except Exception as e:
        print(f"✗ 房产中介插件指令注册异常: {str(e)}")


def unregister_plugin(app):
    try:
        from services.command_config_service import command_config_service
        result = command_config_service.unregister_plugin_commands(PLUGIN_NAME)
        if result['success']:
            print(f"✓ 房产中介插件指令已卸载: 禁用{result['deleted_count']}条")
    except Exception as e:
        print(f"✗ 房产中介插件指令卸载异常: {str(e)}")