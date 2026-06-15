"""
预设规则库初始化脚本
生成9类行业通用规则模板并插入数据库
"""
import json
from database.db_config import get_db_session, init_db
from models.user_models import RuleTemplate


# 9类行业预设规则
PRESET_TEMPLATES = [
    {
        "template_name": "沙县小吃食材配送报单统计规则",
        "industry": "沙县小吃",
        "description": "适用于沙县小吃店的食材配送订单自动统计，支持花生酱、拌面、扁肉等特色食材的智能识别与分类汇总。",
        "parse_rules": [
            {"rule_name": "标准数量+单位+商品", "rule_type": "regex", "pattern": "(\\d+(?:\\.\\d+)?)\\s*(斤|两|kg|公斤|包|箱|瓶)(.+?)(?:，|$)", "priority": 10, "is_active": True},
            {"rule_name": "快捷码识别", "rule_type": "keyword", "pattern": "花生酱|拌面料|扁肉皮|柳叶蒸饺", "priority": 8, "is_active": True},
            {"rule_name": "备注提取", "rule_type": "regex", "pattern": "(要嫩的|不要葱|多放辣|少盐)", "priority": 5, "is_active": True}
        ],
        "stat_rules": [
            {"rule_name": "每日食材汇总", "stat_type": "daily", "chart_type": "bar", "refresh_interval": 3600, "is_active": True},
            {"rule_name": "周销量趋势", "stat_type": "weekly", "chart_type": "line", "refresh_interval": 3600, "is_active": True}
        ],
        "reply_rules": [
            {"rule_name": "接单确认", "trigger_type": "keyword", "trigger_content": "已下单", "reply_content": "收到！您的订单已记录，今晚截单前可修改。", "priority": 10, "is_active": True},
            {"rule_name": "价格查询", "trigger_type": "keyword", "trigger_content": "今日价格", "reply_content": "今日报价单已发送，请查收~", "priority": 8, "is_active": True}
        ],
        "source_type": "official",
        "is_featured": True
    },
    {
        "template_name": "普通餐饮店食材配送报单统计规则",
        "industry": "餐饮通用",
        "description": "适用于一般中餐/晚餐餐厅的食材配送统计，支持蔬菜、肉类、海鲜等常见食材的分类管理。",
        "parse_rules": [
            {"rule_name": "数量商品识别", "rule_type": "regex", "pattern": "(\\d+(?:\\.\\d+)?)\\s*(斤|两|kg|盘|份)(.+?)(?:，|$)", "priority": 10, "is_active": True},
            {"rule_name": "菜品简称匹配", "rule_type": "keyword", "pattern": "土豆|白菜|猪肉|牛肉|鸡肉", "priority": 8, "is_active": True}
        ],
        "stat_rules": [
            {"rule_name": "日采购汇总", "stat_type": "daily", "chart_type": "pie", "refresh_interval": 3600, "is_active": True}
        ],
        "reply_rules": [
            {"rule_name": "欢迎语", "trigger_type": "keyword", "trigger_content": "你好", "reply_content": "您好！请直接发送食材清单，如：土豆10斤，白菜5斤", "priority": 10, "is_active": True}
        ],
        "source_type": "official",
        "is_featured": True
    },
    {
        "template_name": "火锅店食材配送报单统计规则",
        "industry": "火锅",
        "description": "专为火锅店设计，支持毛肚、鸭肠、肥牛等火锅特色食材的智能识别，支持锅底调料单独统计。",
        "parse_rules": [
            {"rule_name": "火锅食材识别", "rule_type": "keyword", "pattern": "毛肚|鸭肠|肥牛|羊肉卷|虾滑|脑花", "priority": 10, "is_active": True},
            {"rule_name": "锅底备注", "rule_type": "regex", "pattern": "(微辣|中辣|特辣|鸳鸯锅|清汤)", "priority": 8, "is_active": True}
        ],
        "stat_rules": [
            {"rule_name": "荤素分类统计", "stat_type": "daily", "chart_type": "pie", "refresh_interval": 3600, "is_active": True}
        ],
        "reply_rules": [
            {"rule_name": "订货确认", "trigger_type": "all", "trigger_content": "", "reply_content": "订单已收到，明早6点前送达~", "priority": 5, "is_active": True}
        ],
        "source_type": "official",
        "is_featured": False
    },
    {
        "template_name": "餐饮店佐料配送报单统计规则",
        "industry": "调味品",
        "description": "专注于餐厅调味品和佐料的配送统计，包括酱油、醋、味精、辣椒等常用调料的库存管理。",
        "parse_rules": [
            {"rule_name": "调味品识别", "rule_type": "keyword", "pattern": "生抽|老抽|陈醋|味精|鸡精|辣椒油|花椒", "priority": 10, "is_active": True},
            {"rule_name": "瓶装数量", "rule_type": "regex", "pattern": "(\\d+)\\s*(瓶|桶|袋|箱)", "priority": 8, "is_active": True}
        ],
        "stat_rules": [
            {"rule_name": "月度消耗分析", "stat_type": "monthly", "chart_type": "line", "refresh_interval": 86400, "is_active": True}
        ],
        "reply_rules": [],
        "source_type": "official",
        "is_featured": False
    },
    {
        "template_name": "粮油食材配送报单统计规则",
        "industry": "粮油副食",
        "description": "适用于粮油批发和配送场景，支持大米、面粉、食用油等大宗商品的重量单位和包装规格管理。",
        "parse_rules": [
            {"rule_name": "粮油商品识别", "rule_type": "keyword", "pattern": "大米|面粉|食用油|大豆油|菜籽油|面条", "priority": 10, "is_active": True},
            {"rule_name": "大包装识别", "rule_type": "regex", "pattern": "(\\d+)\\s*(袋|箱|桶|件)", "priority": 8, "is_active": True}
        ],
        "stat_rules": [
            {"rule_name": "品类占比", "stat_type": "weekly", "chart_type": "pie", "refresh_interval": 3600, "is_active": True}
        ],
        "reply_rules": [],
        "source_type": "official",
        "is_featured": False
    },
    {
        "template_name": "手机维修配件配送报单统计规则",
        "industry": "手机维修",
        "description": "适用于手机维修店的配件配送管理，支持屏幕、电池、后盖等常用配件的型号匹配和库存统计。",
        "parse_rules": [
            {"rule_name": "手机型号+配件", "rule_type": "regex", "pattern": "(iPhone\\s*\\d+|华为|小米|OPPO|vivo)(.+?)(屏幕|电池|后盖|摄像头|排线)", "priority": 10, "is_active": True},
            {"rule_name": "配件数量", "rule_type": "regex", "pattern": "(\\d+)\\s*(个|片|块)", "priority": 8, "is_active": True}
        ],
        "stat_rules": [
            {"rule_name": "品牌配件分布", "stat_type": "monthly", "chart_type": "bar", "refresh_interval": 86400, "is_active": True}
        ],
        "reply_rules": [
            {"rule_name": "缺货提醒回复", "trigger_type": "keyword", "trigger_content": "有货吗", "reply_content": "正在查询库存，请稍等...", "priority": 8, "is_active": True}
        ],
        "source_type": "official",
        "is_featured": False
    },
    {
        "template_name": "摩托车配件配送报单统计规则",
        "industry": "摩配",
        "description": "摩托车配件配送专用，支持发动机配件、刹车系统、轮胎等摩配商品的分类管理和车型适配。",
        "parse_rules": [
            {"rule_name": "摩配商品识别", "rule_type": "keyword", "pattern": "刹车片|机油滤芯|火花塞|链条|轮胎|离合器", "priority": 10, "is_active": True},
            {"rule_name": "车型适配", "rule_type": "regex", "pattern": "(125|150|250|300)\\s*cc", "priority": 7, "is_active": True}
        ],
        "stat_rules": [
            {"rule_name": "配件类别统计", "stat_type": "monthly", "chart_type": "pie", "refresh_interval": 86400, "is_active": True}
        ],
        "reply_rules": [],
        "source_type": "official",
        "is_featured": False
    },
    {
        "template_name": "电动车配件配送报单统计规则",
        "industry": "电动车",
        "description": "电动车及电动自行车配件配送管理，支持电池、电机、控制器、轮胎等核心配件的统计。",
        "parse_rules": [
            {"rule_name": "电配商品识别", "rule_type": "keyword", "pattern": "电池|电机|控制器|充电器|刹车|轮胎|减震", "priority": 10, "is_active": True},
            {"rule_name": "电池规格", "rule_type": "regex", "pattern": "(48V|60V|72V)\\s*(\\d+)Ah", "priority": 8, "is_active": True}
        ],
        "stat_rules": [
            {"rule_name": "电池销量排行", "stat_type": "monthly", "chart_type": "bar", "refresh_interval": 86400, "is_active": True}
        ],
        "reply_rules": [],
        "source_type": "official",
        "is_featured": False
    },
    {
        "template_name": "汽车配件配送报单统计规则",
        "industry": "汽配",
        "description": "汽车维修配件配送专用，支持发动机、变速箱、底盘、电气系统等全类别汽配零件的管理。",
        "parse_rules": [
            {"rule_name": "汽配零件识别", "rule_type": "keyword", "pattern": "机滤|空滤|空调滤|刹车盘|雨刮|电瓶|皮带", "priority": 10, "is_active": True},
            {"rule_name": "车型年份", "rule_type": "regex", "pattern": "(\\d{4})款\\s*(丰田|大众|本田|宝马|奔驰)", "priority": 7, "is_active": True}
        ],
        "stat_rules": [
            {"rule_name": "品牌配件占比", "stat_type": "monthly", "chart_type": "pie", "refresh_interval": 86400, "is_active": True},
            {"rule_name": "保养件vs易损件", "stat_type": "monthly", "chart_type": "bar", "refresh_interval": 86400, "is_active": True}
        ],
        "reply_rules": [
            {"rule_name": "VIN码查询引导", "trigger_type": "keyword", "trigger_content": "车架号", "reply_content": "请提供17位车架号(VIN)，帮您精确匹配配件~", "priority": 9, "is_active": True}
        ],
        "source_type": "official",
        "is_featured": True
    }
]


