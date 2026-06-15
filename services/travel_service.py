"""
旅行社服务模块
实现旅游线路解析、转发、自动回复、报名处理、日报等功能
"""
import json
import logging
import re
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional

from config.settings import settings
from database.db_config import get_db_session
from models.travel_models import TravelRoute, TravelGroup, TravelRegistration, TravelFeedback, TravelReplyRule
from services.ai_parser import parse_order_with_ai, is_ai_enabled
from services.hook_client import hook_client
from services.feishu_client import feishu_client

logger = logging.getLogger(__name__)


class TravelService:
    """旅行社服务类"""

    def parse_travel_route(self, text: str) -> Dict[str, Any]:
        """解析旅游线路信息"""
        logger.info(f"开始解析旅游线路: {text[:50]}...")

        if is_ai_enabled():
            ai_result = parse_order_with_ai(text, {'type': 'travel'})
            if ai_result.get('success'):
                return self._normalize_ai_route(ai_result)

        return self._parse_with_rules(text)

    def _normalize_ai_route(self, ai_result: Dict[str, Any]) -> Dict[str, Any]:
        """规范化AI解析结果"""
        items = ai_result.get('items', [])
        if not items:
            return {'success': False, 'message': '未解析到线路信息'}

        first_item = items[0]
        return {
            'success': True,
            'route_name': first_item.get('product_name', ''),
            'price': first_item.get('quantity', 0),
            'start_date': ai_result.get('customer_name', ''),
            'group_size': 0,
            'duration': 0,
            'route_details': '',
            'highlights': ai_result.get('remarks', []),
            'confidence': ai_result.get('confidence', 0.0),
        }

    def _parse_with_rules(self, text: str) -> Dict[str, Any]:
        """使用规则解析线路信息"""
        result = {
            'success': True,
            'route_name': '',
            'price': 0.00,
            'start_date': '',
            'group_size': 10,
            'duration': 0,
            'route_details': '',
            'highlights': [],
            'confidence': 0.6,
        }

        price_match = re.search(r'(\d+(?:\.\d+)?)\s*[元块]', text)
        if price_match:
            result['price'] = float(price_match.group(1))

        date_match = re.search(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})[日号]?', text)
        if date_match:
            try:
                result['start_date'] = f"{date_match.group(1)}-{date_match.group(2).zfill(2)}-{date_match.group(3).zfill(2)}"
            except:
                pass

        days_match = re.search(r'(\d+)\s*天', text)
        if days_match:
            result['duration'] = int(days_match.group(1))

        people_match = re.search(r'(\d+)\s*[人位]', text)
        if people_match:
            result['group_size'] = int(people_match.group(1))

        result['route_name'] = text[:100]
        result['route_details'] = text

        return result

    def create_route(self, route_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建旅游线路"""
        db = get_db_session()
        try:
            route = TravelRoute(
                route_name=route_data['route_name'],
                price=route_data.get('price', 0.00),
                start_date=route_data.get('start_date'),
                group_size=route_data.get('group_size', 10),
                duration=route_data.get('duration', 1),
                route_details=route_data.get('route_details', ''),
                highlights=json.dumps(route_data.get('highlights', [])),
                source_url=route_data.get('source_url', ''),
                status=route_data.get('status', 'draft'),
            )
            db.add(route)
            db.commit()
            db.refresh(route)
            logger.info(f"旅游线路创建成功: {route.route_name}")
            return {'success': True, 'data': route.to_dict()}
        except Exception as e:
            db.rollback()
            logger.error(f"旅游线路创建失败: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            db.close()

    def get_route(self, route_id: int) -> Optional[TravelRoute]:
        """获取线路详情"""
        db = get_db_session()
        try:
            return db.query(TravelRoute).filter(TravelRoute.id == route_id).first()
        finally:
            db.close()

    def get_routes(self, status: Optional[str] = None) -> List[TravelRoute]:
        """获取线路列表"""
        db = get_db_session()
        try:
            query = db.query(TravelRoute)
            if status:
                query = query.filter(TravelRoute.status == status)
            return query.order_by(TravelRoute.created_at.desc()).all()
        finally:
            db.close()

    def update_route(self, route_id: int, route_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新线路信息"""
        db = get_db_session()
        try:
            route = db.query(TravelRoute).filter(TravelRoute.id == route_id).first()
            if not route:
                return {'success': False, 'error': '线路不存在'}

            if 'route_name' in route_data:
                route.route_name = route_data['route_name']
            if 'price' in route_data:
                route.price = route_data['price']
            if 'start_date' in route_data:
                route.start_date = route_data['start_date']
            if 'group_size' in route_data:
                route.group_size = route_data['group_size']
            if 'duration' in route_data:
                route.duration = route_data['duration']
            if 'route_details' in route_data:
                route.route_details = route_data['route_details']
            if 'highlights' in route_data:
                route.highlights = json.dumps(route_data['highlights'])
            if 'status' in route_data:
                route.status = route_data['status']

            db.commit()
            db.refresh(route)
            return {'success': True, 'data': route.to_dict()}
        except Exception as e:
            db.rollback()
            logger.error(f"更新线路失败: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            db.close()

    def delete_route(self, route_id: int) -> Dict[str, Any]:
        """删除线路"""
        db = get_db_session()
        try:
            route = db.query(TravelRoute).filter(TravelRoute.id == route_id).first()
            if not route:
                return {'success': False, 'error': '线路不存在'}

            db.delete(route)
            db.commit()
            return {'success': True}
        except Exception as e:
            db.rollback()
            logger.error(f"删除线路失败: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            db.close()

    def create_group(self, group_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建群配置"""
        db = get_db_session()
        try:
            group = TravelGroup(
                platform=group_data.get('platform', 'wechat'),
                group_id=group_data['group_id'],
                group_name=group_data.get('group_name', ''),
                boss_wxid=group_data.get('boss_wxid', ''),
                is_active=group_data.get('is_active', 1),
            )
            db.add(group)
            db.commit()
            db.refresh(group)
            logger.info(f"旅游群配置创建成功: {group.group_name}")
            return {'success': True, 'data': group.to_dict()}
        except Exception as e:
            db.rollback()
            logger.error(f"创建群配置失败: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            db.close()

    def get_groups(self) -> List[TravelGroup]:
        """获取群列表"""
        db = get_db_session()
        try:
            return db.query(TravelGroup).filter(TravelGroup.is_active == 1).all()
        finally:
            db.close()

    def forward_route_to_groups(self, route_id: int) -> Dict[str, Any]:
        """转发线路到所有旅游群"""
        if not settings.TRAVEL_AUTO_FORWARD:
            return {'success': False, 'message': '自动转发未启用'}

        route = self.get_route(route_id)
        if not route:
            return {'success': False, 'error': '线路不存在'}

        groups = self.get_groups()
        if not groups:
            return {'success': False, 'message': '未配置旅游群'}

        results = []
        for group in groups:
            success = self._send_route_to_group(route, group)
            results.append({
                'group_name': group.group_name,
                'platform': group.platform,
                'success': success,
            })

        success_count = sum(1 for r in results if r['success'])
        return {
            'success': True,
            'message': f'已转发到 {success_count}/{len(groups)} 个群',
            'results': results,
        }

    def _send_route_to_group(self, route: TravelRoute, group: TravelGroup) -> bool:
        """发送线路信息到指定群"""
        route_info = route.to_dict()
        message = self._format_route_message(route_info)

        if group.platform == 'feishu' and feishu_client.is_enabled():
            card = feishu_client.create_travel_card(route_info)
            return feishu_client.send_card(group.group_id, card)
        elif group.platform == 'wechat':
            return hook_client.send_text(group.group_id, message)

        logger.warning(f"不支持的平台: {group.platform}")
        return False

    def _format_route_message(self, route_info: Dict[str, Any]) -> str:
        """格式化线路消息"""
        highlights = route_info.get('highlights', [])
        highlights_text = '\n✨ ' + '\n✨ '.join(highlights) if highlights else ''

        return f"""🌟 {route_info['route_name']}

💰 价格: ¥{route_info['price']:.2f}
📅 出发时间: {route_info['start_date']}
👥 成团要求: {route_info['group_size']}人起
⏱️ 行程天数: {route_info['duration']}天
📍 线路详情: {route_info['route_details']}
{highlights_text}

感兴趣的朋友可以直接报名！"""

    def process_group_feedback(self, group_id: str, user_id: str, user_name: str, content: str) -> Dict[str, Any]:
        """处理群反馈"""
        db = get_db_session()
        try:
            travel_group = db.query(TravelGroup).filter(TravelGroup.group_id == group_id).first()
            if not travel_group:
                return {'success': False, 'error': '群配置不存在'}

            intent = self._analyze_intent(content)
            route_id = self._extract_route_id(content)

            feedback = TravelFeedback(
                group_id=travel_group.id,
                user_id=user_id,
                user_name=user_name,
                content=content,
                route_id=route_id,
                intent=intent,
                status='pending',
            )
            db.add(feedback)
            db.commit()
            db.refresh(feedback)

            if intent == 'registration':
                return self._handle_registration(travel_group, feedback)

            if settings.TRAVEL_AUTO_REPLY:
                response = self._find_auto_reply(content, route_id)
                if response:
                    feedback.response = response
                    feedback.status = 'responded'
                    db.commit()
                    self._send_response(group_id, user_id, response, travel_group.platform)
                    return {'success': True, 'message': '已自动回复', 'response': response}

            feedback.status = 'escalated'
            db.commit()
            self._escalate_to_boss(travel_group, feedback)
            return {'success': True, 'message': '已转发给老板', 'escalated': True}

        except Exception as e:
            db.rollback()
            logger.error(f"处理群反馈失败: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            db.close()

    def _analyze_intent(self, content: str) -> str:
        """分析用户意图"""
        content_lower = content.lower()
        if any(keyword in content_lower for keyword in ['报名', '参加', '我要', '预订', '下单']):
            return 'registration'
        if any(keyword in content_lower for keyword in ['投诉', '不满', '不好', '问题']):
            return 'complaint'
        if any(keyword in content_lower for keyword in ['多少钱', '价格', '贵', '便宜', '包含', '住宿', '交通']):
            return 'inquiry'
        return 'other'

    def _extract_route_id(self, content: str) -> Optional[int]:
        """从内容中提取线路ID"""
        match = re.search(r'线路(\d+)', content)
        if match:
            return int(match.group(1))
        return None

    def _find_auto_reply(self, content: str, route_id: Optional[int] = None) -> Optional[str]:
        """查找自动回复规则"""
        db = get_db_session()
        try:
            query = db.query(TravelReplyRule).filter(TravelReplyRule.is_active == 1)
            if route_id:
                query = query.filter((TravelReplyRule.route_id == route_id) | (TravelReplyRule.route_id.is_(None)))
            rules = query.order_by(TravelReplyRule.priority.desc()).all()

            for rule in rules:
                if rule.keyword and rule.keyword in content:
                    rule.match_count += 1
                    db.commit()
                    return rule.response
                if rule.pattern:
                    try:
                        if re.search(rule.pattern, content):
                            rule.match_count += 1
                            db.commit()
                            return rule.response
                    except:
                        continue

            return None
        finally:
            db.close()

    def _handle_registration(self, travel_group: TravelGroup, feedback: TravelFeedback) -> Dict[str, Any]:
        """处理报名"""
        route_id = feedback.route_id
        if not route_id:
            routes = self.get_routes(status='published')
            if routes:
                route_id = routes[0].id

        if not route_id:
            return {'success': False, 'error': '未找到可报名的线路'}

        db = get_db_session()
        try:
            registration = TravelRegistration(
                route_id=route_id,
                user_id=feedback.user_id,
                user_name=feedback.user_name,
                people_count=1,
                status='pending',
            )
            db.add(registration)
            db.commit()
            db.refresh(registration)

            self._send_promotion_message(travel_group, registration)
            return {'success': True, 'message': '报名成功', 'registration_id': registration.id}
        except Exception as e:
            db.rollback()
            logger.error(f"创建报名失败: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            db.close()

    def _send_promotion_message(self, travel_group: TravelGroup, registration: TravelRegistration):
        """发送促单消息"""
        route = self.get_route(registration.route_id)
        if not route:
            return

        message = f"""🎉 感谢您的报名！

📋 线路: {route.route_name}
💰 价格: ¥{route.price:.2f}/人
📅 出发: {route.start_date}
👥 成团: {route.group_size}人起

请尽快确认并提供以下信息：
1. 联系电话
2. 出行人数
3. 特殊需求

如有疑问请随时联系！"""

        if travel_group.platform == 'feishu' and feishu_client.is_enabled():
            feishu_client.send_text(registration.user_id, message)
        elif travel_group.platform == 'wechat':
            hook_client.send_text(registration.user_id, message)

    def _send_response(self, group_id: str, user_id: str, response: str, platform: str):
        """发送回复消息"""
        if platform == 'feishu' and feishu_client.is_enabled():
            feishu_client.send_text(group_id, response, at_user_ids=[user_id])
        elif platform == 'wechat':
            hook_client.send_at_text(group_id, response, [user_id])

    def _escalate_to_boss(self, travel_group: TravelGroup, feedback: TravelFeedback):
        """将反馈转发给老板"""
        if not travel_group.boss_wxid:
            logger.warning("老板微信/飞书ID未配置")
            return

        message = f"""📩 群反馈待处理

群名称: {travel_group.group_name}
用户: {feedback.user_name}
内容: {feedback.content}
意图: {feedback.intent}

请回复处理方案，系统将自动转发给用户。"""

        if travel_group.platform == 'feishu' and feishu_client.is_enabled():
            feishu_client.send_text(travel_group.boss_wxid, message)
        elif travel_group.platform == 'wechat':
            hook_client.send_text(travel_group.boss_wxid, message)

    def create_registration(self, registration_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建报名"""
        db = get_db_session()
        try:
            registration = TravelRegistration(
                route_id=registration_data['route_id'],
                user_id=registration_data.get('user_id', ''),
                user_name=registration_data.get('user_name', ''),
                phone=registration_data.get('phone', ''),
                people_count=registration_data.get('people_count', 1),
                status='pending',
                remark=registration_data.get('remark', ''),
            )
            db.add(registration)
            db.commit()
            db.refresh(registration)
            logger.info(f"报名创建成功: {registration.user_name}")
            return {'success': True, 'data': registration.to_dict()}
        except Exception as e:
            db.rollback()
            logger.error(f"创建报名失败: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            db.close()

    def update_registration(self, registration_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新报名状态"""
        db = get_db_session()
        try:
            registration = db.query(TravelRegistration).filter(TravelRegistration.id == registration_id).first()
            if not registration:
                return {'success': False, 'error': '报名不存在'}

            if 'status' in data:
                registration.status = data['status']
            if 'phone' in data:
                registration.phone = data['phone']
            if 'people_count' in data:
                registration.people_count = data['people_count']
            if 'remark' in data:
                registration.remark = data['remark']

            db.commit()
            db.refresh(registration)
            return {'success': True, 'data': registration.to_dict()}
        except Exception as e:
            db.rollback()
            logger.error(f"更新报名失败: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            db.close()

    def get_registrations(self, route_id: Optional[int] = None, status: Optional[str] = None) -> List[TravelRegistration]:
        """获取报名列表"""
        db = get_db_session()
        try:
            query = db.query(TravelRegistration)
            if route_id:
                query = query.filter(TravelRegistration.route_id == route_id)
            if status:
                query = query.filter(TravelRegistration.status == status)
            return query.order_by(TravelRegistration.created_at.desc()).all()
        finally:
            db.close()

    def reply_feedback(self, feedback_id: int, response: str) -> Dict[str, Any]:
        """回复反馈"""
        db = get_db_session()
        try:
            feedback = db.query(TravelFeedback).filter(TravelFeedback.id == feedback_id).first()
            if not feedback:
                return {'success': False, 'error': '反馈不存在'}

            feedback.response = response
            feedback.status = 'responded'
            db.commit()

            travel_group = db.query(TravelGroup).filter(TravelGroup.id == feedback.group_id).first()
            if travel_group:
                self._send_response(travel_group.group_id, feedback.user_id, response, travel_group.platform)

            return {'success': True, 'data': feedback.to_dict()}
        except Exception as e:
            db.rollback()
            logger.error(f"回复反馈失败: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            db.close()

    def get_feedbacks(self, group_id: Optional[int] = None, status: Optional[str] = None) -> List[TravelFeedback]:
        """获取反馈列表"""
        db = get_db_session()
        try:
            query = db.query(TravelFeedback)
            if group_id:
                query = query.filter(TravelFeedback.group_id == group_id)
            if status:
                query = query.filter(TravelFeedback.status == status)
            return query.order_by(TravelFeedback.created_at.desc()).all()
        finally:
            db.close()

    def generate_daily_report(self, date_str: Optional[str] = None) -> Dict[str, Any]:
        """生成日报"""
        if not date_str:
            date_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        db = get_db_session()
        try:
            feedbacks = db.query(TravelFeedback).filter(
                TravelFeedback.created_at >= date_str,
                TravelFeedback.created_at < (datetime.strptime(date_str, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
            ).all()

            registrations = db.query(TravelRegistration).filter(
                TravelRegistration.created_at >= date_str,
                TravelRegistration.created_at < (datetime.strptime(date_str, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
            ).all()

            route_stats = {}
            for reg in registrations:
                route_name = str(reg.route_id)
                route_stats[route_name] = route_stats.get(route_name, 0) + 1

            report = {
                'date': date_str,
                'feedback_count': len(feedbacks),
                'registration_count': len(registrations),
                'route_stats': route_stats,
                'feedbacks': [f.to_dict() for f in feedbacks],
                'registrations': [r.to_dict() for r in registrations],
            }

            return {'success': True, 'data': report}
        finally:
            db.close()

    def send_daily_report(self):
        """发送日报给老板"""
        report = self.generate_daily_report()
        if not report['success']:
            return

        data = report['data']
        message = f"""📊 旅游业务日报 ({data['date']})

📩 群反馈: {data['feedback_count']} 条
📝 报名数: {data['registration_count']} 个

📋 各线路报名统计:
"""
        for route_name, count in data['route_stats'].items():
            message += f"  - 线路{route_name}: {count}人\n"

        message += "\n如有异常请及时处理！"

        groups = self.get_groups()
        for group in groups:
            if group.boss_wxid:
                if group.platform == 'feishu' and feishu_client.is_enabled():
                    feishu_client.send_text(group.boss_wxid, message)
                elif group.platform == 'wechat':
                    hook_client.send_text(group.boss_wxid, message)

    def create_reply_rule(self, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建自动回复规则"""
        db = get_db_session()
        try:
            rule = TravelReplyRule(
                rule_name=rule_data['rule_name'],
                keyword=rule_data.get('keyword', ''),
                pattern=rule_data.get('pattern', ''),
                response=rule_data['response'],
                route_id=rule_data.get('route_id'),
                priority=rule_data.get('priority', 0),
                is_active=rule_data.get('is_active', 1),
            )
            db.add(rule)
            db.commit()
            db.refresh(rule)
            return {'success': True, 'data': rule.to_dict()}
        except Exception as e:
            db.rollback()
            logger.error(f"创建回复规则失败: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            db.close()

    def get_reply_rules(self, route_id: Optional[int] = None) -> List[TravelReplyRule]:
        """获取回复规则列表"""
        db = get_db_session()
        try:
            query = db.query(TravelReplyRule).filter(TravelReplyRule.is_active == 1)
            if route_id:
                query = query.filter((TravelReplyRule.route_id == route_id) | (TravelReplyRule.route_id.is_(None)))
            return query.order_by(TravelReplyRule.priority.desc()).all()
        finally:
            db.close()


travel_service = TravelService()
