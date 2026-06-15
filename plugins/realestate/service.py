"""
房产中介行业插件服务层
"""
from datetime import datetime
from sqlalchemy.orm import Session
from plugins.realestate.models import (
    RealEstateProperty, RealEstateCustomer, RealEstateAgent,
    RealEstateMatch, RealEstateViewing, RealEstateTransaction, RealEstateContract
)


class RealEstateService:
    """房产中介服务"""

    def list_properties(self, db: Session, district: str = None, property_type: str = None) -> list:
        query = db.query(RealEstateProperty).filter(RealEstateProperty.is_active == True)
        if district:
            query = query.filter(RealEstateProperty.district == district)
        if property_type:
            query = query.filter(RealEstateProperty.property_type == property_type)
        return [p.to_dict() for p in query.all()]

    def create_property(self, db: Session, data: dict) -> dict:
        property = RealEstateProperty(
            property_name=data['property_name'],
            property_type=data.get('property_type', ''),
            area=data.get('area', 0.0),
            price=data.get('price', 0.0),
            location=data.get('location', ''),
            district=data.get('district', ''),
            bedroom_count=data.get('bedroom_count'),
            bathroom_count=data.get('bathroom_count'),
            floor=data.get('floor', ''),
            total_floor=data.get('total_floor'),
            orientation=data.get('orientation', ''),
            decoration=data.get('decoration', ''),
            age=data.get('age'),
            description=data.get('description', ''),
            images=data.get('images', '')
        )
        db.add(property)
        db.commit()
        db.refresh(property)
        return {'success': True, 'property': property.to_dict()}

    def list_customers(self, db: Session) -> list:
        return [c.to_dict() for c in db.query(RealEstateCustomer).filter(RealEstateCustomer.is_active == True).all()]

    def create_customer(self, db: Session, data: dict) -> dict:
        customer = RealEstateCustomer(
            customer_name=data['customer_name'],
            phone=data['phone'],
            wechat_id=data.get('wechat_id', ''),
            demand=data.get('demand', ''),
            budget_min=data.get('budget_min', 0.0),
            budget_max=data.get('budget_max', 0.0),
            preferred_area=data.get('preferred_area', ''),
            preferred_type=data.get('preferred_type', '')
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
        return {'success': True, 'customer': customer.to_dict()}

    def list_agents(self, db: Session) -> list:
        return [a.to_dict() for a in db.query(RealEstateAgent).filter(RealEstateAgent.is_active == True).all()]

    def create_agent(self, db: Session, data: dict) -> dict:
        agent = RealEstateAgent(
            agent_name=data['agent_name'],
            phone=data['phone'],
            department=data.get('department', ''),
            team=data.get('team', '')
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)
        return {'success': True, 'agent': agent.to_dict()}

    def list_transactions(self, db: Session) -> list:
        return [t.to_dict() for t in db.query(RealEstateTransaction).all()]

    def smart_match(self, db: Session, customer_id: int) -> dict:
        customer = db.query(RealEstateCustomer).filter(RealEstateCustomer.id == customer_id).first()
        if not customer:
            return {'success': False, 'error': '客户不存在'}

        properties = db.query(RealEstateProperty).filter(RealEstateProperty.is_active == True).all()
        matches = []

        for prop in properties:
            score = 0

            if customer.preferred_type and prop.property_type == customer.preferred_type:
                score += 25

            if customer.preferred_area and prop.district in customer.preferred_area:
                score += 25

            if customer.budget_min and customer.budget_max:
                if customer.budget_min <= prop.price <= customer.budget_max:
                    score += 30
                elif abs(prop.price - customer.budget_max) < customer.budget_max * 0.2:
                    score += 15

            if customer.demand:
                demand_lower = customer.demand.lower()
                desc_lower = (prop.description or '').lower()
                if any(keyword in desc_lower for keyword in demand_lower.split()):
                    score += 20

            if score > 0:
                match = RealEstateMatch(
                    customer_id=customer_id,
                    property_id=prop.id,
                    match_score=score
                )
                db.add(match)
                matches.append({
                    'property': prop.to_dict(),
                    'match_score': score
                })

        db.commit()

        matches.sort(key=lambda x: -x['match_score'])
        return {'success': True, 'matches': matches[:10]}

    def record_viewing(self, db: Session, customer_id: int, property_id: int, agent_id: int = None, feedback: str = None) -> dict:
        viewing = RealEstateViewing(
            customer_id=customer_id,
            property_id=property_id,
            agent_id=agent_id,
            viewing_date=datetime.now(),
            feedback=feedback
        )
        db.add(viewing)
        db.commit()
        db.refresh(viewing)
        return {'success': True, 'viewing': viewing.to_dict()}

    def create_transaction(self, db: Session, customer_id: int, property_id: int, agent_id: int = None, amount: float = None) -> dict:
        existing = db.query(RealEstateTransaction).filter(
            RealEstateTransaction.customer_id == customer_id,
            RealEstateTransaction.property_id == property_id,
            RealEstateTransaction.status != 'completed'
        ).first()
        if existing:
            return {'success': False, 'error': '该客户已与该房源存在未完成交易'}

        transaction = RealEstateTransaction(
            customer_id=customer_id,
            property_id=property_id,
            agent_id=agent_id,
            amount=amount or 0.0,
            status='pending'
        )
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
        return {'success': True, 'transaction': transaction.to_dict()}

    def update_transaction_status(self, db: Session, transaction_id: int, status: str) -> dict:
        transaction = db.query(RealEstateTransaction).filter(RealEstateTransaction.id == transaction_id).first()
        if not transaction:
            return {'success': False, 'error': '交易不存在'}

        transaction.status = status
        if status == 'completed':
            transaction.completion_date = datetime.now()
        elif status == 'signed':
            transaction.contract_date = datetime.now()

        db.commit()
        db.refresh(transaction)
        return {'success': True, 'transaction': transaction.to_dict()}

    def create_contract(self, db: Session, transaction_id: int, contract_number: str, content: str = None) -> dict:
        transaction = db.query(RealEstateTransaction).filter(RealEstateTransaction.id == transaction_id).first()
        if not transaction:
            return {'success': False, 'error': '交易不存在'}

        contract = RealEstateContract(
            transaction_id=transaction_id,
            contract_number=contract_number,
            content=content,
            sign_date=datetime.now()
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)

        transaction.status = 'signed'
        transaction.contract_date = datetime.now()
        db.commit()

        return {'success': True, 'contract': contract.to_dict()}

    def generate_report(self, db: Session, report_type: str) -> dict:
        if report_type == 'transaction_summary':
            transactions = db.query(RealEstateTransaction).all()
            pending_count = sum(1 for t in transactions if t.status == 'pending')
            signed_count = sum(1 for t in transactions if t.status == 'signed')
            completed_count = sum(1 for t in transactions if t.status == 'completed')
            total_amount = sum(t.amount or 0 for t in transactions if t.status == 'completed')

            return {
                'success': True,
                'data': {
                    'total_transactions': len(transactions),
                    'pending_count': pending_count,
                    'signed_count': signed_count,
                    'completed_count': completed_count,
                    'total_amount': round(total_amount, 2)
                }
            }

        return {'success': False, 'error': '未知报表类型'}