def init_preset_templates():
    """初始化预设规则模板到数据库"""
    import sys
    import io
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    db = get_db_session()
    try:
        # 检查是否已有预设模板
        existing_count = db.query(RuleTemplate).filter(
            RuleTemplate.source_type == 'official'
        ).count()

        if existing_count > 0:
            print(f"已存在 {existing_count} 个官方模板，跳过初始化")
            return

        print("正在导入预设规则模板...")
        
        for template_data in PRESET_TEMPLATES:
            template = RuleTemplate(
                template_name=template_data['template_name'],
                industry=template_data['industry'],
                description=template_data['description'],
                parse_rules=json.dumps(template_data.get('parse_rules', []), ensure_ascii=False),
                stat_rules=json.dumps(template_data.get('stat_rules', []), ensure_ascii=False),
                reply_rules=json.dumps(template_data.get('reply_rules', []), ensure_ascii=False),
                source_type=template_data.get('source_type', 'official'),
                is_featured=template_data.get('is_featured', False),
                is_public=True,
                is_active=True
            )
            db.add(template)

        db.commit()
        print(f"[OK] 成功导入 {len(PRESET_TEMPLATES)} 个预设规则模板")
        
        # 打印模板列表
        for t in PRESET_TEMPLATES:
            print(f"  - [{t['industry']}] {t['template_name']}")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] 预设模板导入失败: {e}")
        raise
    finally:
        db.close()


if __name__ == '__main__':
    init_db()  # 确保表已创建
    init_preset_templates()
