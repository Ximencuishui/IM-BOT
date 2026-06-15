import json
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from plugins.base.base_service import BaseService
from plugins.travel.models import (
    TravelRoute, TravelGroup, TravelRegistration, TravelFeedback, TravelReplyRule
)

logger = logging.getLogger(__name__)


class TravelService(BaseService):

    def create_route(self, route_data: Dict) -> Dict:
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
            self.db.add(route)
            self.db.commit()
            self.db.refresh(route)
            return {'success': True, 'data': route.to_dict()}
        except Exception as e:
            self.db.rollback()
            logger.error(f"创建线路失败: {e}")
            return {'success': False, 'error': str(e)}

    def list_routes(self, status: Optional[str] = None) -> List[Dict]:
        query = self.db.query(TravelRoute)
        if status:
            query = query.filter(TravelRoute.status == status)
        return [r.to_dict() for r in query.order_by(TravelRoute.created_at.desc()).all()]

    def get_route(self, route_id: int) -> Optional[Dict]:
        route = self.db.query(TravelRoute).filter(TravelRoute.id == route_id).first()
        return route.to_dict() if route else None

    def update_route(self, route_id: int, route_data: Dict) -> Dict:
        route = self.db.query(TravelRoute).filter(TravelRoute.id == route_id).first()
        if not route:
            return {'success': False, 'error': '线路不存在'}

        try:
            for key, value in route_data.items():
                if hasattr(route, key):
                    if key == 'highlights':
                        setattr(route, key, json.dumps(value))
                    else:
                        setattr(route, key, value)
            self.db.commit()
            self.db.refresh(route)
            return {'success': True, 'data': route.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def delete_route(self, route_id: int) -> Dict:
        route = self.db.query(TravelRoute).filter(TravelRoute.id == route_id).first()
        if not route:
            return {'success': False, 'error': '线路不存在'}

        try:
            self.db.delete(route)
            self.db.commit()
            return {'success': True}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def create_group(self, group_data: Dict) -> Dict:
        try:
            group = TravelGroup(
                platform=group_data.get('platform', 'wechat'),
                group_id=group_data['group_id'],
                group_name=group_data.get('group_name', ''),
                boss_wxid=group_data.get('boss_wxid', ''),
                is_active=group_data.get('is_active', 1),
            )
            self.db.add(group)
            self.db.commit()
            self.db.refresh(group)
            return {'success': True, 'data': group.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def list_groups(self) -> List[Dict]:
        return [g.to_dict() for g in self.db.query(TravelGroup).filter(TravelGroup.is_active == 1).all()]

    def create_registration(self, registration_data: Dict) -> Dict:
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
            self.db.add(registration)
            self.db.commit()
            self.db.refresh(registration)
            return {'success': True, 'data': registration.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def list_registrations(self, route_id: Optional[int] = None, status: Optional[str] = None) -> List[Dict]:
        query = self.db.query(TravelRegistration)
        if route_id:
            query = query.filter(TravelRegistration.route_id == route_id)
        if status:
            query = query.filter(TravelRegistration.status == status)
        return [r.to_dict() for r in query.order_by(TravelRegistration.created_at.desc()).all()]

    def update_registration(self, registration_id: int, data: Dict) -> Dict:
        registration = self.db.query(TravelRegistration).filter(TravelRegistration.id == registration_id).first()
        if not registration:
            return {'success': False, 'error': '报名不存在'}

        try:
            for key, value in data.items():
                if hasattr(registration, key):
                    setattr(registration, key, value)
            self.db.commit()
            self.db.refresh(registration)
            return {'success': True, 'data': registration.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def create_feedback(self, feedback_data: Dict) -> Dict:
        try:
            feedback = TravelFeedback(
                group_id=feedback_data['group_id'],
                user_id=feedback_data.get('user_id', ''),
                user_name=feedback_data.get('user_name', ''),
                content=feedback_data['content'],
                route_id=feedback_data.get('route_id'),
                intent=feedback_data.get('intent', 'other'),
                status='pending',
            )
            self.db.add(feedback)
            self.db.commit()
            self.db.refresh(feedback)
            return {'success': True, 'data': feedback.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def list_feedbacks(self, group_id: Optional[int] = None, status: Optional[str] = None) -> List[Dict]:
        query = self.db.query(TravelFeedback)
        if group_id:
            query = query.filter(TravelFeedback.group_id == group_id)
        if status:
            query = query.filter(TravelFeedback.status == status)
        return [f.to_dict() for f in query.order_by(TravelFeedback.created_at.desc()).all()]

    def reply_feedback(self, feedback_id: int, response: str) -> Dict:
        feedback = self.db.query(TravelFeedback).filter(TravelFeedback.id == feedback_id).first()
        if not feedback:
            return {'success': False, 'error': '反馈不存在'}

        try:
            feedback.response = response
            feedback.status = 'responded'
            self.db.commit()
            return {'success': True, 'data': feedback.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def create_reply_rule(self, rule_data: Dict) -> Dict:
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
            self.db.add(rule)
            self.db.commit()
            self.db.refresh(rule)
            return {'success': True, 'data': rule.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def list_reply_rules(self, route_id: Optional[int] = None) -> List[Dict]:
        query = self.db.query(TravelReplyRule).filter(TravelReplyRule.is_active == 1)
        if route_id:
            query = query.filter((TravelReplyRule.route_id == route_id) | (TravelReplyRule.route_id.is_(None)))
        return [r.to_dict() for r in query.order_by(TravelReplyRule.priority.desc()).all()]

    def parse_message(self, message_text: str) -> Dict:
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

        price_match = re.search(r'(\d+(?:\.\d+)?)\s*[元块]', message_text)
        if price_match:
            result['price'] = float(price_match.group(1))

        date_match = re.search(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})[日号]?', message_text)
        if date_match:
            try:
                result['start_date'] = f"{date_match.group(1)}-{date_match.group(2).zfill(2)}-{date_match.group(3).zfill(2)}"
            except:
                pass

        days_match = re.search(r'(\d+)\s*天', message_text)
        if days_match:
            result['duration'] = int(days_match.group(1))

        people_match = re.search(r'(\d+)\s*[人位]', message_text)
        if people_match:
            result['group_size'] = int(people_match.group(1))

        result['route_name'] = message_text[:100]
        result['route_details'] = message_text

        return result

    def generate_report(self, report_type: str, date_range: Optional[str] = None) -> Dict:
        if not date_range:
            date_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            date_str = date_range

        feedbacks = self.db.query(TravelFeedback).filter(
            TravelFeedback.created_at >= date_str
        ).all()

        registrations = self.db.query(TravelRegistration).filter(
            TravelRegistration.created_at >= date_str
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

    def get_stats(self, period: str = 'today') -> Dict:
        today = datetime.now().date()
        start_date = today

        if period == 'week':
            start_date = today - timedelta(days=7)
        elif period == 'month':
            start_date = today - timedelta(days=30)

        registrations = self.db.query(TravelRegistration).filter(
            TravelRegistration.created_at >= start_date
        ).all()

        feedbacks = self.db.query(TravelFeedback).filter(
            TravelFeedback.created_at >= start_date
        ).all()

        return {
            'period': period,
            'registration_count': len(registrations),
            'feedback_count': len(feedbacks),
            'pending_feedback': len([f for f in feedbacks if f.status == 'pending']),
        }