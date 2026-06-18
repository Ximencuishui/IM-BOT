from flask import Flask, request, jsonify
import json

app = Flask(__name__)


@app.route('/api/recvMsg', methods=['POST'])
def handle_message():
    try:
        request_data = request.get_json()
        print(json.dumps(request_data))

        if not request_data:
            return jsonify({"error": "No JSON data received"}), 400

        return jsonify({
            "status": "success",
            "message": "Data received",
        }), 200

    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return jsonify({"error": str(e)}), 500


def dealJSAPI(msg):
    datas = json.loads(msg['JsApiResponse']['RespJson'])
    if 'msg_list' in datas:
        msg_list = datas['msg_list']
        for i in msg_list:
            print(f"{i['nickname']} : {i['content']}")


def init_app():
    from plugins import load_plugins
    load_plugins(app)
    print("✓ 所有插件加载完成")


if __name__ == '__main__':
    init_app()
    app.run(host='0.0.0.0', port=5000)