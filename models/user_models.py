"""
用户端系统 ORM 模型定义
包含：用户账户、授权码管理、机器人配置、规则配置、团队管理等
"""
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, Float, Numeric, DateTime, Boolean, Text, ForeignKey, Index
from sqlalchemy.types import SMALLINT as TinyInteger
from sqlalchemy.orm import relationship
from database.db_config import Base


class User(Base):
    """用户账户表 - 本地配送商经营者"""
    __tablename__ = 't_user_account'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='用户ID')
    email = Column(String(100), unique=True, nullable=False, index=True, comment='登录邮箱')
    password_hash = Column(String(255), nullable=False, comment='密码哈希')
    username = Column(String(50), comment='用户名/昵称')
    phone = Column(String(20), comment='联系电话')
    company_name = Column(String(100), comment='公司/店铺名称')
    industry = Column(String(50), comment='所属行业')
    role = Column(String(20), default='user', comment='角色: super_admin-超级管理员, admin-管理员, user-普通用户')
    subscription_type = Column(String(20), default='monthly', comment='订阅类型: monthly-月付, yearly-年付')
    subscription_expires_at = Column(DateTime, comment='订阅过期时间')
    max_groups = Column(Integer, default=3, comment='最大允许群数量')
    is_active = Column(Boolean, default=True, comment='账户是否激活')
    last_login_at = Column(DateTime, comment='最后登录时间')
    setup_completed = Column(Boolean, default=False, comment='是否完成安装引导')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关系
    licenses = relationship('License', back_populates='user')
    team_members = relationship('TeamMember', back_populates='user')
    robot_configs = relationship('RobotConfig', back_populates='user')
    parse_rules = relationship('ParseRule', back_populates='user')
    stat_rules = relationship('StatRule', back_populates='user')

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'username': self.username,
            'phone': self.phone,
            'company_name': self.company_name,
            'industry': self.industry,
            'role': self.role,
            'subscription_type': self.subscription_type,
            'subscription_expires_at': self.subscription_expires_at.isoformat() if self.subscription_expires_at else None,
            'max_groups': self.max_groups,
            'is_active': self.is_active,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
            'setup_completed': self.setup_completed
        }

    @property
    def is_subscription_valid(self):
        """检查订阅是否有效"""
        if not self.is_active or not self.subscription_expires_at:
            return False
        return datetime.now() < self.subscription_expires_at

    @property
    def available_groups(self):
        """剩余可用群数量"""
        used_groups = len([lic for lic in self.licenses if lic.is_active])
        return max(0, self.max_groups - used_groups)


