"""
支付宝支付工具类
支持 PC 网页支付签名生成与验签
"""
import json
import time
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA256
from base64 import b64encode, b64decode
from urllib.parse import quote_plus
from config.settings import settings

class AliPayUtils:
    def __init__(self):
        self.app_id = settings.ALIPAY_APP_ID
        self.app_private_key_string = settings.ALIPAY_APP_PRIVATE_KEY
        self.alipay_public_key_string = settings.ALIPAY_PUBLIC_KEY
        self.sign_type = "RSA2"
        self.charset = "utf-8"
        self.gateway_url = settings.ALIPAY_GATEWAY_URL or "https://openapi.alipay.com/gateway.do"

    def _build_sign(self, data):
        """生成签名"""
        unsigned_items = sorted(data.items())
        message = "&".join(f"{k}={v}" for k, v in unsigned_items)
        key = RSA.importKey(self.app_private_key_string.encode())
        signer = PKCS1_v1_5.new(key)
        signature = signer.sign(SHA256.new(message.encode()))
        return b64encode(signature).decode("utf-8")

    def create_web_pay_url(self, out_trade_no, total_amount, subject, return_url, notify_url):
        """
        创建 PC 网站支付链接
        :return: 支付跳转 URL
        """
        biz_content = {
            "out_trade_no": out_trade_no,
            "total_amount": str(total_amount),
            "subject": subject,
            "product_code": "FAST_INSTANT_TRADE_PAY"
        }

        data = {
            "app_id": self.app_id,
            "method": "alipay.trade.page.pay",
            "charset": self.charset,
            "sign_type": self.sign_type,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "version": "1.0",
            "biz_content": json.dumps(biz_content),
            "return_url": return_url,
            "notify_url": notify_url
        }

        sign = self._build_sign(data)
        data["sign"] = sign
        
        query_string = "&".join(f"{k}={quote_plus(str(v))}" for k, v in sorted(data.items()))
        return f"{self.gateway_url}?{query_string}"

    def verify_callback(self, data, signature):
        """验证支付宝回调签名"""
        sign_data = {k: v for k, v in data.items() if k != "sign" and k != "sign_type"}
        unsigned_items = sorted(sign_data.items())
        message = "&".join(f"{k}={v}" for k, v in unsigned_items)
        
        key = RSA.importKey(self.alipay_public_key_string.encode())
        verifier = PKCS1_v1_5.new(key)
        return verifier.verify(
            SHA256.new(message.encode()),
            b64decode(signature.encode())
        )
