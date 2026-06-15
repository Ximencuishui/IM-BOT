"""
订单解析服务单元测试
"""
import sys
import os
import pytest

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.order_parser import parse_order_message


class TestOrderParser:
    """订单解析器测试类"""

    def test_parse_simple_order(self):
        """测试简单订单解析"""
        result = parse_order_message("来10斤土豆")

        assert result['success'] == True
        assert len(result['items']) == 1
        assert result['items'][0]['product_name'] == '土豆'
        assert result['items'][0]['quantity'] == 10.0

    def test_parse_with_remark(self):
        """测试带备注的订单"""
        result = parse_order_message("土豆10斤,要嫩的")

        assert result['success'] == True
        assert len(result['remarks']) > 0

    def test_parse_multiple_items(self):
        """测试多个商品"""
        result = parse_order_message("10斤土豆,5斤白菜")

        assert result['success'] == True
        assert len(result['items']) >= 1

    def test_parse_shortcut_code(self):
        """测试快捷码识别"""
        result = parse_order_message("TD 10斤")

        assert result['success'] == True

    def test_parse_empty_content(self):
        """测试空内容"""
        result = parse_order_message("")

        assert result['success'] == False
        assert result['error'] is not None

    def test_parse_unknown_product(self):
        """测试未知商品"""
        result = parse_order_message("来10斤榴莲")

        # 榴莲不在商品库中,应该失败
        assert result['success'] == False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