class License(Base):
    """授权码表 - 用于群统计功能授权"""
    __tablename__ = 't_license_v2'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='授权ID')
    user_id = Column(Integer, ForeignKey('t_user_account.id'), nullable=False, comment='所属用户ID')
    license_code = Column(String(64), unique=True, nullable=False, index=True, comment='授权码')
    license_type = Column(String(20), default='monthly', comment='授权类型: monthly-月付, yearly-年付')
    bound_to = Column(String(100), comment='绑定的微信群ID')
    assigned_to = Column(Integer, ForeignKey('t_team_member.id'), comment='分配给的销售员ID')
    machine_id = Column(String(64), comment='机器指纹')
    activated_at = Column(DateTime, comment='激活时间')
    expires_at = Column(DateTime, comment='过期时间')
    is_active = Column(Boolean, default=False, comment='是否激活')
    is_revoked = Column(Boolean, default=False, comment='是否已撤销')
    auto_renew = Column(Boolean, default=False, comment='是否自动续费')
    renew_period = Column(String(20), comment='续费周期: 1m-1个月, 3m-3个月, 6m-6个月, 1y-1年')
    last_renewed_at = Column(DateTime, comment='上次续费时间')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关系
    user = relationship('User', back_populates='licenses')
    team_member = relationship('TeamMember', back_populates='assigned_licenses')

    def to_dict(self):
        # 获取销售员信息
        salesperson_info = None
        if self.team_member:
            salesperson_info = {
                'id': self.team_member.id,
                'name': self.team_member.name,
                'phone': self.team_member.phone,
                'wx_id': self.team_member.wx_id
            }
        
        # 获取用户信息
        user_email = None
        if self.user:
            user_email = self.user.email
        
        return {
            'id': self.id,
            'license_code': self.license_code,
            'license_type': self.license_type,
            'bound_to': self.bound_to,
            'assigned_to': self.assigned_to,
            'user_email': user_email,
            'salesperson': salesperson_info,
            'activated_at': self.activated_at.isoformat() if self.activated_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active,
            'is_revoked': self.is_revoked,
            'auto_renew': self.auto_renew,
            'renew_period': self.renew_period,
            'last_renewed_at': self.last_renewed_at.isoformat() if self.last_renewed_at else None,
            'days_remaining': self.days_remaining,
            'machine_id': self.machine_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @property
    def days_remaining(self):
        """剩余天数"""
        if not self.expires_at or self.is_revoked:
            return 0
        delta = self.expires_at - datetime.now()
        return max(0, delta.days)


class TeamMember(Base):
    """团队成员表 - 销售人员"""
    __tablename__ = 't_team_member'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='成员ID')
    user_id = Column(Integer, ForeignKey('t_user_account.id'), nullable=False, comment='所属用户ID')
    name = Column(String(50), nullable=False, comment='销售员姓名')
    phone = Column(String(20), comment='联系电话')
    wx_id = Column(String(64), comment='微信号')
    managed_group_id = Column(String(100), comment='管理的微信群ID')
    position = Column(String(50), comment='职位')
    is_active = Column(Boolean, default=True, comment='是否在职')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关系
    user = relationship('User', back_populates='team_members')
    assigned_licenses = relationship('License', back_populates='team_member')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'wx_id': self.wx_id,
            'managed_group_id': self.managed_group_id,
            'position': self.position,
            'is_active': self.is_active,
            'license_count': len([lic for lic in self.assigned_licenses if lic.is_active])
        }


class RobotConfig(Base):
    """机器人配置表 - 微信Hook配置"""
    __tablename__ = 't_robot_config'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='配置ID')
    user_id = Column(Integer, ForeignKey('t_user_account.id'), nullable=False, comment='所属用户ID')
    config_name = Column(String(50), default='默认机器人', comment='配置名称')
    wechat_path = Column(String(255), comment='微信安装路径')
    wechat_version = Column(String(20), comment='微信版本号')
    hook_dll_path = Column(String(255), comment='Hook DLL路径')
    tcp_server_host = Column(String(50), default='127.0.0.1', comment='TCP服务器地址')
    tcp_server_port = Column(Integer, default=8888, comment='TCP服务器端口')
    auto_start = Column(Boolean, default=False, comment='是否自动启动')
    is_default = Column(Boolean, default=False, comment='是否为默认配置')
    status = Column(String(20), default='stopped', comment='运行状态: stopped-停止, running-运行中, error-错误')
    last_started_at = Column(DateTime, comment='最后启动时间')
    last_error = Column(Text, comment='最后错误信息')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关系
    user = relationship('User', back_populates='robot_configs')
    reply_rules = relationship('ReplyRule', back_populates='robot_config', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'config_name': self.config_name,
            'wechat_path': self.wechat_path,
            'wechat_version': self.wechat_version,
            'hook_dll_path': self.hook_dll_path,
            'tcp_server_host': self.tcp_server_host,
            'tcp_server_port': self.tcp_server_port,
            'auto_start': self.auto_start,
            'is_default': self.is_default,
            'status': self.status,
            'last_started_at': self.last_started_at.isoformat() if self.last_started_at else None,
            'last_error': self.last_error
        }


