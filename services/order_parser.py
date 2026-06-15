"""
订单解析服务
从自然语言消息中提取商品信息、数量、备注
支持规则引擎 + jieba分词模糊匹配
"""
import re
import json
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import jieba

from config.settings import settings
from services.ai_parser import parse_order_with_ai, is_ai_enabled

logger = logging.getLogger(__name__)


class ProductMatcher:
    """商品匹配器"""

    def __init__(self):
        self.products = []
        self.shortcut_map = {}  # 快捷码 -> 商品
        self.name_map = {}  # 商品名 -> 商品
        self._load_products()

    def _load_products(self):
        """从数据库加载商品数据"""
        try:
            from database.db_config import get_db_session
            from models.models import Product
            
            db = get_db_session()
            products = db.query(Product).filter(Product.is_active == 1).all()
            
            for prod in products:
                product = {
                    'id': prod.id,
                    'name': prod.product_name,
                    'shortcuts': prod.shortcut_codes.split(',') if prod.shortcut_codes else [],
                    'unit': prod.unit or '斤',
                    'price': float(prod.price) if prod.price else 0.0
                }
                self.products.append(product)

                # 建立快捷码索引
                for shortcut in product['shortcuts']:
                    self.shortcut_map[shortcut.strip().lower()] = product

                # 建立商品名索引
                self.name_map[prod.product_name] = product
            
            db.close()
            logger.info(f"从数据库加载商品数据成功: {len(self.products)}个商品")
        except Exception as e:
            logger.error(f"从数据库加载商品数据失败: {e}，尝试使用JSON文件")
            self._load_products_from_json()
    
    def _load_products_from_json(self):
        """从JSON文件加载商品数据（备用方案）"""
        try:
            with open('data/products.json', 'r', encoding='utf-8') as f:
                data = json.load(f)

            for prod in data['products']:
                product = {
                    'id': prod['id'],
                    'name': prod['name'],
                    'shortcuts': prod['shortcuts'],
                    'unit': prod['unit'],
                    'price': prod['price']
                }
                self.products.append(product)

                # 建立快捷码索引
                for shortcut in prod['shortcuts']:
                    self.shortcut_map[shortcut.lower()] = product

                # 建立商品名索引
                self.name_map[prod['name']] = product

            logger.info(f"从JSON文件加载商品数据成功: {len(self.products)}个商品")
        except Exception as e:
            logger.error(f"加载商品数据失败: {e}")

    def match_product(self, text: str) -> Optional[Dict]:
        """
        从文本中匹配商品
        优先级: 精确匹配 > 快捷码匹配 > jieba分词模糊匹配
        """
        text_lower = text.lower()

        # 1. 精确匹配商品名
        for name, product in self.name_map.items():
            if name in text:
                logger.debug(f"精确匹配商品: {name}")
                return product

        # 2. 快捷码匹配
        for shortcut, product in self.shortcut_map.items():
            if shortcut in text_lower:
                logger.debug(f"快捷码匹配商品: {product['name']} (匹配:{shortcut})")
                return product

        # 3. jieba分词模糊匹配
        words = jieba.lcut(text)
        for word in words:
            word_stripped = word.strip().lower()
            if word_stripped in self.shortcut_map:
                product = self.shortcut_map[word_stripped]
                logger.debug(f"分词匹配商品: {product['name']} (匹配:{word_stripped})")
                return product

        return None


