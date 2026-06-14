"""
AI 解析模块单元测试
"""
import sys
import os
import json
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings
from services.ai_parser import parse_order_with_ai, get_ai_config, is_ai_enabled


class DummyResponse:
    def __init__(self, body: str):
        self._body = body.encode('utf-8')

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


class TestAIParser:
    def test_ai_disabled_by_default(self, monkeypatch):
        monkeypatch.setattr(settings, 'AI_PARSER_ENABLED', False)
        monkeypatch.setattr(settings, 'AI_PARSER_PROVIDER', 'none')
        result = parse_order_with_ai('来10斤土豆', {})
        assert result['success'] is False
        assert 'disabled' in result['message'].lower()

    def test_get_ai_config_defaults(self, monkeypatch):
        monkeypatch.setattr(settings, 'AI_PARSER_ENABLED', False)
        monkeypatch.setattr(settings, 'AI_PARSER_PROVIDER', 'none')
        monkeypatch.setattr(settings, 'AI_PARSER_API_URL', '')
        monkeypatch.setattr(settings, 'AI_PARSER_API_KEY', '')
        monkeypatch.setattr(settings, 'AI_PARSER_MODEL', '')
        monkeypatch.setattr(settings, 'AI_PARSER_TIMEOUT', 15)
        monkeypatch.setattr(settings, 'AI_PARSER_TEMPERATURE', 0.3)
        
        config = get_ai_config()
        assert config['provider'] == 'none'
        assert config['api_url'] == ''
        assert config['timeout'] == 15
        assert config['temperature'] == 0.3

    def test_is_ai_enabled_default(self):
        assert is_ai_enabled() is False

    def test_custom_http_provider_url_not_configured(self, monkeypatch):
        monkeypatch.setattr(settings, 'AI_PARSER_ENABLED', True)
        monkeypatch.setattr(settings, 'AI_PARSER_PROVIDER', 'custom_http')
        monkeypatch.setattr(settings, 'AI_PARSER_API_URL', '')
        result = parse_order_with_ai('来10斤土豆', {})
        assert result['success'] is False
        assert 'API URL' in result['message']

    def test_custom_http_provider_calls_request(self, monkeypatch):
        monkeypatch.setattr(settings, 'AI_PARSER_ENABLED', True)
        monkeypatch.setattr(settings, 'AI_PARSER_PROVIDER', 'custom_http')
        monkeypatch.setattr(settings, 'AI_PARSER_API_URL', 'http://example.com/ai')
        monkeypatch.setattr(settings, 'AI_PARSER_API_KEY', 'test-key')
        monkeypatch.setattr(settings, 'AI_PARSER_MODEL', 'test-model')
        monkeypatch.setattr(settings, 'AI_PARSER_TEMPERATURE', 0.3)

        mock_response = DummyResponse(json.dumps({
            'choices': [{
                'message': {
                    'content': json.dumps({
                        'success': True,
                        'confidence': 0.92,
                        'items': [
                            {'product_name': '土豆', 'quantity': 10.0, 'unit': '斤'}
                        ],
                        'remarks': ['要嫩的'],
                    })
                }
            }]
        }))

        with patch('services.ai_parser.urllib.request.urlopen', return_value=mock_response) as mock_urlopen:
            result = parse_order_with_ai('来10斤土豆', {})
            assert result['success'] is True
            assert result['confidence'] == 0.92
            assert len(result['items']) == 1
            mock_urlopen.assert_called_once()

    def test_ai_config_uses_system_config_override(self, monkeypatch):
        monkeypatch.setattr(settings, 'AI_PARSER_ENABLED', False)
        monkeypatch.setattr(settings, 'AI_PARSER_PROVIDER', 'none')
        monkeypatch.setattr(settings, 'AI_PARSER_API_URL', '')

        monkeypatch.setattr(
            'services.ai_parser.get_system_config_dict',
            lambda prefix=None: {
                'ai_parser_enabled': 'true',
                'ai_parser_provider': 'custom_http',
                'ai_parser_api_url': 'http://example.com/ai',
                'ai_parser_api_key': 'secret',
                'ai_parser_model': 'test-model',
                'ai_parser_timeout': '5',
                'ai_parser_temperature': '0.5'
            }
        )

        config = get_ai_config()
        assert config['enabled'] is True
        assert config['provider'] == 'custom_http'
        assert config['api_url'] == 'http://example.com/ai'
        assert config['api_key'] == 'secret'
        assert config['model'] == 'test-model'
        assert config['timeout'] == 5
        assert config['temperature'] == 0.5
        assert is_ai_enabled() is True

    def test_openai_provider_config(self, monkeypatch):
        monkeypatch.setattr(settings, 'AI_PARSER_ENABLED', True)
        monkeypatch.setattr(settings, 'AI_PARSER_PROVIDER', 'openai')
        monkeypatch.setattr(settings, 'AI_PARSER_API_KEY', 'sk-test-key')
        
        config = get_ai_config()
        assert config['provider'] == 'openai'
        assert config['api_key'] == 'sk-test-key'

    def test_deepseek_provider_config(self, monkeypatch):
        monkeypatch.setattr(settings, 'AI_PARSER_ENABLED', True)
        monkeypatch.setattr(settings, 'AI_PARSER_PROVIDER', 'deepseek')
        monkeypatch.setattr(settings, 'AI_PARSER_API_KEY', 'sk-deepseek-test')
        
        config = get_ai_config()
        assert config['provider'] == 'deepseek'
        assert config['api_key'] == 'sk-deepseek-test'

    def test_qwen_provider_config(self, monkeypatch):
        monkeypatch.setattr(settings, 'AI_PARSER_ENABLED', True)
        monkeypatch.setattr(settings, 'AI_PARSER_PROVIDER', 'qwen')
        monkeypatch.setattr(settings, 'AI_PARSER_API_KEY', 'sk-qwen-test')
        
        config = get_ai_config()
        assert config['provider'] == 'qwen'
        assert config['api_key'] == 'sk-qwen-test'

    def test_unsupported_provider(self, monkeypatch):
        monkeypatch.setattr(settings, 'AI_PARSER_ENABLED', True)
        monkeypatch.setattr(settings, 'AI_PARSER_PROVIDER', 'unsupported_provider')
        
        result = parse_order_with_ai('来10斤土豆', {})
        assert result['success'] is False
        assert 'unsupported' in result['message'].lower()
