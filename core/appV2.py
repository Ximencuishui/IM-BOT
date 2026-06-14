"""
HTTP消息接收服务 (Flask)
接收PC微信Hook推送的消息,进行去重、推MQ、存ES处理
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import logging
from datetime import datetime
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings
from services.message_service import process_incoming_message

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format=settings.LOG_FORMAT,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(settings.LOG_DIR, 'app.log'), encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# 确保日志目录存在
os.makedirs(settings.LOG_DIR, exist_ok=True)

app = Flask(__name__)
CORS(app, origins=settings.CORS_ORIGINS)

# 消息统计指标
metrics = {
    'total_received': 0,
    'total_duplicated': 0,
    'total_queued': 0,
    'total_errors': 0,
    'last_receive_time': None
}


@app.route('/api/recvMsg', methods=['POST'])
def handle_message():
    """接收Hook推送的消息"""
    metrics['total_received'] += 1
    metrics['last_receive_time'] = datetime.now().isoformat()

    try:
        # 获取JSON数据
        request_data = request.get_json()

        if not request_data:
            logger.warning("接收到空JSON请求")
            return jsonify({"error": "No JSON data received"}), 400

        logger.debug(f"接收到消息: {json.dumps(request_data, ensure_ascii=False)[:200]}")

        # 处理消息(去重、推MQ、存ES)
        result = process_incoming_message(request_data)

        # 更新统计
        if result.get('duplicated'):
            metrics['total_duplicated'] += 1
        if result.get('queued'):
            metrics['total_queued'] += 1
        if result.get('status') == 'error':
            metrics['total_errors'] += 1

        # 返回响应
        return jsonify({
            "status": "success",
            "message": "Message processed",
            "data": {
                "duplicated": result.get('duplicated', False),
                "queued": result.get('queued', False),
                "stored": result.get('stored', False)
            }
        }), 200

    except Exception as e:
        metrics['total_errors'] += 1
        logger.error(f"处理消息异常: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        "status": "healthy",
        "service": "message-receiver",
        "version": settings.APP_VERSION,
        "timestamp": datetime.now().isoformat()
    }), 200


@app.route('/metrics', methods=['GET'])
def get_metrics():
    """暴露监控指标(Prometheus格式简化版)"""
    return jsonify({
        "service": "message-receiver",
        "metrics": metrics,
        "timestamp": datetime.now().isoformat()
    }), 200


def dealJSAPI(msg):
    """
    兼容旧版JSAPI消息处理(保留)
    已废弃,使用process_incoming_message替代
    """
    logger.warning("dealJSAPI已废弃,请使用process_incoming_message")
    try:
        datas = json.loads(msg['JsApiResponse']['RespJson'])
        if 'msg_list' in datas:
            msg_list = datas['msg_list']
            for i in msg_list:
                print(f"{i['nickname']} : {i['content']}")
    except Exception as e:
        logger.error(f"dealJSAPI处理失败: {e}")


if __name__ == '__main__':
    logger.info(f"启动消息接收服务: {settings.FLASK_HOST}:{settings.FLASK_PORT}")
    app.run(host=settings.FLASK_HOST, port=settings.FLASK_PORT, debug=settings.DEBUG)