class QuantityExtractor:
    """数量提取器"""

    # 数量正则模式
    PATTERNS = [
        r'(\d+\.?\d*)\s*(斤|两|箱|包|个|公斤)',  # "10斤", "5.5箱"
        r'(半)\s*(斤|两|箱|包|个)',  # "半斤"
        r'(\d+\.?\d*)',  # 纯数字(默认单位)
    ]

    UNIT_CONVERSION = {
        '斤': 1.0,
        '公斤': 2.0,  # 1公斤 = 2斤
        '两': 0.1,  # 1两 = 0.1斤
        '箱': 1.0,
        '包': 1.0,
        '个': 1.0
    }

    def extract(self, text: str, default_unit: str = '斤') -> Tuple[float, str]:
        """
        从文本中提取数量和单位
        返回: (数量, 标准化单位)
        """
        for pattern in self.PATTERNS:
            match = re.search(pattern, text)
            if match:
                if match.group(1) == '半':
                    quantity = 0.5
                    unit = match.group(2) if len(match.groups()) > 1 else default_unit
                else:
                    quantity = float(match.group(1))
                    unit = match.group(2) if len(match.groups()) > 1 else default_unit

                # 转换为标准单位
                standardized_quantity = quantity * self.UNIT_CONVERSION.get(unit, 1.0)
                logger.debug(f"提取数量: {quantity}{unit} -> {standardized_quantity}斤")
                return standardized_quantity, '斤'

        # 未找到数量,默认1斤
        logger.warning(f"未找到数量信息,使用默认值: 1{default_unit}")
        return 1.0, default_unit


class RemarkExtractor:
    """备注提取器"""

    # 常见备注关键词
    REMARK_PATTERNS = [
        r'(要|不要|加|减|免|多|少)(.+?)(?=，|。|$|\d)',
    ]

    def extract(self, text: str) -> List[str]:
        """提取备注信息"""
        remarks = []

        for pattern in self.REMARK_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                remark = match.group(0).strip()
                if remark and len(remark) > 1:
                    remarks.append(remark)

        return remarks


class BatchSelectionParser:
    """批量圈选解析器"""

    def parse_batch_syntax(self, content: str, route_id: int = None) -> Optional[Dict]:
        """
        解析批量圈选语法

        支持格式:
        - "下单 1-10 5斤"
        - "下单 1-10 除3,7 5斤"
        - "圈选 1,3,5-8 10斤"

        返回:
        {
            "product_indices": [1,2,3,4,5,6,7,8,9,10],  # 排除后的索引列表
            "quantity": 5.0,
            "unit": "斤"
        }
        """
        # 正则匹配批量语法
        pattern = r'(?:下单|圈选)\s+(\d+(?:,\d+|-?\d+)*)\s+(?:除([\d,]+)\s+)?(\d+\.?\d*)\s*(斤|两|箱|包|个|公斤)?'
        match = re.search(pattern, content)

        if not match:
            return None

        range_str = match.group(1)  # "1-10" 或 "1,3,5"
        exclude_str = match.group(2)  # "3,7" (可选)
        quantity = float(match.group(3))
        unit = match.group(4) or '斤'

        # 解析索引范围
        indices = self._parse_range(range_str)

        # 处理排除项
        if exclude_str:
            exclude_indices = [int(x) for x in exclude_str.split(',')]
            indices = [i for i in indices if i not in exclude_indices]

        return {
            'product_indices': indices,
            'quantity': quantity,
            'unit': unit
        }

    def _parse_range(self, range_str: str) -> List[int]:
        """解析范围字符串: "1-10" -> [1,2,3,...,10], "1,3,5" -> [1,3,5]"""
        indices = []
        parts = range_str.split(',')

        for part in parts:
            if '-' in part:
                start, end = map(int, part.split('-'))
                indices.extend(range(start, end + 1))
            else:
                indices.append(int(part))

        return sorted(set(indices))  # 去重并排序

    def map_indices_to_products(self, indices: List[int],
                                 route_products: List[Dict]) -> List[Dict]:
        """
        将序号映射到实际商品

        参数:
        - indices: [1, 2, 3, 5] (客户圈选的序号)
        - route_products: 线路产品清单(已按sort_order排序)

        返回:
        [
            {"product_id": 1, "product_name": "土豆", ...},
            {"product_id": 2, "product_name": "鸡蛋", ...},
            ...
        ]
        """
        products = []
        for idx in indices:
            # 序号从1开始，列表索引从0开始
            if 1 <= idx <= len(route_products):
                products.append(route_products[idx - 1])

        return products


