"""
插件数据隔离服务
确保不同行业插件的数据独立存储，实现数据隔离
"""
import json
import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect
from database.db_config import get_db_session, Base, engine

logger = logging.getLogger(__name__)


class DataIsolationService:
    """数据隔离服务"""

    PLUGIN_TABLE_PREFIXES = {
        'core': 't_core_',
        'seafood': 't_seafood_',
        'fooddelivery': 't_fooddelivery_',
        'education': 't_education_',
        'realestate': 't_realestate_',
        'travel': 't_travel_',
        'construction': 't_construction_',
    }

    @staticmethod
    def get_table_prefix(plugin_code: str) -> str:
        """获取插件的表前缀"""
        return DataIsolationService.PLUGIN_TABLE_PREFIXES.get(plugin_code, 't_plugin_')

    @staticmethod
    def get_tables_for_plugin(db: Session, plugin_code: str) -> List[str]:
        """获取插件的所有数据表"""
        prefix = DataIsolationService.get_table_prefix(plugin_code)
        
        inspector = inspect(engine)
        all_tables = inspector.get_table_names()
        
        return [table for table in all_tables if table.startswith(prefix)]

    @staticmethod
    def create_plugin_tables(db: Session, plugin_code: str, tables_definition: Dict) -> Dict:
        """
        为插件创建数据表
        tables_definition: {
            'table_name': {
                'columns': [
                    {'name': 'id', 'type': 'INTEGER', 'primary_key': True, 'auto_increment': True},
                    {'name': 'name', 'type': 'VARCHAR(100)', 'nullable': False},
                    ...
                ],
                'indexes': ['idx_name', ...]
            }
        }
        """
        prefix = DataIsolationService.get_table_prefix(plugin_code)
        created_tables = []

        try:
            for table_name, definition in tables_definition.items():
                full_table_name = f"{prefix}{table_name}"
                
                existing_tables = DataIsolationService.get_tables_for_plugin(db, plugin_code)
                if full_table_name in existing_tables:
                    logger.info(f"表已存在: {full_table_name}")
                    continue

                columns_sql = []
                for col in definition['columns']:
                    col_sql = f"`{col['name']}` {col['type']}"
                    if col.get('nullable', False) is False:
                        col_sql += ' NOT NULL'
                    if col.get('primary_key', False):
                        col_sql += ' PRIMARY KEY'
                    if col.get('auto_increment', False):
                        col_sql += ' AUTO_INCREMENT'
                    if col.get('default') is not None:
                        col_sql += f" DEFAULT {col['default']}"
                    if col.get('comment'):
                        col_sql += f" COMMENT '{col['comment']}'"
                    columns_sql.append(col_sql)

                create_sql = f"CREATE TABLE IF NOT EXISTS `{full_table_name}` ({', '.join(columns_sql)}) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
                
                db.execute(text(create_sql))
                created_tables.append(full_table_name)
                logger.info(f"创建表成功: {full_table_name}")

                if definition.get('indexes'):
                    for idx in definition['indexes']:
                        idx_sql = f"CREATE INDEX `{idx}` ON `{full_table_name}`({idx.split('_')[1]})"
                        try:
                            db.execute(text(idx_sql))
                        except Exception:
                            pass

            db.commit()
            return {'success': True, 'created_tables': created_tables}
        except Exception as e:
            db.rollback()
            logger.error(f"创建插件表失败: {e}")
            return {'success': False, 'error': str(e), 'created_tables': created_tables}

    @staticmethod
    def drop_plugin_tables(db: Session, plugin_code: str) -> Dict:
        """删除插件的所有数据表"""
        prefix = DataIsolationService.get_table_prefix(plugin_code)
        tables = DataIsolationService.get_tables_for_plugin(db, plugin_code)
        
        dropped_tables = []
        try:
            for table in tables:
                if table.startswith(prefix):
                    db.execute(text(f"DROP TABLE IF EXISTS `{table}`"))
                    dropped_tables.append(table)
            
            db.commit()
            return {'success': True, 'dropped_tables': dropped_tables}
        except Exception as e:
            db.rollback()
            logger.error(f"删除插件表失败: {e}")
            return {'success': False, 'error': str(e), 'dropped_tables': dropped_tables}

    @staticmethod
    def isolate_user_data(db: Session, user_id: int, industry: str) -> Dict:
        """
        隔离用户数据
        根据用户选择的行业，确保用户只能访问自己行业的数据
        """
        from models.user_models import User
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {'success': False, 'error': '用户不存在'}

        user.industry = industry
        db.commit()

        return {
            'success': True,
            'message': f'用户数据已隔离到 {industry} 行业',
            'user_id': user_id,
            'industry': industry
        }

    @staticmethod
    def get_user_industry(db: Session, user_id: int) -> Optional[str]:
        """获取用户所属行业"""
        from models.user_models import User
        
        user = db.query(User).filter(User.id == user_id).first()
        return user.industry if user else None

    @staticmethod
    def check_data_access(db: Session, user_id: int, table_name: str, record_id: int = None) -> bool:
        """
        检查用户是否有权限访问数据
        """
        industry = DataIsolationService.get_user_industry(db, user_id)
        if not industry:
            return True

        prefix = DataIsolationService.get_table_prefix(industry)
        return table_name.startswith(prefix) or table_name.startswith('t_core_')

    @staticmethod
    def migrate_data(db: Session, from_industry: str, to_industry: str, user_id: int = None) -> Dict:
        """
        迁移用户数据从一个行业到另一个行业
        """
        from_prefix = DataIsolationService.get_table_prefix(from_industry)
        to_prefix = DataIsolationService.get_table_prefix(to_industry)
        
        from_tables = DataIsolationService.get_tables_for_plugin(db, from_industry)
        migrated_tables = []

        try:
            for from_table in from_tables:
                to_table = from_table.replace(from_prefix, to_prefix)
                
                existing_tables = DataIsolationService.get_tables_for_plugin(db, to_industry)
                if to_table not in existing_tables:
                    db.execute(text(f"CREATE TABLE IF NOT EXISTS `{to_table}` LIKE `{from_table}`"))
                
                if user_id:
                    db.execute(text(f"INSERT INTO `{to_table}` SELECT * FROM `{from_table}` WHERE user_id = {user_id}"))
                else:
                    db.execute(text(f"INSERT INTO `{to_table}` SELECT * FROM `{from_table}`"))
                
                migrated_tables.append({
                    'from': from_table,
                    'to': to_table
                })

            db.commit()
            return {'success': True, 'migrated_tables': migrated_tables}
        except Exception as e:
            db.rollback()
            logger.error(f"迁移数据失败: {e}")
            return {'success': False, 'error': str(e), 'migrated_tables': migrated_tables}

    @staticmethod
    def get_industry_data_stats(db: Session, user_id: int, industry: str) -> Dict:
        """
        获取用户在特定行业的数据统计
        """
        prefix = DataIsolationService.get_table_prefix(industry)
        tables = DataIsolationService.get_tables_for_plugin(db, industry)
        
        stats = {}
        for table in tables:
            try:
                count_result = db.execute(text(f"SELECT COUNT(*) FROM `{table}` WHERE user_id = {user_id}"))
                count = count_result.scalar()
                stats[table.replace(prefix, '')] = count
            except Exception:
                pass

        return stats

    @staticmethod
    def validate_plugin_data(db: Session, plugin_code: str) -> Dict:
        """
        验证插件数据完整性
        """
        prefix = DataIsolationService.get_table_prefix(plugin_code)
        tables = DataIsolationService.get_tables_for_plugin(db, plugin_code)
        
        validation = {
            'plugin_code': plugin_code,
            'tables_found': len(tables),
            'tables': [],
            'errors': []
        }

        for table in tables:
            try:
                row_count = db.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar()
                validation['tables'].append({
                    'name': table,
                    'row_count': row_count,
                    'status': 'ok'
                })
            except Exception as e:
                validation['tables'].append({
                    'name': table,
                    'row_count': 0,
                    'status': 'error',
                    'error': str(e)
                })
                validation['errors'].append(f"{table}: {e}")

        return validation


data_isolation_service = DataIsolationService()