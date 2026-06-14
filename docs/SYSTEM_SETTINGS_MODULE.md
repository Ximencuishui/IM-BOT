# 系统设置模块文档

## 概述

系统设置模块提供了完整的系统配置管理功能，包括邮件配置、支付配置、系统参数设置和通知模板管理。

## 功能特性

### 1. 邮件配置 (SMTP设置)

- **SMTP服务器配置**：支持配置SMTP服务器地址、端口、用户名和密码
- **发件人邮箱设置**：配置系统邮件的发件人邮箱
- **报表收件人**：配置接收系统报表的邮箱列表
- **测试发送**：提供测试邮件发送功能，验证SMTP配置是否正确

#### API接口

```
GET  /api/admin/system/email-config          # 获取邮件配置
POST /api/admin/system/email-config          # 更新邮件配置
POST /api/admin/system/email-config/test     # 测试邮件发送
```

### 2. 支付配置

#### 支付宝配置

- **App ID**：支付宝应用的AppID
- **应用私钥**：RSA2格式的应用私钥
- **支付宝公钥**：支付宝提供的公钥
- **网关地址**：支持正式环境和沙箱环境切换
- **回调地址**：支付成功后的跳转地址
- **异步通知**：支付宝服务器的异步通知地址

#### 微信支付配置

- **App ID**：微信公众号/小程序的AppID
- **商户号**：微信支付商户号
- **API密钥**：微信支付API密钥
- **异步通知**：微信支付的异步通知地址

#### API接口

```
GET  /api/admin/system/payment-config        # 获取支付配置
POST /api/admin/system/payment-config        # 更新支付配置
```

### 3. 系统参数设置

- **系统名称**：自定义系统显示名称
- **最大用户数**：限制系统最大注册用户数
- **默认订阅天数**：新用户的默认订阅时长
- **维护模式**：开启后用户无法访问系统
- **允许注册**：控制是否开放用户注册
- **会话超时时间**：用户会话的超时时间（秒）

#### API接口

```
GET  /api/admin/system/parameters            # 获取系统参数
POST /api/admin/system/parameters            # 更新系统参数
```

### 4. 通知模板管理

- **模板列表**：查看所有通知模板
- **新建模板**：创建新的通知模板
- **编辑模板**：修改现有模板
- **删除模板**：删除不需要的模板
- **模板预览**：预览模板内容，支持变量替换
- **启用/禁用**：控制模板的启用状态

#### 模板变量

通知模板支持以下变量：

- `{{username}}` - 用户名
- `{{license_code}}` - 授权码
- `{{days_remaining}}` - 剩余天数
- `{{expires_at}}` - 过期时间
- `{{login_url}}` - 登录地址
- `{{new_expiry}}` - 新过期时间
- `{{amount}}` - 金额

#### API接口

```
GET    /api/admin/system/notification-templates              # 获取模板列表
POST   /api/admin/system/notification-templates              # 创建模板
PUT    /api/admin/system/notification-templates/{id}         # 更新模板
DELETE /api/admin/system/notification-templates/{id}         # 删除模板
POST   /api/admin/system/notification-templates/{id}/preview # 预览模板
```

## 前端界面

### 系统设置页面布局

系统设置页面包含以下标签页：

1. **基础设置**：系统基本参数配置
2. **邮件配置**：SMTP服务器和邮件相关设置
3. **支付配置**：支付宝和微信支付配置（子标签页）
4. **通知模板**：通知模板管理列表

### 对话框

- **测试邮件发送对话框**：输入测试邮箱地址，发送测试邮件
- **通知模板编辑对话框**：创建或编辑通知模板
- **模板预览对话框**：预览模板渲染后的效果

## 后端实现

### API蓝图

系统设置API定义在 `api/system_settings.py` 文件中，通过以下路由前缀访问：

```
/api/admin/system/*
```

### 数据库存储

目前系统设置数据主要从配置文件读取，未来可以扩展到数据库存储：

- 邮件配置：从 `config/settings.py` 读取
- 支付配置：从 `config/settings.py` 读取
- 系统参数：可存储在数据库的系统配置表中
- 通知模板：可存储在数据库的通知模板表中

### 权限控制

所有系统设置API都需要管理员权限，通过 `@admin_required` 装饰器保护。

## 使用示例

### 1. 配置邮件服务器

```python
# 在 .env 文件中配置
SMTP_HOST=smtp.qq.com
SMTP_PORT=587
SMTP_USER=your_email@qq.com
SMTP_PASSWORD=your_password
FROM_EMAIL=your_email@qq.com
REPORT_RECIPIENTS=admin@example.com,manager@example.com
```

### 2. 配置支付宝

```python
# 在 .env 文件中配置
ALIPAY_APP_ID=2021001234567890
ALIPAY_APP_PRIVATE_KEY=your_private_key
ALIPAY_PUBLIC_KEY=alipay_public_key
ALIPAY_GATEWAY_URL=https://openapi.alipay.com/gateway.do
```

### 3. 调用API更新配置

```javascript
// 前端调用示例
const token = localStorage.getItem('token');

// 更新邮件配置
fetch('/api/admin/system/email-config', {
    method: 'POST',
    headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        smtp_host: 'smtp.qq.com',
        smtp_port: 587,
        smtp_user: 'test@qq.com',
        smtp_password: 'password',
        from_email: 'test@qq.com',
        report_recipients: 'admin@example.com'
    })
});
```

## 测试

运行测试脚本验证系统设置API：

```bash
python test_system_settings.py
```

测试脚本会执行以下操作：

1. 登录获取token
2. 测试邮件配置API
3. 测试支付配置API
4. 测试系统参数API
5. 测试通知模板API

## 注意事项

1. **安全性**：敏感配置（如密码、密钥）应该加密存储
2. **验证**：保存配置前应该进行有效性验证
3. **备份**：修改重要配置前建议备份
4. **测试**：修改支付配置后应该进行测试验证
5. **权限**：只有超级管理员才能访问系统设置

## 未来扩展

1. **配置版本控制**：记录配置变更历史
2. **配置导入导出**：支持配置的导入和导出
3. **多语言支持**：通知模板的多语言版本
4. **模板变量编辑器**：可视化的模板变量编辑器
5. **配置验证工具**：自动验证配置的有效性
6. **审计日志**：记录所有配置变更操作
