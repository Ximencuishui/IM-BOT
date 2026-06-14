"""
商品管理API路由
"""
from flask import Blueprint, request, jsonify
import logging

from services.product_service import product_service

logger = logging.getLogger(__name__)

products_bp = Blueprint('products', __name__, url_prefix='/api/products')


@products_bp.route('', methods=['GET'])
def list_products():
    """
    获取商品列表

    Query Params:
    - category: 分类筛选
    - is_active: 启用状态(1/0)
    """
    try:
        category = request.args.get('category')
        is_active = request.args.get('is_active')

        if is_active is not None:
            is_active = int(is_active) == 1

        products = product_service.list_products(category=category, is_active=is_active)

        return jsonify({
            'success': True,
            'count': len(products),
            'products': products
        }), 200

    except Exception as e:
        logger.error(f"查询商品列表API异常: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@products_bp.route('/search', methods=['GET'])
def search_products():
    """
    搜索商品

    Query Params:
    - keyword: 搜索关键词
    """
    try:
        keyword = request.args.get('keyword', '').strip()

        if not keyword:
            return jsonify({'error': 'keyword不能为空'}), 400

        products = product_service.search_products(keyword)

        return jsonify({
            'success': True,
            'count': len(products),
            'products': products
        }), 200

    except Exception as e:
        logger.error(f"搜索商品API异常: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@products_bp.route('/<int:product_id>', methods=['GET'])
def get_product(product_id):
    """获取商品详情"""
    try:
        product = product_service.get_product_by_id(product_id)

        if not product:
            return jsonify({'error': f'商品不存在: {product_id}'}), 404

        return jsonify({'success': True, 'product': product}), 200

    except Exception as e:
        logger.error(f"查询商品详情API异常: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@products_bp.route('', methods=['POST'])
def create_product():
    """
    创建商品

    Request Body:
    {
        "product_name": "土豆",
        "product_code": "PROD_001",
        "shortcut_codes": ["TD", "土", "土豆"],
        "unit": "斤",
        "price": 2.50,
        "category": "蔬菜",
        "sort_order": 0
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': '请求体不能为空'}), 400

        result = product_service.create_product(data)

        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"创建商品API异常: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@products_bp.route('/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    """
    更新商品

    Request Body:
    {
        "product_name": "新名称",
        "price": 3.00,
        "shortcut_codes": ["新快捷码"]
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': '请求体不能为空'}), 400

        result = product_service.update_product(product_id, data)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"更新商品API异常: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@products_bp.route('/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """删除商品(软删除)"""
    try:
        result = product_service.delete_product(product_id)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"删除商品API异常: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@products_bp.route('/dict/options', methods=['GET'])
def get_dict_options():
    """获取字典选项（分类、单位等）"""
    try:
        from database.db_config import get_db_session
        from models.models import SystemConfig
        import json
        
        db = get_db_session()
        
        # 从系统配置中获取自定义分类和属性
        custom_categories_config = db.query(SystemConfig).filter(
            SystemConfig.config_key == 'product_categories'
        ).first()
        
        custom_attributes_config = db.query(SystemConfig).filter(
            SystemConfig.config_key == 'product_attributes'
        ).first()
        
        # 默认分类和属性
        default_categories = ['蔬菜', '水果', '肉类', '水产', '粮油', '调味品', '其他']
        default_attributes = ['产地', '规格', '等级', '保质期']
        
        # 合并自定义和默认值
        if custom_categories_config:
            try:
                custom_categories = json.loads(custom_categories_config.config_value)
                categories = list(set(default_categories + custom_categories))
            except:
                categories = default_categories
        else:
            categories = default_categories
        
        if custom_attributes_config:
            try:
                custom_attributes = json.loads(custom_attributes_config.config_value)
                attributes = list(set(default_attributes + custom_attributes))
            except:
                attributes = default_attributes
        else:
            attributes = default_attributes
        
        options = {
            'categories': sorted(categories),
            'units': ['斤', '公斤', '个', '箱', '袋', '瓶', '包', '件'],
            'attributes': sorted(attributes)
        }
        
        return jsonify({'success': True, 'options': options}), 200
        
    except Exception as e:
        logger.error(f"获取字典选项API异常: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@products_bp.route('/categories', methods=['POST'])
def add_category():
    """
    添加商品分类
    
    Request Body:
    {
        "category": "新分类名称"
    }
    """
    try:
        from database.db_config import get_db_session
        from models.models import SystemConfig
        import json
        
        data = request.get_json()
        if not data or not data.get('category'):
            return jsonify({'error': '分类名称不能为空'}), 400
        
        category_name = data['category'].strip()
        
        db = get_db_session()
        try:
            # 获取现有分类配置
            config = db.query(SystemConfig).filter(
                SystemConfig.config_key == 'product_categories'
            ).first()
            
            if config:
                try:
                    categories = json.loads(config.config_value)
                except:
                    categories = []
            else:
                categories = []
                config = SystemConfig(
                    config_key='product_categories',
                    config_value='[]',
                    description='自定义商品分类列表'
                )
                db.add(config)
                db.flush()
            
            # 检查是否已存在
            if category_name in categories:
                return jsonify({'success': False, 'error': '该分类已存在'}), 400
            
            # 添加新分类
            categories.append(category_name)
            config.config_value = json.dumps(categories, ensure_ascii=False)
            db.commit()
            
            return jsonify({
                'success': True,
                'message': '分类添加成功',
                'category': category_name
            }), 201
            
        finally:
            db.close()
        
    except Exception as e:
        logger.error(f"添加分类API异常: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@products_bp.route('/attributes', methods=['POST'])
def add_attribute():
    """
    添加商品公共属性
    
    Request Body:
    {
        "attribute": "属性名称"
    }
    """
    try:
        from database.db_config import get_db_session
        from models.models import SystemConfig
        import json
        
        data = request.get_json()
        if not data or not data.get('attribute'):
            return jsonify({'error': '属性名称不能为空'}), 400
        
        attribute_name = data['attribute'].strip()
        
        db = get_db_session()
        try:
            # 获取现有属性配置
            config = db.query(SystemConfig).filter(
                SystemConfig.config_key == 'product_attributes'
            ).first()
            
            if config:
                try:
                    attributes = json.loads(config.config_value)
                except:
                    attributes = []
            else:
                attributes = []
                config = SystemConfig(
                    config_key='product_attributes',
                    config_value='[]',
                    description='自定义商品公共属性列表'
                )
                db.add(config)
                db.flush()
            
            # 检查是否已存在
            if attribute_name in attributes:
                return jsonify({'success': False, 'error': '该属性已存在'}), 400
            
            # 添加新属性
            attributes.append(attribute_name)
            config.config_value = json.dumps(attributes, ensure_ascii=False)
            db.commit()
            
            return jsonify({
                'success': True,
                'message': '属性添加成功',
                'attribute': attribute_name
            }), 201
            
        finally:
            db.close()
        
    except Exception as e:
        logger.error(f"添加属性API异常: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