class ReplyRule(Base):
    """自动回复规则表"""
    __tablename__ = 't_reply_rule'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='规则ID')
    robot_config_id = Column(Integer, ForeignKey('t_robot_config.id'), nullable=False, comment='所属机器人配置ID')
    rule_name = Column(String(50), nullable=False, comment='规则名称')
    trigger_type = Column(String(20), default='keyword', comment='触发类型: keyword-关键词, pattern-正则表达式, all-所有消息')
    trigger_content = Column(Text, comment='触发内容(关键词或正则)')
    reply_type = Column(String(20), default='text', comment='回复类型: text-文本, template-模板')
    reply_content = Column(Text, nullable=False, comment='回复内容')
    priority = Column(Integer, default=0, comment='优先级(数字越大优先级越高)')
    is_active = Column(Boolean, default=True, comment='是否启用')
    match_count = Column(Integer, default=0, comment='匹配次数统计')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关系
    robot_config = relationship('RobotConfig', back_populates='reply_rules')

    def to_dict(self):
        return {
            'id': self.id,
            'rule_name': self.rule_name,
            'trigger_type': self.trigger_type,
            'trigger_content': self.trigger_content,
            'reply_type': self.reply_type,
            'reply_content': self.reply_content,
            'priority': self.priority,
            'is_active': self.is_active,
            'match_count': self.match_count
        }


class ParseRule(Base):
    """消息解析规则表 - 自定义解析逻辑"""
    __tablename__ = 't_parse_rule'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='规则ID')
    user_id = Column(Integer, ForeignKey('t_user_account.id'), nullable=False, comment='所属用户ID')
    rule_name = Column(String(50), nullable=False, comment='规则名称')
    rule_type = Column(String(20), default='regex', comment='规则类型: regex-正则, keyword-关键词, custom-自定义脚本')
    pattern = Column(Text, comment='匹配模式(正则表达式或关键词)')
    extract_fields = Column(Text, comment='提取字段配置JSON')
    priority = Column(Integer, default=0, comment='优先级')
    is_active = Column(Boolean, default=True, comment='是否启用')
    description = Column(String(255), comment='规则描述')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关系
    user = relationship('User', back_populates='parse_rules')

    def to_dict(self):
        return {
            'id': self.id,
            'rule_name': self.rule_name,
            'rule_type': self.rule_type,
            'pattern': self.pattern,
            'extract_fields': self.extract_fields,
            'priority': self.priority,
            'is_active': self.is_active,
            'description': self.description
        }


class StatRule(Base):
    """统计规则表 - 自定义统计维度"""
    __tablename__ = 't_stat_rule'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='规则ID')
    user_id = Column(Integer, ForeignKey('t_user_account.id'), nullable=False, comment='所属用户ID')
    rule_name = Column(String(50), nullable=False, comment='规则名称')
    stat_type = Column(String(20), default='daily', comment='统计类型: daily-日报, weekly-周报, monthly-月报, custom-自定义')
    dimensions = Column(Text, comment='统计维度JSON: 按商品/按客户/按线路等')
    filters = Column(Text, comment='过滤条件JSON')
    chart_type = Column(String(20), default='bar', comment='图表类型: bar-柱状图, line-折线图, pie-饼图')
    refresh_interval = Column(Integer, default=3600, comment='刷新间隔(秒)')
    is_active = Column(Boolean, default=True, comment='是否启用')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关系
    user = relationship('User', back_populates='stat_rules')

    def to_dict(self):
        return {
            'id': self.id,
            'rule_name': self.rule_name,
            'stat_type': self.stat_type,
            'dimensions': self.dimensions,
            'filters': self.filters,
            'chart_type': self.chart_type,
            'refresh_interval': self.refresh_interval,
            'is_active': self.is_active
        }


class DashboardWidget(Base):
    """看板组件配置表 - 用户自定义看板"""
    __tablename__ = 't_dashboard_widget'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='组件ID')
    user_id = Column(Integer, ForeignKey('t_user_account.id'), nullable=False, comment='所属用户ID')
    widget_name = Column(String(50), nullable=False, comment='组件名称')
    widget_type = Column(String(20), default='stat_card', comment='组件类型: stat_card-统计卡片, chart-图表, table-表格')
    data_source = Column(Text, comment='数据源配置JSON')
    stat_period = Column(String(20), default='today', comment='统计周期: today-今日, week-本周, month-本月, custom-自定义')
    position_x = Column(Integer, default=0, comment='X坐标位置')
    position_y = Column(Integer, default=0, comment='Y坐标位置')
    width = Column(Integer, default=1, comment='宽度(栅格单位)')
    height = Column(Integer, default=1, comment='高度(栅格单位)')
    is_visible = Column(Boolean, default=True, comment='是否显示')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关系
    user = relationship('User')

    def to_dict(self):
        return {
            'id': self.id,
            'widget_name': self.widget_name,
            'widget_type': self.widget_type,
            'data_source': self.data_source,
            'stat_period': self.stat_period,
            'position_x': self.position_x,
            'position_y': self.position_y,
            'width': self.width,
            'height': self.height,
            'is_visible': self.is_visible
        }


