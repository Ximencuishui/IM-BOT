"""
规则导入API
支持从文件导入解析规则、统计规则、回复规则
"""
import json
from flask import Blueprint, request, jsonify, session
from functools import wraps
from database.db_config import get_db_session
from services.rule_file_parser import RuleFileParser
from services.rule_service import ParseRuleService, StatRuleService
from models.user_models import User as UserModel

rule_import_bp = Blueprint('rule_import', __name__)


def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': '请先登录'}), 401
        return f(*args, **kwargs)
    return decorated_function


# 临时存储导入任务（生产环境应使用Redis）
import_tasks = {}


@rule_import_bp.route('/api/rules/import', methods=['POST'])
@login_required
def import_rules():
    """
    上传并解析规则文件
    :param file: 规则文件 (txt/csv/md)
    :return: {task_id, preview_data}
    """
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '未找到上传文件'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': '文件名为空'}), 400

    # 检查文件类型
    filename = file.filename.lower()
    if filename.endswith('.txt'):
        file_type = 'txt'
    elif filename.endswith('.csv'):
        file_type = 'csv'
    elif filename.endswith('.md'):
        file_type = 'md'
    else:
        return jsonify({'success': False, 'error': '不支持的文件格式，仅支持txt、csv、md'}), 400

    try:
        # 读取文件内容
        content = file.read().decode('utf-8')

        # 解析文件
        parsed_rules = RuleFileParser.parse_file(content, file_type)

        # 验证解析结果
        validation = RuleFileParser.validate_parsed_rules(parsed_rules)

        # 生成任务ID
        import uuid
        task_id = str(uuid.uuid4())

        # 保存预览数据到临时存储
        import_tasks[task_id] = {
            'user_id': session['user_id'],
            'parsed_rules': parsed_rules,
            'validation': validation,
            'filename': file.filename
        }

        return jsonify({
            'success': True,
            'task_id': task_id,
            'preview': {
                'parse_rules_count': len(parsed_rules.get('parse_rules', [])),
                'stat_rules_count': len(parsed_rules.get('stat_rules', [])),
                'reply_rules_count': len(parsed_rules.get('reply_rules', [])),
                'validation': validation,
                'rules': parsed_rules
            },
            'message': '文件解析成功，请预览并确认'
        })

    except UnicodeDecodeError:
        return jsonify({'success': False, 'error': '文件编码错误，请使用UTF-8编码'}), 400
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': f'文件解析失败: {str(e)}'}), 500


@rule_import_bp.route('/api/rules/import/preview/<task_id>', methods=['GET'])
@login_required
def get_import_preview(task_id):
    """
    获取导入预览
    :param task_id: 任务ID
    :return: 解析后的规则预览
    """
    task = import_tasks.get(task_id)
    if not task:
        return jsonify({'success': False, 'error': '任务不存在或已过期'}), 404

    if task['user_id'] != session['user_id']:
        return jsonify({'success': False, 'error': '无权访问此任务'}), 403

    return jsonify({
        'success': True,
        'preview': {
            'filename': task['filename'],
            'parse_rules_count': len(task['parsed_rules'].get('parse_rules', [])),
            'stat_rules_count': len(task['parsed_rules'].get('stat_rules', [])),
            'reply_rules_count': len(task['parsed_rules'].get('reply_rules', [])),
            'validation': task['validation'],
            'rules': task['parsed_rules']
        }
    })


