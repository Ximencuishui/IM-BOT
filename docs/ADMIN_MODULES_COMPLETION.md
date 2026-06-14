# Admin Portal 新增模块说明

## 概述

本次更新为Admin Portal添加了三个核心管理模块：
1. **系统监控 (Monitoring)** - 实时监控系统健康状态和性能指标
2. **审计日志 (Audit Logs)** - 记录和追踪系统操作
3. **系统设置 (Settings)** - 已存在，包含邮件、支付、通知模板等配置

---

## 1. 系统监控模块

### 功能特性

- **健康摘要**: 显示系统整体健康状态（正常/异常）
- **资源监控**: 
  - CPU使用率
  - 内存使用率
  - 磁盘使用率
- **中间件状态**: 监控Redis、RabbitMQ、Elasticsearch、Database连接状态
- **应用信息**: 显示应用名称、版本、运行时长、进程ID
- **系统详情**: 详细的CPU、内存、磁盘、网络统计信息
- **最近活动**: 显示最近的系统操作记录
- **自动刷新**: 每30秒自动更新数据

### API端点

```
GET /api/admin/monitoring/system-status      # 获取系统状态
GET /api/admin/monitoring/app-status         # 获取应用状态
GET /api/admin/monitoring/database-status    # 获取数据库状态
GET /api/admin/monitoring/recent-activities  # 获取最近活动
GET /api/admin/monitoring/health-summary     # 获取健康摘要
```

### 技术实现

- **后端**: 使用 `psutil` 库获取系统资源信息
- **前端**: Vue 3 + Element Plus，使用进度条和图表展示数据
- **自动刷新**: 使用 setInterval 每30秒更新一次

---

## 2. 审计日志模块

### 功能特性

- **统计卡片**: 
  - 总日志数
  - 今日日志数
  - 成功/失败操作数
- **高级搜索**:
  - 按用户名/IP搜索
  - 按操作类型过滤（登录、创建、更新、删除等）
  - 按资源类型过滤（用户、授权码、订单等）
  - 按状态过滤（成功/失败）
  - 按时间范围过滤
- **日志列表**: 分页显示，支持排序
- **详情查看**: 查看完整的日志详情，包括旧值/新值
- **导出功能**: 导出为CSV文件
- **日志清理**: 清理指定天数前的旧日志

### API端点

```
GET  /api/admin/audit-logs              # 获取审计日志列表
GET  /api/admin/audit-logs/stats        # 获取审计统计
POST /api/admin/audit-logs/export       # 导出审计日志
POST /api/admin/audit-logs/cleanup      # 清理旧日志
```

### 数据模型

**t_audit_log 表结构**:
- `id`: 日志ID
- `user_id`: 操作用户ID
- `username`: 操作用户名
- `action`: 操作类型（login/logout/create/update/delete/export）
- `resource`: 资源类型（user/license/order/product/config）
- `resource_id`: 资源ID
- `description`: 操作描述
- `old_value`: 旧值（JSON格式）
- `new_value`: 新值（JSON格式）
- `ip_address`: IP地址
- `user_agent`: 用户代理
- `status`: 操作状态（success/failed）
- `error_message`: 错误信息
- `created_at`: 操作时间

### 使用示例

在代码中记录审计日志：

```python
from api.audit_log import create_audit_log

# 记录用户登录
create_audit_log(
    user_id=1,
    username='admin',
    action='login',
    description='用户登录系统',
    ip_address='192.168.1.100',
    status='success'
)

# 记录配置修改
create_audit_log(
    user_id=1,
    username='admin',
    action='update',
    resource='config',
    resource_id=1,
    description='修改邮件配置',
    old_value={'smtp_host': 'old.example.com'},
    new_value={'smtp_host': 'new.example.com'},
    status='success'
)
```

---

## 3. 系统设置模块

系统设置模块已在之前完成，包含以下功能：

- **基础设置**: 系统名称、版本、维护模式、注册开关
- **邮件配置**: SMTP服务器配置、测试发送
- **支付配置**: 支付宝、微信支付配置
- **通知模板**: 管理邮件通知模板，支持预览

---

## 安装和配置

### 1. 安装依赖

```bash
pip install psutil==5.9.6
```

或重新安装所有依赖：

```bash
pip install -r requirements.txt
```

### 2. 执行数据库迁移

```bash
mysql -u root -p your_database < database/migrations/add_audit_log_table.sql
```

### 3. 重启服务

```bash
python main.py
```

### 4. 访问模块

启动前端开发服务器后，访问：
- 系统监控: http://localhost:5173/admin/monitoring
- 审计日志: http://localhost:5173/admin/audit-logs
- 系统设置: http://localhost:5173/admin/settings

---

## 注意事项

1. **性能考虑**: 
   - 系统监控每30秒自动刷新，会调用系统API
   - 审计日志表可能快速增长，建议定期清理旧日志

2. **权限控制**: 
   - 所有监控和审计API都需要管理员权限（`@admin_required`装饰器）
   - 确保只有授权用户可以访问敏感信息

3. **数据安全**:
   - 审计日志包含敏感操作记录，应妥善保护
   - 导出的CSV文件包含完整日志，注意保密

4. **日志保留策略**:
   - 建议保留90天的审计日志
   - 可根据合规要求调整保留期限

---

## 后续优化建议

1. **实时监控增强**:
   - 添加WebSocket实时推送
   - 添加告警功能（CPU/内存超过阈值时通知）
   - 添加历史趋势图表

2. **审计日志增强**:
   - 添加更多操作类型的自动记录
   - 集成到各个业务模块的关键操作中
   - 添加日志分析和异常检测

3. **性能优化**:
   - 为审计日志表添加分区
   - 实现日志归档机制
   - 添加缓存层减少数据库查询

---

## 故障排查

### 问题1: 监控页面显示"未连接"

**原因**: psutil未安装或中间件服务未启动

**解决**:
```bash
pip install psutil
# 检查Redis、RabbitMQ等服务是否运行
```

### 问题2: 审计日志无法保存

**原因**: 数据库表未创建

**解决**:
```bash
mysql -u root -p your_database < database/migrations/add_audit_log_table.sql
```

### 问题3: CORS错误

**原因**: 前后端跨域配置问题

**解决**: 确保已正确配置Vite代理和Flask CORS（已在之前修复）

---

## 相关文件清单

### 后端文件
- `api/monitoring.py` - 系统监控API
- `api/audit_log.py` - 审计日志API
- `models/user_models.py` - 添加了AuditLog模型
- `main.py` - 注册新的蓝图

### 前端文件
- `tonjclaw-web/src/api/admin/monitoring.js` - 监控API调用
- `tonjclaw-web/src/api/admin/auditLogs.js` - 审计日志API调用
- `tonjclaw-web/src/views/admin/Monitoring/index.vue` - 监控页面
- `tonjclaw-web/src/views/admin/AuditLogs/index.vue` - 审计日志页面

### 配置文件
- `requirements.txt` - 添加psutil依赖
- `database/migrations/add_audit_log_table.sql` - 数据库迁移脚本

---

## 总结

本次更新完成了Admin Portal的三个核心管理模块：
- ✅ 系统监控 - 实时监控系统健康和性能
- ✅ 审计日志 - 完整记录和追踪系统操作
- ✅ 系统设置 - 已存在的配置管理功能

这些模块为系统管理员提供了全面的监控和管理能力，有助于保障系统的稳定运行和安全合规。
