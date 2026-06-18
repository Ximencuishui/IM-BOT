"""
歌曲分离工作室 - 业务逻辑服务
包含服务配置、订单管理、工作流、知识库、问候、统计等核心业务逻辑
"""
import json
import re
import logging
import random
import threading
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Callable

from sqlalchemy.orm import Session
from plugins.base.base_service import BaseService
from plugins.studio.models import (
    StudioServiceConfig, StudioOrder, StudioWorkflowConfig,
    StudioWorkflowExecution, StudioKnowledgeBase,
    StudioGreetingConfig, StudioStatistics
)

logger = logging.getLogger(__name__)

# 服务类型关键词映射 - 用于意图识别
SERVICE_KEYWORDS = {
    'song_split': ['分离', '人声', '伴奏', '去人声', '去伴奏', '提取人声', '提取伴奏', '消音', '消原唱'],
    'instrument_split': ['乐器', '吉他声', '钢琴声', '鼓声', '贝斯', '提取乐器', '分轨', '单独乐器'],
    'song_polish': ['润色', '修音', '美化', '调音', '混音', '母带', '效果', '录音', '修饰'],
    'dj_remix': ['DJ', '编曲', 'remix', '混音', '风格', '改编', '电音', '舞曲', '重新编曲'],
    'song_search': ['找歌', '代找', '找一首', '什么歌', '歌名', '有首歌', '哪里找', '找不到', '求歌'],
}

# 订单状态流转映射
ORDER_STATUS_FLOW = {
    'consulting': ['quoted', 'cancelled'],
    'quoted': ['paid', 'cancelled'],
    'paid': ['processing', 'cancelled'],
    'processing': ['completed', 'failed'],
    'completed': [],
    'cancelled': [],
    'failed': ['processing'],
}


