"""
插件市场系统 ORM 模型定义
包含：插件包、插件版本、知识库、问答库、解析算法等
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Numeric, DateTime, Boolean, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from database.db_config import Base

try:
    from packaging.version import parse as parse_version
except ImportError:
    def parse_version(v):
        return tuple(map(int, v.split('.')))


class PluginPackage(Base):
    """插件包表 - 插件市场中的插件定义"""
    __tablename__ = 't_plugin_package'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='插件ID')
    plugin_code = Column(String(50), unique=True, nullable=False, index=True, comment='插件唯一标识')
    plugin_name = Column(String(100), nullable=False, comment='插件名称')
    description = Column(String(500), comment='插件描述')
    short_description = Column(String(200), comment='简短描述')
    
    # 分类信息
    category = Column(String(50), comment='插件分类: industry-行业插件, knowledge-知识库, qa-问答库, algorithm-算法, tool-工具')
    industry = Column(String(50), comment='所属行业')
    
    # 作者信息
    author_id = Column(Integer, ForeignKey('t_user_account.id'), comment='作者用户ID')
    author_name = Column(String(100), comment='作者名称')
    organization = Column(String(100), comment='所属组织')
    
    # 元数据
    icon_url = Column(String(500), comment='插件图标URL')
    tags = Column(String(200), comment='标签，逗号分隔')
    compatibility = Column(String(200), comment='兼容版本')
    
    # 状态
    is_public = Column(Boolean, default=True, comment='是否公开')
    is_featured = Column(Boolean, default=False, comment='是否精选')
    is_active = Column(Boolean, default=True, comment='是否启用')
    is_deprecated = Column(Boolean, default=False, comment='是否废弃')
    
    # 统计信息
    download_count = Column(Integer, default=0, comment='下载次数')
    install_count = Column(Integer, default=0, comment='安装次数')
    rating = Column(Numeric(3,2), default=0.00, comment='评分')
    rating_count = Column(Integer, default=0, comment='评分人数')
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    # 关系
    versions = relationship('PluginVersion', back_populates='package', cascade='all, delete-orphan')
    installations = relationship('PluginInstallation', back_populates='package')
    
    def to_dict(self):
        latest_version = max(self.versions, key=lambda v: parse_version(v.version)) if self.versions else None
        return {
            'id': self.id,
            'plugin_code': self.plugin_code,
            'plugin_name': self.plugin_name,
            'description': self.description,
            'short_description': self.short_description,
            'category': self.category,
            'industry': self.industry,
            'author_name': self.author_name,
            'organization': self.organization,
            'icon_url': self.icon_url,
            'tags': self.tags.split(',') if self.tags else [],
            'compatibility': self.compatibility,
            'is_public': self.is_public,
            'is_featured': self.is_featured,
            'is_active': self.is_active,
            'is_deprecated': self.is_deprecated,
            'download_count': self.download_count,
            'install_count': self.install_count,
            'rating': float(self.rating) if self.rating else 0.0,
            'rating_count': self.rating_count,
            'latest_version': latest_version.version if latest_version else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class PluginVersion(Base):
    """插件版本表 - 插件的版本记录"""
    __tablename__ = 't_plugin_version'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='版本ID')
    package_id = Column(Integer, ForeignKey('t_plugin_package.id'), nullable=False, index=True, comment='插件ID')
    version = Column(String(20), nullable=False, comment='版本号')
    changelog = Column(String(1000), comment='更新日志')
    download_url = Column(String(500), comment='下载地址')
    file_size = Column(Integer, comment='文件大小(字节)')
    
    # 依赖配置
    dependencies = Column(Text, comment='依赖插件列表JSON')
    required_permissions = Column(String(200), comment='需要的权限')
    
    # 状态
    is_stable = Column(Boolean, default=True, comment='是否稳定版')
    is_active = Column(Boolean, default=True, comment='是否启用')
    
    # 统计
    download_count = Column(Integer, default=0, comment='下载次数')
    
    # 时间戳
    released_at = Column(DateTime, default=datetime.now, comment='发布时间')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    
    # 关系
    package = relationship('PluginPackage', back_populates='versions')
    installations = relationship('PluginInstallation', back_populates='version')
    
    __table_args__ = (
        Index('idx_package_version', 'package_id', 'version', unique=True),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'package_id': self.package_id,
            'version': self.version,
            'changelog': self.changelog,
            'download_url': self.download_url,
            'file_size': self.file_size,
            'dependencies': self.dependencies,
            'required_permissions': self.required_permissions,
            'is_stable': self.is_stable,
            'is_active': self.is_active,
            'download_count': self.download_count,
            'released_at': self.released_at.isoformat() if self.released_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class PluginInstallation(Base):
    """插件安装记录表 - 用户安装的插件"""
    __tablename__ = 't_plugin_installation'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='安装ID')
    user_id = Column(Integer, ForeignKey('t_user_account.id'), nullable=False, index=True, comment='用户ID')
    package_id = Column(Integer, ForeignKey('t_plugin_package.id'), nullable=False, index=True, comment='插件ID')
    version_id = Column(Integer, ForeignKey('t_plugin_version.id'), comment='版本ID')
    installed_version = Column(String(20), comment='安装的版本号')
    
    # 状态
    status = Column(String(20), default='installed', comment='状态: installing-installing, installed-installed, failed-failed, disabled-disabled')
    installed_path = Column(String(500), comment='安装路径')
    
    # 配置
    config = Column(Text, comment='插件配置JSON')
    
    # 时间戳
    installed_at = Column(DateTime, default=datetime.now, comment='安装时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    # 关系
    package = relationship('PluginPackage', back_populates='installations')
    version = relationship('PluginVersion', back_populates='installations')
    
    __table_args__ = (
        Index('idx_user_package', 'user_id', 'package_id', unique=True),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'package_id': self.package_id,
            'version_id': self.version_id,
            'installed_version': self.installed_version,
            'status': self.status,
            'installed_path': self.installed_path,
            'config': self.config,
            'installed_at': self.installed_at.isoformat() if self.installed_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class KnowledgeBase(Base):
    """知识库表 - 行业知识库"""
    __tablename__ = 't_knowledge_base'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='知识库ID')
    knowledge_name = Column(String(100), nullable=False, comment='知识库名称')
    description = Column(String(500), comment='知识库描述')
    
    # 分类信息
    industry = Column(String(50), comment='所属行业')
    category = Column(String(50), comment='分类')
    
    # 来源
    source_type = Column(String(20), default='official', comment='来源: official-官方, user-用户')
    author_id = Column(Integer, ForeignKey('t_user_account.id'), comment='创建者ID')
    package_id = Column(Integer, ForeignKey('t_plugin_package.id'), comment='关联插件ID')
    
    # 状态
    is_public = Column(Boolean, default=True, comment='是否公开')
    is_active = Column(Boolean, default=True, comment='是否启用')
    
    # 统计
    doc_count = Column(Integer, default=0, comment='文档数量')
    view_count = Column(Integer, default=0, comment='浏览次数')
    search_count = Column(Integer, default=0, comment='搜索次数')
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    # 关系
    documents = relationship('KnowledgeDocument', back_populates='knowledge_base', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'knowledge_name': self.knowledge_name,
            'description': self.description,
            'industry': self.industry,
            'category': self.category,
            'source_type': self.source_type,
            'is_public': self.is_public,
            'is_active': self.is_active,
            'doc_count': self.doc_count,
            'view_count': self.view_count,
            'search_count': self.search_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class KnowledgeDocument(Base):
    """知识文档表 - 知识库中的文档"""
    __tablename__ = 't_knowledge_document'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='文档ID')
    knowledge_id = Column(Integer, ForeignKey('t_knowledge_base.id'), nullable=False, index=True, comment='知识库ID')
    doc_title = Column(String(200), nullable=False, comment='文档标题')
    doc_content = Column(Text, comment='文档内容')
    doc_type = Column(String(20), default='markdown', comment='文档类型: markdown/html/pdf')
    
    # 元数据
    tags = Column(String(200), comment='标签，逗号分隔')
    summary = Column(String(500), comment='文档摘要')
    
    # 状态
    is_active = Column(Boolean, default=True, comment='是否启用')
    
    # 统计
    view_count = Column(Integer, default=0, comment='浏览次数')
    search_count = Column(Integer, default=0, comment='被搜索次数')
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    # 关系
    knowledge_base = relationship('KnowledgeBase', back_populates='documents')
    
    def to_dict(self):
        return {
            'id': self.id,
            'knowledge_id': self.knowledge_id,
            'doc_title': self.doc_title,
            'doc_type': self.doc_type,
            'tags': self.tags.split(',') if self.tags else [],
            'summary': self.summary,
            'is_active': self.is_active,
            'view_count': self.view_count,
            'search_count': self.search_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class FAQ(Base):
    """问答库表 - 常见问题"""
    __tablename__ = 't_faq'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='FAQ ID')
    question = Column(String(500), nullable=False, comment='问题')
    answer = Column(Text, nullable=False, comment='答案')
    
    # 分类信息
    industry = Column(String(50), comment='所属行业')
    category = Column(String(50), comment='分类')
    tags = Column(String(200), comment='标签，逗号分隔')
    
    # 来源
    source_type = Column(String(20), default='official', comment='来源: official-官方, user-用户')
    author_id = Column(Integer, ForeignKey('t_user_account.id'), comment='创建者ID')
    package_id = Column(Integer, ForeignKey('t_plugin_package.id'), comment='关联插件ID')
    
    # 状态
    is_public = Column(Boolean, default=True, comment='是否公开')
    is_active = Column(Boolean, default=True, comment='是否启用')
    
    # 匹配配置
    match_keywords = Column(String(500), comment='匹配关键词')
    match_threshold = Column(Float, default=0.7, comment='匹配阈值(0-1)')
    priority = Column(Integer, default=0, comment='优先级')
    
    # 统计
    view_count = Column(Integer, default=0, comment='浏览次数')
    match_count = Column(Integer, default=0, comment='匹配成功次数')
    helpful_count = Column(Integer, default=0, comment='有用次数')
    not_helpful_count = Column(Integer, default=0, comment='无用次数')
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    def to_dict(self):
        return {
            'id': self.id,
            'question': self.question,
            'answer': self.answer,
            'industry': self.industry,
            'category': self.category,
            'tags': self.tags.split(',') if self.tags else [],
            'source_type': self.source_type,
            'is_public': self.is_public,
            'is_active': self.is_active,
            'match_keywords': self.match_keywords,
            'match_threshold': float(self.match_threshold) if self.match_threshold else 0.7,
            'priority': self.priority,
            'view_count': self.view_count,
            'match_count': self.match_count,
            'helpful_count': self.helpful_count,
            'not_helpful_count': self.not_helpful_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ParseAlgorithm(Base):
    """解析算法表 - 专用解析算法注册"""
    __tablename__ = 't_parse_algorithm'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='算法ID')
    algorithm_code = Column(String(50), unique=True, nullable=False, index=True, comment='算法唯一标识')
    algorithm_name = Column(String(100), nullable=False, comment='算法名称')
    description = Column(String(500), comment='算法描述')
    
    # 分类信息
    industry = Column(String(50), comment='适用行业')
    category = Column(String(50), comment='分类: regex-正则, keyword-关键词, ai-人工智能, custom-自定义')
    
    # 实现配置
    module_path = Column(String(500), comment='模块路径')
    class_name = Column(String(100), comment='类名')
    function_name = Column(String(100), comment='函数名')
    
    # 参数配置
    default_params = Column(Text, comment='默认参数JSON')
    param_schema = Column(Text, comment='参数校验Schema')
    
    # 来源
    source_type = Column(String(20), default='official', comment='来源: official-官方, user-用户')
    author_id = Column(Integer, ForeignKey('t_user_account.id'), comment='创建者ID')
    package_id = Column(Integer, ForeignKey('t_plugin_package.id'), comment='关联插件ID')
    
    # 状态
    is_public = Column(Boolean, default=True, comment='是否公开')
    is_active = Column(Boolean, default=True, comment='是否启用')
    is_deprecated = Column(Boolean, default=False, comment='是否废弃')
    
    # 统计
    usage_count = Column(Integer, default=0, comment='使用次数')
    success_rate = Column(Float, default=0.0, comment='成功率')
    
    # 版本
    version = Column(String(20), default='1.0', comment='版本号')
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    def to_dict(self):
        return {
            'id': self.id,
            'algorithm_code': self.algorithm_code,
            'algorithm_name': self.algorithm_name,
            'description': self.description,
            'industry': self.industry,
            'category': self.category,
            'module_path': self.module_path,
            'class_name': self.class_name,
            'function_name': self.function_name,
            'default_params': self.default_params,
            'param_schema': self.param_schema,
            'source_type': self.source_type,
            'is_public': self.is_public,
            'is_active': self.is_active,
            'is_deprecated': self.is_deprecated,
            'usage_count': self.usage_count,
            'success_rate': float(self.success_rate) if self.success_rate else 0.0,
            'version': self.version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }