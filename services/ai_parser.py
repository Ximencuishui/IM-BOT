"""
AI 订单解析模块
支持多种AI提供商：OpenAI、DeepSeek、通义千问、自定义HTTP API
"""
import json
import logging
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from config.settings import settings
from services.system_config_service import get_system_config_dict

logger = logging.getLogger(__name__)

PROVIDER_CONFIGS = {
    'openai': {
        'base_url': 'https://api.openai.com/v1/chat/completions',
        'headers': {'Authorization': 'Bearer {api_key}'},
        'model': 'gpt-4o-mini',
        'timeout': 15,
    },
    'deepseek': {
        'base_url': 'https://api.deepseek.com/v1/chat/completions',
        'headers': {'Authorization': 'Bearer {api_key}'},
        'model': 'deepseek-chat',
        'timeout': 15,
    },
    'qwen': {
        'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions',
        'headers': {'Authorization': 'Bearer {api_key}'},
        'model': 'qwen-plus',
        'timeout': 15,
    },
    'custom_http': {
        'base_url': '',
        'headers': {'Authorization': 'Bearer {api_key}'},
        'model': '',
        'timeout': 15,
    },
}

SYSTEM_PROMPT = """
你是一个专业的订单解析助手，负责从自然语言消息中提取结构化的订单信息。

消息内容可能包含：
- 商品名称（可能是全称、简称、俗称、快捷码）
- 数量和单位（如：10斤、5箱、3个）
- 备注信息（如：要嫩的、不要葱、加急）
- 客户姓名（可能从消息中识别）

请输出严格的JSON格式，包含以下字段：
{
    "success": true,
    "confidence": 0.95,
    "items": [
        {
            "product_name": "商品名称",
            "quantity": 10.0,
            "unit": "斤"
        }
    ],
    "customer_name": "客户姓名（可选）",
    "remarks": ["备注列表"],
    "raw_text": "原始消息文本"
}

注意事项：
1. 如果无法解析任何有效商品，success应为false
2. confidence表示解析置信度（0-1）
3. items数组中的每个元素必须包含product_name、quantity、unit字段
4. unit统一使用：斤、两、箱、包、个、公斤等
5. 支持口语化表达，如"来十斤土豆"应解析为10斤
6. 支持快捷码，如"TD 5斤"可能代表"土豆 5斤"
"""