@rule_import_bp.route('/api/rules/import/confirm/<task_id>', methods=['PUT'])
@login_required
def confirm_import(task_id):
    """
    确认导入规则
    :param task_id: 任务ID
    :param import_options: {parse_rules: bool, stat_rules: bool, reply_rules: bool, overwrite: bool}
    :return: 导入结果
    """
    task = import_tasks.get(task_id)
    if not task:
        return jsonify({'success': False, 'error': '任务不存在或已过期'}), 404

    if task['user_id'] != session['user_id']:
        return jsonify({'success': False, 'error': '无权访问此任务'}), 403

    # 检查验证结果
    if not task['validation']['valid']:
        return jsonify({
            'success': False,
            'error': '规则验证失败，请先修复错误',
            'errors': task['validation']['errors']
        }), 400

    # 获取导入选项
    data = request.get_json() or {}
    import_options = {
        'parse_rules': data.get('import_parse_rules', True),
        'stat_rules': data.get('import_stat_rules', True),
        'reply_rules': data.get('import_reply_rules', True),
        'overwrite': data.get('overwrite', False)  # 是否覆盖同名规则
    }

    db = get_db_session()
    user_id = session['user_id']
    result = {
        'parse_rules': {'success': 0, 'failed': 0, 'errors': []},
        'stat_rules': {'success': 0, 'failed': 0, 'errors': []},
        'reply_rules': {'success': 0, 'failed': 0, 'errors': []}
    }

    try:
        # 导入解析规则
        if import_options['parse_rules']:
            for rule_data in task['parsed_rules'].get('parse_rules', []):
                try:
                    # 检查是否已存在同名规则
                    existing = db.query(UserModel).filter(
                        UserModel.id == user_id
                    ).first().parse_rules
                    
                    from models.user_models import ParseRule
                    if not import_options['overwrite']:
                        existing_rule = db.query(ParseRule).filter(
                            ParseRule.user_id == user_id,
                            ParseRule.rule_name == rule_data['rule_name']
                        ).first()
                        if existing_rule:
                            result['parse_rules']['failed'] += 1
                            result['parse_rules']['errors'].append(
                                f"规则 '{rule_data['rule_name']}' 已存在，跳过导入"
                            )
                            continue

                    # 创建新规则
                    parse_result = ParseRuleService.create_rule(db, user_id, **rule_data)
                    if parse_result['success']:
                        result['parse_rules']['success'] += 1
                    else:
                        result['parse_rules']['failed'] += 1
                        result['parse_rules']['errors'].append(
                            f"{rule_data.get('rule_name')}: {parse_result.get('error')}"
                        )
                except Exception as e:
                    result['parse_rules']['failed'] += 1
                    result['parse_rules']['errors'].append(
                        f"{rule_data.get('rule_name')}: {str(e)}"
                    )

        # 导入统计规则
        if import_options['stat_rules']:
            for rule_data in task['parsed_rules'].get('stat_rules', []):
                try:
                    from models.user_models import StatRule
                    if not import_options['overwrite']:
                        existing_rule = db.query(StatRule).filter(
                            StatRule.user_id == user_id,
                            StatRule.rule_name == rule_data['rule_name']
                        ).first()
                        if existing_rule:
                            result['stat_rules']['failed'] += 1
                            result['stat_rules']['errors'].append(
                                f"规则 '{rule_data['rule_name']}' 已存在，跳过导入"
                            )
                            continue

                    stat_result = StatRuleService.create_rule(db, user_id, **rule_data)
                    if stat_result['success']:
                        result['stat_rules']['success'] += 1
                    else:
                        result['stat_rules']['failed'] += 1
                        result['stat_rules']['errors'].append(
                            f"{rule_data.get('rule_name')}: {stat_result.get('error')}"
                        )
                except Exception as e:
                    result['stat_rules']['failed'] += 1
                    result['stat_rules']['errors'].append(
                        f"{rule_data.get('rule_name')}: {str(e)}"
                    )

        # 导入回复规则
        if import_options['reply_rules']:
            from models.user_models import ReplyRule, RobotConfig
            for rule_data in task['parsed_rules'].get('reply_rules', []):
                try:
                    # 需要关联一个机器人配置
                    robot_config = db.query(RobotConfig).filter(
                        RobotConfig.user_id == user_id,
                        RobotConfig.is_default == True
                    ).first()

                    if not robot_config:
                        # 如果没有默认机器人，使用第一个
                        robot_config = db.query(RobotConfig).filter(
                            RobotConfig.user_id == user_id
                        ).first()

                    if not robot_config:
                        result['reply_rules']['failed'] += 1
                        result['reply_rules']['errors'].append(
                            f"规则 '{rule_data.get('rule_name')}': 请先创建机器人配置"
                        )
                        continue

                    if not import_options['overwrite']:
                        existing_rule = db.query(ReplyRule).filter(
                            ReplyRule.robot_config_id == robot_config.id,
                            ReplyRule.rule_name == rule_data['rule_name']
                        ).first()
                        if existing_rule:
                            result['reply_rules']['failed'] += 1
                            result['reply_rules']['errors'].append(
                                f"规则 '{rule_data['rule_name']}' 已存在，跳过导入"
                            )
                            continue

                    # 创建回复规则
                    new_rule = ReplyRule(
                        robot_config_id=robot_config.id,
                        rule_name=rule_data.get('rule_name'),
                        trigger_type=rule_data.get('trigger_type', 'keyword'),
                        trigger_content=rule_data.get('trigger_content'),
                        reply_type=rule_data.get('reply_type', 'text'),
                        reply_content=rule_data.get('reply_content'),
                        priority=rule_data.get('priority', 0),
                        is_active=rule_data.get('is_active', True)
                    )
                    db.add(new_rule)
                    db.commit()
                    result['reply_rules']['success'] += 1

                except Exception as e:
                    db.rollback()
                    result['reply_rules']['failed'] += 1
                    result['reply_rules']['errors'].append(
                        f"{rule_data.get('rule_name')}: {str(e)}"
                    )

        # 清理任务
        del import_tasks[task_id]

        total_success = sum(r['success'] for r in result.values())
        total_failed = sum(r['failed'] for r in result.values())

        return jsonify({
            'success': True,
            'result': result,
            'summary': {
                'total_success': total_success,
                'total_failed': total_failed
            },
            'message': f'导入完成：成功{total_success}条，失败{total_failed}条'
        })

    except Exception as e:
        db.rollback()
        return jsonify({
            'success': False,
            'error': f'导入失败: {str(e)}'
        }), 500
    finally:
        db.close()


