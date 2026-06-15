"""
批量圈选和增量操作解析器单元测试
"""
import unittest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.order_parser import BatchSelectionParser, IncrementalParser


class TestBatchSelectionParser(unittest.TestCase):
    """批量圈选解析器测试"""

    def setUp(self):
        self.parser = BatchSelectionParser()

    def test_parse_simple_range(self):
        """测试简单范围解析: "下单 1-10 5斤" """
        result = self.parser.parse_batch_syntax("下单 1-10 5斤")
        self.assertIsNotNone(result)
        self.assertEqual(result['product_indices'], list(range(1, 11)))
        self.assertEqual(result['quantity'], 5.0)
        self.assertEqual(result['unit'], '斤')

    def test_parse_with_exclusion(self):
        """测试排除项解析: "下单 1-10 除3,7 5斤" """
        result = self.parser.parse_batch_syntax("下单 1-10 除3,7 5斤")
        self.assertIsNotNone(result)
        expected = [1, 2, 4, 5, 6, 8, 9, 10]  # 排除了3和7
        self.assertEqual(result['product_indices'], expected)
        self.assertEqual(result['quantity'], 5.0)

    def test_parse_comma_separated(self):
        """测试逗号分隔解析: "圈选 1,3,5 10斤" """
        result = self.parser.parse_batch_syntax("圈选 1,3,5 10斤")
        self.assertIsNotNone(result)
        self.assertEqual(result['product_indices'], [1, 3, 5])
        self.assertEqual(result['quantity'], 10.0)

    def test_parse_mixed_range(self):
        """测试混合范围解析: "下单 1-3,5,7-9 5斤" """
        result = self.parser.parse_batch_syntax("下单 1-3,5,7-9 5斤")
        self.assertIsNotNone(result)
        self.assertEqual(result['product_indices'], [1, 2, 3, 5, 7, 8, 9])

    def test_parse_range_string(self):
        """测试范围字符串解析"""
        self.assertEqual(self.parser._parse_range("1-5"), [1, 2, 3, 4, 5])
        self.assertEqual(self.parser._parse_range("1,3,5"), [1, 3, 5])
        self.assertEqual(self.parser._parse_range("1-3,5,7-9"), [1, 2, 3, 5, 7, 8, 9])

    def test_map_indices_to_products(self):
        """测试序号映射到商品"""
        route_products = [
            {'sort_order': 1, 'product_id': 1, 'product_name': '土豆', 'price': 2.5},
            {'sort_order': 2, 'product_id': 2, 'product_name': '鸡蛋', 'price': 6.5},
            {'sort_order': 3, 'product_id': 3, 'product_name': '白菜', 'price': 1.8},
            {'sort_order': 4, 'product_id': 4, 'product_name': '萝卜', 'price': 2.0},
            {'sort_order': 5, 'product_id': 5, 'product_name': '青菜', 'price': 3.0},
        ]

        indices = [1, 3, 5]
        products = self.parser.map_indices_to_products(indices, route_products)

        self.assertEqual(len(products), 3)
        self.assertEqual(products[0]['product_name'], '土豆')
        self.assertEqual(products[1]['product_name'], '白菜')
        self.assertEqual(products[2]['product_name'], '青菜')

    def test_invalid_syntax(self):
        """测试无效语法"""
        result = self.parser.parse_batch_syntax("来10斤土豆")
        self.assertIsNone(result)


class TestIncrementalParser(unittest.TestCase):
    """增量操作解析器测试"""

    def setUp(self):
        self.parser = IncrementalParser()

    def test_detect_add_operation_plus(self):
        """测试加法操作检测: "鸡蛋+5斤" """
        result = self.parser.detect_incremental_syntax("鸡蛋+5斤")
        self.assertIsNotNone(result)
        self.assertEqual(result['product_name'], '鸡蛋')
        self.assertEqual(result['operation'], 'add')
        self.assertEqual(result['quantity'], 5.0)

    def test_detect_add_operation_chinese(self):
        """测试加法操作检测(中文): "鸡蛋 加5斤" """
        result = self.parser.detect_incremental_syntax("鸡蛋 加5斤")
        self.assertIsNotNone(result)
        self.assertEqual(result['product_name'], '鸡蛋')
        self.assertEqual(result['operation'], 'add')

    def test_detect_subtract_operation_dash(self):
        """测试减法操作检测: "鸡蛋-3斤" """
        result = self.parser.detect_incremental_syntax("鸡蛋-3斤")
        self.assertIsNotNone(result)
        self.assertEqual(result['operation'], 'subtract')
        self.assertEqual(result['quantity'], 3.0)

    def test_detect_subtract_operation_chinese(self):
        """测试减法操作检测(中文): "鸡蛋 减3斤" """
        result = self.parser.detect_incremental_syntax("鸡蛋 减3斤")
        self.assertIsNotNone(result)
        self.assertEqual(result['operation'], 'subtract')

    def test_detect_replace_operation_equals(self):
        """测试替换操作检测: "鸡蛋=15斤" """
        result = self.parser.detect_incremental_syntax("鸡蛋=15斤")
        self.assertIsNotNone(result)
        self.assertEqual(result['operation'], 'replace')
        self.assertEqual(result['quantity'], 15.0)

    def test_detect_replace_operation_chinese(self):
        """测试替换操作检测(中文): "鸡蛋 改为15斤" """
        result = self.parser.detect_incremental_syntax("鸡蛋 改为15斤")
        self.assertIsNotNone(result)
        self.assertEqual(result['operation'], 'replace')

    def test_invalid_syntax(self):
        """测试无效语法"""
        result = self.parser.detect_incremental_syntax("来10斤土豆")
        self.assertIsNone(result)

    def test_with_different_units(self):
        """测试不同单位"""
        result = self.parser.detect_incremental_syntax("土豆+3箱")
        self.assertIsNotNone(result)
        self.assertEqual(result['quantity'], 3.0)
        self.assertEqual(result['unit'], '箱')


if __name__ == '__main__':
    unittest.main()
