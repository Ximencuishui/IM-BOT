"""
数据库迁移脚本：为商品表添加属性、佣金、积分字段
支持SQLite和MySQL
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import sqlite3
import json
from database.db_config import get_db_session
from config.settings import settings

def migrate_sqlite():
    """SQLite数据库迁移"""
    print("🔄 开始SQLite数据库迁移...")
    
    # 获取数据库路径
    db_path = settings.SQLITE_DB_PATH
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        print("请先运行系统初始化数据库")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(t_product)")
        columns = [row[1] for row in cursor.fetchall()]
        
        # 添加 attributes 字段（SQLite使用TEXT存储JSON）
        if 'attributes' not in columns:
            print("✅ 添加 attributes 字段...")
            cursor.execute("""
                ALTER TABLE t_product 
                ADD COLUMN attributes TEXT DEFAULT '[]'
            """)
        else:
            print("⚠️  attributes 字段已存在，跳过")
        
        # 添加 commission 字段
        if 'commission' not in columns:
            print("✅ 添加 commission 字段...")
            cursor.execute("""
                ALTER TABLE t_product 
                ADD COLUMN commission REAL DEFAULT 0.0
            """)
        else:
            print("⚠️  commission 字段已存在，跳过")
        
        # 添加 points 字段
        if 'points' not in columns:
            print("✅ 添加 points 字段...")
            cursor.execute("""
                ALTER TABLE t_product 
                ADD COLUMN points INTEGER DEFAULT 0
            """)
        else:
            print("⚠️  points 字段已存在，跳过")
        
        conn.commit()
        
        # 验证迁移结果
        cursor.execute("PRAGMA table_info(t_product)")
        columns = cursor.fetchall()
        print("\n📊 t_product 表当前字段：")
        for col in columns:
            print(f"   - {col[1]} ({col[2]})")
        
        conn.close()
        print("\n✅ SQLite数据库迁移成功！")
        return True
        
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def migrate_mysql():
    """MySQL数据库迁移"""
    print("🔄 开始MySQL数据库迁移...")
    
    try:
        from sqlalchemy import text
        db = get_db_session()
        
        # 检查字段是否已存在
        check_sql = """
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 't_product'
            AND COLUMN_NAME IN ('attributes', 'commission', 'points')
        """
        result = db.execute(text(check_sql))
        existing_columns = [row[0] for row in result.fetchall()]
        
        # 添加 attributes 字段
        if 'attributes' not in existing_columns:
            print("✅ 添加 attributes 字段...")
            db.execute(text("""
                ALTER TABLE t_product 
                ADD COLUMN attributes JSON COMMENT '商品属性JSON数组,最多10个属性'
            """))
        else:
            print("⚠️  attributes 字段已存在，跳过")
        
        # 添加 commission 字段
        if 'commission' not in existing_columns:
            print("✅ 添加 commission 字段...")
            db.execute(text("""
                ALTER TABLE t_product 
                ADD COLUMN commission DECIMAL(10, 2) DEFAULT 0.00 COMMENT '佣金(元)'
            """))
        else:
            print("⚠️  commission 字段已存在，跳过")
        
        # 添加 points 字段
        if 'points' not in existing_columns:
            print("✅ 添加 points 字段...")
            db.execute(text("""
                ALTER TABLE t_product 
                ADD COLUMN points INT DEFAULT 0 COMMENT '积分'
            """))
        else:
            print("⚠️  points 字段已存在，跳过")
        
        db.commit()
        
        # 验证迁移结果
        result = db.execute(text("""
            SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_COMMENT
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 't_product'
            AND COLUMN_NAME IN ('attributes', 'commission', 'points')
        """))
        
        print("\n📊 新增字段详情：")
        for row in result.fetchall():
            print(f"   - {row[0]}: {row[1]} - {row[2]}")
        
        db.close()
        print("\n✅ MySQL数据库迁移成功！")
        return True
        
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("=" * 60)
    print("📦 商品属性与统计参数 - 数据库迁移工具")
    print("=" * 60)
    print(f"📌 当前数据库类型: {settings.DB_TYPE.upper()}")
    print(f"📌 数据库路径/连接: {settings.DATABASE_URL}")
    print("=" * 60)
    print()
    
    # 根据数据库类型执行相应的迁移
    if settings.DB_TYPE == 'sqlite':
        success = migrate_sqlite()
    else:
        success = migrate_mysql()
    
    print()
    if success:
        print("🎉 迁移完成！可以重启服务使用新功能了。")
    else:
        print("⚠️  迁移过程中出现错误，请检查日志。")
    
    print("=" * 60)