class IncrementalParser:
    """增量操作解析器"""

    def detect_incremental_syntax(self, content: str) -> Optional[Dict]:
        """
        检测增量语法

        支持格式:
        - "鸡蛋+5斤" / "鸡蛋 加5斤"
        - "鸡蛋-3斤" / "鸡蛋 减3斤"
        - "鸡蛋=15斤" / "鸡蛋 改为15斤" (直接替换)

        返回:
        {
            "product_name": "鸡蛋",
            "operation": "add",  # add/subtract/replace
            "quantity": 5.0,
            "unit": "斤"
        }
        """
        patterns = [
            (r'(.+?)[+＋]\s*(\d+\.?\d*)\s*(斤|两|箱|包|个|公斤)?', 'add'),
            (r'(.+?)\s+(?:加|增|添加)\s*(\d+\.?\d*)\s*(斤|两|箱|包|个|公斤)?', 'add'),
            (r'(.+?)[-－]\s*(\d+\.?\d*)\s*(斤|两|箱|包|个|公斤)?', 'subtract'),
            (r'(.+?)\s+(?:减|减少|扣)\s*(\d+\.?\d*)\s*(斤|两|箱|包|个|公斤)?', 'subtract'),
            (r'(.+?)=\s*(\d+\.?\d*)\s*(斤|两|箱|包|个|公斤)?', 'replace'),
            (r'(.+?)(?:改为|改成|变更为)\s*(\d+\.?\d*)\s*(斤|两|箱|包|个|公斤)?', 'replace'),
        ]

        for pattern, operation in patterns:
            match = re.search(pattern, content)
            if match:
                product_name = match.group(1).strip()
                quantity = float(match.group(2))
                unit = match.group(3) or '斤'

                return {
                    'product_name': product_name,
                    'operation': operation,
                    'quantity': quantity,
                    'unit': unit
                }

        return None


