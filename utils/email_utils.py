"""
邮件发送工具
- SMTP邮件发送
- 报表附件发送
"""
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import date
from typing import List, Dict
from config.settings import settings

logger = logging.getLogger(__name__)


class EmailSender:
    """邮件发送器"""

    def __init__(self):
        self.smtp_host = getattr(settings, 'SMTP_HOST', None)
        self.smtp_port = getattr(settings, 'SMTP_PORT', 587)
        self.smtp_user = getattr(settings, 'SMTP_USER', None)
        self.smtp_password = getattr(settings, 'SMTP_PASSWORD', None)
        self.from_email = getattr(settings, 'FROM_EMAIL', None)

    def send_daily_report(self, excel_path: str, report_date: date, orders: List[Dict]) -> bool:
        """
        发送日报表邮件

        Args:
            excel_path: Excel报表文件路径
            report_date: 报表日期
            orders: 订单列表

        Returns:
            是否发送成功
        """
        if not all([self.smtp_host, self.smtp_user, self.smtp_password, self.from_email]):
            logger.warning("SMTP配置不完整,跳过邮件发送")
            return False

        try:
            # 计算汇总数据
            total_orders = len(orders)
            total_amount = sum(o['total_amount'] for o in orders)

            # 构建邮件内容
            subject = f"配送日报 - {report_date.isoformat()} - 共{total_orders}单"

            html_body = self._build_html_body(report_date, total_orders, total_amount, orders)

            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['Subject'] = subject

            # 收件人
            recipients = getattr(settings, 'REPORT_RECIPIENTS', '').split(',')
            recipients = [r.strip() for r in recipients if r.strip()]

            if not recipients:
                logger.warning("未配置收件人,跳过邮件发送")
                return False

            msg['To'] = ', '.join(recipients)

            # 添加HTML正文
            msg.attach(MIMEText(html_body, 'html', 'utf-8'))

            # 添加Excel附件
            with open(excel_path, 'rb') as f:
                attachment = MIMEBase('application', 'octet-stream')
                attachment.set_payload(f.read())
                encoders.encode_base64(attachment)
                attachment.add_header(
                    'Content-Disposition',
                    f'attachment; filename="配送报表_{report_date.isoformat()}.xlsx"'
                )
                msg.attach(attachment)

            # 发送邮件
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.ehlo()
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.sendmail(self.from_email, recipients, msg.as_string())
            server.quit()

            logger.info(f"邮件发送成功: {len(recipients)}个收件人")
            return True

        except Exception as e:
            logger.error(f"邮件发送失败: {e}", exc_info=True)
            return False

    def _build_html_body(self, report_date: date, total_orders: int,
                         total_amount: float, orders: List[Dict]) -> str:
        """构建HTML邮件正文"""

        # 按线路统计
        route_stats = {}
        for order in orders:
            customer = order.get('customer', {}) or {}
            route = customer.get('route', {}) or {}
            route_name = route.get('route_name', '未分配')

            if route_name not in route_stats:
                route_stats[route_name] = {'count': 0, 'amount': 0.0}
            route_stats[route_name]['count'] += 1
            route_stats[route_name]['amount'] += order['total_amount']

        # 构建HTML
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background-color: #4472C4; color: white; padding: 20px; }}
                .summary {{ margin: 20px 0; }}
                .summary table {{ border-collapse: collapse; width: 100%; }}
                .summary th, .summary td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
                .summary th {{ background-color: #f2f2f2; }}
                .footer {{ margin-top: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>配送日报</h2>
                <p>日期: {report_date.isoformat()}</p>
            </div>

            <div class="summary">
                <h3>今日概览</h3>
                <table>
                    <tr>
                        <th>总订单数</th>
                        <th>总金额</th>
                    </tr>
                    <tr>
                        <td>{total_orders} 单</td>
                        <td>¥{total_amount:.2f}</td>
                    </tr>
                </table>
            </div>

            <div class="summary">
                <h3>按线路汇总</h3>
                <table>
                    <tr>
                        <th>线路名称</th>
                        <th>订单数</th>
                        <th>金额</th>
                    </tr>
        """

        for route_name, stats in sorted(route_stats.items()):
            html += f"""
                    <tr>
                        <td>{route_name}</td>
                        <td>{stats['count']} 单</td>
                        <td>¥{stats['amount']:.2f}</td>
                    </tr>
            """

        html += f"""
                </table>
            </div>

            <div class="footer">
                <p>此邮件由系统自动发送,请勿回复。</p>
                <p>详细报表请查看附件。</p>
            </div>
        </body>
        </html>
        """

        return html

    def send_test_email(self, to_email: str) -> bool:
        """发送测试邮件"""
        if not all([self.smtp_host, self.smtp_user, self.smtp_password, self.from_email]):
            logger.warning("SMTP配置不完整")
            return False

        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = "测试邮件"

            msg.attach(MIMEText("这是一封测试邮件,用于验证SMTP配置是否正确。", 'plain', 'utf-8'))

            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.ehlo()
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.sendmail(self.from_email, [to_email], msg.as_string())
            server.quit()

            logger.info(f"测试邮件发送成功: {to_email}")
            return True

        except Exception as e:
            logger.error(f"测试邮件发送失败: {e}", exc_info=True)
            return False
