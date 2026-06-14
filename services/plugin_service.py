"""
插件市场服务
提供插件管理、知识库管理、问答库管理、解析算法管理等核心功能
"""
import json
import importlib
import logging
import threading
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, distinct
from sqlalchemy.sql.functions import sum, count
from sqlalchemy.orm import joinedload
from database.db_config import get_db_session

logger = logging.getLogger(__name__)

try:
    from packaging.version import parse as parse_version
except ImportError:
    def parse_version(v):
        parts = v.split('.')
        result = []
        for part in parts:
            try:
                result.append(int(part))
            except ValueError:
                result.append(part)
        return tuple(result)


def compare_versions(v1: str, v2: str) -> int:
    parsed1 = parse_version(v1)
    parsed2 = parse_version(v2)
    if parsed1 < parsed2:
        return -1
    elif parsed1 > parsed2:
        return 1
    else:
        return 0


def satisfies_version_constraint(installed_version: str, constraint: str) -> bool:
    if not installed_version or not constraint:
        return True
    
    constraint = constraint.strip()
    
    if '>=' in constraint:
        min_version = constraint.split('>=')[1].strip()
        return compare_versions(installed_version, min_version) >= 0
    elif '<=' in constraint:
        max_version = constraint.split('<=')[1].strip()
        return compare_versions(installed_version, max_version) <= 0
    elif '>' in constraint:
        min_version = constraint.split('>')[1].strip()
        return compare_versions(installed_version, min_version) > 0
    elif '<' in constraint:
        max_version = constraint.split('<')[1].strip()
        return compare_versions(installed_version, max_version) < 0
    elif '~=' in constraint:
        base_version = constraint.split('~=')[1].strip()
        parsed_base = parse_version(base_version)
        parsed_installed = parse_version(installed_version)
        if len(parsed_base) >= 2 and len(parsed_installed) >= 2:
            return parsed_installed[:2] == parsed_base[:2] and parsed_installed >= parsed_base
        return False
    else:
        return installed_version == constraint


def detect_circular_dependency(db: Session, starting_plugin_code: str, visited: set = None, path: list = None) -> tuple:
    """
    检测循环依赖
    返回: (是否存在循环依赖, 循环路径)
    """
    if visited is None:
        visited = set()
    if path is None:
        path = []

    if starting_plugin_code in visited:
        cycle_start = path.index(starting_plugin_code)
        cycle_path = path[cycle_start:] + [starting_plugin_code]
        return True, cycle_path

    visited.add(starting_plugin_code)
    path.append(starting_plugin_code)

    package = db.query(PluginPackage).filter(
        PluginPackage.plugin_code == starting_plugin_code
    ).first()

    if package:
        latest_version = db.query(PluginVersion).filter(
            PluginVersion.package_id == package.id,
            PluginVersion.is_stable == True,
            PluginVersion.is_active == True
        ).order_by(PluginVersion.version.desc()).first()

        if latest_version and latest_version.dependencies:
            try:
                deps = json.loads(latest_version.dependencies)
                for dep in deps:
                    dep_code = dep.get('plugin_code')
                    if dep_code:
                        has_cycle, cycle_path = detect_circular_dependency(
                            db, dep_code, visited.copy(), path.copy()
                        )
                        if has_cycle:
                            return True, cycle_path
            except Exception:
                pass

    return False, None


def resolve_dependencies(db: Session, plugin_code: str, resolved: set = None, installing: set = None) -> list:
    """
    解析插件的所有依赖，返回按安装顺序排列的依赖列表
    检测并防止循环依赖
    """
    if resolved is None:
        resolved = set()
    if installing is None:
        installing = set()

    if plugin_code in installing:
        raise ValueError(f"检测到循环依赖: {list(installing) + [plugin_code]}")

    if plugin_code in resolved:
        return []

    installing.add(plugin_code)

    package = db.query(PluginPackage).filter(
        PluginPackage.plugin_code == plugin_code
    ).first()

    dependencies = []

    if package:
        latest_version = db.query(PluginVersion).filter(
            PluginVersion.package_id == package.id,
            PluginVersion.is_stable == True,
            PluginVersion.is_active == True
        ).order_by(PluginVersion.version.desc()).first()

        if latest_version and latest_version.dependencies:
            try:
                deps = json.loads(latest_version.dependencies)
                for dep in deps:
                    dep_code = dep.get('plugin_code')
                    if dep_code:
                        dep_dependencies = resolve_dependencies(
                            db, dep_code, resolved, installing.copy()
                        )
                        dependencies.extend(dep_dependencies)
                        if dep_code not in resolved:
                            dependencies.append({
                                'plugin_code': dep_code,
                                'min_version': dep.get('min_version', '0.0.0')
                            })
            except Exception as e:
                raise ValueError(f"解析依赖失败: {e}")

    installing.remove(plugin_code)
    resolved.add(plugin_code)

    seen = {}
    result = []
    for dep in dependencies:
        key = dep['plugin_code']
        if key not in seen:
            seen[key] = dep
            result.append(dep)
    return result


