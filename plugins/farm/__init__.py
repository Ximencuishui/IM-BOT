"""
养殖场业务插件
提供牲畜生命周期管理、饲料进销存、订单管理、客户管理、员工管理、费用管理等功能
"""
from .models import *
from .service import FarmService
from .api import farm_bp

PLUGIN_NAME = 'farm'

FARM_COMMANDS = [
    {
        'command_name': 'livestock_entry',
        'keywords': ['进了', '入栏', '新进', '仔猪', '苗', '买了', '引进'],
        'patterns': [
            r'(?:进了|入栏|新进|买了|引进).*(?:仔猪|猪仔|鸡苗|鸭苗|牛犊|羊羔)',
            r'(?:仔猪|猪仔|鸡苗|鸭苗).*(?:进了|入栏|多少)',
            r'(\d+)\s*(?:头|只|个)\s*(?:猪|鸡|鸭|牛|羊)',
            r'(?:进了|入栏)\s*(\d+)\s*(?:头|只)'
        ],
        'response_template': 'farm:livestock_entry',
        'description': '记录新进牲畜入栏，支持自动识别数量和品种',
        'examples': ['进了50头仔猪', '入栏 鸡苗 1000只', '新进牛犊 20头'],
        'param_schema': {'quantity': '数量', 'unit': '单位(头/只)', 'text': '品种名称', 'price': '单价'},
        'is_active': 1
    },
    {
        'command_name': 'livestock_birth',
        'keywords': ['生了', '产仔', '下了', '产蛋', '母猪', '产仔数'],
        'patterns': [
            r'(?:生了|产仔|下了).*(?:猪仔|仔猪|小鸡|小鸭)',
            r'(?:母猪|母鸡).*(?:生了|产仔|下了)',
            r'(?:生了|产仔)\s*(\d+)\s*(?:头|只)',
            r'(?:产蛋)\s*(\d+)\s*(?:个|枚)'
        ],
        'response_template': 'farm:livestock_birth',
        'description': '记录牲畜繁殖产仔情况',
        'examples': ['母猪生了12只猪仔', '产蛋 500个', '母鸡下了300枚蛋'],
        'param_schema': {'quantity': '数量', 'unit': '单位(头/只/个)', 'text': '母畜信息'},
        'is_active': 1
    },
    {
        'command_name': 'livestock_death',
        'keywords': ['死了', '病死', '淘汰', '死亡', '损失'],
        'patterns': [
            r'(?:死了|病死|淘汰|死亡).*(?:猪|鸡|鸭|牛|羊)',
            r'(?:猪|鸡|鸭|牛|羊).*(?:死了|病死|多少)',
            r'(?:死了|病死)\s*(\d+)\s*(?:头|只)',
            r'(?:淘汰)\s*(\d+)\s*(?:头|只)'
        ],
        'response_template': 'farm:livestock_death',
        'description': '记录牲畜死亡或淘汰情况',
        'examples': ['死了5只鸡', '病死3头猪', '淘汰10只老鸭'],
        'param_schema': {'quantity': '数量', 'unit': '单位(头/只)', 'text': '品种和原因'},
        'is_active': 1
    },
    {
        'command_name': 'livestock_sale',
        'keywords': ['卖了', '出栏', '售出', '成交', '卖猪', '卖鸡'],
        'patterns': [
            r'(?:卖了|出栏|售出|成交).*(?:猪|鸡|鸭|牛|羊)',
            r'(?:猪|鸡|鸭|牛|羊).*(?:卖了|出栏|多少)',
            r'(?:卖了|出栏)\s*(\d+)\s*(?:头|只)',
            r'(?:卖了)\s*(\d+)\s*(?:斤|公斤|吨)'
        ],
        'response_template': 'farm:livestock_sale',
        'description': '记录牲畜出栏销售情况',
        'examples': ['卖了20头猪', '出栏1000只鸡', '成交5头牛'],
        'param_schema': {'quantity': '数量', 'unit': '单位(头/只/斤)', 'text': '品种信息'},
        'is_active': 1
    },
    {
        'command_name': 'feed_purchase',
        'keywords': ['采购', '买饲料', '饲料进货', '进饲料', '饲料到货'],
        'patterns': [
            r'(?:采购|买|进货|进).*(?:饲料|玉米|豆粕|预混料)',
            r'(?:玉米|豆粕|预混料).*(?:采购|买|进了)',
            r'(?:采购|买)\s*(\d+)\s*(?:吨|袋|公斤)\s*(?:饲料|玉米)'
        ],
        'response_template': 'farm:feed_purchase',
        'description': '记录饲料采购入库',
        'examples': ['采购玉米 20吨', '买饲料 100袋', '进了5吨豆粕'],
        'param_schema': {'quantity': '数量', 'unit': '单位(吨/袋/公斤)', 'text': '饲料名称', 'price': '单价'},
        'is_active': 1
    },
    {
        'command_name': 'feed_usage',
        'keywords': ['喂了', '用了', '消耗', '饲料用量', '吃了多少'],
        'patterns': [
            r'(?:喂了|用了|消耗).*(?:饲料|玉米|豆粕)',
            r'(?:饲料|玉米|豆粕).*(?:喂了|用了|消耗)',
            r'(?:喂了|用了)\s*(\d+)\s*(?:公斤|斤|袋)'
        ],
        'response_template': 'farm:feed_usage',
        'description': '记录饲料消耗用量',
        'examples': ['喂了500公斤饲料', '用了20袋玉米', '今天消耗1吨豆粕'],
        'param_schema': {'quantity': '数量', 'unit': '单位(公斤/斤/袋)', 'text': '饲料名称'},
        'is_active': 1
    },
    {
        'command_name': 'farm_order',
        'keywords': ['订单', '预定', '下单', '订货', '客户订单'],
        'patterns': [
            r'(?:订单|预定|下单|订货).*(?:猪|鸡|鸭|牛|羊)',
            r'(?:客户).*(?:订单|预定|下单)',
            r'(?:预定|下单)\s*(\d+)\s*(?:头|只)\s*(?:猪|鸡)'
        ],
        'response_template': 'farm:farm_order',
        'description': '创建客户订单，支持自动报价',
        'examples': ['订单 张老板 10头猪', '客户预定500只鸡', '下单 5头牛'],
        'param_schema': {'name': '客户名称', 'quantity': '数量', 'unit': '单位(头/只)', 'text': '品种'},
        'is_active': 1
    },
    {
        'command_name': 'farm_expense',
        'keywords': ['费用', '开支', '花了', '支出', '维修费', '水电费'],
        'patterns': [
            r'(?:费用|开支|花了|支出).*(?:维修|水电|办公|租金|燃油)',
            r'(?:维修费|水电费|办公费|租金|燃油费).*(?:多少|花了)',
            r'(?:花了|支出)\s*(\d+)\s*(?:元|块)'
        ],
        'response_template': 'farm:farm_expense',
        'description': '记录运营费用支出',
        'examples': ['维修费 5000元', '水电费 2000元', '燃油费 1500元'],
        'param_schema': {'category': '费用类型', 'amount': '金额(元)'},
        'is_active': 1
    },
    {
        'command_name': 'farm_stats',
        'keywords': ['统计', '报表', '存栏', '多少', '汇总', '概况'],
        'patterns': [
            r'(?:统计|报表|存栏).*(?:多少|查询|汇报)',
            r'(?:存栏|数量).*(?:多少|查询)',
            r'(?:总体|全部).*(?:情况|统计|报表)',
            r'(?:今天|本月|本周).*(?:统计|报表)'
        ],
        'response_template': 'farm:farm_stats',
        'description': '养殖场综合统计报表，包含存栏、销售、成本',
        'examples': ['存栏统计', '养殖场报表', '今天卖了多少'],
        'param_schema': {'period': '时间范围(可选)'},
        'is_active': 1
    }
]


def register_plugin(app):
    app.register_blueprint(farm_bp)
    _register_commands()


def _register_commands():
    try:
        from services.command_config_service import command_config_service
        result = command_config_service.register_plugin_commands(PLUGIN_NAME, FARM_COMMANDS)
        if result['success']:
            print(f"✓ 养殖场插件指令注册成功: 创建{result['created_count']}条, 更新{result['updated_count']}条")
        else:
            print(f"✗ 养殖场插件指令注册失败: {result['error']}")
    except ImportError:
        print("! 全局指令服务未加载，跳过指令注册")
    except Exception as e:
        print(f"✗ 养殖场插件指令注册异常: {str(e)}")


def unregister_plugin(app):
    try:
        from services.command_config_service import command_config_service
        result = command_config_service.unregister_plugin_commands(PLUGIN_NAME)
        if result['success']:
            print(f"✓ 养殖场插件指令已卸载: 禁用{result['deleted_count']}条")
    except Exception as e:
        print(f"✗ 养殖场插件指令卸载异常: {str(e)}")