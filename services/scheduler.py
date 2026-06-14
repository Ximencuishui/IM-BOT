"""
定时任务调度器
处理自动续费等定时任务
"""
import time
import threading
from datetime import datetime
from database.db_config import get_db_session
from services.auto_renew_service import AutoRenewService
import logging

logger = logging.getLogger(__name__)


class SchedulerService:
    """定时任务服务类"""
    
    def __init__(self):
        self.running = False
        self.thread = None
    
    def start(self):
        """启动定时任务调度器"""
        if self.running:
            return

        try:
            import schedule as schedule_mod
        except ImportError:
            logger.warning('未安装 schedule 包，已跳过定时任务（pip install schedule）')
            return

        self._schedule = schedule_mod
        self.running = True
        
        # 设置定时任务
        # 每天凌晨2点执行自动续费检查
        schedule_mod.every().day.at("02:00").do(self.run_auto_renew_check)
        
        # 每天早上9点发送续费提醒
        schedule_mod.every().day.at("09:00").do(self.run_renewal_notification_check)
        
        # 每小时执行一次状态检查（用于测试）
        schedule_mod.every().hour.do(self.run_hourly_check)
        
        # 启动调度线程
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        
        logger.info("定时任务调度器已启动")
    
    def stop(self):
        """停止定时任务调度器"""
        self.running = False
        if self.thread:
            self.thread.join()
        logger.info("定时任务调度器已停止")
    
    def _run_scheduler(self):
        """运行调度器循环"""
        schedule_mod = getattr(self, '_schedule', None)
        if not schedule_mod:
            return
        while self.running:
            schedule_mod.run_pending()
            time.sleep(60)  # 每分钟检查一次
    
    def run_auto_renew_check(self):
        """执行自动续费检查"""
        logger.info(f"开始执行自动续费检查 - {datetime.now()}")
        
        db = get_db_session()
        try:
            result = AutoRenewService.process_auto_renewals(db)
            
            if result['success']:
                logger.info(f"自动续费完成: 成功 {result['renewed_count']} 个, "
                          f"失败 {result['failed_count']} 个")
                
                if result['errors']:
                    logger.warning(f"自动续费错误: {result['errors']}")
            else:
                logger.error(f"自动续费失败: {result['error']}")
                
        except Exception as e:
            logger.error(f"自动续费检查异常: {str(e)}")
        finally:
            db.close()
    
    def run_hourly_check(self):
        """每小时执行的检查任务（用于监控和测试）"""
        logger.debug(f"执行每小时检查 - {datetime.now()}")
        
        # 这里可以添加其他定时检查逻辑
        # 例如：检查系统健康状态、清理过期数据等
    
    def run_renewal_notification_check(self):
        """执行续费提醒检查"""
        logger.info(f"开始执行续费提醒检查 - {datetime.now()}")
        
        from services.renewal_notification_service import RenewalNotificationService
        
        db = get_db_session()
        try:
            result = RenewalNotificationService.process_renewal_notifications(db)
            
            if result['success']:
                logger.info(f"续费提醒完成: 总计 {result['total_notifications']} 条, "
                          f"邮件 {result['email_sent']} 条, 短信 {result['sms_sent']} 条")
                
                if result['errors']:
                    logger.warning(f"续费提醒错误: {result['errors']}")
            else:
                logger.error(f"续费提醒失败: {result['error']}")
                
        except Exception as e:
            logger.error(f"续费提醒检查异常: {str(e)}")
        finally:
            db.close()


# 全局调度器实例
scheduler_service = SchedulerService()


def init_scheduler():
    """初始化并启动调度器"""
    scheduler_service.start()


def shutdown_scheduler():
    """关闭调度器"""
    scheduler_service.stop()
