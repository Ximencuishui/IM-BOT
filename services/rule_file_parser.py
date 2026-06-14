"""
规则文件解析服务
支持从txt、csv、md格式文件中解析规则配置
"""
import csv
import json
import re
from typing import Dict, List, Optional, Tuple
from io import StringIO


class RuleFileParser:
    """规则文件解析器"""

    @staticmethod
    def parse_file(file_content: str, file_type: str) -> Dict:
        """
        解析规则文件
        :param file_content: 文件内容字符串
        :param file_type: 文件类型 (txt/csv/md)
        :return: 解析后的规则字典 {parse_rules, stat_rules, reply_rules}
        """
        if file_type == 'txt':
            return RuleFileParser._parse_txt(file_content)
        elif file_type == 'csv':
            return RuleFileParser._parse_csv(file_content)
        elif file_type == 'md':
            return RuleFileParser._parse_md(file_content)
        else:
            raise ValueError(f"不支持的文件类型: {file_type}")

    @staticmethod
    def _parse_txt(content: str) -> Dict:
        """
        解析TXT格式规则文件
        支持结构化文本格式：
        
        === 解析规则 ===
        规则名称: 标准数量+单位+商品
        规则类型: regex
        匹配模式: (\d+(?:\.\d+)?)\s*(斤|两|kg|公斤|包|箱|瓶)(.+?)(?:，|$)
        优先级: 10
        启用状态: true
        ---
        规则名称: 关键词匹配
        规则类型: keyword
        匹配模式: 下单
        优先级: 5
        启用状态: true
        
        === 统计规则 ===
        规则名称: 每日销售统计
        统计类型: daily
        图表类型: bar
        刷新间隔: 3600
        启用状态: true
        
        === 回复规则 ===
        规则名称: 订单确认回复
        触发类型: keyword
        触发内容: 下单成功
        回复类型: text
        回复内容: 已收到您的订单
        优先级: 10
        启用状态: true
        """
        result = {
            'parse_rules': [],
            'stat_rules': [],
            'reply_rules': []
        }

        # 分割不同规则区块
        sections = re.split(r'===\s*(.*?)\s*===', content)

        for i in range(1, len(sections), 2):
            section_title = sections[i].strip()
            section_content = sections[i + 1] if i + 1 < len(sections) else ''

            if '解析规则' in section_title:
                result['parse_rules'] = RuleFileParser._parse_txt_section(section_content, 'parse')
            elif '统计规则' in section_title:
                result['stat_rules'] = RuleFileParser._parse_txt_section(section_content, 'stat')
            elif '回复规则' in section_title:
                result['reply_rules'] = RuleFileParser._parse_txt_section(section_content, 'reply')

        return result

    @staticmethod
    def _parse_txt_section(content: str, rule_type: str) -> List[Dict]:
        """解析TXT格式的单个规则区块"""
        rules = []
        # 使用 --- 分隔多个规则
        rule_blocks = re.split(r'\n---\s*\n', content.strip())

        for block in rule_blocks:
            if not block.strip():
                continue

            rule = {}
            lines = block.strip().split('\n')

            for line in lines:
                line = line.strip()
                if ':' in line or '：' in line:
                    # 支持中英文冒号
                    parts = re.split(r'[：:]', line, maxsplit=1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parts[1].strip()
                        rule[key] = value

            # 根据规则类型转换字段
            if rule_type == 'parse':
                parsed_rule = RuleFileParser._convert_parse_rule(rule)
                if parsed_rule:
                    rules.append(parsed_rule)
            elif rule_type == 'stat':
                parsed_rule = RuleFileParser._convert_stat_rule(rule)
                if parsed_rule:
                    rules.append(parsed_rule)
            elif rule_type == 'reply':
                parsed_rule = RuleFileParser._convert_reply_rule(rule)
                if parsed_rule:
                    rules.append(parsed_rule)

        return rules

    @staticmethod
    def _parse_csv(content: str) -> Dict:
        """
        解析CSV格式规则文件
        支持三个工作表（通过注释或分隔符区分）：
        
        # 解析规则
        规则名称,规则类型,匹配模式,提取字段,优先级,启用状态,描述
        标准规则,regex,"(\d+)\s*(斤|两)",{},10,true,标准数量匹配
        
        # 统计规则
        规则名称,统计类型,维度配置,过滤条件,图表类型,刷新间隔,启用状态
        日报,daily,"{""by"":""product""}","{}",bar,3600,true
        """
        result = {
            'parse_rules': [],
            'stat_rules': [],
            'reply_rules': []
        }

        current_section = None
        csv_content = StringIO(content)
        reader = csv.reader(csv_content)

        headers = None
        for row in reader:
            if not row or not any(cell.strip() for cell in row):
                continue

            first_cell = row[0].strip()

            # 检测章节标记
            if first_cell.startswith('#'):
                section_name = first_cell[1:].strip()
                if '解析规则' in section_name:
                    current_section = 'parse'
                    headers = None
                elif '统计规则' in section_name:
                    current_section = 'stat'
                    headers = None
                elif '回复规则' in section_name:
                    current_section = 'reply'
                    headers = None
                continue

            # 处理数据行
            if current_section:
                if headers is None:
                    headers = [h.strip() for h in row]
                else:
                    rule_dict = dict(zip(headers, row))
                    if current_section == 'parse':
                        parsed = RuleFileParser._convert_parse_rule(rule_dict)
                        if parsed:
                            result['parse_rules'].append(parsed)
                    elif current_section == 'stat':
                        parsed = RuleFileParser._convert_stat_rule(rule_dict)
                        if parsed:
                            result['stat_rules'].append(parsed)
                    elif current_section == 'reply':
                        parsed = RuleFileParser._convert_reply_rule(rule_dict)
                        if parsed:
                            result['reply_rules'].append(parsed)

        return result

    @staticmethod
    def _parse_md(content: str) -> Dict:
        """
        解析Markdown格式规则文件
        支持表格和列表格式：
        
        ## 解析规则
        
        | 规则名称 | 规则类型 | 匹配模式 | 优先级 | 启用状态 |
        |---------|---------|---------|-------|---------|
        | 标准规则 | regex | `(\d+)\s*(斤\|两)` | 10 | true |
        
        ## 统计规则
        
        - 规则名称: 日报
        - 统计类型: daily
        - 图表类型: bar
        - 刷新间隔: 3600
        - 启用状态: true
        """
        result = {
            'parse_rules': [],
            'stat_rules': [],
            'reply_rules': []
        }

        # 按标题分割
        sections = re.split(r'^##\s+', content, flags=re.MULTILINE)

        for section in sections:
            if not section.strip():
                continue

            # 提取标题和内容
            lines = section.split('\n')
            title = lines[0].strip()

            if '解析规则' in title:
                result['parse_rules'] = RuleFileParser._parse_md_section('\n'.join(lines[1:]), 'parse')
            elif '统计规则' in title:
                result['stat_rules'] = RuleFileParser._parse_md_section('\n'.join(lines[1:]), 'stat')
            elif '回复规则' in title:
                result['reply_rules'] = RuleFileParser._parse_md_section('\n'.join(lines[1:]), 'reply')

        return result

    @staticmethod
    def _parse_md_section(content: str, rule_type: str) -> List[Dict]:
        """解析Markdown格式的单个规则区块"""
        rules = []

        # 尝试解析表格格式
        if '|' in content and '---' in content:
            table_rules = RuleFileParser._parse_md_table(content, rule_type)
            rules.extend(table_rules)

        # 尝试解析列表格式
        list_rules = RuleFileParser._parse_md_list(content, rule_type)
        rules.extend(list_rules)

        return rules

    @staticmethod
    def _parse_md_table(content: str, rule_type: str) -> List[Dict]:
        """解析Markdown表格"""
        rules = []
        lines = content.strip().split('\n')

        headers = []
        data_rows = []
        is_header = True
        passed_separator = False

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 跳过代码块标记
            if line.startswith('```'):
                continue

            # 检测分隔线
            if '|---' in line or '-|-' in line:
                passed_separator = True
                is_header = False
                continue

            # 提取单元格
            cells = [cell.strip() for cell in line.split('|')]
            cells = [c for c in cells if c]  # 移除空单元格

            if not cells:
                continue

            if is_header and not passed_separator:
                headers = cells
            elif passed_separator:
                data_rows.append(cells)

        # 转换数据行
        for row in data_rows:
            if len(row) != len(headers):
                continue

            rule_dict = dict(zip(headers, row))
            # 清理代码标记
            for key in rule_dict:
                if isinstance(rule_dict[key], str):
                    rule_dict[key] = rule_dict[key].strip('`').strip()

            if rule_type == 'parse':
                parsed = RuleFileParser._convert_parse_rule(rule_dict)
                if parsed:
                    rules.append(parsed)
            elif rule_type == 'stat':
                parsed = RuleFileParser._convert_stat_rule(rule_dict)
                if parsed:
                    rules.append(parsed)
            elif rule_type == 'reply':
                parsed = RuleFileParser._convert_reply_rule(rule_dict)
                if parsed:
                    rules.append(parsed)

        return rules

    @staticmethod
    def _parse_md_list(content: str, rule_type: str) -> List[Dict]:
        """解析Markdown列表格式"""
        rules = []
        current_rule = {}
        lines = content.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line or line.startswith('```'):
                continue

            # 检测新规则开始（以 - 或 * 开头且包含冒号）
            is_new_rule = (line.startswith('- ') or line.startswith('* ')) and ':' in line
            
            if is_new_rule and current_rule and any(k in line for k in ['规则名称', 'rule_name']):
                # 保存上一个规则
                if rule_type == 'parse':
                    parsed = RuleFileParser._convert_parse_rule(current_rule)
                    if parsed:
                        rules.append(parsed)
                elif rule_type == 'stat':
                    parsed = RuleFileParser._convert_stat_rule(current_rule)
                    if parsed:
                        rules.append(parsed)
                elif rule_type == 'reply':
                    parsed = RuleFileParser._convert_reply_rule(current_rule)
                    if parsed:
                        rules.append(parsed)

                current_rule = {}

            # 解析键值对
            if ':' in line or '：' in line:
                parts = re.split(r'[：:]', line.lstrip('- ').lstrip('* '), maxsplit=1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip().strip('`')
                    current_rule[key] = value

        # 处理最后一个规则
        if current_rule:
            if rule_type == 'parse':
                parsed = RuleFileParser._convert_parse_rule(current_rule)
                if parsed:
                    rules.append(parsed)
            elif rule_type == 'stat':
                parsed = RuleFileParser._convert_stat_rule(current_rule)
                if parsed:
                    rules.append(parsed)
            elif rule_type == 'reply':
                parsed = RuleFileParser._convert_reply_rule(current_rule)
                if parsed:
                    rules.append(parsed)

        return rules

    @staticmethod
    def _convert_parse_rule(rule_dict: Dict) -> Optional[Dict]:
        """转换为解析规则格式"""
        try:
            rule_name = rule_dict.get('规则名称') or rule_dict.get('rule_name', '').strip()
            if not rule_name:
                return None

            rule_type = rule_dict.get('规则类型') or rule_dict.get('rule_type', 'regex')
            pattern = rule_dict.get('匹配模式') or rule_dict.get('pattern', '')
            extract_fields = rule_dict.get('提取字段') or rule_dict.get('extract_fields', '{}')
            priority = int(rule_dict.get('优先级') or rule_dict.get('priority', 0))
            is_active = RuleFileParser._parse_bool(rule_dict.get('启用状态') or rule_dict.get('is_active', 'true'))
            description = rule_dict.get('描述') or rule_dict.get('description', '')

            # 尝试解析JSON字段
            try:
                if isinstance(extract_fields, str):
                    extract_fields = json.loads(extract_fields)
            except:
                extract_fields = {}

            return {
                'rule_name': rule_name,
                'rule_type': rule_type,
                'pattern': pattern,
                'extract_fields': json.dumps(extract_fields, ensure_ascii=False) if isinstance(extract_fields, dict) else extract_fields,
                'priority': priority,
                'is_active': is_active,
                'description': description
            }
        except Exception as e:
            print(f"解析解析规则失败: {e}")
            return None

    @staticmethod
    def _convert_stat_rule(rule_dict: Dict) -> Optional[Dict]:
        """转换为统计规则格式"""
        try:
            rule_name = rule_dict.get('规则名称') or rule_dict.get('rule_name', '').strip()
            if not rule_name:
                return None

            stat_type = rule_dict.get('统计类型') or rule_dict.get('stat_type', 'daily')
            dimensions = rule_dict.get('维度配置') or rule_dict.get('dimensions', '{}')
            filters = rule_dict.get('过滤条件') or rule_dict.get('filters', '{}')
            chart_type = rule_dict.get('图表类型') or rule_dict.get('chart_type', 'bar')
            refresh_interval = int(rule_dict.get('刷新间隔') or rule_dict.get('refresh_interval', 3600))
            is_active = RuleFileParser._parse_bool(rule_dict.get('启用状态') or rule_dict.get('is_active', 'true'))

            # 尝试解析JSON字段
            try:
                if isinstance(dimensions, str):
                    dimensions = json.loads(dimensions)
            except:
                dimensions = {}

            try:
                if isinstance(filters, str):
                    filters = json.loads(filters)
            except:
                filters = {}

            return {
                'rule_name': rule_name,
                'stat_type': stat_type,
                'dimensions': json.dumps(dimensions, ensure_ascii=False) if isinstance(dimensions, dict) else dimensions,
                'filters': json.dumps(filters, ensure_ascii=False) if isinstance(filters, dict) else filters,
                'chart_type': chart_type,
                'refresh_interval': refresh_interval,
                'is_active': is_active
            }
        except Exception as e:
            print(f"解析统计规则失败: {e}")
            return None

    @staticmethod
    def _convert_reply_rule(rule_dict: Dict) -> Optional[Dict]:
        """转换为回复规则格式"""
        try:
            rule_name = rule_dict.get('规则名称') or rule_dict.get('rule_name', '').strip()
            if not rule_name:
                return None

            trigger_type = rule_dict.get('触发类型') or rule_dict.get('trigger_type', 'keyword')
            trigger_content = rule_dict.get('触发内容') or rule_dict.get('trigger_content', '')
            reply_type = rule_dict.get('回复类型') or rule_dict.get('reply_type', 'text')
            reply_content = rule_dict.get('回复内容') or rule_dict.get('reply_content', '')
            priority = int(rule_dict.get('优先级') or rule_dict.get('priority', 0))
            is_active = RuleFileParser._parse_bool(rule_dict.get('启用状态') or rule_dict.get('is_active', 'true'))

            return {
                'rule_name': rule_name,
                'trigger_type': trigger_type,
                'trigger_content': trigger_content,
                'reply_type': reply_type,
                'reply_content': reply_content,
                'priority': priority,
                'is_active': is_active
            }
        except Exception as e:
            print(f"解析回复规则失败: {e}")
            return None

    @staticmethod
    def _parse_bool(value) -> bool:
        """解析布尔值"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', 'yes', '1', '启用', '是')
        return bool(value)

    @staticmethod
    def validate_parsed_rules(rules: Dict) -> Dict:
        """
        验证解析后的规则
        :return: {valid: bool, errors: [], warnings: []}
        """
        errors = []
        warnings = []

        # 验证解析规则
        for i, rule in enumerate(rules.get('parse_rules', [])):
            if not rule.get('rule_name'):
                errors.append(f"解析规则#{i+1}: 缺少规则名称")
            if not rule.get('pattern') and rule.get('rule_type') != 'custom':
                warnings.append(f"解析规则#{i+1} '{rule.get('rule_name')}': 未设置匹配模式")

        # 验证统计规则
        for i, rule in enumerate(rules.get('stat_rules', [])):
            if not rule.get('rule_name'):
                errors.append(f"统计规则#{i+1}: 缺少规则名称")
            stat_type = rule.get('stat_type', '')
            if stat_type and stat_type not in ['daily', 'weekly', 'monthly', 'custom']:
                errors.append(f"统计规则#{i+1} '{rule.get('rule_name')}': 无效的统计类型")

        # 验证回复规则
        for i, rule in enumerate(rules.get('reply_rules', [])):
            if not rule.get('rule_name'):
                errors.append(f"回复规则#{i+1}: 缺少规则名称")
            if not rule.get('reply_content'):
                errors.append(f"回复规则#{i+1} '{rule.get('rule_name')}': 缺少回复内容")

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