def parse_order_with_ai(raw_text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """使用 AI 解析原始订单文本，返回结构化结果。"""
    logger.info("调用 AI 解析模块: %s", raw_text[:50] + '...' if len(raw_text) > 50 else raw_text)

    config = get_ai_config()
    provider = config.get('provider', 'none')
    
    if provider in ('none', '', 'mock'):
        return _build_disabled_result('AI parser is disabled or provider is not configured.')

    if provider not in PROVIDER_CONFIGS:
        return _build_disabled_result(f'Unsupported AI provider: {provider}')

    provider_config = PROVIDER_CONFIGS[provider]
    api_url = config.get('api_url') or provider_config['base_url']
    
    if not api_url:
        return _build_disabled_result('AI parser API URL is not configured.')

    return _send_ai_request(raw_text, context or {}, config, provider_config)


def is_ai_enabled() -> bool:
    """检查 AI 解析是否开启。"""
    return bool(get_ai_config().get('enabled', False))


def _parse_bool(value: Optional[Any], default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ('1', 'true', 'yes', 'on')


def _parse_int(value: Optional[Any], default: int = 10) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _parse_float(value: Optional[Any], default: float = 0.3) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def get_ai_config() -> Dict[str, Any]:
    """获取 AI 解析配置。"""
    env_config = {
        'enabled': getattr(settings, 'AI_PARSER_ENABLED', False),
        'provider': getattr(settings, 'AI_PARSER_PROVIDER', 'none'),
        'api_url': getattr(settings, 'AI_PARSER_API_URL', ''),
        'api_key': getattr(settings, 'AI_PARSER_API_KEY', ''),
        'model': getattr(settings, 'AI_PARSER_MODEL', ''),
        'timeout': getattr(settings, 'AI_PARSER_TIMEOUT', 15),
        'temperature': getattr(settings, 'AI_PARSER_TEMPERATURE', 0.3),
    }

    db_config = get_system_config_dict(prefix='ai_parser_')

    if 'ai_parser_enabled' in db_config:
        env_config['enabled'] = _parse_bool(db_config.get('ai_parser_enabled'), env_config['enabled'])
    if 'ai_parser_provider' in db_config:
        env_config['provider'] = db_config.get('ai_parser_provider', env_config['provider'])
    if 'ai_parser_api_url' in db_config:
        env_config['api_url'] = db_config.get('ai_parser_api_url', env_config['api_url'])
    if 'ai_parser_api_key' in db_config:
        env_config['api_key'] = db_config.get('ai_parser_api_key', env_config['api_key'])
    if 'ai_parser_model' in db_config:
        env_config['model'] = db_config.get('ai_parser_model', env_config['model'])
    if 'ai_parser_timeout' in db_config:
        env_config['timeout'] = _parse_int(db_config.get('ai_parser_timeout'), env_config['timeout'])
    if 'ai_parser_temperature' in db_config:
        env_config['temperature'] = _parse_float(db_config.get('ai_parser_temperature'), env_config['temperature'])

    return env_config


def _build_disabled_result(message: str) -> Dict[str, Any]:
    return {
        'success': False,
        'confidence': 0.0,
        'items': [],
        'customer_name': None,
        'remarks': [],
        'raw_text': None,
        'message': message,
    }


def _build_chat_completion_payload(raw_text: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """构建标准的Chat Completion请求体。"""
    model = config.get('model') or 'deepseek-chat'
    temperature = config.get('temperature', 0.3)

    return {
        'model': model,
        'messages': [
            {'role': 'system', 'content': SYSTEM_PROMPT.strip()},
            {'role': 'user', 'content': f'请解析以下订单消息：\n\n{raw_text}'},
        ],
        'temperature': temperature,
        'response_format': {'type': 'json_object'},
    }


def _send_ai_request(raw_text: str, context: Dict[str, Any], config: Dict[str, Any], 
                     provider_config: Dict[str, Any]) -> Dict[str, Any]:
    """发送AI请求到指定提供商。"""
    api_url = config['api_url']
    api_key = config.get('api_key', '')
    timeout = config.get('timeout', 15)

    payload = _build_chat_completion_payload(raw_text, config)

    headers = {
        'Content-Type': 'application/json',
    }
    
    if api_key:
        for key, value in provider_config.get('headers', {}).items():
            headers[key] = value.format(api_key=api_key)

    req = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode('utf-8'),
        headers=headers,
        method='POST'
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            response_text = response.read().decode('utf-8')
            logger.debug('AI provider response: %s', response_text[:200] + '...' if len(response_text) > 200 else response_text)
            return _normalize_ai_response(response_text)
    except urllib.error.HTTPError as http_err:
        logger.error('AI provider HTTP error: %s', http_err)
        return _build_disabled_result(f'AI provider HTTP error: {http_err.code} {http_err.reason}')
    except urllib.error.URLError as url_err:
        logger.error('AI provider URL error: %s', url_err)
        return _build_disabled_result(f'AI provider URL error: {url_err.reason}')
    except Exception as exc:
        logger.error('AI provider request failed: %s', exc, exc_info=True)
        return _build_disabled_result(f'AI provider request failed: {exc}')


def _normalize_ai_response(response_text: str) -> Dict[str, Any]:
    """规范化 AI 提供商返回值。"""
    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError:
        logger.error('AI provider返回结果不是JSON格式')
        return _build_disabled_result('AI provider returned invalid JSON response.')

    if not isinstance(payload, dict):
        return _build_disabled_result('AI provider returned unexpected response structure.')

    if payload.get('error'):
        error_msg = payload['error'].get('message', str(payload['error']))
        logger.error('AI provider error: %s', error_msg)
        return _build_disabled_result(f'AI provider error: {error_msg}')

    content = payload.get('choices', [{}])[0].get('message', {}).get('content')
    
    if content:
        try:
            result = json.loads(content)
            if isinstance(result, dict) and result.get('items') is not None:
                return {
                    'success': bool(result.get('success', True) and result.get('items')),
                    'confidence': float(result.get('confidence', 0.0) or 0.0),
                    'items': result.get('items', []),
                    'customer_name': result.get('customer_name'),
                    'remarks': result.get('remarks', []),
                    'raw_text': result.get('raw_text', None),
                    'message': result.get('message', 'AI parsing completed'),
                }
        except json.JSONDecodeError:
            logger.error('AI provider返回的content不是JSON格式')

    if payload.get('items') is not None:
        return {
            'success': bool(payload.get('success', True) and payload.get('items')),
            'confidence': float(payload.get('confidence', 0.0) or 0.0),
            'items': payload.get('items', []),
            'customer_name': payload.get('customer_name'),
            'remarks': payload.get('remarks', []),
            'raw_text': payload.get('raw_text', None),
            'message': payload.get('message', 'AI parsing completed'),
        }

    if payload.get('result') and isinstance(payload['result'], dict):
        result = payload['result']
        return {
            'success': bool(result.get('success', True) and result.get('items')),
            'confidence': float(result.get('confidence', 0.0) or 0.0),
            'items': result.get('items', []),
            'customer_name': result.get('customer_name'),
            'remarks': result.get('remarks', []),
            'raw_text': result.get('raw_text', None),
            'message': result.get('message', 'AI parsing completed'),
        }

    return _build_disabled_result('AI provider response does not contain expected fields.')
