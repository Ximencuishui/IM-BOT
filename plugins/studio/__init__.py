"""
歌曲分离工作室插件
提供歌曲分离、乐器分离、歌曲润色、DJ编曲、歌曲代找等服务
包含自动接单、工作流管理、知识库、定时问候等功能
"""
from .models import *
from .service import StudioService
from .api import studio_bp

PLUGIN_NAME = 'studio'
PLUGIN_CODE = 'studio'
PLUGIN_VERSION = '1.0.0'
PLUGIN_DESCRIPTION = '歌曲分离工作室 - 提供歌曲分离、乐器分离、歌曲润色、DJ编曲、歌曲代找等服务'

STUDIO_COMMANDS = [
    {
        'command_name': 'studio_greeting',
        'keywords': ['早安', '早上好', '大家早上好', '上午好', '歌友们好'],
        'patterns': [
            r'(?:早安|早上好|上午好|大家好)',
        ],
        'response_template': 'studio:greeting',
        'description': '发送问候消息',
        'examples': ['早安', '早上好', '大家早上好'],
        'param_schema': {},
        'is_active': 1
    },
    {
        'command_name': 'studio_help',
        'keywords': ['歌曲', 'K歌', '唱歌', '卡拉OK', '服务', '能做什么'],
        'patterns': [
            r'(?:歌曲|K歌|唱歌|卡拉OK).*(?:服务|帮助|能)',
            r'(?:有什么|哪些).*(?:服务|功能)',
            r'(?:能)?(?:做什么|干嘛)',
        ],
        'response_template': 'studio:help',
        'description': '展示服务菜单',
        'examples': ['有什么服务', '能做什么', '歌曲服务'],
        'param_schema': {},
        'is_active': 1
    },
    {
        'command_name': 'studio_consult',
        'keywords': ['分离', '伴奏', '人声', '修音', '润色', '找歌', '编曲', 'DJ'],
        'patterns': [
            r'(?:分离|伴奏|人声|修音|润色|找歌|编曲|DJ|remix)',
            r'(?:帮|给|请).*(?:分离|找|做|唱|弄)',
            r'(?:我).*(?:想|要|需要)(?:分离|找|做|唱)',
        ],
        'response_template': 'studio:consult',
        'description': '触发咨询接单流程',
        'examples': ['帮我把这首歌分离一下', '我想找一首歌', '需要修音'],
        'param_schema': {'text': '用户需求描述'},
        'is_active': 1
    },
    {
        'command_name': 'studio_order_status',
        'keywords': ['订单', '进度', '好了吗', '完成了吗', '处理好了'],
        'patterns': [
            r'(?:订单|进度).*(?:查询|状态|多少|如何)',
            r'(?:好了|完成|处理).*(?:吗|了|没有)',
            r'(?:我的).*(?:订单|歌)',
        ],
        'response_template': 'studio:order_status',
        'description': '查询订单处理进度',
        'examples': ['我的订单进度', '处理好了吗', '查订单'],
        'param_schema': {'order_no': '订单号'},
        'is_active': 1
    },
    {
        'command_name': 'studio_price',
        'keywords': ['价格', '多少钱', '收费', '费用', '报价', '怎么收费'],
        'patterns': [
            r'(?:价格|收费|费用|多少钱|报价).*(?:多少|怎么|是)',
            r'(?:怎么).*(?:收费|算|计费)',
        ],
        'response_template': 'studio:price',
        'description': '查询收费标准',
        'examples': ['怎么收费', '分离多少钱', '价格表'],
        'param_schema': {},
        'is_active': 1
    },
    {
        'command_name': 'studio_contact_boss',
        'keywords': ['老板', '人工', '客服', '真人', '转人工'],
        'patterns': [
            r'(?:找|叫|转).*(?:老板|人工|客服|真人)',
            r'(?:老板|人工|客服).*(?:在|有|在吗)',
        ],
        'response_template': 'studio:contact_boss',
        'description': '转人工服务',
        'examples': ['找老板', '转人工', '客服在吗'],
        'param_schema': {},
        'is_active': 1
    },
]


def register_plugin(app):
    app.register_blueprint(studio_bp)
    _register_commands()


def _register_commands():
    try:
        from services.command_config_service import command_config_service
        result = command_config_service.register_plugin_commands(PLUGIN_NAME, STUDIO_COMMANDS)
        if result['success']:
            print(f"✓ 歌曲分离工作室插件指令注册成功: 创建{result['created_count']}条, 更新{result['updated_count']}条")
        else:
            print(f"✗ 歌曲分离工作室插件指令注册失败: {result['error']}")
    except ImportError:
        print("! 全局指令服务未加载，跳过指令注册")
    except Exception as e:
        print(f"✗ 歌曲分离工作室插件指令注册异常: {str(e)}")


def unregister_plugin(app):
    try:
        from services.command_config_service import command_config_service
        result = command_config_service.unregister_plugin_commands(PLUGIN_NAME)
        if result['success']:
            print(f"✓ 歌曲分离工作室插件指令已卸载: 禁用{result['deleted_count']}条")
    except Exception as e:
        print(f"✗ 歌曲分离工作室插件指令卸载异常: {str(e)}")