class OrderParser:
    """订单解析器 - 主类"""

    def __init__(self):
        self.product_matcher = ProductMatcher()
        self.quantity_extractor = QuantityExtractor()
        self.remark_extractor = RemarkExtractor()
        self.batch_parser = BatchSelectionParser()  # 新增批量圈选解析器
        self.incremental_parser = IncrementalParser()  # 新增增量操作解析器
        self.confidence_threshold = settings.PARSE_CONFIDENCE_THRESHOLD

    def parse_message(self, content: str, route_id: int = None) -> Dict:
        """
        解析单条消息,提取订单信息(增强版)

        Args:
            content: 消息内容,如 "来10斤土豆,要嫩的"
            route_id: 线路ID(用于批量圈选时获取线路产品清单)

        Returns:
            解析结果字典:
            {
                "success": bool,
                "items": [...],
                "confidence": float,
                "remarks": [],
                "error": str (可选),
                "is_batch": bool (是否批量圈选)
            }
        """
        result = {
            'success': False,
            'items': [],
            'confidence': 0.0,
            'remarks': [],
            'error': None,
            'is_batch': False
        }

        try:
            # 预处理: 去除多余空格和标点
            content = content.strip()
            if not content:
                result['error'] = '消息内容为空'
                return result

            logger.info(f"开始解析消息: {content}")

            # 0. 优先尝试 AI 解析（开启时）
            if is_ai_enabled():
                logger.info("AI 解析已启用，尝试调用 AI 模块")
                ai_result = parse_order_with_ai(content, {'route_id': route_id})
                if ai_result.get('success') and ai_result.get('items'):
                    logger.info("AI 解析成功，返回结构化订单")
                    result['success'] = True
                    result['items'] = ai_result.get('items', [])
                    result['confidence'] = round(ai_result.get('confidence', 0.0), 2)
                    result['remarks'] = ai_result.get('remarks', []) or []
                    result['error'] = None
                    return result
                logger.warning("AI 解析未命中结果，回退到常规模式解析: %s", ai_result.get('message'))

            # 1. 优先尝试批量圈选解析
            if route_id:
                batch_result = self.batch_parser.parse_batch_syntax(content, route_id)
                if batch_result:
                    # 导入线路产品服务
                    from services.route_product_service import RouteProductService
                    route_product_service = RouteProductService()
                    route_products = route_product_service.get_route_products(route_id)

                    # 映射序号到商品
                    selected_products = self.batch_parser.map_indices_to_products(
                        batch_result['product_indices'],
                        route_products
                    )

                    if selected_products:
                        # 构建订单项列表
                        items = []
                        for product in selected_products:
                            quantity = batch_result['quantity']
                            unit = batch_result['unit']
                            price = product['price']
                            items.append({
                                'product_id': product['product_id'],
                                'product_name': product['product_name'],
                                'quantity': quantity,
                                'unit': unit,
                                'unit_price': price,
                                'subtotal': round(quantity * price, 2)
                            })

                        logger.info(f"批量圈选解析成功: {len(items)}个商品")
                        result['success'] = True
                        result['items'] = items
                        result['confidence'] = 0.95
                        result['is_batch'] = True
                        return result

            # 2. 原有单条订单解析逻辑
            # 尝试提取多个订单项(支持逗号/空格分隔)
            segments = re.split(r'[，,\s]+', content)

            items = []
            total_confidence = 0.0

            for segment in segments:
                if not segment.strip():
                    continue

                item_result = self._parse_segment(segment.strip())
                if item_result['product']:
                    items.append(item_result['item'])
                    total_confidence += item_result['confidence']

            if not items:
                result['error'] = '未能识别任何商品'
                result['confidence'] = 0.0
                return result

            # 计算整体置信度
            avg_confidence = total_confidence / len(items) if items else 0.0

            result['success'] = True
            result['items'] = items
            result['confidence'] = round(avg_confidence, 2)
            result['remarks'] = self.remark_extractor.extract(content)

            logger.info(f"解析成功: {len(items)}个商品, 置信度={result['confidence']}")

        except Exception as e:
            logger.error(f"解析消息异常: {e}", exc_info=True)
            result['error'] = str(e)

        return result

    def _parse_segment(self, segment: str) -> Dict:
        """
        解析单个片段

        Returns:
            {
                "product": Product or None,
                "item": {...} or None,
                "confidence": float
            }
        """
        # 匹配商品
        product = self.product_matcher.match_product(segment)

        if not product:
            return {'product': None, 'item': None, 'confidence': 0.0}

        # 提取数量
        quantity, unit = self.quantity_extractor.extract(segment, product['unit'])

        # 提取备注
        remarks = self.remark_extractor.extract(segment)

        # 计算置信度
        confidence = self._calculate_confidence(segment, product, quantity)

        item = {
            'product_id': product['id'],
            'product_name': product['name'],
            'quantity': quantity,
            'unit': unit,
            'unit_price': product['price'],
            'subtotal': round(quantity * product['price'], 2),
            'remark': ', '.join(remarks) if remarks else None
        }

        return {
            'product': product,
            'item': item,
            'confidence': confidence
        }

    def _calculate_confidence(self, text: str, product: Dict, quantity: float) -> float:
        """
        计算解析置信度

        评分因素:
        - 商品匹配方式(精确>快捷码>分词)
        - 数量是否明确
        - 文本长度合理性
        """
        confidence = 0.5  # 基础分

        # 商品匹配质量
        product_name = product['name']
        if product_name in text:
            confidence += 0.3  # 精确匹配
        elif any(s.lower() in text.lower() for s in product['shortcuts']):
            confidence += 0.2  # 快捷码匹配

        # 数量明确性
        if quantity > 0:
            confidence += 0.2

        # 文本长度合理性
        if 2 <= len(text) <= 50:
            confidence += 0.1

        return min(confidence, 1.0)


# 全局单例
order_parser = OrderParser()


def parse_order_message(content: str) -> Dict:
    """
    便捷函数: 解析订单消息

    Args:
        content: 消息内容

    Returns:
        解析结果
    """
    return order_parser.parse_message(content)