from models.plugin_models import (
    PluginPackage, PluginVersion, PluginInstallation,
    KnowledgeBase, KnowledgeDocument, FAQ, ParseAlgorithm
)


class PluginService:
    """插件管理服务"""

    @staticmethod
    def list_plugins(db: Session, category: str = None, industry: str = None,
                     featured_only: bool = False, search: str = None) -> List[Dict]:
        """
        获取插件列表
        """
        query = db.query(PluginPackage).filter(
            PluginPackage.is_public == True,
            PluginPackage.is_active == True,
            PluginPackage.is_deprecated == False
        )

        if category:
            query = query.filter(PluginPackage.category == category)
        if industry:
            query = query.filter(PluginPackage.industry == industry)
        if featured_only:
            query = query.filter(PluginPackage.is_featured == True)
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(or_(
                PluginPackage.plugin_name.like(search_pattern),
                PluginPackage.description.like(search_pattern),
                PluginPackage.tags.like(search_pattern)
            ))

        plugins = query.order_by(
            PluginPackage.is_featured.desc(),
            PluginPackage.download_count.desc()
        ).all()

        return [p.to_dict() for p in plugins]

    @staticmethod
    def get_plugin(db: Session, plugin_id: int = None, plugin_code: str = None) -> Optional[Dict]:
        """
        获取插件详情
        """
        query = db.query(PluginPackage)
        if plugin_id:
            query = query.filter(PluginPackage.id == plugin_id)
        elif plugin_code:
            query = query.filter(PluginPackage.plugin_code == plugin_code)

        plugin = query.first()
        return plugin.to_dict() if plugin else None

    @staticmethod
    def install_plugin(db: Session, user_id: int, plugin_id: int, version: str = None) -> Dict:
        """
        安装插件
        """
        package = db.query(PluginPackage).filter(PluginPackage.id == plugin_id).first()
        if not package:
            return {'success': False, 'error': '插件不存在'}

        existing_install = db.query(PluginInstallation).filter(
            PluginInstallation.user_id == user_id,
            PluginInstallation.package_id == plugin_id
        ).first()
        if existing_install:
            return {'success': False, 'error': '插件已安装'}

        if version:
            plugin_version = db.query(PluginVersion).filter(
                PluginVersion.package_id == plugin_id,
                PluginVersion.version == version
            ).first()
            if not plugin_version:
                return {'success': False, 'error': '指定版本不存在'}
        else:
            plugin_version = db.query(PluginVersion).filter(
                PluginVersion.package_id == plugin_id,
                PluginVersion.is_stable == True,
                PluginVersion.is_active == True
            ).order_by(PluginVersion.version.desc()).first()
            if not plugin_version:
                return {'success': False, 'error': '没有可用的稳定版本'}

        has_cycle, cycle_path = detect_circular_dependency(db, package.plugin_code)
        if has_cycle:
            return {'success': False, 'error': f'检测到循环依赖: {" → ".join(cycle_path)}'}

        dependencies = []
        if plugin_version.dependencies:
            try:
                resolved_deps = resolve_dependencies(db, package.plugin_code)
                for dep in resolved_deps:
                    dep_package = db.query(PluginPackage).filter(
                        PluginPackage.plugin_code == dep['plugin_code']
                    ).first()
                    if not dep_package:
                        return {'success': False, 'error': f'依赖插件 {dep["plugin_code"]} 不存在'}

                    dep_install = db.query(PluginInstallation).filter(
                        PluginInstallation.user_id == user_id,
                        PluginInstallation.package_id == dep_package.id
                    ).first()
                    if not dep_install:
                        install_result = PluginService.install_plugin(db, user_id, dep_package.id)
                        if not install_result['success']:
                            return install_result
                        dependencies.append(dep_package.plugin_code)
            except Exception as e:
                return {'success': False, 'error': f'解析依赖失败: {str(e)}'}

        install_path = f"plugins/{package.plugin_code}/{plugin_version.version}"

        installation = PluginInstallation(
            user_id=user_id,
            package_id=plugin_id,
            version_id=plugin_version.id,
            installed_version=plugin_version.version,
            status='installed',
            installed_path=install_path,
            config='{}'
        )
        db.add(installation)

        package.install_count += 1
        plugin_version.download_count += 1

        db.commit()
        db.refresh(installation)

        return {
            'success': True,
            'installation': installation.to_dict(),
            'dependencies_installed': dependencies
        }

    @staticmethod
    def uninstall_plugin(db: Session, user_id: int, plugin_id: int) -> Dict:
        """
        卸载插件
        """
        installation = db.query(PluginInstallation).filter(
            PluginInstallation.user_id == user_id,
            PluginInstallation.package_id == plugin_id
        ).first()

        if not installation:
            return {'success': False, 'error': '插件未安装'}

        package = db.query(PluginPackage).filter(PluginPackage.id == plugin_id).first()
        if package:
            installed_packages = db.query(PluginPackage).join(
                PluginInstallation, PluginInstallation.package_id == PluginPackage.id
            ).filter(
                PluginInstallation.user_id == user_id,
                PluginPackage.id != plugin_id
            ).all()

            for installed_pkg in installed_packages:
                latest_version = db.query(PluginVersion).filter(
                    PluginVersion.package_id == installed_pkg.id
                ).order_by(PluginVersion.version.desc()).first()

                if latest_version and latest_version.dependencies:
                    try:
                        deps = json.loads(latest_version.dependencies)
                        for dep in deps:
                            if dep.get('plugin_code') == package.plugin_code:
                                return {
                                    'success': False,
                                    'error': f'存在依赖此插件的其他插件（{installed_pkg.plugin_name}），请先卸载依赖插件'
                                }
                    except Exception:
                        pass

        db.delete(installation)
        db.commit()

        return {'success': True, 'message': '插件已卸载'}

    @staticmethod
    def update_plugin(db: Session, user_id: int, plugin_id: int, version: str = None) -> Dict:
        """
        更新插件
        """
        installation = db.query(PluginInstallation).filter(
            PluginInstallation.user_id == user_id,
            PluginInstallation.package_id == plugin_id
        ).first()

        if not installation:
            return {'success': False, 'error': '插件未安装'}

        if version:
            plugin_version = db.query(PluginVersion).filter(
                PluginVersion.package_id == plugin_id,
                PluginVersion.version == version
            ).first()
            if not plugin_version:
                return {'success': False, 'error': '指定版本不存在'}
        else:
            plugin_version = db.query(PluginVersion).filter(
                PluginVersion.package_id == plugin_id,
                PluginVersion.is_stable == True,
                PluginVersion.is_active == True
            ).order_by(PluginVersion.version.desc()).first()
            if not plugin_version:
                return {'success': False, 'error': '没有可用的稳定版本'}

        if plugin_version.version == installation.installed_version:
            return {'success': False, 'error': '已是指定版本'}

        comparison = compare_versions(plugin_version.version, installation.installed_version)
        update_type = 'upgrade' if comparison > 0 else 'downgrade'

        if plugin_version.dependencies:
            try:
                deps = json.loads(plugin_version.dependencies)
                for dep in deps:
                    dep_package = db.query(PluginPackage).filter(
                        PluginPackage.plugin_code == dep.get('plugin_code')
                    ).first()
                    if not dep_package:
                        return {'success': False, 'error': f'依赖插件 {dep.get("plugin_code")} 不存在'}

                    dep_install = db.query(PluginInstallation).filter(
                        PluginInstallation.user_id == user_id,
                        PluginInstallation.package_id == dep_package.id
                    ).first()
                    if not dep_install:
                        install_result = PluginService.install_plugin(db, user_id, dep_package.id)
                        if not install_result['success']:
                            return install_result
                    else:
                        min_version = dep.get('min_version', '0.0.0')
                        if not satisfies_version_constraint(dep_install.installed_version, f'>= {min_version}'):
                            upgrade_result = PluginService.update_plugin(db, user_id, dep_package.id)
                            if not upgrade_result['success']:
                                return {'success': False, 'error': f'依赖插件 {dep_package.plugin_name} 需要升级'}
            except Exception as e:
                return {'success': False, 'error': f'解析依赖失败: {str(e)}'}

        installation.version_id = plugin_version.id
        installation.installed_version = plugin_version.version
        installation.status = 'installed'
        installation.installed_path = f"plugins/{installation.package.plugin_code}/{plugin_version.version}"

        plugin_version.download_count += 1
        db.commit()
        db.refresh(installation)

        return {'success': True, 'installation': installation.to_dict()}

    @staticmethod
    def list_installed_plugins(db: Session, user_id: int) -> List[Dict]:
        """
        获取用户已安装的插件列表
        """
        installations = db.query(PluginInstallation).filter(
            PluginInstallation.user_id == user_id
        ).options(
            joinedload(PluginInstallation.package)
        ).all()

        result = []
        for install in installations:
            plugin_data = install.to_dict()
            if install.package:
                plugin_data['plugin'] = install.package.to_dict()
                
                latest_version = db.query(PluginVersion).filter(
                    PluginVersion.package_id == install.package_id,
                    PluginVersion.is_stable == True,
                    PluginVersion.is_active == True
                ).order_by(PluginVersion.version.desc()).first()
                
                if latest_version:
                    plugin_data['has_update'] = compare_versions(
                        latest_version.version, 
                        install.installed_version
                    ) > 0
                    plugin_data['latest_version'] = latest_version.version
                
                all_versions = db.query(PluginVersion).filter(
                    PluginVersion.package_id == install.package_id,
                    PluginVersion.is_active == True
                ).order_by(PluginVersion.version.desc()).all()
                plugin_data['available_versions'] = [v.version for v in all_versions]
                
            result.append(plugin_data)

        return result

    @staticmethod
    def rollback_plugin(db: Session, user_id: int, plugin_id: int, target_version: str) -> Dict:
        """
        回滚插件到指定版本
        """
        installation = db.query(PluginInstallation).filter(
            PluginInstallation.user_id == user_id,
            PluginInstallation.package_id == plugin_id
        ).first()

        if not installation:
            return {'success': False, 'error': '插件未安装'}

        target_plugin_version = db.query(PluginVersion).filter(
            PluginVersion.package_id == plugin_id,
            PluginVersion.version == target_version,
            PluginVersion.is_active == True
        ).first()

        if not target_plugin_version:
            return {'success': False, 'error': '目标版本不存在或不可用'}

        comparison = compare_versions(target_version, installation.installed_version)
        if comparison >= 0:
            return {'success': False, 'error': '目标版本不是历史版本'}

        if target_plugin_version.dependencies:
            try:
                deps = json.loads(target_plugin_version.dependencies)
                for dep in deps:
                    dep_package = db.query(PluginPackage).filter(
                        PluginPackage.plugin_code == dep.get('plugin_code')
                    ).first()
                    if not dep_package:
                        return {'success': False, 'error': f'依赖插件 {dep.get("plugin_code")} 不存在'}

                    dep_install = db.query(PluginInstallation).filter(
                        PluginInstallation.user_id == user_id,
                        PluginInstallation.package_id == dep_package.id
                    ).first()
                    if not dep_install:
                        return {'success': False, 'error': f'依赖插件 {dep_package.plugin_name} 未安装'}

                    min_version = dep.get('min_version', '0.0.0')
                    if not satisfies_version_constraint(dep_install.installed_version, f'>= {min_version}'):
                        return {'success': False, 'error': f'依赖插件 {dep_package.plugin_name} 版本不满足要求'}
            except Exception as e:
                return {'success': False, 'error': f'解析依赖失败: {str(e)}'}

        installation.version_id = target_plugin_version.id
        installation.installed_version = target_plugin_version.version
        installation.status = 'installed'
        installation.installed_path = f"plugins/{installation.package.plugin_code}/{target_plugin_version.version}"

        target_plugin_version.download_count += 1
        db.commit()
        db.refresh(installation)

        return {'success': True, 'installation': installation.to_dict(), 'message': f'已回滚到版本 {target_version}'}

    @staticmethod
    def check_updates(db: Session, user_id: int) -> List[Dict]:
        """
        检查所有已安装插件的更新
        """
        installations = db.query(PluginInstallation).filter(
            PluginInstallation.user_id == user_id,
            PluginInstallation.status == 'installed'
        ).options(
            joinedload(PluginInstallation.package)
        ).all()

        updates = []
        for install in installations:
            if not install.package:
                continue

            latest_version = db.query(PluginVersion).filter(
                PluginVersion.package_id == install.package_id,
                PluginVersion.is_stable == True,
                PluginVersion.is_active == True
            ).order_by(PluginVersion.version.desc()).first()

            if latest_version and compare_versions(latest_version.version, install.installed_version) > 0:
                updates.append({
                    'plugin_id': install.package_id,
                    'plugin_code': install.package.plugin_code,
                    'plugin_name': install.package.plugin_name,
                    'current_version': install.installed_version,
                    'latest_version': latest_version.version,
                    'changelog': latest_version.changelog
                })

        return updates