class RuleTemplate(Base):
    """规则模板库表 - 云端共享规则"""
    __tablename__ = 't_rule_template'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='模板ID')
    template_name = Column(String(100), nullable=False, comment='模板名称')
    industry = Column(String(50), nullable=False, index=True, comment='所属行业')
    description = Column(String(500), comment='模板描述')
    
    # 规则内容（JSON格式存储）
    parse_rules = Column(Text, comment='解析规则JSON数组')
    stat_rules = Column(Text, comment='统计规则JSON数组')
    reply_rules = Column(Text, comment='回复规则JSON数组')
    
    # 来源与版本
    source_type = Column(String(20), default='official', comment='来源: official-官方, community-社区, user-用户上传')
    author_id = Column(Integer, ForeignKey('t_user_account.id'), comment='上传用户ID')
    version = Column(String(20), default='1.0', comment='版本号')
    
    # 统计信息
    download_count = Column(Integer, default=0, comment='下载次数')
    rating = Column(Numeric(3, 2), default=0.00, comment='评分(0-5)')
    rating_count = Column(Integer, default=0, comment='评分人数')
    
    # 状态
    is_public = Column(Boolean, default=True, comment='是否公开')
    is_featured = Column(Boolean, default=False, comment='是否精选')
    is_active = Column(Boolean, default=True, comment='是否启用')
    
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关系
    author = relationship('User')

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'template_name': self.template_name,
            'industry': self.industry,
            'description': self.description,
            'parse_rules': json.loads(self.parse_rules) if self.parse_rules else [],
            'stat_rules': json.loads(self.stat_rules) if self.stat_rules else [],
            'reply_rules': json.loads(self.reply_rules) if self.reply_rules else [],
            'source_type': self.source_type,
            'author_name': self.author.username if self.author else '官方',
            'version': self.version,
            'download_count': self.download_count,
            'rating': float(self.rating),
            'rating_count': self.rating_count,
            'is_featured': self.is_featured,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class UserRuleBackup(Base):
    """用户规则备份表 - 云端备份"""
    __tablename__ = 't_user_rule_backup'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='备份ID')
    user_id = Column(Integer, ForeignKey('t_user_account.id'), nullable=False, comment='用户ID')
    backup_name = Column(String(100), comment='备份名称')
    
    # 规则内容
    parse_rules = Column(Text, comment='解析规则JSON')
    stat_rules = Column(Text, comment='统计规则JSON')
    reply_rules = Column(Text, comment='回复规则JSON')
    
    # 来源模板（如果是从模板下载的）
    template_id = Column(Integer, ForeignKey('t_rule_template.id'), comment='来源模板ID')
    
    # 版本控制
    version = Column(String(20), default='1.0', comment='版本号')
    is_current = Column(Boolean, default=True, comment='是否为当前使用版本')
    
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关系
    user = relationship('User')
    template = relationship('RuleTemplate')

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'backup_name': self.backup_name,
            'parse_rules': json.loads(self.parse_rules) if self.parse_rules else [],
            'stat_rules': json.loads(self.stat_rules) if self.stat_rules else [],
            'reply_rules': json.loads(self.reply_rules) if self.reply_rules else [],
            'template_id': self.template_id,
            'template_name': self.template.template_name if self.template else None,
            'version': self.version,
            'is_current': self.is_current,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class CommandConfig(Base):
    """指令配置表 t_command_config"""
    __tablename__ = 't_command_config'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='指令ID')
    command_name = Column(String(50), nullable=False, unique=True, comment='指令名称')
    keywords = Column(Text, comment='关键词列表(JSON)')
    patterns = Column(Text, comment='正则表达式列表(JSON)')
    response_template = Column(Text, comment='回复模板')
    description = Column(String(255), comment='指令描述')
    is_active = Column(TinyInteger, default=1, comment='是否启用')
    usage_count = Column(Integer, default=0, comment='使用次数统计')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'command_name': self.command_name,
            'keywords': json.loads(self.keywords) if self.keywords else [],
            'patterns': json.loads(self.patterns) if self.patterns else [],
            'response_template': self.response_template,
            'description': self.description,
            'is_active': self.is_active,
            'usage_count': self.usage_count,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ReportPushLog(Base):
    """报表推送日志表 t_report_push_log"""
    __tablename__ = 't_report_push_log'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='日志ID')
    route_id = Column(Integer, ForeignKey('t_delivery_route.id'), comment='配送线路ID')
    push_time = Column(DateTime, nullable=False, comment='推送时间')
    recipient_group = Column(String(64), comment='接收群ID')
    report_content = Column(Text, comment='推送内容')
    status = Column(String(20), default='success', comment='推送状态: success/failed')
    error_message = Column(Text, comment='错误信息')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')

    # 关系
    route = relationship('DeliveryRoute')

    def to_dict(self):
        return {
            'id': self.id,
            'route_id': self.route_id,
            'route_name': self.route.route_name if self.route else None,
            'push_time': self.push_time.isoformat() if self.push_time else None,
            'recipient_group': self.recipient_group,
            'report_content': self.report_content,
            'status': self.status,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class PricingPackage(Base):
    """定价套餐表"""
    __tablename__ = 't_pricing_package'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='套餐ID')
    package_name = Column(String(100), nullable=False, comment='套餐名称')
    includes_desktop = Column(Boolean, default=False, comment='是否包含桌面端')
    license_count = Column(Integer, default=0, comment='赠送授权码数量')
    validity_months = Column(Integer, default=1, comment='有效期（月）')
    price = Column(Numeric(10, 2), nullable=False, comment='价格（元）')
    description = Column(String(500), comment='套餐描述')
    is_active = Column(Boolean, default=True, comment='是否启用')
    sort_order = Column(Integer, default=0, comment='排序顺序')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    def to_dict(self):
        return {
            'id': self.id,
            'package_name': self.package_name,
            'includes_desktop': self.includes_desktop,
            'license_count': self.license_count,
            'validity_months': self.validity_months,
            'price': float(self.price),
            'description': self.description,
            'is_active': self.is_active,
            'sort_order': self.sort_order,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class PricingConfig(Base):
    """应用定价配置表"""
    __tablename__ = 't_pricing_config'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='配置ID')
    config_key = Column(String(50), unique=True, nullable=False, comment='配置键: app_yearly_fee, license_monthly_price')
    config_value = Column(Numeric(10, 2), nullable=False, comment='配置值（价格）')
    description = Column(String(255), comment='描述')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    def to_dict(self):
        return {
            'id': self.id,
            'config_key': self.config_key,
            'config_value': float(self.config_value),
            'description': self.description,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class PaymentRecord(Base):
    """支付记录表"""
    __tablename__ = 't_payment_record'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='记录ID')
    order_no = Column(String(64), unique=True, nullable=False, index=True, comment='平台订单号')
    trade_no = Column(String(64), comment='支付宝交易号')
    user_id = Column(Integer, ForeignKey('t_user_account.id'), comment='用户ID')
    admin_id = Column(Integer, ForeignKey('t_user_account.id'), comment='操作管理员ID（如果是代付）')
    amount = Column(Numeric(10, 2), nullable=False, comment='支付金额')
    subject = Column(String(255), comment='商品标题')
    payment_method = Column(String(20), default='alipay', comment='支付方式: alipay, manual')
    status = Column(String(20), default='pending', comment='状态: pending, success, failed')
    extend_info = Column(Text, comment='扩展信息JSON（如展期的授权码ID列表）')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    paid_at = Column(DateTime, comment='支付完成时间')

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'order_no': self.order_no,
            'trade_no': self.trade_no,
            'amount': float(self.amount),
            'subject': self.subject,
            'payment_method': self.payment_method,
            'status': self.status,
            'extend_info': json.loads(self.extend_info) if self.extend_info else {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None
        }