@rule_import_bp.route('/api/rules/import/cancel/<task_id>', methods=['POST'])
@login_required
def cancel_import(task_id):
    """取消导入任务"""
    task = import_tasks.get(task_id)
    if not task:
        return jsonify({'success': False, 'error': '任务不存在'}), 404

    if task['user_id'] != session['user_id']:
        return jsonify({'success': False, 'error': '无权访问此任务'}), 403

    del import_tasks[task_id]
    return jsonify({'success': True, 'message': '已取消导入'})


@rule_import_bp.route('/api/rules/export', methods=['GET'])
@login_required
def export_rules():
    """
    导出规则为文件
    :param format: 导出格式 (txt/csv/md)
    :return: 规则文件下载
    """
    from flask import Response
    db = get_db_session()
    user_id = session['user_id']
    export_format = request.args.get('format', 'txt')

    try:
        # 获取用户的所有规则
        from models.user_models import ParseRule, StatRule, ReplyRule, RobotConfig
        
        parse_rules = db.query(ParseRule).filter(ParseRule.user_id == user_id).all()
        stat_rules = db.query(StatRule).filter(StatRule.user_id == user_id).all()
        
        # 获取回复规则（需要通过机器人配置）
        robot_configs = db.query(RobotConfig).filter(RobotConfig.user_id == user_id).all()
        reply_rules = []
        for config in robot_configs:
            reply_rules.extend(config.reply_rules)

        # 根据格式生成文件内容
        if export_format == 'txt':
            content = _generate_txt_export(parse_rules, stat_rules, reply_rules)
            mimetype = 'text/plain'
            extension = 'txt'
        elif export_format == 'csv':
            content = _generate_csv_export(parse_rules, stat_rules, reply_rules)
            mimetype = 'text/csv'
            extension = 'csv'
        elif export_format == 'md':
            content = _generate_md_export(parse_rules, stat_rules, reply_rules)
            mimetype = 'text/markdown'
            extension = 'md'
        else:
            return jsonify({'success': False, 'error': '不支持的导出格式'}), 400

        response = Response(content, mimetype=mimetype)
        response.headers['Content-Disposition'] = f'attachment; filename=rules_export.{extension}'
        return response

    except Exception as e:
        return jsonify({'success': False, 'error': f'导出失败: {str(e)}'}), 500
    finally:
        db.close()


def _generate_txt_export(parse_rules, stat_rules, reply_rules) -> str:
    """生成TXT格式导出"""
    lines = []
    
    # 解析规则
    lines.append('=== 解析规则 ===')
    lines.append('')
    for rule in parse_rules:
        lines.append(f'规则名称: {rule.rule_name}')
        lines.append(f'规则类型: {rule.rule_type}')
        lines.append(f'匹配模式: {rule.pattern or ""}')
        lines.append(f'优先级: {rule.priority}')
        lines.append(f'启用状态: {"true" if rule.is_active else "false"}')
        if rule.description:
            lines.append(f'描述: {rule.description}')
        lines.append('---')
        lines.append('')

    # 统计规则
    lines.append('=== 统计规则 ===')
    lines.append('')
    for rule in stat_rules:
        lines.append(f'规则名称: {rule.rule_name}')
        lines.append(f'统计类型: {rule.stat_type}')
        lines.append(f'图表类型: {rule.chart_type}')
        lines.append(f'刷新间隔: {rule.refresh_interval}')
        lines.append(f'启用状态: {"true" if rule.is_active else "false"}')
        lines.append('---')
        lines.append('')

    # 回复规则
    lines.append('=== 回复规则 ===')
    lines.append('')
    for rule in reply_rules:
        lines.append(f'规则名称: {rule.rule_name}')
        lines.append(f'触发类型: {rule.trigger_type}')
        lines.append(f'触发内容: {rule.trigger_content or ""}')
        lines.append(f'回复类型: {rule.reply_type}')
        lines.append(f'回复内容: {rule.reply_content}')
        lines.append(f'优先级: {rule.priority}')
        lines.append(f'启用状态: {"true" if rule.is_active else "false"}')
        lines.append('---')
        lines.append('')

    return '\n'.join(lines)


