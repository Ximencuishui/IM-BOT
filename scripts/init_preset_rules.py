"""
预设规则库初始化脚本
生成9类行业通用规则模板并插入数据库
"""
import json
from database.db_config import get_db_session, init_db
from models.user_models import RuleTemplate


# 20类行业预设规则（完整版）
PRESET_TEMPLATES = [
    {
        "template_name": "沙县小吃食材配送报单统计规则",
        "industry": "沙县小吃",
        "description": "适用于沙县小吃店的食材配送订单自动统计，支持花生酱、拌面、扁肉等特色食材的智能识别与分类汇总。支持批量圈选语法（如：下单 1-10 5斤）和增量操作（如：花生酱+2瓶）。",
        "parse_rules": [
            {"rule_name": "标准数量+单位+商品", "rule_type": "regex", "pattern": "(\\d+(?:\\.\\d+)?)\\s*(斤|两|kg|公斤|包|箱|瓶|袋)(.+?)(?:，|,|$)", "priority": 10, "is_active": True, "description": "匹配标准格式：10斤土豆、5.5箱矿泉水、2瓶花生酱"},
            {"rule_name": "沙县特色食材关键词", "rule_type": "keyword", "pattern": "花生酱|拌面料|扁肉皮|柳叶蒸饺|炖罐|飘香拌面|营养馄饨", "priority": 8, "is_active": True, "description": "快速识别沙县特色食材"},
            {"rule_name": "常用蔬菜肉类", "rule_type": "keyword", "pattern": "土豆|白菜|青菜|猪肉|牛肉|鸡肉|鸭肉|鸡蛋", "priority": 7, "is_active": True, "description": "匹配常见基础食材"},
            {"rule_name": "快捷码识别", "rule_type": "keyword", "pattern": "HSJ|BM|BRP|LZ|DG", "priority": 7, "is_active": True, "description": "快捷码：HSJ=花生酱，BM=拌面，BRP=扁肉皮"},
            {"rule_name": "备注提取-口味要求", "rule_type": "regex", "pattern": "(要嫩的|不要葱|多放辣|少盐|加辣|免香菜)", "priority": 5, "is_active": True, "description": "提取客户特殊要求"},
            {"rule_name": "备注提取-时间要求", "rule_type": "regex", "pattern": "(明天送|后天到|急用|下午前|早上8点前)", "priority": 5, "is_active": True, "description": "提取配送时间要求"},
            {"rule_name": "批量圈选支持", "rule_type": "custom", "pattern": "下单 1-10 5斤 | 圈选 1,3,5-8 10斤", "priority": 9, "is_active": True, "description": "支持批量圈选语法，需配合线路产品清单使用"},
            {"rule_name": "增量操作支持", "rule_type": "custom", "pattern": "花生酱+2瓶 | 土豆-3斤 | 白菜=15斤", "priority": 9, "is_active": True, "description": "支持增量修改：加、减、直接替换"}
        ],
        "stat_rules": [
            {"rule_name": "每日食材汇总", "stat_type": "daily", "chart_type": "bar", "refresh_interval": 3600, "is_active": True, "description": "统计当日所有食材的总量，柱状图展示TOP10食材"},
            {"rule_name": "周销量趋势", "stat_type": "weekly", "chart_type": "line", "refresh_interval": 3600, "is_active": True, "description": "近7天食材销量变化趋势，折线图展示"},
            {"rule_name": "食材类别占比", "stat_type": "daily", "chart_type": "pie", "refresh_interval": 3600, "is_active": True, "description": "按类别统计：主食类、肉类、蔬菜类、调味类的占比"},
            {"rule_name": "月度消耗分析", "stat_type": "monthly", "chart_type": "line", "refresh_interval": 86400, "is_active": True, "description": "近30天主要食材消耗量对比，辅助采购决策"},
            {"rule_name": "特色食材TOP榜", "stat_type": "weekly", "chart_type": "bar", "refresh_interval": 3600, "is_active": True, "description": "沙县特色食材（花生酱、拌面料等）销量排行"}
        ],
        "reply_rules": [
            {"rule_name": "欢迎语", "trigger_type": "keyword", "trigger_content": "你好|您好|help|帮助", "reply_content": "您好！欢迎使用沙县小吃食材配送系统。\n\n📋 下单示例：\n• 花生酱10瓶，拌面料5包\n• 土豆20斤，要嫩的\n• 下单 1-10 5斤（批量圈选）\n• 花生酱+2瓶（增量添加）\n\n💡 发送食材清单即可自动识别，如有问题请留言~", "priority": 10, "is_active": True, "description": "新用户引导和使用说明"},
            {"rule_name": "接单确认", "trigger_type": "keyword", "trigger_content": "已下单|提交|确认", "reply_content": "✅ 收到！您的订单已记录。\n\n⏰ 今晚22:00截单，截单前可修改订单。\n🚚 明早6:00-8:00配送到店。\n\n如有疑问请联系客服：400-xxx-xxxx", "priority": 10, "is_active": True, "description": "订单提交后的确认回复"},
            {"rule_name": "价格查询", "trigger_type": "keyword", "trigger_content": "价格|报价|多少钱|今日价格", "reply_content": "📊 今日报价单已生成，请点击下方链接查看：\n\n[查看今日报价](http://xxx.com/price/today)\n\n💡 报价每日6:00更新，大批量订购可享优惠~", "priority": 8, "is_active": True, "description": "价格查询自动回复"},
            {"rule_name": "库存查询", "trigger_type": "keyword", "trigger_content": "有货吗|库存|还有吗", "reply_content": "🔍 正在查询库存...\n\n请输入您要查询的商品名称，如：花生酱\n或直接发送订单，系统会自动检测库存并提示~", "priority": 8, "is_active": True, "description": "库存查询引导"},
            {"rule_name": "截单时间提醒", "trigger_type": "all", "trigger_content": "", "reply_content": "⏰ 温馨提醒：\n今日截单时间为22:00，请及时提交订单哦~\n\n🚚 配送时间：明早6:00-8:00", "priority": 5, "is_active": False, "description": "定时发送的截单提醒（需配合定时任务）"}
        ],
        "source_type": "official",
        "is_featured": True
    },
    {
        "template_name": "普通餐饮店食材配送报单统计规则",
        "industry": "餐饮通用",
        "description": "适用于一般中餐/晚餐餐厅的食材配送统计，支持蔬菜、肉类、海鲜等常见食材的分类管理。支持批量圈选和增量操作。",
        "parse_rules": [
            {"rule_name": "标准数量+单位+商品", "rule_type": "regex", "pattern": "(\\d+(?:\\.\\d+)?)\\s*(斤|两|kg|公斤|盘|份|箱)(.+?)(?:，|,|$)", "priority": 10, "is_active": True, "description": "匹配标准格式：10斤土豆、5盘牛肉"},
            {"rule_name": "常用蔬菜识别", "rule_type": "keyword", "pattern": "土豆|白菜|青菜|菠菜|芹菜|萝卜|茄子|西红柿|黄瓜", "priority": 8, "is_active": True, "description": "快速识别常见蔬菜"},
            {"rule_name": "常用肉类识别", "rule_type": "keyword", "pattern": "猪肉|牛肉|羊肉|鸡肉|鸭肉|排骨|五花肉", "priority": 8, "is_active": True, "description": "快速识别常见肉类"},
            {"rule_name": "海鲜类识别", "rule_type": "keyword", "pattern": "鱼|虾|蟹|贝类|鱿鱼|海参", "priority": 7, "is_active": True, "description": "识别海鲜类食材"},
            {"rule_name": "备注提取-新鲜度", "rule_type": "regex", "pattern": "(要新鲜的|不要冻的|活的|现杀)", "priority": 5, "is_active": True, "description": "提取新鲜度要求"},
            {"rule_name": "备注提取-加工要求", "rule_type": "regex", "pattern": "(切好|洗净|去皮|去骨|切片|切丝)", "priority": 5, "is_active": True, "description": "提取加工处理要求"},
            {"rule_name": "批量圈选支持", "rule_type": "custom", "pattern": "下单 1-10 5斤 | 圈选 1,3,5-8 10斤", "priority": 9, "is_active": True, "description": "支持批量圈选语法"},
            {"rule_name": "增量操作支持", "rule_type": "custom", "pattern": "土豆+5斤 | 牛肉-3斤 | 白菜=20斤", "priority": 9, "is_active": True, "description": "支持增量修改"}
        ],
        "stat_rules": [
            {"rule_name": "日采购汇总", "stat_type": "daily", "chart_type": "pie", "refresh_interval": 3600, "is_active": True, "description": "统计当日采购总量，饼图展示各类食材占比"},
            {"rule_name": "周销量趋势", "stat_type": "weekly", "chart_type": "line", "refresh_interval": 3600, "is_active": True, "description": "近7天采购量变化趋势"},
            {"rule_name": "月度消耗分析", "stat_type": "monthly", "chart_type": "bar", "refresh_interval": 86400, "is_active": True, "description": "近30天主要食材消耗对比"},
            {"rule_name": "荤素比例分析", "stat_type": "weekly", "chart_type": "pie", "refresh_interval": 3600, "is_active": True, "description": "统计荤菜与素菜的采购比例"}
        ],
        "reply_rules": [
            {"rule_name": "欢迎语", "trigger_type": "keyword", "trigger_content": "你好|您好|help|帮助", "reply_content": "您好！欢迎使用餐饮食材配送系统。\n\n📋 下单示例：\n• 土豆10斤，牛肉5斤\n• 青菜20斤，要新鲜的\n• 下单 1-10 5斤（批量圈选）\n• 土豆+5斤（增量添加）\n\n💡 发送食材清单即可自动识别~", "priority": 10, "is_active": True, "description": "新用户引导"},
            {"rule_name": "接单确认", "trigger_type": "keyword", "trigger_content": "已下单|提交|确认", "reply_content": "✅ 收到！您的订单已记录。\n\n⏰ 今晚22:00截单\n🚚 明早5:00-7:00配送到店\n\n如有疑问请联系客服", "priority": 10, "is_active": True, "description": "订单确认回复"},
            {"rule_name": "价格查询", "trigger_type": "keyword", "trigger_content": "价格|报价|多少钱", "reply_content": "📊 今日报价单已生成\n\n请点击链接查看：[今日报价](http://xxx.com/price)\n\n💡 报价每日更新", "priority": 8, "is_active": True, "description": "价格查询"},
            {"rule_name": "库存查询", "trigger_type": "keyword", "trigger_content": "有货吗|库存", "reply_content": "🔍 请提供要查询的商品名称\n或直接发送订单，系统会自动检测库存", "priority": 8, "is_active": True, "description": "库存查询引导"}
        ],
        "source_type": "official",
        "is_featured": True
    },
    {
        "template_name": "火锅店食材配送报单统计规则",
        "industry": "火锅",
        "description": "专为火锅店设计，支持毛肚、鸭肠、肥牛等火锅特色食材的智能识别，支持锅底调料单独统计。支持批量圈选和增量操作。",
        "parse_rules": [
            {"rule_name": "标准数量+单位+商品", "rule_type": "regex", "pattern": "(\\d+(?:\\.\\d+)?)\\s*(斤|两|kg|公斤|盘|份)(.+?)(?:，|,|$)", "priority": 10, "is_active": True, "description": "匹配标准格式：10斤肥牛、5盘毛肚"},
            {"rule_name": "火锅特色食材", "rule_type": "keyword", "pattern": "毛肚|鸭肠|肥牛|羊肉卷|虾滑|脑花|黄喉|千层肚|鹅肠|腰片", "priority": 9, "is_active": True, "description": "快速识别火锅特色食材"},
            {"rule_name": "蔬菜豆制品", "rule_type": "keyword", "pattern": "白菜|菠菜|茼蒿|豆皮|豆腐|粉丝|宽粉|土豆片", "priority": 7, "is_active": True, "description": "识别火锅常用蔬菜和豆制品"},
            {"rule_name": "锅底备注", "rule_type": "regex", "pattern": "(微辣|中辣|特辣|鸳鸯锅|清汤|番茄锅|菌汤)", "priority": 8, "is_active": True, "description": "提取锅底口味要求"},
            {"rule_name": "蘸料备注", "rule_type": "regex", "pattern": "(麻酱|蒜泥|香油|蚝油|香菜|葱花)", "priority": 6, "is_active": True, "description": "提取蘸料偏好"},
            {"rule_name": "新鲜度要求", "rule_type": "regex", "pattern": "(要新鲜的|现切|不要冻的)", "priority": 5, "is_active": True, "description": "提取新鲜度要求"},
            {"rule_name": "批量圈选支持", "rule_type": "custom", "pattern": "下单 1-10 2盘 | 圈选 1,3,5-8 3盘", "priority": 9, "is_active": True, "description": "支持批量圈选语法"},
            {"rule_name": "增量操作支持", "rule_type": "custom", "pattern": "肥牛+5盘 | 毛肚-2盘 | 鸭肠=10盘", "priority": 9, "is_active": True, "description": "支持增量修改"}
        ],
        "stat_rules": [
            {"rule_name": "荤素分类统计", "stat_type": "daily", "chart_type": "pie", "refresh_interval": 3600, "is_active": True, "description": "统计当日荤菜与素菜的采购比例"},
            {"rule_name": "日食材汇总", "stat_type": "daily", "chart_type": "bar", "refresh_interval": 3600, "is_active": True, "description": "统计当日所有食材总量，柱状图展示TOP10"},
            {"rule_name": "周销量趋势", "stat_type": "weekly", "chart_type": "line", "refresh_interval": 3600, "is_active": True, "description": "近7天食材销量变化趋势"},
            {"rule_name": "特色食材TOP榜", "stat_type": "weekly", "chart_type": "bar", "refresh_interval": 3600, "is_active": True, "description": "火锅特色食材（毛肚、鸭肠等）销量排行"},
            {"rule_name": "月度消耗分析", "stat_type": "monthly", "chart_type": "line", "refresh_interval": 86400, "is_active": True, "description": "近30天主要食材消耗对比"}
        ],
        "reply_rules": [
            {"rule_name": "欢迎语", "trigger_type": "keyword", "trigger_content": "你好|您好|help|帮助", "reply_content": "您好！欢迎使用火锅店食材配送系统。\n\n📋 下单示例：\n• 肥牛10盘，毛肚5盘\n• 鸭肠8盘，要新鲜的\n• 下单 1-10 2盘（批量圈选）\n• 肥牛+3盘（增量添加）\n\n💡 发送食材清单即可自动识别~", "priority": 10, "is_active": True, "description": "新用户引导"},
            {"rule_name": "接单确认", "trigger_type": "keyword", "trigger_content": "已下单|提交|确认", "reply_content": "✅ 收到！您的订单已记录。\n\n⏰ 今晚22:00截单\n🚚 明早5:00-7:00配送到店\n\n如有疑问请联系客服", "priority": 10, "is_active": True, "description": "订单确认回复"},
            {"rule_name": "价格查询", "trigger_type": "keyword", "trigger_content": "价格|报价|多少钱", "reply_content": "📊 今日报价单已生成\n\n请点击链接查看：[今日报价](http://xxx.com/price)\n\n💡 报价每日更新", "priority": 8, "is_active": True, "description": "价格查询"},
            {"rule_name": "锅底咨询", "trigger_type": "keyword", "trigger_content": "锅底|辣度", "reply_content": "🍲 我们提供多种锅底选择：\n• 微辣/中辣/特辣\n• 鸳鸯锅/清汤\n• 番茄锅/菌汤\n\n请在订单中备注您需要的锅底类型~", "priority": 7, "is_active": True, "description": "锅底选择引导"}
        ],
        "source_type": "official",
        "is_featured": False
    },
    {
        "template_name": "餐饮店佐料配送报单统计规则",
        "industry": "调味品",
        "description": "专注于餐厅调味品和佐料的配送统计，包括酱油、醋、味精、辣椒等常用调料的库存管理。支持批量圈选和增量操作。",
        "parse_rules": [
            {"rule_name": "标准数量+单位+商品", "rule_type": "regex", "pattern": "(\\d+(?:\\.\\d+)?)\\s*(瓶|桶|袋|箱|斤|kg)(.+?)(?:，|,|$)", "priority": 10, "is_active": True, "description": "匹配标准格式：10瓶生抽、5袋味精"},
            {"rule_name": "常用调味品识别", "rule_type": "keyword", "pattern": "生抽|老抽|陈醋|白醋|味精|鸡精|盐|糖|料酒", "priority": 9, "is_active": True, "description": "快速识别基础调味品"},
            {"rule_name": "辣味调料", "rule_type": "keyword", "pattern": "辣椒油|花椒|胡椒|豆瓣酱|辣椒面|小米辣", "priority": 8, "is_active": True, "description": "识别辣味调料"},
            {"rule_name": "香料类", "rule_type": "keyword", "pattern": "八角|桂皮|香叶|草果|丁香|小茴香", "priority": 7, "is_active": True, "description": "识别常用香料"},
            {"rule_name": "品牌规格备注", "rule_type": "regex", "pattern": "(海天|李锦记|厨邦|千禾|恒顺)", "priority": 6, "is_active": True, "description": "提取品牌要求"},
            {"rule_name": "批量圈选支持", "rule_type": "custom", "pattern": "下单 1-10 5瓶 | 圈选 1,3,5-8 10瓶", "priority": 9, "is_active": True, "description": "支持批量圈选语法"},
            {"rule_name": "增量操作支持", "rule_type": "custom", "pattern": "生抽+10瓶 | 味精-5袋 | 盐=20袋", "priority": 9, "is_active": True, "description": "支持增量修改"}
        ],
        "stat_rules": [
            {"rule_name": "月度消耗分析", "stat_type": "monthly", "chart_type": "line", "refresh_interval": 86400, "is_active": True, "description": "近30天主要调料消耗量对比"},
            {"rule_name": "日采购汇总", "stat_type": "daily", "chart_type": "bar", "refresh_interval": 3600, "is_active": True, "description": "统计当日采购总量"},
            {"rule_name": "品类占比", "stat_type": "weekly", "chart_type": "pie", "refresh_interval": 3600, "is_active": True, "description": "按类别统计：酱油类、醋类、辣味类、香料类占比"},
            {"rule_name": "TOP调料排行", "stat_type": "monthly", "chart_type": "bar", "refresh_interval": 86400, "is_active": True, "description": "月度消耗最多的TOP10调料"}
        ],
        "reply_rules": [
            {"rule_name": "欢迎语", "trigger_type": "keyword", "trigger_content": "你好|您好|help|帮助", "reply_content": "您好！欢迎使用调味品配送系统。\n\n📋 下单示例：\n• 生抽10瓶，味精5袋\n• 辣椒油8瓶，要中辣的\n• 下单 1-10 5瓶（批量圈选）\n• 生抽+5瓶（增量添加）\n\n💡 发送调料清单即可自动识别~", "priority": 10, "is_active": True, "description": "新用户引导"},
            {"rule_name": "接单确认", "trigger_type": "keyword", "trigger_content": "已下单|提交|确认", "reply_content": "✅ 收到！您的订单已记录。\n\n⏰ 今晚20:00截单\n🚚 明早配送到店\n\n如有疑问请联系客服", "priority": 10, "is_active": True, "description": "订单确认回复"},
            {"rule_name": "价格查询", "trigger_type": "keyword", "trigger_content": "价格|报价|多少钱", "reply_content": "📊 今日报价单已生成\n\n请点击链接查看：[今日报价](http://xxx.com/price)\n\n💡 大批量订购可享优惠", "priority": 8, "is_active": True, "description": "价格查询"},
            {"rule_name": "保质期咨询", "trigger_type": "keyword", "trigger_content": "保质期|有效期", "reply_content": "📅 我们的调料保质期说明：\n• 酱油/醋：18个月\n• 味精/鸡精：24个月\n• 辣椒油：12个月\n• 香料：6-12个月\n\n所有产品均为近期生产，请放心使用~", "priority": 7, "is_active": True, "description": "保质期说明"}
        ],
        "source_type": "official",
        "is_featured": False
    },
    {
        "template_name": "粮油食材配送报单统计规则",
        "industry": "粮油副食",
        "description": "适用于粮油批发和配送场景，支持大米、面粉、食用油等大宗商品的重量单位和包装规格管理。支持批量圈选和增量操作。",
        "parse_rules": [
            {"rule_name": "标准数量+单位+商品", "rule_type": "regex", "pattern": "(\\d+(?:\\.\\d+)?)\\s*(袋|箱|桶|件|斤|kg)(.+?)(?:，|,|$)", "priority": 10, "is_active": True, "description": "匹配标准格式：10袋大米、5桶油"},
            {"rule_name": "粮油商品识别", "rule_type": "keyword", "pattern": "大米|面粉|食用油|大豆油|菜籽油|面条|挂面|米粉", "priority": 9, "is_active": True, "description": "快速识别粮油主食品"},
            {"rule_name": "杂粮类", "rule_type": "keyword", "pattern": "小米|玉米|红豆|绿豆|黑米|燕麦", "priority": 7, "is_active": True, "description": "识别杂粮类商品"},
            {"rule_name": "规格备注", "rule_type": "regex", "pattern": "(5kg|10kg|25kg|50斤|100斤)", "priority": 8, "is_active": True, "description": "提取包装规格要求"},
            {"rule_name": "品牌备注", "rule_type": "regex", "pattern": "(金龙鱼|福临门|鲁花|五得利|香满园)", "priority": 6, "is_active": True, "description": "提取品牌要求"},
            {"rule_name": "批量圈选支持", "rule_type": "custom", "pattern": "下单 1-10 5袋 | 圈选 1,3,5-8 10袋", "priority": 9, "is_active": True, "description": "支持批量圈选语法"},
            {"rule_name": "增量操作支持", "rule_type": "custom", "pattern": "大米+10袋 | 面粉-5袋 | 油=20桶", "priority": 9, "is_active": True, "description": "支持增量修改"}
        ],
        "stat_rules": [
            {"rule_name": "品类占比", "stat_type": "weekly", "chart_type": "pie", "refresh_interval": 3600, "is_active": True, "description": "按类别统计：米类、面类、油类、杂粮类占比"},
            {"rule_name": "日采购汇总", "stat_type": "daily", "chart_type": "bar", "refresh_interval": 3600, "is_active": True, "description": "统计当日采购总量"},
            {"rule_name": "月度消耗分析", "stat_type": "monthly", "chart_type": "line", "refresh_interval": 86400, "is_active": True, "description": "近30天主要商品消耗对比"},
            {"rule_name": "品牌销量排行", "stat_type": "monthly", "chart_type": "bar", "refresh_interval": 86400, "is_active": True, "description": "各品牌销量排行"}
        ],
        "reply_rules": [
            {"rule_name": "欢迎语", "trigger_type": "keyword", "trigger_content": "你好|您好|help|帮助", "reply_content": "您好！欢迎使用粮油副食配送系统。\n\n📋 下单示例：\n• 大米10袋（25kg），面粉5袋\n• 金龙鱼油8桶\n• 下单 1-10 5袋（批量圈选）\n• 大米+5袋（增量添加）\n\n💡 发送商品清单即可自动识别~", "priority": 10, "is_active": True, "description": "新用户引导"},
            {"rule_name": "接单确认", "trigger_type": "keyword", "trigger_content": "已下单|提交|确认", "reply_content": "✅ 收到！您的订单已记录。\n\n⏰ 今晚18:00截单\n🚚 明早配送到店\n\n如有疑问请联系客服", "priority": 10, "is_active": True, "description": "订单确认回复"},
            {"rule_name": "价格查询", "trigger_type": "keyword", "trigger_content": "价格|报价|多少钱", "reply_content": "📊 今日报价单已生成\n\n请点击链接查看：[今日报价](http://xxx.com/price)\n\n💡 大批量订购可享优惠", "priority": 8, "is_active": True, "description": "价格查询"},
            {"rule_name": "规格咨询", "trigger_type": "keyword", "trigger_content": "规格|包装", "reply_content": "📦 我们提供的常见规格：\n• 大米：5kg/10kg/25kg/50斤\n• 面粉：5kg/10kg/25kg\n• 食用油：5L/10L/20L\n\n请在订单中注明您需要的规格~", "priority": 7, "is_active": True, "description": "规格说明"}
        ],
        "source_type": "official",
        "is_featured": False
    },
    {
        "template_name": "手机维修配件配送报单统计规则",
        "industry": "手机维修",
        "description": "适用于手机维修店的配件配送管理，支持屏幕、电池、后盖等常用配件的型号匹配和库存统计。支持批量圈选和增量操作。",
        "parse_rules": [
            {"rule_name": "手机型号+配件", "rule_type": "regex", "pattern": "(iPhone\\s*\\d+|华为|小米|OPPO|vivo|三星|荣耀)(.+?)(屏幕|电池|后盖|摄像头|排线|按键)", "priority": 10, "is_active": True, "description": "匹配格式：iPhone13屏幕、华为电池"},
            {"rule_name": "配件数量", "rule_type": "regex", "pattern": "(\\d+)\\s*(个|片|块|套)", "priority": 9, "is_active": True, "description": "提取配件数量"},
            {"rule_name": "常用配件识别", "rule_type": "keyword", "pattern": "屏幕总成|电池|后盖|摄像头模组|排线|听筒|扬声器|充电口", "priority": 8, "is_active": True, "description": "快速识别常用配件"},
            {"rule_name": "品质备注", "rule_type": "regex", "pattern": "(原装|国产|高仿|品质|A货)", "priority": 7, "is_active": True, "description": "提取品质要求"},
            {"rule_name": "颜色备注", "rule_type": "regex", "pattern": "(黑色|白色|蓝色|红色|金色|银色)", "priority": 6, "is_active": True, "description": "提取颜色要求"},
            {"rule_name": "批量圈选支持", "rule_type": "custom", "pattern": "下单 1-10 2个 | 圈选 1,3,5-8 5个", "priority": 9, "is_active": True, "description": "支持批量圈选语法"},
            {"rule_name": "增量操作支持", "rule_type": "custom", "pattern": "iPhone13屏幕+5个 | 电池-3个 | 后盖=10个", "priority": 9, "is_active": True, "description": "支持增量修改"}
        ],
        "stat_rules": [
            {"rule_name": "品牌配件分布", "stat_type": "monthly", "chart_type": "bar", "refresh_interval": 86400, "is_active": True, "description": "各品牌配件销量分布"},
            {"rule_name": "日采购汇总", "stat_type": "daily", "chart_type": "pie", "refresh_interval": 3600, "is_active": True, "description": "统计当日采购总量"},
            {"rule_name": "配件类别占比", "stat_type": "weekly", "chart_type": "pie", "refresh_interval": 3600, "is_active": True, "description": "按类别统计：屏幕类、电池类、外壳类占比"},
            {"rule_name": "月度消耗分析", "stat_type": "monthly", "chart_type": "line", "refresh_interval": 86400, "is_active": True, "description": "近30天主要配件消耗对比"},
            {"rule_name": "TOP配件排行", "stat_type": "monthly", "chart_type": "bar", "refresh_interval": 86400, "is_active": True, "description": "月度销量最多的TOP10配件"}
        ],
        "reply_rules": [
            {"rule_name": "欢迎语", "trigger_type": "keyword", "trigger_content": "你好|您好|help|帮助", "reply_content": "您好！欢迎使用手机配件配送系统。\n\n📋 下单示例：\n• iPhone13屏幕2个，要原装的\n• 华为P40电池5个\n• 下单 1-10 2个（批量圈选）\n• iPhone13屏幕+3个（增量添加）\n\n💡 发送配件清单即可自动识别~", "priority": 10, "is_active": True, "description": "新用户引导"},
            {"rule_name": "接单确认", "trigger_type": "keyword", "trigger_content": "已下单|提交|确认", "reply_content": "✅ 收到！您的订单已记录。\n\n⏰ 今晚20:00截单\n🚚 明早配送到店\n\n如有疑问请联系客服", "priority": 10, "is_active": True, "description": "订单确认回复"},
            {"rule_name": "价格查询", "trigger_type": "keyword", "trigger_content": "价格|报价|多少钱", "reply_content": "📊 今日报价单已生成\n\n请点击链接查看：[今日报价](http://xxx.com/price)\n\n💡 大批量订购可享优惠", "priority": 8, "is_active": True, "description": "价格查询"},
            {"rule_name": "库存查询", "trigger_type": "keyword", "trigger_content": "有货吗|库存", "reply_content": "🔍 请提供要查询的配件信息\n格式：手机型号+配件名称\n例如：iPhone13屏幕\n或直接发送订单，系统会自动检测库存", "priority": 8, "is_active": True, "description": "库存查询引导"},
            {"rule_name": "品质说明", "trigger_type": "keyword", "trigger_content": "原装|品质|质量", "reply_content": "✨ 我们提供多种品质选择：\n• 原装正品：官方渠道，质保1年\n• 高品质国产：性价比高，质保6个月\n• 经济型：价格实惠，质保3个月\n\n请在订单中注明您需要的品质等级~", "priority": 7, "is_active": True, "description": "品质等级说明"}
        ],
        "source_type": "official",
        "is_featured": False
    },
    {
        "template_name": "摩托车配件配送报单统计规则",
        "industry": "摩配",
        "description": "摩托车配件配送专用，支持发动机配件、刹车系统、轮胎等摩配商品的分类管理和车型适配。支持批量圈选和增量操作。",
        "parse_rules": [
            {"rule_name": "摩配商品识别", "rule_type": "keyword", "pattern": "刹车片|机油滤芯|火花塞|链条|轮胎|离合器|减震器|空滤", "priority": 9, "is_active": True, "description": "快速识别常用摩配"},
            {"rule_name": "车型适配", "rule_type": "regex", "pattern": "(125|150|250|300|400|600)\\s*cc", "priority": 8, "is_active": True, "description": "提取排量信息"},
            {"rule_name": "品牌型号", "rule_type": "regex", "pattern": "(豪爵|铃木|本田|雅马哈|川崎|宝马|杜卡迪)", "priority": 7, "is_active": True, "description": "提取品牌信息"},
            {"rule_name": "数量提取", "rule_type": "regex", "pattern": "(\\d+)\\s*(个|套|条|对)", "priority": 9, "is_active": True, "description": "提取配件数量"},
            {"rule_name": "原厂/副厂备注", "rule_type": "regex", "pattern": "(原厂|正厂|副厂|品牌件)", "priority": 6, "is_active": True, "description": "提取品质要求"},
            {"rule_name": "批量圈选支持", "rule_type": "custom", "pattern": "下单 1-10 2个 | 圈选 1,3,5-8 5个", "priority": 9, "is_active": True, "description": "支持批量圈选语法"},
            {"rule_name": "增量操作支持", "rule_type": "custom", "pattern": "刹车片+5套 | 轮胎-2条 | 链条=10条", "priority": 9, "is_active": True, "description": "支持增量修改"}
        ],
        "stat_rules": [
            {"rule_name": "配件类别统计", "stat_type": "monthly", "chart_type": "pie", "refresh_interval": 86400, "is_active": True, "description": "按类别统计：发动机类、刹车类、传动类占比"},
            {"rule_name": "日采购汇总", "stat_type": "daily", "chart_type": "bar", "refresh_interval": 3600, "is_active": True, "description": "统计当日采购总量"},
            {"rule_name": "品牌配件分布", "stat_type": "monthly", "chart_type": "bar", "refresh_interval": 86400, "is_active": True, "description": "各品牌配件销量分布"},
            {"rule_name": "月度消耗分析", "stat_type": "monthly", "chart_type": "line", "refresh_interval": 86400, "is_active": True, "description": "近30天主要配件消耗对比"},
            {"rule_name": "TOP配件排行", "stat_type": "monthly", "chart_type": "bar", "refresh_interval": 86400, "is_active": True, "description": "月度销量最多的TOP10配件"}
        ],
        "reply_rules": [
            {"rule_name": "欢迎语", "trigger_type": "keyword", "trigger_content": "你好|您好|help|帮助", "reply_content": "您好！欢迎使用摩托车配件配送系统。\n\n📋 下单示例：\n• 125cc刹车片5套，要原厂的\n• 铃木链条10条\n• 下单 1-10 2个（批量圈选）\n• 刹车片+3套（增量添加）\n\n💡 发送配件清单即可自动识别~", "priority": 10, "is_active": True, "description": "新用户引导"},
            {"rule_name": "接单确认", "trigger_type": "keyword", "trigger_content": "已下单|提交|确认", "reply_content": "✅ 收到！您的订单已记录。\n\n⏰ 今晚19:00截单\n🚚 明早配送到店\n\n如有疑问请联系客服", "priority": 10, "is_active": True, "description": "订单确认回复"},
            {"rule_name": "价格查询", "trigger_type": "keyword", "trigger_content": "价格|报价|多少钱", "reply_content": "📊 今日报价单已生成\n\n请点击链接查看：[今日报价](http://xxx.com/price)\n\n💡 大批量订购可享优惠", "priority": 8, "is_active": True, "description": "价格查询"},
            {"rule_name": "车型适配咨询", "trigger_type": "keyword", "trigger_content": "适配|通用|兼容", "reply_content": "🏍️ 请在订单中注明：\n• 摩托车型号（如：豪爵125）\n• 排量（如：125cc）\n• 年份（如：2023款）\n\n这样我们可以为您精确匹配配件~", "priority": 7, "is_active": True, "description": "车型适配引导"}
        ],
        "source_type": "official",
        "is_featured": False
    },
    {
        "template_name": "电动车配件配送报单统计规则",
        "industry": "电动车",
        "description": "电动车及电动自行车配件配送管理，支持电池、电机、控制器、轮胎等核心配件的统计。支持批量圈选和增量操作。",
        "parse_rules": [
            {"rule_name": "电配商品识别", "rule_type": "keyword", "pattern": "电池|电机|控制器|充电器|刹车|轮胎|减震|转把|仪表", "priority": 9, "is_active": True, "description": "快速识别常用电动车配件"},
            {"rule_name": "电池规格", "rule_type": "regex", "pattern": "(48V|60V|72V)\\s*(\\d+)Ah", "priority": 10, "is_active": True, "description": "提取电池规格：48V20Ah"},
            {"rule_name": "数量提取", "rule_type": "regex", "pattern": "(\\d+)\\s*(个|套|条|块)", "priority": 9, "is_active": True, "description": "提取配件数量"},
            {"rule_name": "品牌备注", "rule_type": "regex", "pattern": "(天能|超威|星恒|海宝|旭派)", "priority": 7, "is_active": True, "description": "提取电池品牌"},
            {"rule_name": "类型备注", "rule_type": "regex", "pattern": "(锂电|铅酸|石墨烯)", "priority": 6, "is_active": True, "description": "提取电池类型"},
            {"rule_name": "批量圈选支持", "rule_type": "custom", "pattern": "下单 1-10 2个 | 圈选 1,3,5-8 5个", "priority": 9, "is_active": True, "description": "支持批量圈选语法"},
            {"rule_name": "增量操作支持", "rule_type": "custom", "pattern": "电池+5块 | 轮胎-2条 | 控制器=10个", "priority": 9, "is_active": True, "description": "支持增量修改"}
        ],
        "stat_rules": [
            {"rule_name": "电池销量排行", "stat_type": "monthly", "chart_type": "bar", "refresh_interval": 86400, "is_active": True, "description": "各规格电池销量排行"},
            {"rule_name": "日采购汇总", "stat_type": "daily", "chart_type": "pie", "refresh_interval": 3600, "is_active": True, "description": "统计当日采购总量"},
            {"rule_name": "配件类别占比", "stat_type": "weekly", "chart_type": "pie", "refresh_interval": 3600, "is_active": True, "description": "按类别统计：电池类、电机类、控制类占比"},
            {"rule_name": "月度消耗分析", "stat_type": "monthly", "chart_type": "line", "refresh_interval": 86400, "is_active": True, "description": "近30天主要配件消耗对比"},
            {"rule_name": "品牌分布", "stat_type": "monthly", "chart_type": "bar", "refresh_interval": 86400, "is_active": True, "description": "各品牌配件销量分布"}
        ],
        "reply_rules": [
            {"rule_name": "欢迎语", "trigger_type": "keyword", "trigger_content": "你好|您好|help|帮助", "reply_content": "您好！欢迎使用电动车配件配送系统。\n\n📋 下单示例：\n• 48V20Ah电池5块，要天能的\n• 充电器10个\n• 下单 1-10 2个（批量圈选）\n• 电池+3块（增量添加）\n\n💡 发送配件清单即可自动识别~", "priority": 10, "is_active": True, "description": "新用户引导"},
            {"rule_name": "接单确认", "trigger_type": "keyword", "trigger_content": "已下单|提交|确认", "reply_content": "✅ 收到！您的订单已记录。\n\n⏰ 今晚19:00截单\n🚚 明早配送到店\n\n如有疑问请联系客服", "priority": 10, "is_active": True, "description": "订单确认回复"},
            {"rule_name": "价格查询", "trigger_type": "keyword", "trigger_content": "价格|报价|多少钱", "reply_content": "📊 今日报价单已生成\n\n请点击链接查看：[今日报价](http://xxx.com/price)\n\n💡 大批量订购可享优惠", "priority": 8, "is_active": True, "description": "价格查询"},
            {"rule_name": "电池规格咨询", "trigger_type": "keyword", "trigger_content": "规格|型号|电压", "reply_content": "🔋 常见电池规格：\n• 48V12Ah / 48V20Ah / 48V32Ah\n• 60V20Ah / 60V32Ah\n• 72V20Ah / 72V32Ah\n\n类型：铅酸/锂电/石墨烯\n品牌：天能/超威/星恒\n\n请在订单中注明您需要的规格~", "priority": 7, "is_active": True, "description": "电池规格说明"}
        ],
        "source_type": "official",
        "is_featured": False
    },
    {
        "template_name": "汽车配件配送报单统计规则",
        "industry": "汽配",
        "description": "汽车维修配件配送专用，支持发动机、变速箱、底盘、电气系统等全类别汽配零件的管理。支持批量圈选和增量操作。",
        "parse_rules": [
            {"rule_name": "汽配零件识别", "rule_type": "keyword", "pattern": "机滤|空滤|空调滤|刹车盘|雨刮|电瓶|皮带|火花塞|减震器", "priority": 9, "is_active": True, "description": "快速识别常用汽配"},
            {"rule_name": "车型年份", "rule_type": "regex", "pattern": "(\\d{4})款\\s*(丰田|大众|本田|宝马|奔驰|日产|福特)", "priority": 8, "is_active": True, "description": "提取车型年份和品牌"},
            {"rule_name": "VIN码识别", "rule_type": "regex", "pattern": "([A-HJ-NPR-Z0-9]{17})", "priority": 10, "is_active": True, "description": "识别17位车架号(VIN)"},
            {"rule_name": "数量提取", "rule_type": "regex", "pattern": "(\\d+)\\s*(个|套|条|对|块)", "priority": 9, "is_active": True, "description": "提取配件数量"},
            {"rule_name": "原厂/品牌件备注", "rule_type": "regex", "pattern": "(原厂|正厂|品牌件|副厂)", "priority": 7, "is_active": True, "description": "提取品质要求"},
            {"rule_name": "保养类型", "rule_type": "regex", "pattern": "(小保养|大保养|常规保养)", "priority": 6, "is_active": True, "description": "提取保养类型"},
            {"rule_name": "批量圈选支持", "rule_type": "custom", "pattern": "下单 1-10 2个 | 圈选 1,3,5-8 5个", "priority": 9, "is_active": True, "description": "支持批量圈选语法"},
            {"rule_name": "增量操作支持", "rule_type": "custom", "pattern": "机滤+10个 | 刹车盘-2套 | 雨刮=20条", "priority": 9, "is_active": True, "description": "支持增量修改"}
        ],
        "stat_rules": [
            {"rule_name": "品牌配件占比", "stat_type": "monthly", "chart_type": "pie", "refresh_interval": 86400, "is_active": True, "description": "按品牌统计配件销量占比"},
            {"rule_name": "保养件vs易损件", "stat_type": "monthly", "chart_type": "bar", "refresh_interval": 86400, "is_active": True, "description": "统计保养件与易损件的销量对比"},
            {"rule_name": "日采购汇总", "stat_type": "daily", "chart_type": "pie", "refresh_interval": 3600, "is_active": True, "description": "统计当日采购总量"},
            {"rule_name": "月度消耗分析", "stat_type": "monthly", "chart_type": "line", "refresh_interval": 86400, "is_active": True, "description": "近30天主要配件消耗对比"},
            {"rule_name": "TOP配件排行", "stat_type": "monthly", "chart_type": "bar", "refresh_interval": 86400, "is_active": True, "description": "月度销量最多的TOP10配件"}
        ],
        "reply_rules": [
            {"rule_name": "欢迎语", "trigger_type": "keyword", "trigger_content": "你好|您好|help|帮助", "reply_content": "您好！欢迎使用汽车配件配送系统。\n\n📋 下单示例：\n• 2023款丰田卡罗拉机滤10个\n• VIN: LFMCC1BR5E0123456 刹车盘2套\n• 下单 1-10 2个（批量圈选）\n• 机滤+5个（增量添加）\n\n💡 发送配件清单即可自动识别~", "priority": 10, "is_active": True, "description": "新用户引导"},
            {"rule_name": "接单确认", "trigger_type": "keyword", "trigger_content": "已下单|提交|确认", "reply_content": "✅ 收到！您的订单已记录。\n\n⏰ 今晚18:00截单\n🚚 明早配送到店\n\n如有疑问请联系客服", "priority": 10, "is_active": True, "description": "订单确认回复"},
            {"rule_name": "价格查询", "trigger_type": "keyword", "trigger_content": "价格|报价|多少钱", "reply_content": "📊 今日报价单已生成\n\n请点击链接查看：[今日报价](http://xxx.com/price)\n\n💡 大批量订购可享优惠", "priority": 8, "is_active": True, "description": "价格查询"},
            {"rule_name": "VIN码查询引导", "trigger_type": "keyword", "trigger_content": "车架号|VIN", "reply_content": "🔍 请提供17位车架号(VIN)，帮您精确匹配配件~\n\nVIN码位置：\n• 行驶证上\n• 前挡风玻璃左下角\n• 车门B柱铭牌\n\n例如：LFMCC1BR5E0123456", "priority": 9, "is_active": True, "description": "VIN码查询引导"},
            {"rule_name": "品质说明", "trigger_type": "keyword", "trigger_content": "原厂|品牌件|质量", "reply_content": "✨ 我们提供多种品质选择：\n• 原厂件：4S店同款，质保1年\n• 品牌件：知名品牌，性价比高，质保6个月\n• 副厂件：价格实惠，质保3个月\n\n请在订单中注明您需要的品质等级~", "priority": 7, "is_active": True, "description": "品质等级说明"}
        ],
        "source_type": "official",
        "is_featured": True
    },
    # ==================== 新增11个行业 ====================
    {
        "template_name": "奶茶店原料配送报单统计规则",
        "industry": "奶茶店",
        "description": "适用于奶茶店的原料配送管理，支持茶叶、奶精、珍珠、杯子等常用原料的智能识别与统计。支持批量圈选和增量操作。",
        "parse_rules": [
            {"rule_name": "标准数量+单位+商品", "rule_type": "regex", "pattern": "(\\d+(?:\\.\\d+)?)\\s*(包|箱|袋|桶|斤|kg)(.+?)(?:，|,|$)", "priority": 10, "is_active": True, "description": "匹配标准格式：10包茶叶、5箱杯子"},
            {"rule_name": "茶类原料", "rule_type": "keyword", "pattern": "红茶|绿茶|乌龙茶|茉莉花茶|普洱茶|铁观音", "priority": 9, "is_active": True, "description": "快速识别茶类原料"},
            {"rule_name": "配料类", "rule_type": "keyword", "pattern": "珍珠|椰果|布丁|仙草|红豆|芋圆|波霸", "priority": 8, "is_active": True, "description": "识别奶茶配料"},
            {"rule_name": "包材类", "rule_type": "keyword", "pattern": "杯子|吸管|封口膜|打包袋|杯盖", "priority": 7, "is_active": True, "description": "识别包装材料"},
            {"rule_name": "奶制品", "rule_type": "keyword", "pattern": "奶精|鲜奶|炼乳|奶油|芝士", "priority": 7, "is_active": True, "description": "识别奶制品原料"},
            {"rule_name": "糖浆备注", "rule_type": "regex", "pattern": "(全糖|半糖|微糖|无糖|少糖)", "priority": 6, "is_active": True, "description": "提取糖度要求"},
            {"rule_name": "批量圈选支持", "rule_type": "custom", "pattern": "下单 1-10 5包 | 圈选 1,3,5-8 10包", "priority": 9, "is_active": True, "description": "支持批量圈选语法"},
            {"rule_name": "增量操作支持", "rule_type": "custom", "pattern": "珍珠+10包 | 杯子-5箱 | 茶叶=20包", "priority": 9, "is_active": True, "description": "支持增量修改"}
        ],
        "stat_rules": [
            {"rule_name": "日原料汇总", "stat_type": "daily", "chart_type": "bar", "refresh_interval": 3600, "is_active": True, "description": "统计当日所有原料采购总量"},
            {"rule_name": "周销量趋势", "stat_type": "weekly", "chart_type": "line", "refresh_interval": 3600, "is_active": True, "description": "近7天原料销量变化趋势"},
            {"rule_name": "原料类别占比", "stat_type": "weekly", "chart_type": "pie", "refresh_interval": 3600, "is_active": True, "description": "按类别统计：茶类、配料类、包材类占比"},
            {"rule_name": "月度消耗分析", "stat_type": "monthly", "chart_type": "line", "refresh_interval": 86400, "is_active": True, "description": "近30天主要原料消耗对比"},
            {"rule_name": "TOP原料排行", "stat_type": "monthly", "chart_type": "bar", "refresh_interval": 86400, "is_active": True, "description": "月度消耗最多的TOP10原料"}
        ],
        "reply_rules": [
            {"rule_name": "欢迎语", "trigger_type": "keyword", "trigger_content": "你好|您好|help|帮助", "reply_content": "您好！欢迎使用奶茶店原料配送系统。\n\n📋 下单示例：\n• 红茶10包，珍珠5包\n• 杯子2箱，要500ml的\n• 下单 1-10 5包（批量圈选）\n• 珍珠+3包（增量添加）\n\n💡 发送原料清单即可自动识别~", "priority": 10, "is_active": True, "description": "新用户引导"},
            {"rule_name": "接单确认", "trigger_type": "keyword", "trigger_content": "已下单|提交|确认", "reply_content": "✅ 收到！您的订单已记录。\n\n⏰ 今晚21:00截单\n🚚 明早配送到店\n\n如有疑问请联系客服", "priority": 10, "is_active": True, "description": "订单确认回复"},
            {"rule_name": "价格查询", "trigger_type": "keyword", "trigger_content": "价格|报价|多少钱", "reply_content": "📊 今日报价单已生成\n\n请点击链接查看：[今日报价](http://xxx.com/price)\n\n💡 大批量订购可享优惠", "priority": 8, "is_active": True, "description": "价格查询"},
            {"rule_name": "规格咨询", "trigger_type": "keyword", "trigger_content": "规格|型号|容量", "reply_content": "🥤 常见规格说明：\n• 杯子：360ml/500ml/700ml\n• 吸管：粗吸管/细吸管\n• 茶叶：500g/包、1kg/包\n\n请在订单中注明您需要的规格~", "priority": 7, "is_active": True, "description": "规格说明"}
        ],
        "source_type": "official",
        "is_featured": False
    },
    {
        "template_name": "烘焙店原料配送报单统计规则",
        "industry": "烘焙店",
        "description": "适用于烘焙店的原料配送管理，支持面粉、奶油、黄油、糖等烘焙原料的智能识别与统计。支持批量圈选和增量操作。",
        "parse_rules": [
            {"rule_name": "标准数量+单位+商品", "rule_type": "regex", "pattern": "(\\d+(?:\\.\\d+)?)\\s*(袋|箱|桶|斤|kg|包)(.+?)(?:，|,|$)", "priority": 10, "is_active": True, "description": "匹配标准格式：10袋面粉、5桶奶油"},
            {"rule_name": "粉类原料", "rule_type": "keyword", "pattern": "高筋面粉|低筋面粉|中筋面粉|全麦粉|玉米淀粉|糯米粉", "priority": 9, "is_active": True, "description": "快速识别粉类原料"},
            {"rule_name": "油脂类", "rule_type": "keyword", "pattern": "黄油|奶油|植物油|橄榄油|起酥油", "priority": 8, "is_active": True, "description": "识别油脂类原料"},
            {"rule_name": "糖类", "rule_type": "keyword", "pattern": "白砂糖|红糖|糖粉|蜂蜜|麦芽糖", "priority": 7, "is_active": True, "description": "识别糖类原料"},
            {"rule_name": "添加剂", "rule_type": "keyword", "pattern": "酵母|泡打粉|小苏打|吉利丁|香草精", "priority": 6, "is_active": True, "description": "识别烘焙添加剂"},
            {"rule_name": "品牌备注", "rule_type": "regex", "pattern": "(安佳|总统|铁塔|金像|美玫)", "priority": 6, "is_active": True, "description": "提取品牌要求"},
            {"rule_name": "批量圈选支持", "rule_type": "custom", "pattern": "下单 1-10 5袋 | 圈选 1,3,5-8 10袋", "priority": 9, "is_active": True, "description": "支持批量圈选语法"},
            {"rule_name": "增量操作支持", "rule_type": "custom", "pattern": "面粉+10袋 | 黄油-5桶 | 奶油=20桶", "priority": 9, "is_active": True, "description": "支持增量修改"}
        ],
        "stat_rules": [
            {"rule_name": "日原料汇总", "stat_type": "daily", "chart_type": "bar", "refresh_interval": 3600, "is_active": True, "description": "统计当日所有原料采购总量"},
            {"rule_name": "周销量趋势", "stat_type": "weekly", "chart_type": "line", "refresh_interval": 3600, "is_active": True, "description": "近7天原料销量变化趋势"},
            {"rule_name": "原料类别占比", "stat_type": "weekly", "chart_type": "pie", "refresh_interval": 3600, "is_active": True, "description": "按类别统计：粉类、油脂类、糖类占比"},
            {"rule_name": "月度消耗分析", "stat_type": "monthly", "chart_type": "line", "refresh_interval": 86400, "is_active": True, "description": "近30天主要原料消耗对比"},
            {"rule_name": "TOP原料排行", "stat_type": "monthly", "chart_type": "bar", "refresh_interval": 86400, "is_active": True, "description": "月度消耗最多的TOP10原料"}
        ],
        "reply_rules": [
            {"rule_name": "欢迎语", "trigger_type": "keyword", "trigger_content": "你好|您好|help|帮助", "reply_content": "您好！欢迎使用烘焙店原料配送系统。\n\n📋 下单示例：\n• 高筋面粉10袋，黄油5桶\n• 奶油8桶，要安佳的\n• 下单 1-10 5袋（批量圈选）\n• 面粉+3袋（增量添加）\n\n💡 发送原料清单即可自动识别~", "priority": 10, "is_active": True, "description": "新用户引导"},
            {"rule_name": "接单确认", "trigger_type": "keyword", "trigger_content": "已下单|提交|确认", "reply_content": "✅ 收到！您的订单已记录。\n\n⏰ 今晚20:00截单\n🚚 明早配送到店\n\n如有疑问请联系客服", "priority": 10, "is_active": True, "description": "订单确认回复"},
            {"rule_name": "价格查询", "trigger_type": "keyword", "trigger_content": "价格|报价|多少钱", "reply_content": "📊 今日报价单已生成\n\n请点击链接查看：[今日报价](http://xxx.com/price)\n\n💡 大批量订购可享优惠", "priority": 8, "is_active": True, "description": "价格查询"},
            {"rule_name": "保质期咨询", "trigger_type": "keyword", "trigger_content": "保质期|有效期", "reply_content": "📅 原料保质期说明：\n• 面粉：6-12个月\n• 黄油/奶油：冷藏6个月\n• 酵母：冷藏12个月\n\n所有产品均为近期生产，请放心使用~", "priority": 7, "is_active": True, "description": "保质期说明"}
        ],
        "source_type": "official",
        "is_featured": False
    },
    {
        "template_name": "生鲜超市商品配送报单统计规则",
        "industry": "生鲜超市",
        "description": "适用于生鲜超市的商品配送管理，支持蔬菜水果、肉类水产、日用品等全品类商品的智能识别与统计。支持批量圈选和增量操作。",
        "parse_rules": [
            {"rule_name": "标准数量+单位+商品", "rule_type": "regex", "pattern": "(\\d+(?:\\.\\d+)?)\\s*(斤|两|kg|公斤|箱|包|个)(.+?)(?:，|,|$)", "priority": 10, "is_active": True, "description": "匹配标准格式：10斤苹果、5箱牛奶"},
            {"rule_name": "蔬菜类", "rule_type": "keyword", "pattern": "土豆|白菜|青菜|菠菜|芹菜|萝卜|茄子|西红柿|黄瓜|辣椒", "priority": 9, "is_active": True, "description": "快速识别蔬菜类商品"},
            {"rule_name": "水果类", "rule_type": "keyword", "pattern": "苹果|香蕉|橙子|葡萄|西瓜|草莓|梨", "priority": 8, "is_active": True, "description": "识别水果类商品"},
            {"rule_name": "肉类", "rule_type": "keyword", "pattern": "猪肉|牛肉|羊肉|鸡肉|鸭肉|排骨", "priority": 8, "is_active": True, "description": "识别肉类商品"},
            {"rule_name": "水产类", "rule_type": "keyword", "pattern": "鱼|虾|蟹|贝类|鱿鱼", "priority": 7, "is_active": True, "description": "识别水产类商品"},
            {"rule_name": "新鲜度备注", "rule_type": "regex", "pattern": "(要新鲜的|不要冻的|活的|现杀)", "priority": 6, "is_active": True, "description": "提取新鲜度要求"},
            {"rule_name": "批量圈选支持", "rule_type": "custom", "pattern": "下单 1-10 5斤 | 圈选 1,3,5-8 10斤", "priority": 9, "is_active": True, "description": "支持批量圈选语法"},
            {"rule_name": "增量操作支持", "rule_type": "custom", "pattern": "苹果+10斤 | 猪肉-5斤 | 牛奶=20箱", "priority": 9, "is_active": True, "description": "支持增量修改"}
        ],
        "stat_rules": [
            {"rule_name": "日采购汇总", "stat_type": "daily", "chart_type": "bar", "refresh_interval": 3600, "is_active": True, "description": "统计当日所有商品采购总量"},
            {"rule_name": "周销量趋势", "stat_type": "weekly", "chart_type": "line", "refresh_interval": 3600, "is_active": True, "description": "近7天商品销量变化趋势"},
            {"rule_name": "商品类别占比", "stat_type": "weekly", "chart_type": "pie", "refresh_interval": 3600, "is_active": True, "description": "按类别统计：蔬菜、水果、肉类、水产占比"},
            {"rule_name": "月度消耗分析", "stat_type": "monthly", "chart_type": "line", "refresh_interval": 86400, "is_active": True, "description": "近30天主要商品消耗对比"},
            {"rule_name": "TOP商品排行", "stat_type": "monthly", "chart_type": "bar", "refresh_interval": 86400, "is_active": True, "description": "月度销量最多的TOP10商品"}
        ],
        "reply_rules": [
            {"rule_name": "欢迎语", "trigger_type": "keyword", "trigger_content": "你好|您好|help|帮助", "reply_content": "您好！欢迎使用生鲜超市配送系统。\n\n📋 下单示例：\n• 苹果10斤，猪肉5斤\n• 牛奶2箱，要新鲜的\n• 下单 1-10 5斤（批量圈选）\n• 苹果+3斤（增量添加）\n\n💡 发送商品清单即可自动识别~", "priority": 10, "is_active": True, "description": "新用户引导"},
            {"rule_name": "接单确认", "trigger_type": "keyword", "trigger_content": "已下单|提交|确认", "reply_content": "✅ 收到！您的订单已记录。\n\n⏰ 今晚21:00截单\n🚚 明早4:00-6:00配送到店\n\n如有疑问请联系客服", "priority": 10, "is_active": True, "description": "订单确认回复"},
            {"rule_name": "价格查询", "trigger_type": "keyword", "trigger_content": "价格|报价|多少钱", "reply_content": "📊 今日报价单已生成\n\n请点击链接查看：[今日报价](http://xxx.com/price)\n\n💡 大批量订购可享优惠", "priority": 8, "is_active": True, "description": "价格查询"},
            {"rule_name": "新鲜度咨询", "trigger_type": "keyword", "trigger_content": "新鲜|保质期", "reply_content": "🥬 我们保证所有生鲜产品：\n• 蔬菜：当日采摘，24小时内送达\n• 水果：精选优质果，坏果包赔\n• 肉类：检疫合格，冷链配送\n• 水产：活鲜配送，保证鲜活\n\n请放心订购~", "priority": 7, "is_active": True, "description": "新鲜度保证说明"}
        ],
        "source_type": "official",
        "is_featured": False
    },
    {
        "template_name": "水果店商品配送报单统计规则",
        "industry": "水果店",
        "description": "适用于水果店的商品配送管理，支持时令水果、进口水果、包装礼盒的智能识别与统计。支持批量圈选和增量操作。",
        "parse_rules": [
            {"rule_name": "标准数量+单位+商品", "rule_type": "regex", "pattern": "(\\d+(?:\\.\\d+)?)\\s*(斤|两|kg|公斤|箱|个|盒)(.+?)(?:，|,|$)", "priority": 10, "is_active": True, "description": "匹配标准格式：10斤苹果、5箱橙子"},
            {"rule_name": "常见水果", "rule_type": "keyword", "pattern": "苹果|香蕉|橙子|葡萄|西瓜|草莓|梨|桃子|芒果", "priority": 9, "is_active": True, "description": "快速识别常见水果"},
            {"rule_name": "进口水果", "rule_type": "keyword", "pattern": "车厘子|榴莲|山竹|牛油果|蓝莓|奇异果", "priority": 8, "is_active": True, "description": "识别进口水果"},
            {"rule_name": "礼盒装", "rule_type": "keyword", "pattern": "礼盒|礼篮|精装|礼品装", "priority": 7, "is_active": True, "description": "识别礼盒装商品"},
            {"rule_name": "品质备注", "rule_type": "regex", "pattern": "(要甜的|大的|小的|熟的|硬的)", "priority": 6, "is_active": True, "description": "提取品质要求"},
            {"rule_name": "批量圈选支持", "rule_type": "custom", "pattern": "下单 1-10 5斤 | 圈选 1,3,5-8 10斤", "priority": 9, "is_active": True, "description": "支持批量圈选语法"},
            {"rule_name": "增量操作支持", "rule_type": "custom", "pattern": "苹果+10斤 | 橙子-5箱 | 草莓=20盒", "priority": 9, "is_active": True, "description": "支持增量修改"}
        ],
        "stat_rules": [
            {"rule_name": "日采购汇总", "stat_type": "daily", "chart_type": "bar", "refresh_interval": 3600, "is_active": True, "description": "统计当日所有水果采购总量"},
            {"rule_name": "周销量趋势", "stat_type": "weekly", "chart_type": "line", "refresh_interval": 3600, "is_active": True, "description": "近7天水果销量变化趋势"},
            {"rule_name": "水果类别占比", "stat_type": "weekly", "chart_type": "pie", "refresh_interval": 3600, "is_active": True, "description": "按类别统计：国产、进口、礼盒占比"},
            {"rule_name": "月度消耗分析", "stat_type": "monthly", "chart_type": "line", "refresh_interval": 86400, "is_active": True, "description": "近30天主要水果消耗对比"},
            {"rule_name": "TOP水果排行", "stat_type": "monthly", "chart_type": "bar", "refresh_interval": 86400, "is_active": True, "description": "月度销量最多的TOP10水果"}
        ],
        "reply_rules": [
            {"rule_name": "欢迎语", "trigger_type": "keyword", "trigger_content": "你好|您好|help|帮助", "reply_content": "您好！欢迎使用水果店配送系统。\n\n📋 下单示例：\n• 苹果10斤，橙子5箱\n• 车厘子2盒，要甜的\n• 下单 1-10 5斤（批量圈选）\n• 苹果+3斤（增量添加）\n\n💡 发送水果清单即可自动识别~", "priority": 10, "is_active": True, "description": "新用户引导"},
            {"rule_name": "接单确认", "trigger_type": "keyword", "trigger_content": "已下单|提交|确认", "reply_content": "✅ 收到！您的订单已记录。\n\n⏰ 今晚20:00截单\n🚚 明早配送到店\n\n如有疑问请联系客服", "priority": 10, "is_active": True, "description": "订单确认回复"},
            {"rule_name": "价格查询", "trigger_type": "keyword", "trigger_content": "价格|报价|多少钱", "reply_content": "📊 今日报价单已生成\n\n请点击链接查看：[今日报价](http://xxx.com/price)\n\n💡 大批量订购可享优惠", "priority": 8, "is_active": True, "description": "价格查询"},
            {"rule_name": "时令推荐", "trigger_type": "keyword", "trigger_content": "推荐|当季|时令", "reply_content": "🍎 当前时令水果推荐：\n• 春季：草莓、樱桃、菠萝\n• 夏季：西瓜、桃子、葡萄\n• 秋季：苹果、梨、柿子\n• 冬季：橙子、柚子、甘蔗\n\n时令水果更新鲜、更实惠~", "priority": 7, "is_active": True, "description": "时令水果推荐"}
        ],
        "source_type": "official",
        "is_featured": False
    },
    {
        "template_name": "便利店商品配送报单统计规则",
        "industry": "便利店",
        "description": "适用于便利店的商品配送管理，支持饮料零食、日用品、烟酒等商品的智能识别与统计。支持批量圈选和增量操作。",
        "parse_rules": [
            {"rule_name": "标准数量+单位+商品", "rule_type": "regex", "pattern": "(\\d+(?:\\.\\d+)?)\\s*(瓶|箱|袋|包|条|个)(.+?)(?:，|,|$)", "priority": 10, "is_active": True, "description": "匹配标准格式：10瓶可乐、5箱薯片"},
            {"rule_name": "饮料类", "rule_type": "keyword", "pattern": "可乐|雪碧|矿泉水|果汁|茶饮料|功能饮料", "priority": 9, "is_active": True, "description": "快速识别饮料类商品"},
            {"rule_name": "零食类", "rule_type": "keyword", "pattern": "薯片|饼干|巧克力|糖果|瓜子|坚果", "priority": 8, "is_active": True, "description": "识别零食类商品"},
            {"rule_name": "日用品", "rule_type": "keyword", "pattern": "纸巾|洗发水|沐浴露|牙膏|洗衣液", "priority": 7, "is_active": True, "description": "识别日用品"},
            {"rule_name": "批量圈选支持", "rule_type": "custom", "pattern": "下单 1-10 5瓶 | 圈选 1,3,5-8 10瓶", "priority": 9, "is_active": True, "description": "支持批量圈选语法"},
            {"rule_name": "增量操作支持", "rule_type": "custom", "pattern": "可乐+10瓶 | 薯片-5箱 | 纸巾=20袋", "priority": 9, "is_active": True, "description": "支持增量修改"}
        ],
        "stat_rules": [
            {"rule_name": "日采购汇总", "stat_type": "daily", "chart_type": "bar", "refresh_interval": 3600, "is_active": True, "description": "统计当日所有商品采购总量"},
            {"rule_name": "周销量趋势", "stat_type": "weekly", "chart_type": "line", "refresh_interval": 3600, "is_active": True, "description": "近7天商品销量变化趋势"},
            {"rule_name": "商品类别占比", "stat_type": "weekly", "chart_type": "pie", "refresh_interval": 3600, "is_active": True, "description": "按类别统计：饮料、零食、日用品占比"},
            {"rule_name": "月度消耗分析", "stat_type": "monthly", "chart_type": "line", "refresh_interval": 86400, "is_active": True, "description": "近30天主要商品消耗对比"}
        ],
        "reply_rules": [
            {"rule_name": "欢迎语", "trigger_type": "keyword", "trigger_content": "你好|您好|help|帮助", "reply_content": "您好！欢迎使用便利店配送系统。\n\n📋 下单示例：\n• 可乐10瓶，薯片5箱\n• 纸巾2袋\n• 下单 1-10 5瓶（批量圈选）\n• 可乐+3瓶（增量添加）\n\n💡 发送商品清单即可自动识别~", "priority": 10, "is_active": True, "description": "新用户引导"},
            {"rule_name": "接单确认", "trigger_type": "keyword", "trigger_content": "已下单|提交|确认", "reply_content": "✅ 收到！您的订单已记录。\n\n⏰ 今晚22:00截单\n🚚 明早配送到店\n\n如有疑问请联系客服", "priority": 10, "is_active": True, "description": "订单确认回复"},
            {"rule_name": "价格查询", "trigger_type": "keyword", "trigger_content": "价格|报价|多少钱", "reply_content": "📊 今日报价单已生成\n\n请点击链接查看：[今日报价](http://xxx.com/price)\n\n💡 大批量订购可享优惠", "priority": 8, "is_active": True, "description": "价格查询"}
        ],
        "source_type": "official",
        "is_featured": False
    },
    {
        "template_name": "快餐店食材配送报单统计规则",
        "industry": "快餐店",
        "description": "适用于快餐店的食材配送管理，支持半成品食材、包装盒、一次性餐具的智能识别与统计。支持批量圈选和增量操作。",
        "parse_rules": [
            {"rule_name": "标准数量+单位+商品", "rule_type": "regex", "pattern": "(\\d+(?:\\.\\d+)?)\\s*(斤|两|kg|公斤|箱|包|个)(.+?)(?:，|,|$)", "priority": 10, "is_active": True, "description": "匹配标准格式：10斤鸡排、5箱餐盒"},
            {"rule_name": "半成品食材", "rule_type": "keyword", "pattern": "鸡排|鸡腿|鸡翅|薯条|洋葱圈|汉堡肉", "priority": 9, "is_active": True, "description": "快速识别半成品食材"},
            {"rule_name": "包装材料", "rule_type": "keyword", "pattern": "餐盒|打包袋|纸杯|吸管|餐巾纸", "priority": 8, "is_active": True, "description": "识别包装材料"},
            {"rule_name": "蔬菜配料", "rule_type": "keyword", "pattern": "生菜|西红柿|黄瓜|洋葱|酸黄瓜", "priority": 7, "is_active": True, "description": "识别蔬菜配料"},
            {"rule_name": "批量圈选支持", "rule_type": "custom", "pattern": "下单 1-10 5斤 | 圈选 1,3,5-8 10斤", "priority": 9, "is_active": True, "description": "支持批量圈选语法"},
            {"rule_name": "增量操作支持", "rule_type": "custom", "pattern": "鸡排+10斤 | 餐盒-5箱 | 薯条=20包", "priority": 9, "is_active": True, "description": "支持增量修改"}
        ],
        "stat_rules": [
            {"rule_name": "日采购汇总", "stat_type": "daily", "chart_type": "bar", "refresh_interval": 3600, "is_active": True, "description": "统计当日所有商品采购总量"},
            {"rule_name": "周销量趋势", "stat_type": "weekly", "chart_type": "line", "refresh_interval": 3600, "is_active": True, "description": "近7天商品销量变化趋势"},
            {"rule_name": "商品类别占比", "stat_type": "weekly", "chart_type": "pie", "refresh_interval": 3600, "is_active": True, "description": "按类别统计：食材、包材、配料占比"},
            {"rule_name": "月度消耗分析", "stat_type": "monthly", "chart_type": "line", "refresh_interval": 86400, "is_active": True, "description": "近30天主要商品消耗对比"}
        ],
        "reply_rules": [
            {"rule_name": "欢迎语", "trigger_type": "keyword", "trigger_content": "你好|您好|help|帮助", "reply_content": "您好！欢迎使用快餐店配送系统。\n\n📋 下单示例：\n• 鸡排10斤，餐盒5箱\n• 薯条8包\n• 下单 1-10 5斤（批量圈选）\n• 鸡排+3斤（增量添加）\n\n💡 发送商品清单即可自动识别~", "priority": 10, "is_active": True, "description": "新用户引导"},
            {"rule_name": "接单确认", "trigger_type": "keyword", "trigger_content": "已下单|提交|确认", "reply_content": "✅ 收到！您的订单已记录。\n\n⏰ 今晚21:00截单\n🚚 明早配送到店\n\n如有疑问请联系客服", "priority": 10, "is_active": True, "description": "订单确认回复"},
            {"rule_name": "价格查询", "trigger_type": "keyword", "trigger_content": "价格|报价|多少钱", "reply_content": "📊 今日报价单已生成\n\n请点击链接查看：[今日报价](http://xxx.com/price)\n\n💡 大批量订购可享优惠", "priority": 8, "is_active": True, "description": "价格查询"}
        ],
        "source_type": "official",
        "is_featured": False
    },
    {
        "template_name": "烧烤店食材配送报单统计规则",
        "industry": "烧烤店",
        "description": "适用于烧烤店的食材配送管理，支持肉类串品、炭火、调料的智能识别与统计。支持批量圈选和增量操作。",
        "parse_rules": [
            {"rule_name": "标准数量+单位+商品", "rule_type": "regex", "pattern": "(\\d+(?:\\.\\d+)?)\\s*(斤|两|kg|公斤|串|箱|包)(.+?)(?:，|,|$)", "priority": 10, "is_active": True, "description": "匹配标准格式：10斤羊肉、5箱炭火"},
            {"rule_name": "肉类串品", "rule_type": "keyword", "pattern": "羊肉串|牛肉串|鸡翅|五花肉|排骨|鱿鱼", "priority": 9, "is_active": True, "description": "快速识别肉类串品"},
            {"rule_name": "素菜类", "rule_type": "keyword", "pattern": "茄子|韭菜|土豆|玉米|青椒|金针菇", "priority": 8, "is_active": True, "description": "识别烧烤素菜"},
            {"rule_name": "炭火调料", "rule_type": "keyword", "pattern": "炭火|木炭|孜然|辣椒面|芝麻|烧烤酱", "priority": 7, "is_active": True, "description": "识别炭火和调料"},
            {"rule_name": "批量圈选支持", "rule_type": "custom", "pattern": "下单 1-10 5斤 | 圈选 1,3,5-8 10斤", "priority": 9, "is_active": True, "description": "支持批量圈选语法"},
            {"rule_name": "增量操作支持", "rule_type": "custom", "pattern": "羊肉+10斤 | 炭火-5箱 | 鸡翅=20串", "priority": 9, "is_active": True, "description": "支持增量修改"}
        ],
        "stat_rules": [
            {"rule_name": "日采购汇总", "stat_type": "daily", "chart_type": "bar", "refresh_interval": 3600, "is_active": True, "description": "统计当日所有商品采购总量"},
            {"rule_name": "周销量趋势", "stat_type": "weekly", "chart_type": "line", "refresh_interval": 3600, "is_active": True, "description": "近7天商品销量变化趋势"},
            {"rule_name": "商品类别占比", "stat_type": "weekly", "chart_type": "pie", "refresh_interval": 3600, "is_active": True, "description": "按类别统计：肉类、素菜、调料占比"},
            {"rule_name": "月度消耗分析", "stat_type": "monthly", "chart_type": "line", "refresh_interval": 86400, "is_active": True, "description": "近30天主要商品消耗对比"}
        ],
        "reply_rules": [
            {"rule_name": "欢迎语", "trigger_type": "keyword", "trigger_content": "你好|您好|help|帮助", "reply_content": "您好！欢迎使用烧烤店配送系统。\n\n📋 下单示例：\n• 羊肉串10斤，炭火5箱\n• 鸡翅8串\n• 下单 1-10 5斤（批量圈选）\n• 羊肉+3斤（增量添加）\n\n💡 发送商品清单即可自动识别~", "priority": 10, "is_active": True, "description": "新用户引导"},
            {"rule_name": "接单确认", "trigger_type": "keyword", "trigger_content": "已下单|提交|确认", "reply_content": "✅ 收到！您的订单已记录。\n\n⏰ 今晚20:00截单\n🚚 明早配送到店\n\n如有疑问请联系客服", "priority": 10, "is_active": True, "description": "订单确认回复"},
            {"rule_name": "价格查询", "trigger_type": "keyword", "trigger_content": "价格|报价|多少钱", "reply_content": "📊 今日报价单已生成\n\n请点击链接查看：[今日报价](http://xxx.com/price)\n\n💡 大批量订购可享优惠", "priority": 8, "is_active": True, "description": "价格查询"}
        ],
        "source_type": "official",
        "is_featured": False
    },
    {
        "template_name": "日料店食材配送报单统计规则",
        "industry": "日料店",
        "description": "适用于日料店的食材配送管理，支持海鲜、寿司材料、日式调料的智能识别与统计。支持批量圈选和增量操作。",
        "parse_rules": [
            {"rule_name": "标准数量+单位+商品", "rule_type": "regex", "pattern": "(\\d+(?:\\.\\d+)?)\\s*(斤|两|kg|公斤|盒|包|瓶)(.+?)(?:，|,|$)", "priority": 10, "is_active": True, "description": "匹配标准格式：10斤三文鱼、5盒海苔"},
            {"rule_name": "海鲜类", "rule_type": "keyword", "pattern": "三文鱼|金枪鱼|甜虾|北极贝|章鱼|鳗鱼", "priority": 9, "is_active": True, "description": "快速识别海鲜类食材"},
            {"rule_name": "寿司材料", "rule_type": "keyword", "pattern": "海苔|寿司米|醋|芥末|酱油|姜", "priority": 8, "is_active": True, "description": "识别寿司材料"},
            {"rule_name": "日式调料", "rule_type": "keyword", "pattern": "味淋|清酒|味噌|出汁|照烧酱", "priority": 7, "is_active": True, "description": "识别日式调料"},
            {"rule_name": "新鲜度备注", "rule_type": "regex", "pattern": "(要新鲜的|刺身级|冰鲜|活的)", "priority": 6, "is_active": True, "description": "提取新鲜度要求"},
            {"rule_name": "批量圈选支持", "rule_type": "custom", "pattern": "下单 1-10 5斤 | 圈选 1,3,5-8 10斤", "priority": 9, "is_active": True, "description": "支持批量圈选语法"},
            {"rule_name": "增量操作支持", "rule_type": "custom", "pattern": "三文鱼+10斤 | 海苔-5盒 | 甜虾=20盒", "priority": 9, "is_active": True, "description": "支持增量修改"}
        ],
        "stat_rules": [
            {"rule_name": "日采购汇总", "stat_type": "daily", "chart_type": "bar", "refresh_interval": 3600, "is_active": True, "description": "统计当日所有商品采购总量"},
            {"rule_name": "周销量趋势", "stat_type": "weekly", "chart_type": "line", "refresh_interval": 3600, "is_active": True, "description": "近7天商品销量变化趋势"},
            {"rule_name": "商品类别占比", "stat_type": "weekly", "chart_type": "pie", "refresh_interval": 3600, "is_active": True, "description": "按类别统计：海鲜、寿司材料、调料占比"},
            {"rule_name": "月度消耗分析", "stat_type": "monthly", "chart_type": "line", "refresh_interval": 86400, "is_active": True, "description": "近30天主要商品消耗对比"}
        ],
        "reply_rules": [
            {"rule_name": "欢迎语", "trigger_type": "keyword", "trigger_content": "你好|您好|help|帮助", "reply_content": "您好！欢迎使用日料店配送系统。\n\n📋 下单示例：\n• 三文鱼10斤，海苔5盒\n• 甜虾8盒，要刺身级的\n• 下单 1-10 5斤（批量圈选）\n• 三文鱼+3斤（增量添加）\n\n💡 发送商品清单即可自动识别~", "priority": 10, "is_active": True, "description": "新用户引导"},
            {"rule_name": "接单确认", "trigger_type": "keyword", "trigger_content": "已下单|提交|确认", "reply_content": "✅ 收到！您的订单已记录。\n\n⏰ 今晚19:00截单\n🚚 明早配送到店\n\n如有疑问请联系客服", "priority": 10, "is_active": True, "description": "订单确认回复"},
            {"rule_name": "价格查询", "trigger_type": "keyword", "trigger_content": "价格|报价|多少钱", "reply_content": "📊 今日报价单已生成\n\n请点击链接查看：[今日报价](http://xxx.com/price)\n\n💡 大批量订购可享优惠", "priority": 8, "is_active": True, "description": "价格查询"},
            {"rule_name": "新鲜度保证", "trigger_type": "keyword", "trigger_content": "新鲜|品质", "reply_content": "🐟 我们保证所有海鲜：\n• 空运直达，24小时内送达\n• 刺身级品质，严格检验\n• 冷链配送，保证新鲜\n\n请放心订购~", "priority": 7, "is_active": True, "description": "新鲜度保证说明"}
        ],
        "source_type": "official",
        "is_featured": False
    },
    {
        "template_name": "西餐厅食材配送报单统计规则",
        "industry": "西餐厅",
        "description": "适用于西餐厅的食材配送管理，支持牛排、意面、奶酪、红酒等西式食材的智能识别与统计。支持批量圈选和增量操作。",
        "parse_rules": [
            {"rule_name": "标准数量+单位+商品", "rule_type": "regex", "pattern": "(\\d+(?:\\.\\d+)?)\\s*(斤|两|kg|公斤|瓶|盒|包)(.+?)(?:，|,|$)", "priority": 10, "is_active": True, "description": "匹配标准格式：10斤牛排、5瓶红酒"},
            {"rule_name": "肉类", "rule_type": "keyword", "pattern": "牛排|羊排|猪排|鸡胸肉|培根|香肠", "priority": 9, "is_active": True, "description": "快速识别西式肉类"},
            {"rule_name": "主食类", "rule_type": "keyword", "pattern": "意面|通心粉|披萨饼底|面包|吐司", "priority": 8, "is_active": True, "description": "识别西式主食"},
            {"rule_name": "奶制品", "rule_type": "keyword", "pattern": "奶酪|奶油|黄油|牛奶|酸奶", "priority": 7, "is_active": True, "description": "识别奶制品"},
            {"rule_name": "酒水", "rule_type": "keyword", "pattern": "红酒|白酒|香槟|啤酒", "priority": 7, "is_active": True, "description": "识别酒水类"},
            {"rule_name": "批量圈选支持", "rule_type": "custom", "pattern": "下单 1-10 5斤 | 圈选 1,3,5-8 10斤", "priority": 9, "is_active": True, "description": "支持批量圈选语法"},
            {"rule_name": "增量操作支持", "rule_type": "custom", "pattern": "牛排+10斤 | 红酒-5瓶 | 意面=20包", "priority": 9, "is_active": True, "description": "支持增量修改"}
        ],
        "stat_rules": [
            {"rule_name": "日采购汇总", "stat_type": "daily", "chart_type": "bar", "refresh_interval": 3600, "is_active": True, "description": "统计当日所有商品采购总量"},
            {"rule_name": "周销量趋势", "stat_type": "weekly", "chart_type": "line", "refresh_interval": 3600, "is_active": True, "description": "近7天商品销量变化趋势"},
            {"rule_name": "商品类别占比", "stat_type": "weekly", "chart_type": "pie", "refresh_interval": 3600, "is_active": True, "description": "按类别统计：肉类、主食、奶制品、酒水占比"},
            {"rule_name": "月度消耗分析", "stat_type": "monthly", "chart_type": "line", "refresh_interval": 86400, "is_active": True, "description": "近30天主要商品消耗对比"}
        ],
        "reply_rules": [
            {"rule_name": "欢迎语", "trigger_type": "keyword", "trigger_content": "你好|您好|help|帮助", "reply_content": "您好！欢迎使用西餐厅配送系统。\n\n📋 下单示例：\n• 牛排10斤，红酒5瓶\n• 意面8包\n• 下单 1-10 5斤（批量圈选）\n• 牛排+3斤（增量添加）\n\n💡 发送商品清单即可自动识别~", "priority": 10, "is_active": True, "description": "新用户引导"},
            {"rule_name": "接单确认", "trigger_type": "keyword", "trigger_content": "已下单|提交|确认", "reply_content": "✅ 收到！您的订单已记录。\n\n⏰ 今晚20:00截单\n🚚 明早配送到店\n\n如有疑问请联系客服", "priority": 10, "is_active": True, "description": "订单确认回复"},
            {"rule_name": "价格查询", "trigger_type": "keyword", "trigger_content": "价格|报价|多少钱", "reply_content": "📊 今日报价单已生成\n\n请点击链接查看：[今日报价](http://xxx.com/price)\n\n💡 大批量订购可享优惠", "priority": 8, "is_active": True, "description": "价格查询"}
        ],
        "source_type": "official",
        "is_featured": False
    },
    {
        "template_name": "咖啡店原料配送报单统计规则",
        "industry": "咖啡店",
        "description": "适用于咖啡店的原料配送管理，支持咖啡豆、牛奶、糖浆、纸杯等原料的智能识别与统计。支持批量圈选和增量操作。",
        "parse_rules": [
            {"rule_name": "标准数量+单位+商品", "rule_type": "regex", "pattern": "(\\d+(?:\\.\\d+)?)\\s*(袋|箱|桶|瓶|包|个)(.+?)(?:，|,|$)", "priority": 10, "is_active": True, "description": "匹配标准格式：10袋咖啡豆、5箱牛奶"},
            {"rule_name": "咖啡豆", "rule_type": "keyword", "pattern": "咖啡豆|咖啡粉|意式拼配|单品豆", "priority": 9, "is_active": True, "description": "快速识别咖啡类产品"},
            {"rule_name": "奶制品", "rule_type": "keyword", "pattern": "牛奶|鲜奶|燕麦奶|杏仁奶|奶油", "priority": 8, "is_active": True, "description": "识别奶制品"},
            {"rule_name": "糖浆调味", "rule_type": "keyword", "pattern": "香草糖浆|焦糖糖浆|榛果糖浆|巧克力酱", "priority": 7, "is_active": True, "description": "识别糖浆和调味品"},
            {"rule_name": "包材类", "rule_type": "keyword", "pattern": "纸杯|杯盖|吸管|搅拌棒|打包袋", "priority": 7, "is_active": True, "description": "识别包装材料"},
            {"rule_name": "批量圈选支持", "rule_type": "custom", "pattern": "下单 1-10 5袋 | 圈选 1,3,5-8 10袋", "priority": 9, "is_active": True, "description": "支持批量圈选语法"},
            {"rule_name": "增量操作支持", "rule_type": "custom", "pattern": "咖啡豆+10袋 | 牛奶-5箱 | 纸杯=20箱", "priority": 9, "is_active": True, "description": "支持增量修改"}
        ],
        "stat_rules": [
            {"rule_name": "日原料汇总", "stat_type": "daily", "chart_type": "bar", "refresh_interval": 3600, "is_active": True, "description": "统计当日所有原料采购总量"},
            {"rule_name": "周销量趋势", "stat_type": "weekly", "chart_type": "line", "refresh_interval": 3600, "is_active": True, "description": "近7天原料销量变化趋势"},
            {"rule_name": "原料类别占比", "stat_type": "weekly", "chart_type": "pie", "refresh_interval": 3600, "is_active": True, "description": "按类别统计：咖啡、奶制品、糖浆、包材占比"},
            {"rule_name": "月度消耗分析", "stat_type": "monthly", "chart_type": "line", "refresh_interval": 86400, "is_active": True, "description": "近30天主要原料消耗对比"}
        ],
        "reply_rules": [
            {"rule_name": "欢迎语", "trigger_type": "keyword", "trigger_content": "你好|您好|help|帮助", "reply_content": "您好！欢迎使用咖啡店配送系统。\n\n📋 下单示例：\n• 咖啡豆10袋，牛奶5箱\n• 纸杯2箱\n• 下单 1-10 5袋（批量圈选）\n• 咖啡豆+3袋（增量添加）\n\n💡 发送原料清单即可自动识别~", "priority": 10, "is_active": True, "description": "新用户引导"},
            {"rule_name": "接单确认", "trigger_type": "keyword", "trigger_content": "已下单|提交|确认", "reply_content": "✅ 收到！您的订单已记录。\n\n⏰ 今晚21:00截单\n🚚 明早配送到店\n\n如有疑问请联系客服", "priority": 10, "is_active": True, "description": "订单确认回复"},
            {"rule_name": "价格查询", "trigger_type": "keyword", "trigger_content": "价格|报价|多少钱", "reply_content": "📊 今日报价单已生成\n\n请点击链接查看：[今日报价](http://xxx.com/price)\n\n💡 大批量订购可享优惠", "priority": 8, "is_active": True, "description": "价格查询"}
        ],
        "source_type": "official",
        "is_featured": False
    },
    {
        "template_name": "文具办公用品配送报单统计规则",
        "industry": "文具办公",
        "description": "适用于文具店和办公用品配送管理，支持笔类、纸张、文件夹等办公文具的智能识别与统计。支持批量圈选和增量操作。",
        "parse_rules": [
            {"rule_name": "标准数量+单位+商品", "rule_type": "regex", "pattern": "(\\d+(?:\\.\\d+)?)\\s*(盒|箱|包|本|支|个)(.+?)(?:，|,|$)", "priority": 10, "is_active": True, "description": "匹配标准格式：10盒笔、5箱纸"},
            {"rule_name": "笔类", "rule_type": "keyword", "pattern": "圆珠笔|中性笔|钢笔|铅笔|马克笔|荧光笔", "priority": 9, "is_active": True, "description": "快速识别笔类商品"},
            {"rule_name": "纸张类", "rule_type": "keyword", "pattern": "A4纸|复印纸|打印纸|笔记本|便签纸", "priority": 8, "is_active": True, "description": "识别纸张类商品"},
            {"rule_name": "文件收纳", "rule_type": "keyword", "pattern": "文件夹|档案袋|文件柜|收纳盒", "priority": 7, "is_active": True, "description": "识别文件收纳用品"},
            {"rule_name": "批量圈选支持", "rule_type": "custom", "pattern": "下单 1-10 5盒 | 圈选 1,3,5-8 10盒", "priority": 9, "is_active": True, "description": "支持批量圈选语法"},
            {"rule_name": "增量操作支持", "rule_type": "custom", "pattern": "笔+10盒 | 纸-5箱 | 文件夹=20个", "priority": 9, "is_active": True, "description": "支持增量修改"}
        ],
        "stat_rules": [
            {"rule_name": "日采购汇总", "stat_type": "daily", "chart_type": "bar", "refresh_interval": 3600, "is_active": True, "description": "统计当日所有商品采购总量"},
            {"rule_name": "周销量趋势", "stat_type": "weekly", "chart_type": "line", "refresh_interval": 3600, "is_active": True, "description": "近7天商品销量变化趋势"},
            {"rule_name": "商品类别占比", "stat_type": "weekly", "chart_type": "pie", "refresh_interval": 3600, "is_active": True, "description": "按类别统计：笔类、纸张、收纳占比"},
            {"rule_name": "月度消耗分析", "stat_type": "monthly", "chart_type": "line", "refresh_interval": 86400, "is_active": True, "description": "近30天主要商品消耗对比"}
        ],
        "reply_rules": [
            {"rule_name": "欢迎语", "trigger_type": "keyword", "trigger_content": "你好|您好|help|帮助", "reply_content": "您好！欢迎使用文具办公用品配送系统。\n\n📋 下单示例：\n• 圆珠笔10盒，A4纸5箱\n• 文件夹8个\n• 下单 1-10 5盒（批量圈选）\n• 笔+3盒（增量添加）\n\n💡 发送商品清单即可自动识别~", "priority": 10, "is_active": True, "description": "新用户引导"},
            {"rule_name": "接单确认", "trigger_type": "keyword", "trigger_content": "已下单|提交|确认", "reply_content": "✅ 收到！您的订单已记录。\n\n⏰ 今晚20:00截单\n🚚 明早配送到店\n\n如有疑问请联系客服", "priority": 10, "is_active": True, "description": "订单确认回复"},
            {"rule_name": "价格查询", "trigger_type": "keyword", "trigger_content": "价格|报价|多少钱", "reply_content": "📊 今日报价单已生成\n\n请点击链接查看：[今日报价](http://xxx.com/price)\n\n💡 大批量订购可享优惠", "priority": 8, "is_active": True, "description": "价格查询"}
        ],
        "source_type": "official",
        "is_featured": False
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
