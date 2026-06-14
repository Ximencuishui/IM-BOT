"""
飞书API客户端
支持飞书机器人消息发送、用户信息获取、群信息管理等功能
"""
import json
import logging
import time
from typing import Any, Dict, List, Optional

import requests

from config.settings import settings

logger = logging.getLogger(__name__)

FEISHU_API_BASE = "https://open.feishu.cn/open-apis"


class FeishuClient:
    def __init__(self):
        self.app_id = settings.FEISHU_APP_ID
        self.app_secret = settings.FEISHU_APP_SECRET
        self.bot_webhook = settings.FEISHU_BOT_WEBHOOK
        self.event_secret = settings.FEISHU_EVENT_SECRET
        self.encrypt_key = settings.FEISHU_ENCRYPT_KEY
        self.access_token = None
        self.token_expire_time = 0

    def _get_access_token(self) -> str:
        if self.access_token and time.time() < self.token_expire_time:
            return self.access_token

        if not self.app_id or not self.app_secret:
            logger.warning("飞书App ID或App Secret未配置")
            return ""

        url = f"{FEISHU_API_BASE}/auth/v3/tenant_access_token/internal"
        payload = {"app_id": self.app_id, "app_secret": self.app_secret}

        try:
            response = requests.post(url, json=payload, timeout=10)
            data = response.json()

            if data.get("code") == 0:
                self.access_token = data["tenant_access_token"]
                self.token_expire_time = time.time() + data.get("expire", 3600) - 60
                logger.info("飞书access_token获取成功")
                return self.access_token
            else:
                logger.error(f"飞书access_token获取失败: {data.get('msg')}")
                return ""
        except Exception as e:
            logger.error(f"飞书API请求异常: {e}")
            return ""

    def send_text(self, chat_id: str, text: str, at_user_ids: Optional[List[str]] = None) -> bool:
        try:
            token = self._get_access_token()
            if not token:
                logger.error("飞书access_token为空，无法发送消息")
                return False

            url = f"{FEISHU_API_BASE}/im/v1/messages"
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

            payload = {
                "receive_id_type": "chat_id",
                "receive_id": chat_id,
                "msg_type": "text",
                "content": json.dumps({"text": text}),
            }

            if at_user_ids:
                at_text = "".join([f"<at user_id=\"{uid}\"></at>" for uid in at_user_ids])
                content = json.loads(payload["content"])
                content["text"] = at_text + " " + content["text"]
                payload["content"] = json.dumps(content)

            response = requests.post(url, headers=headers, json=payload, timeout=10)
            data = response.json()

            if data.get("code") == 0:
                logger.info(f"飞书消息发送成功: chat_id={chat_id}")
                return True
            else:
                logger.error(f"飞书消息发送失败: {data.get('msg')}")
                return False
        except Exception as e:
            logger.error(f"飞书发送消息异常: {e}")
            return False

    def send_card(self, chat_id: str, card: Dict[str, Any]) -> bool:
        try:
            token = self._get_access_token()
            if not token:
                logger.error("飞书access_token为空，无法发送消息卡片")
                return False

            url = f"{FEISHU_API_BASE}/im/v1/messages"
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

            payload = {
                "receive_id_type": "chat_id",
                "receive_id": chat_id,
                "msg_type": "interactive",
                "content": json.dumps(card),
            }

            response = requests.post(url, headers=headers, json=payload, timeout=10)
            data = response.json()

            if data.get("code") == 0:
                logger.info(f"飞书消息卡片发送成功: chat_id={chat_id}")
                return True
            else:
                logger.error(f"飞书消息卡片发送失败: {data.get('msg')}")
                return False
        except Exception as e:
            logger.error(f"飞书发送消息卡片异常: {e}")
            return False

    def send_webhook_text(self, text: str, at_user_ids: Optional[List[str]] = None) -> bool:
        if not self.bot_webhook:
            logger.error("飞书机器人Webhook未配置")
            return False

        try:
            url = self.bot_webhook
            headers = {"Content-Type": "application/json"}

            payload = {"msg_type": "text", "content": {"text": text}}

            if at_user_ids:
                payload["content"]["at"] = {"user_ids": at_user_ids}

            response = requests.post(url, headers=headers, json=payload, timeout=10)
            data = response.json()

            if data.get("StatusCode") == 0:
                logger.info("飞书Webhook消息发送成功")
                return True
            else:
                logger.error(f"飞书Webhook消息发送失败: {data.get('StatusMessage')}")
                return False
        except Exception as e:
            logger.error(f"飞书Webhook发送消息异常: {e}")
            return False

    def send_webhook_card(self, card: Dict[str, Any]) -> bool:
        if not self.bot_webhook:
            logger.error("飞书机器人Webhook未配置")
            return False

        try:
            url = self.bot_webhook
            headers = {"Content-Type": "application/json"}

            payload = {"msg_type": "interactive", "card": card}

            response = requests.post(url, headers=headers, json=payload, timeout=10)
            data = response.json()

            if data.get("StatusCode") == 0:
                logger.info("飞书Webhook消息卡片发送成功")
                return True
            else:
                logger.error(f"飞书Webhook消息卡片发送失败: {data.get('StatusMessage')}")
                return False
        except Exception as e:
            logger.error(f"飞书Webhook发送消息卡片异常: {e}")
            return False

    def get_user_info(self, user_id: str) -> Dict[str, Any]:
        try:
            token = self._get_access_token()
            if not token:
                logger.error("飞书access_token为空，无法获取用户信息")
                return {}

            url = f"{FEISHU_API_BASE}/contact/v3/users/{user_id}"
            headers = {"Authorization": f"Bearer {token}"}

            response = requests.get(url, headers=headers, timeout=10)
            data = response.json()

            if data.get("code") == 0:
                return data.get("data", {})
            else:
                logger.error(f"飞书获取用户信息失败: {data.get('msg')}")
                return {}
        except Exception as e:
            logger.error(f"飞书获取用户信息异常: {e}")
            return {}

    def get_chat_info(self, chat_id: str) -> Dict[str, Any]:
        try:
            token = self._get_access_token()
            if not token:
                logger.error("飞书access_token为空，无法获取群信息")
                return {}

            url = f"{FEISHU_API_BASE}/im/v1/chats/{chat_id}"
            headers = {"Authorization": f"Bearer {token}"}

            response = requests.get(url, headers=headers, timeout=10)
            data = response.json()

            if data.get("code") == 0:
                return data.get("data", {})
            else:
                logger.error(f"飞书获取群信息失败: {data.get('msg')}")
                return {}
        except Exception as e:
            logger.error(f"飞书获取群信息异常: {e}")
            return {}

    def get_chat_members(self, chat_id: str) -> List[Dict[str, Any]]:
        try:
            token = self._get_access_token()
            if not token:
                logger.error("飞书access_token为空，无法获取群成员")
                return []

            url = f"{FEISHU_API_BASE}/im/v1/chats/{chat_id}/members"
            headers = {"Authorization": f"Bearer {token}"}

            response = requests.get(url, headers=headers, timeout=10)
            data = response.json()

            if data.get("code") == 0:
                return data.get("data", {}).get("items", [])
            else:
                logger.error(f"飞书获取群成员失败: {data.get('msg')}")
                return []
        except Exception as e:
            logger.error(f"飞书获取群成员异常: {e}")
            return []

    def create_travel_card(self, route_info: Dict[str, Any]) -> Dict[str, Any]:
        card = {
            "config": {"wide_screen_mode": True, "enable_forward": True},
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"🌟 {route_info.get('route_name', '旅游线路')}",
                },
                "template": "turquoise",
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"💰 **价格**: ¥{route_info.get('price', 0):.2f}",
                    },
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"📅 **出发时间**: {route_info.get('start_date', '')}",
                    },
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"👥 **成团要求**: {route_info.get('group_size', 0)}人起",
                    },
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"⏱️ **行程天数**: {route_info.get('duration', 0)}天",
                    },
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"📍 **线路详情**: {route_info.get('route_details', '')}",
                    },
                },
            ],
        }

        highlights = route_info.get("highlights", [])
        if highlights:
            highlights_text = "✨ **特色亮点**: " + "、".join(highlights)
            card["elements"].append(
                {
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": highlights_text},
                }
            )

        card["elements"].append(
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "立即报名"},
                        "type": "primary",
                        "value": {"route_id": route_info.get("id", "")},
                    }
                ],
            }
        )

        return card

    def is_enabled(self) -> bool:
        return settings.FEISHU_ENABLED and bool(self.app_id and self.app_secret)


feishu_client = FeishuClient()