class KnowledgeService:
    """知识库服务"""

    @staticmethod
    def list_knowledge_bases(db: Session, industry: str = None, category: str = None) -> List[Dict]:
        """
        获取知识库列表
        """
        query = db.query(KnowledgeBase).filter(
            KnowledgeBase.is_public == True,
            KnowledgeBase.is_active == True
        )

        if industry:
            query = query.filter(KnowledgeBase.industry == industry)
        if category:
            query = query.filter(KnowledgeBase.category == category)

        return [kb.to_dict() for kb in query.all()]

    @staticmethod
    def get_knowledge_base(db: Session, knowledge_id: int) -> Optional[Dict]:
        """
        获取知识库详情
        """
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == knowledge_id).first()
        if not kb:
            return None

        result = kb.to_dict()
        result['documents'] = [doc.to_dict() for doc in kb.documents]
        return result

    @staticmethod
    def create_knowledge_base(db: Session, user_id: int, data: Dict) -> Dict:
        """
        创建知识库
        """
        if 'knowledge_name' not in data:
            return {'success': False, 'error': '缺少知识库名称'}

        kb = KnowledgeBase(
            knowledge_name=data['knowledge_name'],
            description=data.get('description', ''),
            industry=data.get('industry', ''),
            category=data.get('category', ''),
            source_type='user',
            author_id=user_id,
            package_id=data.get('package_id')
        )
        db.add(kb)
        db.commit()
        db.refresh(kb)

        return {'success': True, 'knowledge_base': kb.to_dict()}

    @staticmethod
    def add_document(db: Session, knowledge_id: int, data: Dict) -> Dict:
        """
        添加文档到知识库
        """
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == knowledge_id).first()
        if not kb:
            return {'success': False, 'error': '知识库不存在'}

        doc = KnowledgeDocument(
            knowledge_id=knowledge_id,
            doc_title=data['doc_title'],
            doc_content=data.get('doc_content', ''),
            doc_type=data.get('doc_type', 'markdown'),
            tags=data.get('tags', ''),
            summary=data.get('summary', '')[:500] if data.get('summary') else data.get('doc_content', '')[:500]
        )
        db.add(doc)

        kb.doc_count += 1
        db.commit()
        db.refresh(doc)

        return {'success': True, 'document': doc.to_dict()}

    @staticmethod
    def search_documents(db: Session, knowledge_id: int = None, query: str = None) -> List[Dict]:
        """
        搜索知识库文档
        """
        if not query:
            return []

        search_pattern = f"%{query}%"
        query_obj = db.query(KnowledgeDocument).filter(
            KnowledgeDocument.is_active == True,
            or_(
                KnowledgeDocument.doc_title.like(search_pattern),
                KnowledgeDocument.doc_content.like(search_pattern),
                KnowledgeDocument.tags.like(search_pattern)
            )
        )

        if knowledge_id:
            query_obj = query_obj.filter(KnowledgeDocument.knowledge_id == knowledge_id)

        docs = query_obj.all()
        for doc in docs:
            doc.search_count += 1

        db.commit()

        return [doc.to_dict() for doc in docs]

    @staticmethod
    def get_document(db: Session, doc_id: int) -> Optional[Dict]:
        """
        获取文档详情
        """
        doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_id).first()
        if not doc:
            return None

        doc.view_count += 1
        db.commit()

        result = doc.to_dict()
        result['doc_content'] = doc.doc_content
        return result


