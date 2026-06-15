"""
网站端超级管理员初始化脚本
创建网站后台管理系统的超级管理员账号: admin/12345678
"""
import sys
import os

# 设置控制台编码为UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_config import init_db, get_db_session
from models.user_models import User
from services.auth_service import AuthService


def init_super_admin():
    """初始化网站端超级管理员账号"""
    print("=" * 60)
    print("网站端超级管理员初始化")
    print("=" * 60)

    # 初始化数据库
    try:
        print("\n正在初始化数据库...")
        init_db()
        print("[OK] 数据库初始化完成")
    except Exception as e:
        print(f"[ERROR] 数据库初始化失败: {e}")
        return False

    db = get_db_session()

    try:
        # 检查是否已存在admin账号
        existing_admin = db.query(User).filter(User.email == 'admin@web.local').first()
        if existing_admin:
            print("\n[WARN] 检测到已存在admin账号")
            print(f"  邮箱: {existing_admin.email}")
            print(f"  用户名: {existing_admin.username}")
            print(f"  创建时间: {existing_admin.created_at}")

            choice = input("\n是否重置密码为默认值 12345678? (y/n): ")
            if choice.lower() == 'y':
                existing_admin.password_hash = AuthService.hash_password('12345678')
                existing_admin.role = 'super_admin'
                db.commit()
                print("[OK] 密码已重置为: 12345678")
                print("[OK] 角色已设置为: super_admin")
            else:
                print("[CANCEL] 操作已取消")
            return

        # 检查是否已有其他用户
        user_count = db.query(User).count()
        if user_count > 0:
            print(f"\n[WARN] 系统中已存在 {user_count} 个用户")
            choice = input("是否仍要创建超级管理员账号? (y/n): ")
            if choice.lower() != 'y':
                print("[CANCEL] 操作已取消")
                return

        # 创建超级管理员账号
        print("\n正在创建超级管理员账号...")
        result = AuthService.register(
            db,
            email='admin@web.local',
            password='12345678',
            username='admin',
            company_name='网站管理中心',
            phone='13800138000',
            subscription_type='yearly',
            max_groups=9999
        )

        if result['success']:
            # 设置超级管理员角色
            admin_user = db.query(User).filter(User.email == 'admin@web.local').first()
            if admin_user:
                admin_user.role = 'super_admin'
                admin_user.is_active = True
                db.commit()

                print("\n" + "=" * 60)
                print("[SUCCESS] 超级管理员账号创建成功!")
                print("=" * 60)
                print(f"  登录地址: http://localhost:5173 (启动 tonjclaw-web Vue 项目)")
                print(f"  邮箱: admin@web.local")
                print(f"  用户名: admin")
                print(f"  密码: 12345678")
                print("=" * 60)
                print("[WARN] 请立即登录并修改默认密码以确保安全!")
                print("=" * 60)
        else:
            print(f"\n[ERROR] 超级管理员账号创建失败: {result.get('error')}")
            return False

        return True

    except Exception as e:
        print(f"\n[ERROR] 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == '__main__':
    success = init_super_admin()
    sys.exit(0 if success else 1)
