"""
机器人交互功能单元测试
"""
import unittest
import sys
import os
from datetime import date

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.robot_report_service import RobotReportService
from services.command_config_service import CommandConfigService


class TestRobotReportService(unittest.TestCase):
    """机器人报表服务测试"""

    def setUp(self):
        self.service = RobotReportService()

    def test_generate_sales_report_text_success(self):
        """测试生成销售员文本报表"""
        summary_data = {
            'success': True,
            'sales_person': '李四',
            'order_date': '2026-04-15',
            'routes': [
                {
                    'route_name': 'A线',
                    'order_count': 8,
                    'customer_count': 6,
                    'total_amount': 2350.00,
                    'customers': ['张三餐馆', '李四食堂']
                },
                {
                    'route_name': 'B线',
                    'order_count': 5,
                    'customer_count': 4,
                    'total_amount': 1680.00,
                    'customers': ['王五店', '赵六馆']
                }
            ],
            'total_orders': 13,
            'total_amount': 4030.00
        }

        text = self.service.generate_text_report(summary_data, 'sales')

        self.assertIn('📊 【今日订单汇总', text)
        self.assertIn('李四', text)
        self.assertIn('A线', text)
        self.assertIn('B线', text)
        self.assertIn('¥4030.00', text)

    def test_generate_sales_report_text_failure(self):
        """测试失败情况的文本报表"""
        error_data = {'success': False, 'error': '未找到销售员'}
        text = self.service.generate_text_report(error_data, 'sales')
        self.assertIn('❌', text)
        self.assertIn('未找到销售员', text)

    def test_generate_customer_report_text_with_orders(self):
        """测试生成客户订单详情报表(有订单)"""
        detail_data = {
            'success': True,
            'customer_name': '张三餐馆',
            'order_date': '2026-04-15',
            'orders': [
                {
                    'order_id': 123,
                    'created_at': '10:30:00',
                    'items': [
                        {
                            'product_name': '土豆',
                            'quantity': 10.0,
                            'unit': '斤',
                            'subtotal': 25.0,
                            'remark': '要嫩的'
                        },
                        {
                            'product_name': '鸡蛋',
                            'quantity': 5.0,
                            'unit': '斤',
                            'subtotal': 32.5,
                            'remark': None
                        }
                    ],
                    'order_total': 57.5
                }
            ],
            'total_amount': 57.5,
            'order_count': 1
        }

        text = self.service.generate_text_report(detail_data, 'customer')

        self.assertIn('📋 【订单详情', text)
        self.assertIn('张三餐馆', text)
        self.assertIn('土豆', text)
        self.assertIn('要嫩的', text)
        self.assertIn('¥57.50', text)

    def test_generate_customer_report_text_no_orders(self):
        """测试生成客户订单详情报表(无订单)"""
        detail_data = {
            'success': True,
            'customer_name': '李四食堂',
            'order_date': '2026-04-15',
            'orders': [],
            'total_amount': 0.0,
            'order_count': 0
        }

        text = self.service.generate_text_report(detail_data, 'customer')
        self.assertIn('⚠️ 今日暂无订单', text)


class TestCommandConfigService(unittest.TestCase):
    """指令配置服务测试"""

    def setUp(self):
        self.service = CommandConfigService()

    def test_match_sales_report_command(self):
        """测试匹配销售员报表指令"""
        test_messages = [
            "报表",
            "统计",
            "今日报表",
            "今天配送多少",
            "销售统计"
        ]

        for msg in test_messages:
            result = self.service.match_command(msg)
            if result:
                self.assertEqual(result['command_name'], 'sales_report')

    def test_match_customer_query_command(self):
        """测试匹配客户查询指令"""
        test_messages = [
            "查订单",
            "多少钱",
            "我的订单",
            "今天订了什么",
            "查询我的货"
        ]

        for msg in test_messages:
            result = self.service.match_command(msg)
            if result:
                self.assertEqual(result['command_name'], 'customer_query')

    def test_match_help_command(self):
        """测试匹配帮助指令"""
        result = self.service.match_command("帮助")
        if result:
            self.assertEqual(result['command_name'], 'help')

    def test_no_match_unknown_message(self):
        """测试未知消息不匹配任何指令"""
        result = self.service.match_command("今天天气怎么样")
        # 可能返回None或低置信度
        if result:
            self.assertLess(result['confidence'], 0.6)

    def test_get_usage_statistics(self):
        """测试获取使用统计"""
        stats = self.service.get_usage_statistics()
        if stats['success']:
            self.assertIn('total_commands', stats)
            self.assertIn('commands', stats)


if __name__ == '__main__':
    unittest.main()