class FAQService:
    """问答库服务"""

    @staticmethod
    def list_faqs(db: Session, industry: str = None, category: str = None) -> List[Dict]:
        """
        获取FAQ列表
        """
        query = db.query(FAQ).filter(
            FAQ.is_public == True,
            FAQ.is_active == True
        )

        if industry:
            query = query.filter(FAQ.industry == industry)
        if category:
            query = query.filter(FAQ.category == category)

        return [faq.to_dict() for faq in query.all()]

    @staticmethod
    def create_faq(db: Session, user_id: int, data: Dict) -> Dict:
        """
        创建FAQ
        """
        if 'question' not in data or 'answer' not in data:
            return {'success': False, 'error': '缺少问题或答案'}

        faq = FAQ(
            question=data['question'],
            answer=data['answer'],
            industry=data.get('industry', ''),
            category=data.get('category', ''),
            tags=data.get('tags', ''),
            source_type='user',
            author_id=user_id,
            package_id=data.get('package_id'),
            match_keywords=data.get('match_keywords', ''),
            match_threshold=data.get('match_threshold', 0.7),
            priority=data.get('priority', 0)
        )
        db.add(faq)
        db.commit()
        db.refresh(faq)

        return {'success': True, 'faq': faq.to_dict()}

    @staticmethod
    def match_faq(db: Session, query: str, industry: str = None, top_n: int = 3) -> List[Dict]:
        """
        智能匹配FAQ
        """
        if not query or len(query.strip()) < 2:
            return []

        query_lower = query.lower().strip()

        query_obj = db.query(FAQ).filter(
            FAQ.is_public == True,
            FAQ.is_active == True
        )

        if industry:
            query_obj = query_obj.filter(FAQ.industry == industry)

        faqs = query_obj.all()
        matches = []

        for faq in faqs:
            score = 0
            question_lower = faq.question.lower()

            if query_lower in question_lower:
                score += 0.6
            else:
                query_words = set(query_lower.split())
                question_words = set(question_lower.split())
                common_words = query_words & question_words
                if common_words:
                    score += 0.4 * len(common_words) / max(len(query_words), len(question_words))

            if faq.match_keywords:
                keywords = [k.strip().lower() for k in faq.match_keywords.split(',')]
                for keyword in keywords:
                    if keyword in query_lower:
                        score += 0.1

            score += faq.priority * 0.01

            if score >= (faq.match_threshold or 0.7):
                matches.append((score, faq))

        matches.sort(key=lambda x: -x[0])
        top_matches = matches[:top_n]

        for _, faq in top_matches:
            faq.match_count += 1

        db.commit()

        return [faq.to_dict() for _, faq in top_matches]

    @staticmethod
    def rate_faq(db: Session, faq_id: int, helpful: bool) -> Dict:
        """
        评价FAQ
        """
        faq = db.query(FAQ).filter(FAQ.id == faq_id).first()
        if not faq:
            return {'success': False, 'error': 'FAQ不存在'}

        if helpful:
            faq.helpful_count += 1
        else:
            faq.not_helpful_count += 1

        db.commit()
        return {'success': True, 'faq': faq.to_dict()}


