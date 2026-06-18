"""
工地管理业务插件
提供工程量上报、费用管理、耗材管理、设备租赁、财务管理、薪资管理、工地统计等功能
"""
from .models import *
from .service import ConstructionService
from .api import construction_bp

PLUGIN_NAME = 'construction'

CONSTRUCTION_COMMANDS = [
    {
        'command_name': 'report_volume',
        'keywords': ['工程量', '上报工程量', '今日工程量', '施工量', '今日挖了多少', '今天干了多少', '施工进度'],
        'patterns': [
            r'(?:工程量|施工量|挖了).*(?:上报|记录|多少|汇报)',
            r'(?:今日|今天|昨天).*(?:工程量|施工量|挖|干)',
            r'(\d+)\s*(?:方|吨|车)\s*(?:土方|石方|混凝土)',
            r'(?:挖了|干了|做了)\s*(\d+)'
        ],
        'response_template': 'construction:report_volume',
        'description': '上报每日施工工程量，支持自动识别数量和单位',
        'examples': ['工程量 城东工地 土方开挖 500方', '今天挖了300方土方', '上报工程量 混凝土 50吨'],
        'param_schema': {'site_name': '工地名称', 'quantity': '工程数量', 'unit': '单位(方/吨/车)', 'text': '施工内容描述'},
        'is_active': 1
    },
    {
        'command_name': 'report_expense',
        'keywords': ['费用', '上报费用', '报销', '支出', '花了', '开支', '成本'],
        'patterns': [
            r'(?:费用|报销|支出|花了|开支).*(?:上报|记录|多少)',
            r'(?:燃油费|过路费|维修费|补贴|生活费).*(?:多少|上报|花了)',
            r'(\d+)\s*(?:元|块)\s*(?:加油|过路|修车)',
            r'(?:花了|用了|支出)\s*(\d+)'
        ],
        'response_template': 'construction:report_expense',
        'description': '上报运营费用，支持自动识别费用类型和金额',
        'examples': ['费用 燃油费 300元', '今天花了500元过路费', '上报费用 生活费 1000元'],
        'param_schema': {'category': '费用类型', 'amount': '金额(元)', 'site_name': '工地名称'},
        'is_active': 1
    },
    {
        'command_name': 'consumable_in',
        'keywords': ['入库', '耗材入库', '进货', '采购', '到货', '进了'],
        'patterns': [
            r'(?:入库|进货|采购|入了|进了).*(?:耗材|物资|材料)',
            r'(?:柴油|水泥|钢材|石子|砂子).*(?:入库|进货|进了)',
            r'(\d+)\s*(?:升|吨|袋|箱)\s*(?:柴油|水泥|钢材)'
        ],
        'response_template': 'construction:consumable_in',
        'description': '耗材入库登记，自动解析耗材名称和数量',
        'examples': ['入库 柴油 500升', '水泥 20吨 入库', '进了500升柴油'],
        'param_schema': {'quantity': '数量', 'unit': '单位', 'text': '耗材名称', 'site_name': '工地名称'},
        'is_active': 1
    },
    {
        'command_name': 'consumable_out',
        'keywords': ['出库', '领用', '使用', '消耗', '用了', '领了'],
        'patterns': [
            r'(?:出库|领用|使用|用了|领了).*(?:耗材|物资|材料)',
            r'(?:柴油|水泥|钢材|石子).*(?:用了|领了|消耗)',
            r'(\d+)\s*(?:升|吨|袋)\s*(?:柴油|水泥|钢材).*(?:用了|领了)'
        ],
        'response_template': 'construction:consumable_out',
        'description': '耗材出库/领用记录',
        'examples': ['出库 水泥 10袋', '用了100升柴油', '领用 钢材 2吨'],
        'param_schema': {'quantity': '数量', 'unit': '单位', 'text': '耗材名称', 'site_name': '工地名称'},
        'is_active': 1
    },
    {
        'command_name': 'equipment_lease',
        'keywords': ['设备', '租赁', '挖掘机', '装载机', '租', '机械'],
        'patterns': [
            r'(?:设备|机械|挖掘机|装载机|推土机).*(?:租赁|租用|到期)',
            r'(?:租).*(?:设备|挖掘机|装载机)',
            r'(?:租赁).*(?:到期|费用|多少钱)'
        ],
        'response_template': 'construction:equipment_lease',
        'description': '设备租赁管理和到期提醒',
        'examples': ['设备租赁 挖掘机 30天', '挖掘机租用 城东工地', '租赁到期查询'],
        'param_schema': {'text': '设备名称', 'quantity': '租期天数', 'site_name': '工地名称'},
        'is_active': 1
    },
    {
        'command_name': 'financial_record',
        'keywords': ['记账', '收支', '回款', '结算', '收到款', '付款', '对账'],
        'patterns': [
            r'(?:记账|收支|回款|结算|收到款|付款).*(?:记录|多少|查询)',
            r'(?:收入|支出|收款|付款)\s*(\d+)',
            r'(?:对方|客户).*(?:打款|付款)'
        ],
        'response_template': 'construction:financial_record',
        'description': '财务收支记账管理',
        'examples': ['记账 收入 50000元 工程款', '收到款 30000元', '支出 10000元 材料费'],
        'param_schema': {'amount': '金额', 'category': '收支类型', 'text': '备注说明'},
        'is_active': 1
    },
    {
        'command_name': 'salary_report',
        'keywords': ['薪资', '工资', '结算', '考勤', '发工资', '算出勤'],
        'patterns': [
            r'(?:薪资|工资|工钱).*(?:多少|结算|查询|发了)',
            r'(?:考勤).*(?:记录|统计|查询)',
            r'(?:给|帮).*(?:算|查).*(?:工资|薪资)'
        ],
        'response_template': 'construction:salary_report',
        'description': '员工薪资查询与结算',
        'examples': ['薪资查询 张三', '工资结算', '考勤统计 本月'],
        'param_schema': {'name': '员工姓名', 'date': '日期范围'},
        'is_active': 1
    },
    {
        'command_name': 'site_stats',
        'keywords': ['工地', '统计', '汇总', '报表', '进度', '完成情况', '概况'],
        'patterns': [
            r'(?:工地|项目|工程).*(?:统计|汇总|报表|进度)',
            r'(?:进度|完成|施工).*(?:多少|统计|怎么样)',
            r'(?:总体|全部).*(?:情况|统计|报表)'
        ],
        'response_template': 'construction:site_stats',
        'description': '工地综合统计报表，包含进度、费用、耗材',
        'examples': ['工地统计', '城东工地进度', '全部工程报表'],
        'param_schema': {'site_name': '工地名称(可选)'},
        'is_active': 1
    }
]


def register_plugin(app):
    app.register_blueprint(construction_bp)
    _register_commands()


def _register_commands():
    try:
        from services.command_config_service import command_config_service
        result = command_config_service.register_plugin_commands(PLUGIN_NAME, CONSTRUCTION_COMMANDS)
        if result['success']:
            print(f"✓ 建筑工程插件指令注册成功: 创建{result['created_count']}条, 更新{result['updated_count']}条")
        else:
            print(f"✗ 建筑工程插件指令注册失败: {result['error']}")
    except ImportError:
        print("! 全局指令服务未加载，跳过指令注册")
    except Exception as e:
        print(f"✗ 建筑工程插件指令注册异常: {str(e)}")


def unregister_plugin(app):
    try:
        from services.command_config_service import command_config_service
        result = command_config_service.unregister_plugin_commands(PLUGIN_NAME)
        if result['success']:
            print(f"✓ 建筑工程插件指令已卸载: 禁用{result['deleted_count']}条")
    except Exception as e:
        print(f"✗ 建筑工程插件指令卸载异常: {str(e)}")