class RenewalHistory(Base):
    """续费历史记录表"""
    __tablename__ = 't_renewal_history'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='记录ID')
    user_id = Column(Integer, ForeignKey('t_user_account.id'), nullable=False, comment='用户ID')
    license_id = Column(Integer, ForeignKey('t_license_v2.id'), nullable=False, comment='授权码ID')
    order_no = Column(String(64), comment='订单号')
    trade_no = Column(String(64), comment='交易号')
    renew_type = Column(String(20), nullable=False, comment='续费类型: manual-手动, auto-自动, batch-批量')
    period = Column(String(20), nullable=False, comment='续费周期: 1m, 3m, 6m, 1y')
    months = Column(Integer, nullable=False, comment='续费月数')
    amount = Column(Numeric(10, 2), nullable=False, comment='支付金额')
    discount = Column(Numeric(5, 2), default=1.0, comment='折扣率')
    old_expiry = Column(DateTime, comment='原过期时间')
    new_expiry = Column(DateTime, nullable=False, comment='新过期时间')
    payment_method = Column(String(20), default='alipay', comment='支付方式: alipay, wechat, manual')
    status = Column(String(20), default='success', comment='状态: success, failed, pending')
    error_message = Column(Text, comment='错误信息')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    paid_at = Column(DateTime, comment='支付完成时间')

    # 关系
    user = relationship('User')
    license = relationship('License')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'license_id': self.license_id,
            'license_code': self.license.license_code if self.license else None,
            'order_no': self.order_no,
            'trade_no': self.trade_no,
            'renew_type': self.renew_type,
            'period': self.period,
            'months': self.months,
            'amount': float(self.amount),
            'discount': float(self.discount),
            'old_expiry': self.old_expiry.isoformat() if self.old_expiry else None,
            'new_expiry': self.new_expiry.isoformat() if self.new_expiry else None,
            'payment_method': self.payment_method,
            'status': self.status,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None
        }