class AlgorithmService:
    """解析算法服务"""

    _algorithm_cache = {}
    _cache_lock = threading.Lock()

    @staticmethod
    def list_algorithms(db: Session, industry: str = None, category: str = None) -> List[Dict]:
        """
        获取算法列表
        """
        query = db.query(ParseAlgorithm).filter(
            ParseAlgorithm.is_public == True,
            ParseAlgorithm.is_active == True,
            ParseAlgorithm.is_deprecated == False
        )

        if industry:
            query = query.filter(ParseAlgorithm.industry == industry)
        if category:
            query = query.filter(ParseAlgorithm.category == category)

        return [algo.to_dict() for algo in query.all()]

    @staticmethod
    def register_algorithm(db: Session, user_id: int, data: Dict) -> Dict:
        """
        注册算法
        """
        if 'algorithm_code' not in data or 'algorithm_name' not in data:
            return {'success': False, 'error': '缺少算法标识或名称'}

        existing = db.query(ParseAlgorithm).filter(
            ParseAlgorithm.algorithm_code == data['algorithm_code']
        ).first()
        if existing:
            return {'success': False, 'error': '算法标识已存在'}

        algo = ParseAlgorithm(
            algorithm_code=data['algorithm_code'],
            algorithm_name=data['algorithm_name'],
            description=data.get('description', ''),
            industry=data.get('industry', ''),
            category=data.get('category', 'custom'),
            module_path=data.get('module_path', ''),
            class_name=data.get('class_name', ''),
            function_name=data.get('function_name', ''),
            default_params=data.get('default_params', '{}'),
            param_schema=data.get('param_schema', '{}'),
            source_type='user',
            author_id=user_id,
            package_id=data.get('package_id'),
            version=data.get('version', '1.0')
        )
        db.add(algo)
        db.commit()
        db.refresh(algo)

        return {'success': True, 'algorithm': algo.to_dict()}

    @staticmethod
    def load_algorithm(db: Session, algorithm_code: str) -> Optional[callable]:
        """
        动态加载算法
        """
        with AlgorithmService._cache_lock:
            if algorithm_code in AlgorithmService._algorithm_cache:
                return AlgorithmService._algorithm_cache[algorithm_code]

        algo = db.query(ParseAlgorithm).filter(
            ParseAlgorithm.algorithm_code == algorithm_code,
            ParseAlgorithm.is_active == True
        ).first()

        if not algo:
            return None

        try:
            if algo.module_path and algo.function_name:
                module = importlib.import_module(algo.module_path)
                if algo.class_name:
                    cls = getattr(module, algo.class_name)
                    instance = cls()
                    func = getattr(instance, algo.function_name)
                else:
                    func = getattr(module, algo.function_name)

                with AlgorithmService._cache_lock:
                    AlgorithmService._algorithm_cache[algorithm_code] = func
                return func
        except Exception as e:
            logger.error(f"加载算法失败: {algorithm_code}, error: {e}", exc_info=True)

        return None

    @staticmethod
    def execute_algorithm(db: Session, algorithm_code: str, input_data: Dict, params: Dict = None) -> Dict:
        """
        执行算法
        """
        func = AlgorithmService.load_algorithm(db, algorithm_code)
        if not func:
            return {'success': False, 'error': f'算法 {algorithm_code} 未找到或无法加载'}

        algo = db.query(ParseAlgorithm).filter(
            ParseAlgorithm.algorithm_code == algorithm_code
        ).first()

        default_params = {}
        if algo and algo.default_params:
            try:
                default_params = json.loads(algo.default_params)
            except:
                pass

        execution_params = {**default_params, **(params or {})}

        try:
            result = func(input_data, **execution_params)

            if algo:
                algo.usage_count += 1
                success_count = algo.usage_count * algo.success_rate / 100 if algo.success_rate else 0
                success_count += 1
                algo.success_rate = (success_count / algo.usage_count) * 100
                db.commit()

            return {'success': True, 'result': result}
        except Exception as e:
            if algo:
                algo.usage_count += 1
                success_count = algo.usage_count * algo.success_rate / 100 if algo.success_rate else 0
                algo.success_rate = (success_count / algo.usage_count) * 100
                db.commit()

            return {'success': False, 'error': str(e)}