def _generate_csv_export(parse_rules, stat_rules, reply_rules) -> str:
    """生成CSV格式导出"""
    import csv
    output = StringIO()
    writer = csv.writer(output)

    # 解析规则
    writer.writerow(['# 解析规则'])
    writer.writerow(['规则名称', '规则类型', '匹配模式', '提取字段', '优先级', '启用状态', '描述'])
    for rule in parse_rules:
        writer.writerow([
            rule.rule_name,
            rule.rule_type,
            rule.pattern or '',
            rule.extract_fields or '{}',
            rule.priority,
            'true' if rule.is_active else 'false',
            rule.description or ''
        ])
    writer.writerow([])

    # 统计规则
    writer.writerow(['# 统计规则'])
    writer.writerow(['规则名称', '统计类型', '维度配置', '过滤条件', '图表类型', '刷新间隔', '启用状态'])
    for rule in stat_rules:
        writer.writerow([
            rule.rule_name,
            rule.stat_type,
            rule.dimensions or '{}',
            rule.filters or '{}',
            rule.chart_type,
            rule.refresh_interval,
            'true' if rule.is_active else 'false'
        ])
    writer.writerow([])

    # 回复规则
    writer.writerow(['# 回复规则'])
    writer.writerow(['规则名称', '触发类型', '触发内容', '回复类型', '回复内容', '优先级', '启用状态'])
    for rule in reply_rules:
        writer.writerow([
            rule.rule_name,
            rule.trigger_type,
            rule.trigger_content or '',
            rule.reply_type,
            rule.reply_content,
            rule.priority,
            'true' if rule.is_active else 'false'
        ])

    return output.getvalue()


def _generate_md_export(parse_rules, stat_rules, reply_rules) -> str:
    """生成Markdown格式导出"""
    lines = ['# 规则导出', '']

    # 解析规则
    lines.append('## 解析规则')
    lines.append('')
    lines.append('| 规则名称 | 规则类型 | 匹配模式 | 优先级 | 启用状态 | 描述 |')
    lines.append('|---------|---------|---------|-------|---------|------|')
    for rule in parse_rules:
        pattern = f'`{rule.pattern}`' if rule.pattern else ''
        lines.append(f'| {rule.rule_name} | {rule.rule_type} | {pattern} | {rule.priority} | {"true" if rule.is_active else "false"} | {rule.description or ""} |')
    lines.append('')

    # 统计规则
    lines.append('## 统计规则')
    lines.append('')
    lines.append('| 规则名称 | 统计类型 | 图表类型 | 刷新间隔 | 启用状态 |')
    lines.append('|---------|---------|---------|----------|---------|')
    for rule in stat_rules:
        lines.append(f'| {rule.rule_name} | {rule.stat_type} | {rule.chart_type} | {rule.refresh_interval} | {"true" if rule.is_active else "false"} |')
    lines.append('')

    # 回复规则
    lines.append('## 回复规则')
    lines.append('')
    lines.append('| 规则名称 | 触发类型 | 触发内容 | 回复类型 | 回复内容 | 优先级 | 启用状态 |')
    lines.append('|---------|---------|---------|---------|---------|-------|---------|')
    for rule in reply_rules:
        trigger = f'`{rule.trigger_content}`' if rule.trigger_content else ''
        reply = f'`{rule.reply_content}`' if rule.reply_content else ''
        lines.append(f'| {rule.rule_name} | {rule.trigger_type} | {trigger} | {rule.reply_type} | {reply} | {rule.priority} | {"true" if rule.is_active else "false"} |')
    lines.append('')

    return '\n'.join(lines)