class StudioService(BaseService):
    """歌曲分离工作室服务类"""

    # ==================== 服务配置管理 ====================

    def create_service_config(self, data: Dict) -> Dict:
        """创建服务类型配置"""
        try:
            config = StudioServiceConfig(
                service_name=data['service_name'],
                service_code=data['service_code'],
                description=data.get('description', ''),
                base_price=data.get('base_price', 0.00),
                price_unit=data.get('price_unit', '次'),
                is_active=data.get('is_active', 1),
                sort_order=data.get('sort_order', 0),
            )
            self.db.add(config)
            self.db.commit()
            self.db.refresh(config)
            return {'success': True, 'data': config.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def update_service_config(self, config_id: int, data: Dict) -> Dict:
        """更新服务配置"""
        config = self.db.query(StudioServiceConfig).filter(
            StudioServiceConfig.id == config_id
        ).first()
        if not config:
            return {'success': False, 'error': '服务配置不存在'}
        try:
            for key, value in data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            self.db.commit()
            self.db.refresh(config)
            return {'success': True, 'data': config.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def list_service_configs(self, is_active: Optional[int] = None) -> List[Dict]:
        """获取服务配置列表"""
        query = self.db.query(StudioServiceConfig)
        if is_active is not None:
            query = query.filter(StudioServiceConfig.is_active == is_active)
        return [c.to_dict() for c in query.order_by(StudioServiceConfig.sort_order).all()]

    def get_service_config(self, config_id: int) -> Optional[Dict]:
        """获取单个服务配置"""
        config = self.db.query(StudioServiceConfig).filter(
            StudioServiceConfig.id == config_id
        ).first()
        return config.to_dict() if config else None

    def get_service_by_code(self, service_code: str) -> Optional[Dict]:
        """通过编码获取服务配置"""
        config = self.db.query(StudioServiceConfig).filter(
            StudioServiceConfig.service_code == service_code,
            StudioServiceConfig.is_active == 1
        ).first()
        return config.to_dict() if config else None

    def delete_service_config(self, config_id: int) -> Dict:
        """软删除服务配置"""
        return self.update_service_config(config_id, {'is_active': 0})

    # ==================== 订单管理 ====================

    def _generate_order_no(self) -> str:
        """生成订单编号"""
        now = datetime.now()
        date_part = now.strftime('%Y%m%d%H%M%S')
        micro_part = str(now.microsecond)[:3]
        return f"STUDIO{date_part}{micro_part}"

    def create_order(self, data: Dict) -> Dict:
        """创建订单"""
        try:
            order = StudioOrder(
                order_no=self._generate_order_no(),
                service_code=data['service_code'],
                customer_wx_id=data.get('customer_wx_id', ''),
                customer_nickname=data.get('customer_nickname', ''),
                customer_phone=data.get('customer_phone', ''),
                source_type=data.get('source_type', 'group_chat'),
                source_group=data.get('source_group', ''),
                requirement=data.get('requirement', ''),
                song_name=data.get('song_name', ''),
                song_artist=data.get('song_artist', ''),
                song_link=data.get('song_link', ''),
                file_url=data.get('file_url', ''),
                file_name=data.get('file_name', ''),
                status=data.get('status', 'consulting'),
                total_amount=data.get('total_amount', 0.00),
                paid_amount=data.get('paid_amount', 0.00),
                remark=data.get('remark', ''),
            )
            self.db.add(order)
            self.db.commit()
            self.db.refresh(order)
            return {'success': True, 'data': order.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def get_order(self, order_id: int) -> Optional[Dict]:
        """获取订单详情"""
        order = self.db.query(StudioOrder).filter(StudioOrder.id == order_id).first()
        return order.to_dict() if order else None

    def get_order_by_no(self, order_no: str) -> Optional[Dict]:
        """通过编号获取订单"""
        order = self.db.query(StudioOrder).filter(StudioOrder.order_no == order_no).first()
        return order.to_dict() if order else None

    def list_orders(self, status: Optional[str] = None,
                    service_code: Optional[str] = None,
                    customer_wx_id: Optional[str] = None,
                    start_date: Optional[str] = None,
                    end_date: Optional[str] = None,
                    page: int = 1, page_size: int = 20) -> Dict:
        """查询订单列表（分页）"""
        query = self.db.query(StudioOrder)
        if status:
            query = query.filter(StudioOrder.status == status)
        if service_code:
            query = query.filter(StudioOrder.service_code == service_code)
        if customer_wx_id:
            query = query.filter(StudioOrder.customer_wx_id == customer_wx_id)
        if start_date:
            query = query.filter(StudioOrder.created_at >= start_date)
        if end_date:
            query = query.filter(StudioOrder.created_at <= end_date)

        total = query.count()
        orders = query.order_by(
            StudioOrder.created_at.desc()
        ).offset((page - 1) * page_size).limit(page_size).all()

        return {
            'success': True,
            'total': total,
            'page': page,
            'page_size': page_size,
            'orders': [o.to_dict() for o in orders],
        }

    def update_order_status(self, order_id: int, status: str,
                            **extra) -> Dict:
        """更新订单状态（含状态机校验）"""
        order = self.db.query(StudioOrder).filter(StudioOrder.id == order_id).first()
        if not order:
            return {'success': False, 'error': '订单不存在'}

        allowed_next = ORDER_STATUS_FLOW.get(order.status, [])
        if status not in allowed_next:
            return {
                'success': False,
                'error': f"状态 {order.status} 不允许直接转为 {status}，允许的下游状态: {allowed_next}"
            }

        try:
            order.status = status
            for key, value in extra.items():
                if hasattr(order, key):
                    setattr(order, key, value)
            if status == 'paid' and not extra.get('paid_amount'):
                order.paid_amount = order.total_amount
            self.db.commit()
            self.db.refresh(order)
            return {'success': True, 'data': order.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def update_order(self, order_id: int, data: Dict) -> Dict:
        """更新订单信息"""
        order = self.db.query(StudioOrder).filter(StudioOrder.id == order_id).first()
        if not order:
            return {'success': False, 'error': '订单不存在'}
        try:
            for key, value in data.items():
                if hasattr(order, key) and key not in ('id', 'order_no', 'created_at'):
                    setattr(order, key, value)
            self.db.commit()
            self.db.refresh(order)
            return {'success': True, 'data': order.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    # ==================== 工作流配置管理 ====================

    def create_workflow_config(self, data: Dict) -> Dict:
        """创建工作流配置"""
        try:
            wf = StudioWorkflowConfig(
                service_code=data['service_code'],
                workflow_name=data['workflow_name'],
                workflow_type=data.get('workflow_type', 'auto'),
                steps=data.get('steps'),
                script_path=data.get('script_path', ''),
                is_active=data.get('is_active', 1),
            )
            self.db.add(wf)
            self.db.commit()
            self.db.refresh(wf)
            return {'success': True, 'data': wf.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def update_workflow_config(self, wf_id: int, data: Dict) -> Dict:
        """更新工作流配置"""
        wf = self.db.query(StudioWorkflowConfig).filter(
            StudioWorkflowConfig.id == wf_id
        ).first()
        if not wf:
            return {'success': False, 'error': '工作流配置不存在'}
        try:
            for key, value in data.items():
                if hasattr(wf, key):
                    setattr(wf, key, value)
            self.db.commit()
            self.db.refresh(wf)
            return {'success': True, 'data': wf.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def list_workflow_configs(self, service_code: Optional[str] = None) -> List[Dict]:
        """查询工作流配置"""
        query = self.db.query(StudioWorkflowConfig).filter(
            StudioWorkflowConfig.is_active == 1
        )
        if service_code:
            query = query.filter(StudioWorkflowConfig.service_code == service_code)
        return [w.to_dict() for w in query.all()]

    def get_workflow_config(self, wf_id: int) -> Optional[Dict]:
        """获取单个工作流配置"""
        wf = self.db.query(StudioWorkflowConfig).filter(
            StudioWorkflowConfig.id == wf_id
        ).first()
        return wf.to_dict() if wf else None

    def delete_workflow_config(self, wf_id: int) -> Dict:
        """删除工作流配置"""
        wf = self.db.query(StudioWorkflowConfig).filter(
            StudioWorkflowConfig.id == wf_id
        ).first()
        if not wf:
            return {'success': False, 'error': '工作流配置不存在'}
        try:
            wf.is_active = 0
            self.db.commit()
            return {'success': True}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    # ==================== 工作流执行管理 ====================

    def start_workflow(self, order_id: int, file_path: str = None) -> Dict:
        """启动工作流（老板确认后调用），自动异步执行工作流脚本"""
        order = self.db.query(StudioOrder).filter(StudioOrder.id == order_id).first()
        if not order:
            return {'success': False, 'error': '订单不存在'}
        if order.status != 'paid':
            return {'success': False, 'error': f"订单状态为 {order.status}，无法启动工作流"}

        wf = self.db.query(StudioWorkflowConfig).filter(
            StudioWorkflowConfig.service_code == order.service_code,
            StudioWorkflowConfig.is_active == 1
        ).first()
        if not wf:
            return {'success': False, 'error': f"未找到 {order.service_code} 的工作流配置"}

        try:
            execution = StudioWorkflowExecution(
                order_id=order.id,
                workflow_id=wf.id,
                execution_status='running',
                progress=0,
                log=f"[{datetime.now().isoformat()}] 工作流启动\n",
                started_at=datetime.now(),
            )
            self.db.add(execution)
            order.status = 'processing'
            order.workflow_id = str(wf.id)
            self.db.commit()
            self.db.refresh(execution)

            # 在后台线程中异步执行工作流脚本
            self._run_workflow_async(
                execution_id=execution.id,
                service_code=order.service_code,
                song_name=order.song_name,
                song_artist=order.song_artist,
                file_path=file_path or order.file_url,
                script_path=wf.script_path,
            )

            return {'success': True, 'data': execution.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def _run_workflow_async(self, execution_id: int, service_code: str,
                             song_name: str = '', song_artist: str = '',
                             file_path: str = '', script_path: str = ''):
        """异步执行工作流脚本（在后台线程中运行）"""
        def _run():
            try:
                db = type(self.db)() if hasattr(type(self.db), '__call__') else None
                svc = StudioService(db) if db else self

                if service_code == 'song_search':
                    from plugins.studio.workflows import song_search
                    result = song_search.run(
                        song_name=song_name or '',
                        artist=song_artist or '',
                        progress_callback=lambda p, m: svc.update_workflow_progress(
                            execution_id, p, m
                        ),
                    )
                    if result.get('found'):
                        svc.update_workflow_progress(
                            execution_id, 100, '搜索完成，已找到歌曲',
                            'completed', result_url=''
                        )
                    else:
                        svc.update_workflow_progress(
                            execution_id, 100, result.get('message', '未找到歌曲'),
                            'failed'
                        )

                elif service_code == 'song_split' and file_path:
                    from plugins.studio.workflows import song_split
                    result = song_split.run(
                        input_file=file_path,
                        progress_callback=lambda p, m: svc.update_workflow_progress(
                            execution_id, p, m
                        ),
                    )
                    svc.update_workflow_progress(
                        execution_id, 100, '分离完成',
                        'completed', result_url=result.get('output_dir', '')
                    )

                else:
                    svc.update_workflow_progress(
                        execution_id, 0,
                        f'服务类型 {service_code} 暂无可执行的工作流脚本',
                        'failed'
                    )

                if db:
                    db.close()
            except Exception as e:
                logger.error(f"工作流执行失败: {e}", exc_info=True)
                try:
                    self.update_workflow_progress(
                        execution_id, 0, f'工作流执行异常: {str(e)}', 'failed'
                    )
                except Exception:
                    pass

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

    def update_workflow_progress(self, execution_id: int, progress: int,
                                 log_msg: str = '', status: str = None,
                                 result_url: str = None) -> Dict:
        """更新工作流执行进度"""
        execution = self.db.query(StudioWorkflowExecution).filter(
            StudioWorkflowExecution.id == execution_id
        ).first()
        if not execution:
            return {'success': False, 'error': '执行记录不存在'}
        try:
            execution.progress = progress
            if log_msg:
                execution.log = (execution.log or '') + f"[{datetime.now().isoformat()}] {log_msg}\n"
            if status:
                execution.execution_status = status
                if status in ('completed', 'failed'):
                    execution.completed_at = datetime.now()
                    # 同步更新订单状态
                    order = self.db.query(StudioOrder).filter(
                        StudioOrder.id == execution.order_id
                    ).first()
                    if order:
                        order.status = 'completed' if status == 'completed' else 'failed'
                        if result_url:
                            order.result_file_url = result_url
            self.db.commit()
            self.db.refresh(execution)
            return {'success': True, 'data': execution.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def get_workflow_execution(self, execution_id: int) -> Optional[Dict]:
        """获取工作流执行记录"""
        execution = self.db.query(StudioWorkflowExecution).filter(
            StudioWorkflowExecution.id == execution_id
        ).first()
        return execution.to_dict() if execution else None

    def get_workflow_execution_by_order(self, order_id: int) -> Optional[Dict]:
        """通过订单获取工作流执行记录"""
        execution = self.db.query(StudioWorkflowExecution).filter(
            StudioWorkflowExecution.order_id == order_id
        ).order_by(StudioWorkflowExecution.created_at.desc()).first()
        return execution.to_dict() if execution else None

    # ==================== 知识库管理 ====================

    def search_knowledge(self, question: str) -> Optional[Dict]:
        """知识库匹配查询"""
        # 先尝试精确关键字匹配
        all_entries = self.db.query(StudioKnowledgeBase).filter(
            StudioKnowledgeBase.is_resolved == 1
        ).all()

        best_match = None
        best_score = 0

        for entry in all_entries:
            score = self._calc_knowledge_match_score(question, entry)
            if score > best_score:
                best_score = score
                best_match = entry

        if best_match and best_score >= 0.3:
            best_match.match_count = (best_match.match_count or 0) + 1
            self.db.commit()
            return best_match.to_dict()

        return None

    def _calc_knowledge_match_score(self, question: str, entry: StudioKnowledgeBase) -> float:
        """计算知识匹配分数"""
        score = 0.0
        q_lower = question.lower()

        # 关键词匹配
        keywords = entry.keywords or []
        if isinstance(keywords, str):
            try:
                keywords = json.loads(keywords)
            except Exception:
                keywords = []
        if isinstance(keywords, list):
            matched = sum(1 for kw in keywords if kw.lower() in q_lower)
            if keywords:
                score += (matched / len(keywords)) * 0.6

        # 问题文本包含匹配
        if entry.question and entry.question in question:
            score += 0.3
        elif entry.question:
            # 部分匹配
            q_words = set(entry.question.split())
            question_words = set(question.split())
            common = q_words & question_words
            if q_words:
                score += (len(common) / len(q_words)) * 0.3

        return min(score, 1.0)

    def add_knowledge(self, data: Dict) -> Dict:
        """新增知识条目"""
        try:
            keywords = data.get('keywords')
            if keywords and isinstance(keywords, list):
                keywords = json.dumps(keywords, ensure_ascii=False)
            entry = StudioKnowledgeBase(
                question=data['question'],
                answer=data.get('answer', ''),
                keywords=keywords,
                category=data.get('category', 'general'),
                source=data.get('source', 'auto'),
                is_resolved=data.get('is_resolved', 0),
            )
            self.db.add(entry)
            self.db.commit()
            self.db.refresh(entry)
            return {'success': True, 'data': entry.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def answer_knowledge(self, entry_id: int, answer: str) -> Dict:
        """老板回答知识库问题"""
        entry = self.db.query(StudioKnowledgeBase).filter(
            StudioKnowledgeBase.id == entry_id
        ).first()
        if not entry:
            return {'success': False, 'error': '知识条目不存在'}
        try:
            entry.answer = answer
            entry.is_resolved = 1
            entry.source = 'manual'
            self.db.commit()
            self.db.refresh(entry)
            return {'success': True, 'data': entry.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def list_knowledge(self, category: Optional[str] = None,
                       is_resolved: Optional[int] = None,
                       page: int = 1, page_size: int = 20) -> Dict:
        """查询知识库列表"""
        query = self.db.query(StudioKnowledgeBase)
        if category:
            query = query.filter(StudioKnowledgeBase.category == category)
        if is_resolved is not None:
            query = query.filter(StudioKnowledgeBase.is_resolved == is_resolved)
        total = query.count()
        entries = query.order_by(
            StudioKnowledgeBase.match_count.desc()
        ).offset((page - 1) * page_size).limit(page_size).all()
        return {
            'success': True,
            'total': total,
            'page': page,
            'page_size': page_size,
            'entries': [e.to_dict() for e in entries],
        }

    def list_unresolved_questions(self) -> List[Dict]:
        """列出未解答的问题"""
        entries = self.db.query(StudioKnowledgeBase).filter(
            StudioKnowledgeBase.is_resolved == 0
        ).order_by(StudioKnowledgeBase.created_at.desc()).all()
        return [e.to_dict() for e in entries]

    # ==================== 问候语管理 ====================

    def create_greeting(self, data: Dict) -> Dict:
        """创建问候语配置"""
        try:
            target_groups = data.get('target_groups')
            if target_groups and isinstance(target_groups, list):
                target_groups = json.dumps(target_groups, ensure_ascii=False)
            greeting = StudioGreetingConfig(
                greeting_text=data['greeting_text'],
                greeting_type=data.get('greeting_type', 'morning'),
                send_time=data.get('send_time'),
                target_groups=target_groups,
                is_active=data.get('is_active', 1),
                is_random=data.get('is_random', 0),
                sort_order=data.get('sort_order', 0),
            )
            self.db.add(greeting)
            self.db.commit()
            self.db.refresh(greeting)
            return {'success': True, 'data': greeting.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def update_greeting(self, greeting_id: int, data: Dict) -> Dict:
        """更新问候语配置"""
        greeting = self.db.query(StudioGreetingConfig).filter(
            StudioGreetingConfig.id == greeting_id
        ).first()
        if not greeting:
            return {'success': False, 'error': '问候语配置不存在'}
        try:
            if 'target_groups' in data and isinstance(data['target_groups'], list):
                data['target_groups'] = json.dumps(data['target_groups'], ensure_ascii=False)
            for key, value in data.items():
                if hasattr(greeting, key):
                    setattr(greeting, key, value)
            self.db.commit()
            self.db.refresh(greeting)
            return {'success': True, 'data': greeting.to_dict()}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def list_greetings(self, greeting_type: Optional[str] = None) -> List[Dict]:
        """查询问候语配置"""
        query = self.db.query(StudioGreetingConfig).filter(
            StudioGreetingConfig.is_active == 1
        )
        if greeting_type:
            query = query.filter(StudioGreetingConfig.greeting_type == greeting_type)
        return [g.to_dict() for g in query.order_by(StudioGreetingConfig.send_time).all()]

    def delete_greeting(self, greeting_id: int) -> Dict:
        """删除问候语配置"""
        greeting = self.db.query(StudioGreetingConfig).filter(
            StudioGreetingConfig.id == greeting_id
        ).first()
        if not greeting:
            return {'success': False, 'error': '问候语配置不存在'}
        try:
            greeting.is_active = 0
            self.db.commit()
            return {'success': True}
        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def get_greeting_for_time(self, current_time: str) -> List[str]:
        """获取指定时间要发送的问候语"""
        greetings = self.db.query(StudioGreetingConfig).filter(
            StudioGreetingConfig.is_active == 1,
            StudioGreetingConfig.send_time == current_time
        ).all()
        if not greetings:
            return []
        # 如果启用随机，随机取一条
        if any(g.is_random for g in greetings):
            random_greetings = [g for g in greetings if g.is_random]
            if random_greetings:
                return [random.choice(random_greetings).greeting_text]
        return [g.greeting_text for g in greetings]

    # ==================== 意图识别与消息解析 ====================

    def detect_service_type(self, message: str) -> Optional[str]:
        """检测消息中意图的服务类型"""
        for service_code, keywords in SERVICE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in message:
                    return service_code
        return None

    def parse_requirement(self, message: str) -> Dict:
        """解析客户需求消息"""
        result = {
            'success': True,
            'service_code': None,
            'song_name': '',
            'song_artist': '',
            'song_link': '',
            'has_link': False,
            'has_file': False,
            'confidence': 0.0,
        }

        # 检测服务类型
        service_code = self.detect_service_type(message)
        if service_code:
            result['service_code'] = service_code
            result['confidence'] = 0.8

        # 提取链接
        link_pattern = r'(https?://[^\s]+)'
        link_match = re.search(link_pattern, message)
        if link_match:
            result['song_link'] = link_match.group(1)
            result['has_link'] = True
            result['confidence'] = max(result['confidence'], 0.9)

        # 提取歌曲名 - 常见模式: 《歌名》、 「歌名」、 "歌名"、 歌名
        song_patterns = [
            r'[《（(]([^）》)]+)[》）)]',  # 《月亮代表我的心》
            r'「([^」]+)」',
            r'"([^"]+)"',
            r"'([^']+)'",
            r'(?:歌曲|歌名|一首歌?)?[叫作是]?[：《:]\s*([^\s，。,\.]{2,20})',
            r'(?:找|唱|放|听|搜)\s*(?:一首?|下)?\s*(?:歌)?\s*[叫作是]?\s*([^\s，。,\.]{2,20})',
        ]
        for pattern in song_patterns:
            m = re.search(pattern, message)
            if m:
                result['song_name'] = m.group(1).strip()
                break

        # 提取歌手名
        artist_patterns = [
            r'(?:歌手|唱|原唱|演唱)[：:]?\s*([^\s，。,\.]{2,10})',
            r'([^\s，。,\.]{2,10})\s*(?:唱|演唱|版本)',
        ]
        for pattern in artist_patterns:
            m = re.search(pattern, message)
            if m:
                result['song_artist'] = m.group(1).strip()
                break

        # 检测文件上传
        if '文件' in message or '发给你' in message or '上传' in message:
            result['has_file'] = True

        return result

    def generate_consultation_response(self, parse_result: Dict) -> str:
        """根据解析结果生成咨询回复"""
        service_code = parse_result.get('service_code')
        if not service_code:
            return ("您好！请问您需要什么服务呢？我可以帮您：\n"
                    "1️⃣ 歌曲分离（提取人声/伴奏）\n"
                    "2️⃣ 乐器声分离（提取特定乐器）\n"
                    "3️⃣ 歌曲润色（录音美化）\n"
                    "4️⃣ DJ编曲（重新编曲混音）\n"
                    "5️⃣ 歌曲代找（找不到的歌告诉我）\n\n"
                    "请告诉我您的需求~")

        service_names = {
            'song_split': '歌曲分离',
            'instrument_split': '乐器声分离',
            'song_polish': '歌曲润色',
            'dj_remix': 'DJ编曲',
            'song_search': '歌曲代找',
        }
        service_name = service_names.get(service_code, service_code)

        # 查价格
        config = self.get_service_by_code(service_code)
        price_info = f"费用为 {config['base_price']} 元/{config['price_unit']}" if config else ""

        song_info = ""
        if parse_result.get('song_name'):
            song_info = f"《{parse_result['song_name']}》"
        if parse_result.get('song_artist'):
            song_info += f" - {parse_result['song_artist']}"

        if song_info:
            return (f"好的，您需要的是【{service_name}】服务，歌曲：{song_info}。\n"
                    f"{price_info}。\n"
                    "为了方便沟通，我加您好友处理，可以吗？😊")
        else:
            return (f"好的，您需要的是【{service_name}】服务！\n"
                    f"{price_info}。\n"
                    "请问您有这首歌的链接吗？如果有请直接发给我，"
                    "如果没有也可以告诉我歌名，我帮您找~")

    def generate_boss_notification(self, order: Dict) -> str:
        """生成老板通知消息"""
        service_map = {
            'song_split': '歌曲分离',
            'instrument_split': '乐器声分离',
            'song_polish': '歌曲润色',
            'dj_remix': 'DJ编曲',
            'song_search': '歌曲代找',
        }
        service_name = service_map.get(order.get('service_code', ''), order.get('service_code', ''))
        return (
            f"🎵 老板有人下单了！\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📋 订单编号：{order.get('order_no', '')}\n"
            f"🎯 服务类型：{service_name}\n"
            f"👤 客户昵称：{order.get('customer_nickname', '未知')}\n"
            f"🎵 歌曲信息：{order.get('song_name', '无')} {order.get('song_artist', '')}\n"
            f"💰 订单金额：{order.get('total_amount', 0)} 元\n"
            f"📝 需求描述：{order.get('requirement', '无')}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"请尽快确认处理！"
        )

    # ==================== 统计报表 ====================

    def _compute_statistics(self, stat_date: date, stat_type: str,
                            service_code: Optional[str] = None) -> Dict:
        """计算统计数据"""
        query = self.db.query(StudioOrder)
        if stat_type == 'daily':
            query = query.filter(
                StudioOrder.created_at >= stat_date,
                StudioOrder.created_at < stat_date + timedelta(days=1)
            )
        elif stat_type == 'weekly':
            week_start = stat_date - timedelta(days=stat_date.weekday())
            week_end = week_start + timedelta(days=7)
            query = query.filter(
                StudioOrder.created_at >= week_start,
                StudioOrder.created_at < week_end
            )
        elif stat_type == 'monthly':
            month_start = stat_date.replace(day=1)
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1)
            query = query.filter(
                StudioOrder.created_at >= month_start,
                StudioOrder.created_at < month_end
            )

        if service_code:
            query = query.filter(StudioOrder.service_code == service_code)

        orders = query.all()
        total_count = len(orders)
        total_amount = sum(float(o.total_amount or 0) for o in orders)
        completed = len([o for o in orders if o.status == 'completed'])
        cancelled = len([o for o in orders if o.status == 'cancelled'])
        avg_price = round(total_amount / total_count, 2) if total_count > 0 else 0.00

        return {
            'stat_date': stat_date.isoformat(),
            'stat_type': stat_type,
            'service_code': service_code,
            'order_count': total_count,
            'total_amount': round(total_amount, 2),
            'completed_count': completed,
            'cancelled_count': cancelled,
            'avg_price': avg_price,
        }

    def refresh_statistics(self, stat_date: date = None, stat_type: str = 'daily') -> Dict:
        """刷新并保存统计数据"""
        if not stat_date:
            stat_date = date.today()

        try:
            # 计算总计
            total_stat = self._compute_statistics(stat_date, stat_type, None)
            self._upsert_statistics(total_stat)

            # 按服务类型分别统计
            configs = self.list_service_configs(is_active=1)
            for config in configs:
                service_stat = self._compute_statistics(
                    stat_date, stat_type, config['service_code']
                )
                self._upsert_statistics(service_stat)

            return {'success': True, 'message': f'{stat_type}统计刷新成功'}
        except Exception as e:
            logger.error(f"刷新统计数据失败: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def _upsert_statistics(self, stat_data: Dict):
        """插入或更新统计记录"""
        existing = self.db.query(StudioStatistics).filter(
            StudioStatistics.stat_date == stat_data['stat_date'],
            StudioStatistics.stat_type == stat_data['stat_type'],
            StudioStatistics.service_code == stat_data['service_code'],
        ).first()

        if existing:
            for key, value in stat_data.items():
                if key not in ('stat_date', 'stat_type', 'service_code', 'created_at'):
                    if hasattr(existing, key):
                        setattr(existing, key, value)
        else:
            record = StudioStatistics(**stat_data)
            self.db.add(record)
        self.db.commit()

    def get_statistics(self, stat_type: str = 'daily',
                       service_code: Optional[str] = None,
                       days: int = 30) -> Dict:
        """获取统计数据"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        records = self.db.query(StudioStatistics).filter(
            StudioStatistics.stat_date >= start_date,
            StudioStatistics.stat_date <= end_date,
            StudioStatistics.stat_type == stat_type,
        )
        if service_code:
            records = records.filter(StudioStatistics.service_code == service_code)
        else:
            records = records.filter(StudioStatistics.service_code.is_(None))

        records = records.order_by(StudioStatistics.stat_date).all()

        # 按服务类型汇总
        service_totals = {}
        configs = self.list_service_configs(is_active=1)
        for config in configs:
            sc = config['service_code']
            svc_records = self.db.query(StudioStatistics).filter(
                StudioStatistics.stat_date >= start_date,
                StudioStatistics.stat_date <= end_date,
                StudioStatistics.stat_type == stat_type,
                StudioStatistics.service_code == sc,
            ).all()
            service_totals[sc] = {
                'service_name': config['service_name'],
                'total_orders': sum(r.order_count or 0 for r in svc_records),
                'total_amount': round(sum(float(r.total_amount or 0) for r in svc_records), 2),
            }

        return {
            'success': True,
            'stat_type': stat_type,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'daily_records': [r.to_dict() for r in records],
            'service_totals': service_totals,
            'grand_total': {
                'total_orders': sum(r.order_count or 0 for r in records),
                'total_amount': round(sum(float(r.total_amount or 0) for r in records), 2),
            },
        }

    def get_dashboard_stats(self) -> Dict:
        """获取概览统计数据"""
        today = date.today()
        today_start = datetime(today.year, today.month, today.day)

        today_orders = self.db.query(StudioOrder).filter(
            StudioOrder.created_at >= today_start
        ).count()

        total_orders = self.db.query(StudioOrder).count()
        pending_orders = self.db.query(StudioOrder).filter(
            StudioOrder.status.in_(['consulting', 'quoted'])
        ).count()

        total_revenue = self.db.query(StudioOrder).filter(
            StudioOrder.status.in_(['paid', 'processing', 'completed'])
        ).with_entities(
            StudioOrder.paid_amount
        ).all()
        total_revenue = round(sum(float(r[0] or 0) for r in total_revenue), 2)

        unresolved = self.db.query(StudioKnowledgeBase).filter(
            StudioKnowledgeBase.is_resolved == 0
        ).count()

        return {
            'today_orders': today_orders,
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'total_revenue': total_revenue,
            'unresolved_questions': unresolved,
        }