class PluginAdminService:
    """插件管理后台服务"""

    @staticmethod
    def get_plugin_stats(db: Session) -> Dict:
        """
        获取插件全局统计数据
        """
        total_plugins = db.query(PluginPackage).count()
        active_plugins = db.query(PluginPackage).filter(
            PluginPackage.is_active == True,
            PluginPackage.is_deprecated == False
        ).count()
        total_installations = db.query(PluginInstallation).count()
        total_downloads = db.query(PluginVersion).with_entities(
            sum(PluginVersion.download_count)
        ).scalar() or 0

        industry_stats = db.query(
            PluginPackage.industry,
            count(distinct(PluginPackage.id)).label('plugin_count'),
            sum(PluginPackage.install_count).label('install_count')
        ).group_by(PluginPackage.industry).all()

        result = {
            'total_plugins': total_plugins,
            'active_plugins': active_plugins,
            'total_installations': total_installations,
            'total_downloads': total_downloads,
            'industry_stats': []
        }

        for industry, plugin_count, install_count in industry_stats:
            result['industry_stats'].append({
                'industry': industry or '未分类',
                'plugin_count': plugin_count,
                'install_count': install_count or 0
            })

        return result

    @staticmethod
    def get_user_plugin_stats(db: Session, user_id: int = None) -> Dict:
        """
        获取用户插件使用统计
        """
        query = db.query(PluginInstallation)
        if user_id:
            query = query.filter(PluginInstallation.user_id == user_id)

        installations = query.all()
        usage_by_industry = {}
        active_count = 0

        for install in installations:
            if install.status == 'installed':
                active_count += 1
                industry = install.package.industry if install.package else '未分类'
                if industry not in usage_by_industry:
                    usage_by_industry[industry] = {
                        'industry': industry,
                        'plugin_count': 0,
                        'last_used': None
                    }
                usage_by_industry[industry]['plugin_count'] += 1
                if not usage_by_industry[industry]['last_used'] or \
                   (install.last_used_at and install.last_used_at > usage_by_industry[industry]['last_used']):
                    usage_by_industry[industry]['last_used'] = install.last_used_at

        return {
            'total_installed': len(installations),
            'active_plugins': active_count,
            'usage_by_industry': list(usage_by_industry.values())
        }

    @staticmethod
    def get_plugin_version_history(db: Session, plugin_id: int) -> List[Dict]:
        """
        获取插件版本历史
        """
        versions = db.query(PluginVersion).filter(
            PluginVersion.package_id == plugin_id
        ).order_by(PluginVersion.version.desc()).all()

        return [v.to_dict() for v in versions]

    @staticmethod
    def create_plugin_version(db: Session, plugin_id: int, version_data: Dict) -> Dict:
        """
        创建插件版本
        """
        package = db.query(PluginPackage).filter(PluginPackage.id == plugin_id).first()
        if not package:
            return {'success': False, 'error': '插件不存在'}

        existing_version = db.query(PluginVersion).filter(
            PluginVersion.package_id == plugin_id,
            PluginVersion.version == version_data['version']
        ).first()
        if existing_version:
            return {'success': False, 'error': '版本号已存在'}

        version = PluginVersion(
            package_id=plugin_id,
            version=version_data['version'],
            changelog=version_data.get('changelog', ''),
            download_url=version_data.get('download_url', ''),
            file_size=version_data.get('file_size', 0),
            dependencies=version_data.get('dependencies', '{}'),
            is_stable=version_data.get('is_stable', True),
            is_active=version_data.get('is_active', True),
            min_system_version=version_data.get('min_system_version', '1.0'),
            release_notes=version_data.get('release_notes', '')
        )
        db.add(version)
        db.commit()
        db.refresh(version)

        package.latest_version = version.version
        db.commit()

        return {'success': True, 'version': version.to_dict()}

    @staticmethod
    def update_plugin_status(db: Session, plugin_id: int, status_data: Dict) -> Dict:
        """
        更新插件状态
        """
        package = db.query(PluginPackage).filter(PluginPackage.id == plugin_id).first()
        if not package:
            return {'success': False, 'error': '插件不存在'}

        if 'is_active' in status_data:
            package.is_active = status_data['is_active']
        if 'is_public' in status_data:
            package.is_public = status_data['is_public']
        if 'is_featured' in status_data:
            package.is_featured = status_data['is_featured']
        if 'is_deprecated' in status_data:
            package.is_deprecated = status_data['is_deprecated']

        db.commit()
        db.refresh(package)

        return {'success': True, 'plugin': package.to_dict()}

    @staticmethod
    def create_plugin(db: Session, user_id: int, plugin_data: Dict) -> Dict:
        """
        创建插件包
        """
        if 'plugin_name' not in plugin_data or 'plugin_code' not in plugin_data:
            return {'success': False, 'error': '缺少插件名称或标识'}

        existing = db.query(PluginPackage).filter(
            PluginPackage.plugin_code == plugin_data['plugin_code']
        ).first()
        if existing:
            return {'success': False, 'error': '插件标识已存在'}

        plugin = PluginPackage(
            plugin_name=plugin_data['plugin_name'],
            plugin_code=plugin_data['plugin_code'],
            description=plugin_data.get('description', ''),
            category=plugin_data.get('category', 'industry'),
            industry=plugin_data.get('industry', ''),
            icon_url=plugin_data.get('icon_url', ''),
            author_id=user_id,
            tags=plugin_data.get('tags', ''),
            is_public=plugin_data.get('is_public', True),
            is_active=plugin_data.get('is_active', True),
            is_featured=plugin_data.get('is_featured', False),
            is_deprecated=plugin_data.get('is_deprecated', False),
            min_system_version=plugin_data.get('min_system_version', '1.0'),
            license_type=plugin_data.get('license_type', 'free'),
            price=plugin_data.get('price', 0),
            required_permissions=plugin_data.get('required_permissions', '')
        )
        db.add(plugin)
        db.commit()
        db.refresh(plugin)

        return {'success': True, 'plugin': plugin.to_dict()}

    @staticmethod
    def update_plugin(db: Session, plugin_id: int, plugin_data: Dict) -> Dict:
        """
        更新插件信息
        """
        package = db.query(PluginPackage).filter(PluginPackage.id == plugin_id).first()
        if not package:
            return {'success': False, 'error': '插件不存在'}

        for key, value in plugin_data.items():
            if hasattr(package, key):
                setattr(package, key, value)

        db.commit()
        db.refresh(package)

        return {'success': True, 'plugin': package.to_dict()}

    @staticmethod
    def delete_plugin(db: Session, plugin_id: int) -> Dict:
        """
        删除插件（软删除）
        """
        package = db.query(PluginPackage).filter(PluginPackage.id == plugin_id).first()
        if not package:
            return {'success': False, 'error': '插件不存在'}

        package.is_active = False
        package.is_deprecated = True
        db.commit()

        return {'success': True, 'message': '插件已标记为废弃'}

    @staticmethod
    def get_installation_history(db: Session, plugin_id: int = None, user_id: int = None) -> List[Dict]:
        """
        获取安装历史记录
        """
        query = db.query(PluginInstallation)
        if plugin_id:
            query = query.filter(PluginInstallation.package_id == plugin_id)
        if user_id:
            query = query.filter(PluginInstallation.user_id == user_id)

        installations = query.options(
            joinedload(PluginInstallation.package)
        ).order_by(PluginInstallation.created_at.desc()).all()

        result = []
        for install in installations:
            data = install.to_dict()
            if install.package:
                data['plugin_name'] = install.package.plugin_name
                data['plugin_code'] = install.package.plugin_code
                data['industry'] = install.package.industry
            result.append(data)

        return result


plugin_service = PluginService()
knowledge_service = KnowledgeService()
faq_service = FAQService()
algorithm_service = AlgorithmService()
plugin_admin_service = PluginAdminService()