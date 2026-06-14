"""
插件市场初始化数据脚本
在数据库中预先添加各行业插件的元数据
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_config import get_db_session, init_db
from models.plugin_models import PluginPackage, PluginVersion
from sqlalchemy import text


def init_core_plugins(db):
    """初始化核心插件"""
    core_plugins = [
        {
            'plugin_code': 'core',
            'plugin_name': '核心功能插件',
            'description': '订单解析、消息捕获、规则引擎、报表生成等核心功能',
            'short_description': '系统核心功能模块',
            'category': 'core',
            'industry': '',
            'icon_url': '',
            'tags': '核心,必需,基础',
            'compatibility': '1.0+',
            'is_public': True,
            'is_featured': True,
            'is_active': True,
            'is_deprecated': False,
            'versions': [
                {
                    'version': '1.0.0',
                    'changelog': '初始版本',
                    'download_url': '',
                    'file_size': 0,
                    'dependencies': '[]',
                    'required_permissions': 'all',
                    'is_stable': True,
                    'is_active': True
                }
            ]
        },
        {
            'plugin_code': 'wechat',
            'plugin_name': '微信插件',
            'description': '微信消息捕获、自动回复、群管理等微信相关功能',
            'short_description': '微信集成模块',
            'category': 'tool',
            'industry': '',
            'icon_url': '',
            'tags': '微信,消息,群管理',
            'compatibility': '1.0+',
            'is_public': True,
            'is_featured': True,
            'is_active': True,
            'is_deprecated': False,
            'versions': [
                {
                    'version': '1.0.0',
                    'changelog': '初始版本',
                    'download_url': '',
                    'file_size': 0,
                    'dependencies': '[{"plugin_code": "core", "min_version": "1.0.0"}]',
                    'required_permissions': 'message_read,message_send',
                    'is_stable': True,
                    'is_active': True
                }
            ]
        },
        {
            'plugin_code': 'excel',
            'plugin_name': 'Excel报表插件',
            'description': '多格式报表导出、邮件自动发送、数据分析',
            'short_description': '报表导出模块',
            'category': 'tool',
            'industry': '',
            'icon_url': '',
            'tags': '报表,Excel,邮件',
            'compatibility': '1.0+',
            'is_public': True,
            'is_featured': True,
            'is_active': True,
            'is_deprecated': False,
            'versions': [
                {
                    'version': '1.0.0',
                    'changelog': '初始版本',
                    'download_url': '',
                    'file_size': 0,
                    'dependencies': '[{"plugin_code": "core", "min_version": "1.0.0"}]',
                    'required_permissions': 'report_export,email_send',
                    'is_stable': True,
                    'is_active': True
                }
            ]
        }
    ]

    for plugin_data in core_plugins:
        existing = db.query(PluginPackage).filter(
            PluginPackage.plugin_code == plugin_data['plugin_code']
        ).first()
        
        if existing:
            print(f"核心插件已存在: {plugin_data['plugin_name']}")
            continue

        plugin = PluginPackage(**{k: v for k, v in plugin_data.items() if k != 'versions'})
        db.add(plugin)
        db.commit()
        db.refresh(plugin)

        for version_data in plugin_data['versions']:
            version = PluginVersion(package_id=plugin.id, **version_data)
            db.add(version)

        db.commit()
        print(f"核心插件创建成功: {plugin_data['plugin_name']}")


def init_industry_plugins(db):
    """初始化行业插件"""
    industry_plugins = [
        {
            'plugin_code': 'seafood',
            'plugin_name': '海鲜批发插件',
            'description': '客户订单管理、急单处理、截单提醒、供应商管理、业务报表等海鲜批发行业专属功能',
            'short_description': '海鲜批发行业解决方案',
            'category': 'industry',
            'industry': 'seafood',
            'icon_url': '',
            'tags': '海鲜,订单,报表,批发',
            'compatibility': '1.0+',
            'is_public': True,
            'is_featured': True,
            'is_active': True,
            'is_deprecated': False,
            'versions': [
                {
                    'version': '1.0.0',
                    'changelog': '初始版本',
                    'download_url': '',
                    'file_size': 0,
                    'dependencies': '[{"plugin_code": "core", "min_version": "1.0.0"}, {"plugin_code": "wechat", "min_version": "1.0.0"}, {"plugin_code": "excel", "min_version": "1.0.0"}]',
                    'required_permissions': 'order_manage,customer_manage,supplier_manage,report_view',
                    'is_stable': True,
                    'is_active': True
                }
            ]
        },
        {
            'plugin_code': 'fooddelivery',
            'plugin_name': '餐饮配送插件',
            'description': '商品管理、订单处理、桌台管理、促销活动、销售报表等餐饮配送行业专属功能',
            'short_description': '餐饮配送行业解决方案',
            'category': 'industry',
            'industry': 'fooddelivery',
            'icon_url': '',
            'tags': '餐饮,配送,订单,促销',
            'compatibility': '1.0+',
            'is_public': True,
            'is_featured': True,
            'is_active': True,
            'is_deprecated': False,
            'versions': [
                {
                    'version': '1.0.0',
                    'changelog': '初始版本',
                    'download_url': '',
                    'file_size': 0,
                    'dependencies': '[{"plugin_code": "core", "min_version": "1.0.0"}, {"plugin_code": "wechat", "min_version": "1.0.0"}, {"plugin_code": "excel", "min_version": "1.0.0"}]',
                    'required_permissions': 'order_manage,product_manage,promotion_manage,report_view',
                    'is_stable': True,
                    'is_active': True
                }
            ]
        },
        {
            'plugin_code': 'education',
            'plugin_name': '教育培训插件',
            'description': '课程管理、学员管理、教师管理、学习进度跟踪、数据分析等教育培训行业专属功能',
            'short_description': '教育培训行业解决方案',
            'category': 'industry',
            'industry': 'education',
            'icon_url': '',
            'tags': '教育,课程,学员,教师',
            'compatibility': '1.0+',
            'is_public': True,
            'is_featured': True,
            'is_active': True,
            'is_deprecated': False,
            'versions': [
                {
                    'version': '1.0.0',
                    'changelog': '初始版本',
                    'download_url': '',
                    'file_size': 0,
                    'dependencies': '[{"plugin_code": "core", "min_version": "1.0.0"}, {"plugin_code": "wechat", "min_version": "1.0.0"}, {"plugin_code": "excel", "min_version": "1.0.0"}]',
                    'required_permissions': 'course_manage,student_manage,teacher_manage,report_view',
                    'is_stable': True,
                    'is_active': True
                }
            ]
        },
        {
            'plugin_code': 'realestate',
            'plugin_name': '房产中介插件',
            'description': '房源管理、客户管理、智能匹配、交易流程管理、数据分析等房产中介行业专属功能',
            'short_description': '房产中介行业解决方案',
            'category': 'industry',
            'industry': 'realestate',
            'icon_url': '',
            'tags': '房产,中介,房源,匹配',
            'compatibility': '1.0+',
            'is_public': True,
            'is_featured': True,
            'is_active': True,
            'is_deprecated': False,
            'versions': [
                {
                    'version': '1.0.0',
                    'changelog': '初始版本',
                    'download_url': '',
                    'file_size': 0,
                    'dependencies': '[{"plugin_code": "core", "min_version": "1.0.0"}, {"plugin_code": "wechat", "min_version": "1.0.0"}, {"plugin_code": "excel", "min_version": "1.0.0"}]',
                    'required_permissions': 'property_manage,customer_manage,matching,report_view',
                    'is_stable': True,
                    'is_active': True
                }
            ]
        },
        {
            'plugin_code': 'travel',
            'plugin_name': '旅行社插件',
            'description': '线路管理、群配置、报名处理、日报统计、智能回复等旅行社行业专属功能',
            'short_description': '旅行社行业解决方案',
            'category': 'industry',
            'industry': 'travel',
            'icon_url': '',
            'tags': '旅游,线路,报名,自动回复',
            'compatibility': '1.0+',
            'is_public': True,
            'is_featured': True,
            'is_active': True,
            'is_deprecated': False,
            'versions': [
                {
                    'version': '1.0.0',
                    'changelog': '初始版本',
                    'download_url': '',
                    'file_size': 0,
                    'dependencies': '[{"plugin_code": "core", "min_version": "1.0.0"}, {"plugin_code": "wechat", "min_version": "1.0.0"}, {"plugin_code": "excel", "min_version": "1.0.0"}]',
                    'required_permissions': 'route_manage,group_config,registration,auto_reply',
                    'is_stable': True,
                    'is_active': True
                }
            ]
        },
        {
            'plugin_code': 'construction',
            'plugin_name': '工地管理插件',
            'description': '工人打卡、工期管理、安全检查、材料管理、工作面记录等工地管理行业专属功能',
            'short_description': '工地管理行业解决方案',
            'category': 'industry',
            'industry': 'construction',
            'icon_url': '',
            'tags': '工地,考勤,安全,材料',
            'compatibility': '1.0+',
            'is_public': True,
            'is_featured': True,
            'is_active': True,
            'is_deprecated': False,
            'versions': [
                {
                    'version': '1.0.0',
                    'changelog': '初始版本',
                    'download_url': '',
                    'file_size': 0,
                    'dependencies': '[{"plugin_code": "core", "min_version": "1.0.0"}, {"plugin_code": "wechat", "min_version": "1.0.0"}, {"plugin_code": "excel", "min_version": "1.0.0"}]',
                    'required_permissions': 'worker_manage,schedule_manage,safety_check,material_manage',
                    'is_stable': True,
                    'is_active': True
                }
            ]
        },
        {
            'plugin_code': 'fleet',
            'plugin_name': '车队调度插件',
            'description': '泥土车管理、物流车管理、任务调度、路线规划、维护保养等车队调度行业专属功能',
            'short_description': '车队调度行业解决方案',
            'category': 'industry',
            'industry': 'fleet',
            'icon_url': '',
            'tags': '车队,调度,运输,维护',
            'compatibility': '1.0+',
            'is_public': True,
            'is_featured': True,
            'is_active': True,
            'is_deprecated': False,
            'versions': [
                {
                    'version': '1.0.0',
                    'changelog': '初始版本',
                    'download_url': '',
                    'file_size': 0,
                    'dependencies': '[{"plugin_code": "core", "min_version": "1.0.0"}, {"plugin_code": "wechat", "min_version": "1.0.0"}, {"plugin_code": "excel", "min_version": "1.0.0"}]',
                    'required_permissions': 'fleet_manage,truck_manage,task_dispatch,route_optimize',
                    'is_stable': True,
                    'is_active': True
                }
            ]
        }
    ]

    for plugin_data in industry_plugins:
        existing = db.query(PluginPackage).filter(
            PluginPackage.plugin_code == plugin_data['plugin_code']
        ).first()
        
        if existing:
            print(f"行业插件已存在: {plugin_data['plugin_name']}")
            continue

        plugin = PluginPackage(**{k: v for k, v in plugin_data.items() if k != 'versions'})
        db.add(plugin)
        db.commit()
        db.refresh(plugin)

        for version_data in plugin_data['versions']:
            version = PluginVersion(package_id=plugin.id, **version_data)
            db.add(version)

        db.commit()
        print(f"行业插件创建成功: {plugin_data['plugin_name']}")


def init_future_plugins(db):
    """初始化预留插件（可扩展）"""
    future_plugins = [
        {
            'plugin_code': 'feishu',
            'plugin_name': '飞书插件',
            'description': '飞书消息捕获、飞书机器人对接、企业微信集成',
            'short_description': '飞书集成模块',
            'category': 'tool',
            'industry': '',
            'icon_url': '',
            'tags': '飞书,机器人,企业微信',
            'compatibility': '1.0+',
            'is_public': True,
            'is_featured': False,
            'is_active': False,
            'is_deprecated': False,
            'versions': []
        },
        {
            'plugin_code': 'dingtalk',
            'plugin_name': '钉钉插件',
            'description': '钉钉消息捕获、钉钉机器人对接',
            'short_description': '钉钉集成模块',
            'category': 'tool',
            'industry': '',
            'icon_url': '',
            'tags': '钉钉,机器人',
            'compatibility': '1.0+',
            'is_public': True,
            'is_featured': False,
            'is_active': False,
            'is_deprecated': False,
            'versions': []
        }
    ]

    for plugin_data in future_plugins:
        existing = db.query(PluginPackage).filter(
            PluginPackage.plugin_code == plugin_data['plugin_code']
        ).first()
        
        if existing:
            print(f"预留插件已存在: {plugin_data['plugin_name']}")
            continue

        plugin = PluginPackage(**{k: v for k, v in plugin_data.items() if k != 'versions'})
        db.add(plugin)
        db.commit()
        print(f"预留插件创建成功: {plugin_data['plugin_name']}")


def main():
    """主函数"""
    print("=" * 60)
    print("插件市场初始化数据脚本")
    print("=" * 60)

    try:
        init_db()
        db = get_db_session()

        print("\n1. 初始化核心插件...")
        init_core_plugins(db)

        print("\n2. 初始化行业插件...")
        init_industry_plugins(db)

        print("\n3. 初始化预留插件...")
        init_future_plugins(db)

        print("\n" + "=" * 60)
        print("插件初始化完成！")
        print("=" * 60)

        db.close()
    except Exception as e:
        print(f"\n初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()