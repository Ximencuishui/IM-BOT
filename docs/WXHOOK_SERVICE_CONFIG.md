# WXHook 服务配置指南

## 概述

本文档介绍如何在已启动的 WXHook 服务中配置回调地址，使其能够与 TonjClaw 系统进行通信。

## 回调地址配置

WXHook 服务需要配置两个回调地址，分别用于接收群聊消息和私聊消息：

### 1. 群聊消息回调
- **路径**: `/主动推送的群聊消息`
- **方法**: `PUT`
- **完整URL**: `http://localhost:5000/主动推送的群聊消息`

### 2. 私聊消息回调
- **路径**: `/主动推送的私聊消息`
- **方法**: `PUT`
- **完整URL**: `http://localhost:5000/主动推送的私聊消息`

## 配置步骤

### 方法一：通过 WXHook 配置文件

1. 找到 WXHook 服务的配置文件（通常是 `config.json` 或 `settings.ini`）
2. 添加或修改以下配置项：

```json
{
  "callbacks": {
    "group_message": "http://localhost:5000/主动推送的群聊消息",
    "private_message": "http://localhost:5000/主动推送的私聊消息"
  }
}
```

### 方法二：通过 WXHook 管理界面

如果 WXHook 提供了 Web 管理界面：

1. 打开管理界面（通常是 `http://localhost:8888/admin` 或类似地址）
2. 找到"回调设置"或"Webhook 配置"选项
3. 分别设置群聊和私聊的回调地址
4. 保存配置并重启服务（如果需要）

### 方法三：通过命令行参数

某些版本的 WXHook 支持通过命令行参数配置：

```bash
wxhook.exe --group-callback http://localhost:5000/主动推送的群聊消息 --private-callback http://localhost:5000/主动推送的私聊消息
```

## 验证配置

### 1. 检查 WXHook 服务状态

确保 WXHook 服务正在运行：

```bash
# Windows
tasklist | findstr wxhook

# 或者检查端口占用
netstat -ano | findstr 8888
```

### 2. 测试回调连接

使用 curl 或 Postman 测试回调接口是否可访问：

```bash
# 测试群聊消息回调
curl -X PUT http://localhost:5000/主动推送的群聊消息 \
  -H "Content-Type: application/json" \
  -d '{"test": true}'

# 测试私聊消息回调
curl -X PUT http://localhost:5000/主动推送的私聊消息 \
  -H "Content-Type: application/json" \
  -d '{"test": true}'
```

预期响应：
```json
{"success": true, "result": {...}}
```

### 3. 发送测试消息

在微信中发送一条测试消息到群聊或私聊，检查 TonjClaw 应用日志：

```bash
# 查看应用日志
tail -f logs/app.log
```

应该能看到类似以下的日志：
```
INFO:api.hook_callback:收到群聊消息 - 群ID: xxx@chatroom, 发送者: 张三, 内容: 测试消息
```

## 常见问题

### Q: 回调地址配置后没有收到消息？

A: 请检查：
1. TonjClaw 服务是否在运行（端口 5000）
2. 防火墙是否阻止了本地连接
3. WXHook 服务是否正确加载了配置
4. 查看 WXHook 服务的日志，确认是否有回调失败的记录

### Q: 如何修改回调地址？

A: 
1. 修改 WXHook 配置文件中的回调地址
2. 重启 WXHook 服务
3. 验证新地址是否生效

### Q: 可以同时配置多个回调地址吗？

A: 这取决于 WXHook 的具体实现。大多数情况下只支持一个回调地址。如果需要多个接收端，可以考虑：
- 使用消息队列中间件（如 RabbitMQ）
- 创建一个转发服务，将消息分发到多个目标

## 安全建议

1. **限制访问来源**: 如果可能，配置 WXHook 只允许来自本地的回调
2. **使用 HTTPS**: 在生产环境中，建议使用 HTTPS 协议
3. **添加认证**: 如果 WXHook 支持，可以添加简单的 token 认证

## 技术支持

如遇到问题，请：
1. 查阅 WXHook 官方文档
2. 检查 TonjClaw 应用日志 (`logs/` 目录)
3. 联系开发团队获取帮助

---

*最后更新: 2026-04-15*
