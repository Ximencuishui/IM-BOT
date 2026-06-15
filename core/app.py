from flask import Flask, request, jsonify
import json

app = Flask(__name__)


@app.route('/api/recvMsg', methods=['POST'])
def handle_message():
    try:
        # 获取 JSON 数据
        request_data = request.get_json()
        # print(request_data)
        # if 'JsApiResponse' in request_data:
        #     dealJSAPI(request_data)
        print(json.dumps(request_data))


        if not request_data:
            return jsonify({"error": "No JSON data received"}), 400

        # 打印接收到的数据

        # 在这里添加你的业务逻辑处理

        # 返回 JSON 响应
        return jsonify({
            "status": "success",
            "message": "Data received",
        }), 200

    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return jsonify({"error": str(e)}), 500

def dealJSAPI(msg):
    datas=json.loads(msg['JsApiResponse']['RespJson'])
    if 'msg_list' in datas:
        msg_list=datas['msg_list']
        for i in msg_list:
            print(f"{i['nickname']} : {i['content']}")


if __name__ == '__main__':
    # 监听所有网络接口，端口5000
    app.run(host='0.0.0.0', port=5000)