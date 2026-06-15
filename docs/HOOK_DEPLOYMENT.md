# VXHook 集成指南

## 概述

本文档介绍如何获取、安装和配置 VXHook DLL，以实现与 TonjClaw 系统的集成。

## 1. 获取 VXHook DLL

### 选项 1: 官方渠道
- 联系 VXHook 开发者获取最新版本
- 访问官方网站或 GitHub 仓库（如果公开）

### 选项 2: 开源替代方案
如果无法获取官方 VXHook，可以考虑以下开源替代方案：
- [WeChat Hook](https://github.com/topics/wechat-hook) - GitHub 上的相关项目
- [PC WeChat Hook](https://github.com/search?q=wechat+hook&type=repositories) - 搜索相关仓库

### 选项 3: 自行编译
如果有源代码，可以按照以下步骤编译：
```bash
# 示例编译步骤（根据实际项目调整）
git clone <repository-url>
cd vxhook
mkdir build && cd build
cmake ..
make
```

## 2. 安装 VXHook

### Windows 系统
1. 下载 `hook.dll` 文件
2. 将 DLL 放置在指定目录，例如：`D:\tools\vxhook\hook.dll`
3. 确保微信版本与 Hook 兼容（通常支持 3.9.x 系列）

### 配置微信路径
在 `config/hook_config.json` 中设置微信安装路径：
```json
{
  "wechat_path": "C:\\Program Files\\Tencent\\WeChat\\WeChat.exe"
}
```

## 3. 配置 TonjClaw 系统

### 环境变量配置
在 `.env` 文件中添加以下配置：

```env
# VXHook 配置
HOOK_HTTP_PORT=8888
HOOK_CALLBACK_URL_GROUP=http://localhost:5000/主动推送的群聊消息
HOOK_CALLBACK_URL_PRIVATE=http://localhost:5000/主动推送的私聊消息
HOOK_ENABLED=true
```

**注意**: WXHook 服务需要配置两个回调地址：
- 群聊消息回调: `http://localhost:5000/主动推送的群聊消息`
- 私聊消息回调: `http://localhost:5000/主动推送的私聊消息`

### 配置文件
复制示例配置文件并根据需要修改：
```bash
cp config/hook_config.example.json config/hook_config.json
```

编辑 `config/hook_config.json`：
```json
{
  "hook": {
    "http_port": 8888,
    "tcp_port": 61108,
    "callback_url_group": "http://localhost:5000/主动推送的群聊消息",
    "callback_url_private": "http://localhost:5000/主动推送的私聊消息",
    "wechat_path": "C:\\Program Files\\Tencent\\WeChat\\WeChat.exe",
    "dll_path": "D:\\tools\\vxhook\\hook.dll"
  },
  "auto_reply": {
    "enabled": true,
    "order_confirm_template": "✅ 订单已确认\n商品: {items}\n金额: ¥{amount}",
    "help_message": "📦 订货助手\n直接发送商品名称+数量即可下单"
  }
}
```

## 4. 启动顺序

1. **启动微信** - 确保微信客户端正在运行
2. **注入 Hook** - 使用适当的方法将 DLL 注入到微信进程中
3. **启动 TonjClaw 服务** - 运行 Flask 应用

```bash
python main.py
```

## 5. 验证集成

### 测试回调接口
```bash
python test_hook_integration.py
```

### 检查日志
查看应用日志确认 Hook 回调是否正常工作：
```
INFO:api.hook_callback:收到群聊消息 - 群ID: 49767299448@chatroom, 发送者: 张三, 内容: 白菜10斤 鸡蛋5斤
```

## 6. 常见问题

### Q: Hook 注入失败
A: 
- 确认微信版本与 Hook 兼容
- 以管理员权限运行注入工具
- 检查杀毒软件是否阻止了 DLL 注入

### Q: 回调接口无响应
A:
- 确认 TonjClaw 服务正在运行
- 检查防火墙设置，确保端口 5000 可访问
- 验证 `HOOK_CALLBACK_URL` 配置正确

### Q: 消息发送失败
A:
- 检查 Hook HTTP 服务是否在指定端口运行
- 验证网络连接正常
- 查看 Hook 客户端日志获取详细错误信息

## 7. 安全注意事项

⚠️ **重要提醒**:
- 使用 Hook 技术可能存在账号封禁风险
- 建议仅在小号上测试，避免在主账号上使用
- 控制消息发送频率，避免触发微信风控
- 定期更新 Hook 以适配微信版本变化

## 8. 技术支持

如遇到问题，请：
1. 查阅 `VXHOOK_INTEGRATION_PLAN.md` 获取详细开发计划
2. 检查应用日志文件 (`logs/` 目录)
3. 联系开发团队获取帮助

---

*最后更新: 2026-04-15*