class AffiliatePromoter(Base):
    """平台推广员表 - 用于推广TonjClaw系统"""
    __tablename__ = 't_affiliate_promoter'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='推广员ID')
    promoter_code = Column(String(50), unique=True, nullable=False, index=True, comment='推广员编号')
    promoter_name = Column(String(100), nullable=False, comment='推广员姓名/名称')
    contact_info = Column(String(200), comment='联系方式（手机/微信/邮箱）')
    commission_rate = Column(Numeric(5, 2), default=10.00, comment='佣金比例（百分比）')
    promo_link = Column(String(500), comment='推广链接')
    remark = Column(Text, comment='备注信息')
    is_active = Column(Boolean, default=True, comment='是否启用')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    def to_dict(self):
        return {
            'id': self.id,
            'promoter_code': self.promoter_code,
            'promoter_name': self.promoter_name,
            'contact_info': self.contact_info,
            'commission_rate': float(self.commission_rate),
            'promo_link': self.promo_link,
            'remark': self.remark,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class AuditLog(Base):
    """审计日志表 - 记录系统操作"""
    __tablename__ = 't_audit_log'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='日志ID')
    user_id = Column(Integer, ForeignKey('t_user_account.id'), comment='操作用户ID')
    username = Column(String(50), comment='操作用户名')
    action = Column(String(50), nullable=False, comment='操作类型: login-登录, logout-登出, create-创建, update-更新, delete-删除, export-导出')
    resource = Column(String(50), comment='操作资源: user-用户, license-授权码, order-订单, product-商品, config-配置')
    resource_id = Column(Integer, comment='资源ID')
    description = Column(String(500), comment='操作描述')
    old_value = Column(Text, comment='旧值(JSON)')
    new_value = Column(Text, comment='新值(JSON)')
    ip_address = Column(String(50), comment='IP地址')
    user_agent = Column(String(500), comment='用户代理')
    status = Column(String(20), default='success', comment='操作状态: success-成功, failed-失败')
    error_message = Column(Text, comment='错误信息')
    created_at = Column(DateTime, default=datetime.now, index=True, comment='操作时间')

    # 关系
    user = relationship('User')

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'action': self.action,
            'resource': self.resource,
            'resource_id': self.resource_id,
            'description': self.description,
            'old_value': json.loads(self.old_value) if self.old_value else None,
            'new_value': json.loads(self.new_value) if self.new_value else None,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'status': self.status,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
