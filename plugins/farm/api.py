from flask import Blueprint, request, jsonify
from plugins.farm.service import FarmService
from database.db_config import get_db

farm_bp = Blueprint("farm", __name__, url_prefix="/api/farm")

def get_service():
    db = next(get_db())
    return FarmService(db)

@farm_bp.route("/livestock/entry", methods=["POST"])
def livestock_entry():
    data = request.get_json()
    service = get_service()
    result = service.add_livestock_entry(**data)
    return jsonify({"success": True, "data": result})

@farm_bp.route("/livestock/birth", methods=["POST"])
def livestock_birth():
    data = request.get_json()
    service = get_service()
    result = service.add_livestock_birth(**data)
    return jsonify({"success": True, "data": result})

@farm_bp.route("/livestock/death", methods=["POST"])
def livestock_death():
    data = request.get_json()
    service = get_service()
    result = service.add_livestock_death(**data)
    return jsonify({"success": True, "data": result})

@farm_bp.route("/livestock/sale", methods=["POST"])
def livestock_sale():
    data = request.get_json()
    service = get_service()
    result = service.add_livestock_sale(**data)
    return jsonify({"success": True, "data": result})

@farm_bp.route("/livestock/stats", methods=["GET"])
def livestock_stats():
    period = request.args.get("period")
    service = get_service()
    result = service.get_livestock_stats(period)
    return jsonify({"success": True, "data": result})

@farm_bp.route("/feed/purchase", methods=["POST"])
def feed_purchase():
    data = request.get_json()
    service = get_service()
    result = service.add_feed_purchase(**data)
    return jsonify({"success": True, "data": result})

@farm_bp.route("/feed/usage", methods=["POST"])
def feed_usage():
    data = request.get_json()
    service = get_service()
    result = service.add_feed_usage(**data)
    return jsonify({"success": True, "data": result})

@farm_bp.route("/feed/stats", methods=["GET"])
def feed_stats():
    period = request.args.get("period")
    service = get_service()
    result = service.get_feed_stats(period)
    return jsonify({"success": True, "data": result})

@farm_bp.route("/expense/add", methods=["POST"])
def add_expense():
    data = request.get_json()
    service = get_service()
    result = service.add_expense(**data)
    return jsonify({"success": True, "data": result})

@farm_bp.route("/expense/stats", methods=["GET"])
def expense_stats():
    period = request.args.get("period")
    service = get_service()
    result = service.get_expense_stats(period)
    return jsonify({"success": True, "data": result})

@farm_bp.route("/order/create", methods=["POST"])
def create_order():
    data = request.get_json()
    service = get_service()
    result = service.create_order(**data)
    return jsonify({"success": True, "data": result})

@farm_bp.route("/order/stats", methods=["GET"])
def order_stats():
    period = request.args.get("period")
    service = get_service()
    result = service.get_order_stats(period)
    return jsonify({"success": True, "data": result})

@farm_bp.route("/customer/add", methods=["POST"])
def add_customer():
    data = request.get_json()
    service = get_service()
    result = service.add_customer(**data)
    return jsonify({"success": True, "data": result})

@farm_bp.route("/customer/appointment", methods=["POST"])
def customer_appointment():
    data = request.get_json()
    service = get_service()
    result = service.add_customer_appointment(**data)
    return jsonify({"success": True, "data": result})

@farm_bp.route("/employee/add", methods=["POST"])
def add_employee():
    data = request.get_json()
    service = get_service()
    result = service.add_employee(**data)
    return jsonify({"success": True, "data": result})

@farm_bp.route("/employee/attendance", methods=["POST"])
def add_attendance():
    data = request.get_json()
    service = get_service()
    result = service.add_attendance(**data)
    return jsonify({"success": True, "data": result})

@farm_bp.route("/employee/salary", methods=["POST"])
def add_salary():
    data = request.get_json()
    service = get_service()
    result = service.add_salary(**data)
    return jsonify({"success": True, "data": result})

@farm_bp.route("/vaccine/add", methods=["POST"])
def add_vaccine():
    data = request.get_json()
    service = get_service()
    result = service.add_vaccine(**data)
    return jsonify({"success": True, "data": result})

@farm_bp.route("/vaccine/immunization", methods=["POST"])
def add_immunization():
    data = request.get_json()
    service = get_service()
    result = service.add_immunization(**data)
    return jsonify({"success": True, "data": result})

@farm_bp.route("/disease/add", methods=["POST"])
def add_disease():
    data = request.get_json()
    service = get_service()
    result = service.add_disease_record(**data)
    return jsonify({"success": True, "data": result})

@farm_bp.route("/pricing/add", methods=["POST"])
def add_pricing():
    data = request.get_json()
    service = get_service()
    result = service.add_pricing_rule(**data)
    return jsonify({"success": True, "data": result})

@farm_bp.route("/summary", methods=["GET"])
def farm_summary():
    period = request.args.get("period")
    service = get_service()
    result = service.get_farm_summary(period)
    return jsonify({"success": True, "data": result})

@farm_bp.route("/parse", methods=["POST"])
def parse_message():
    data = request.get_json()
    service = get_service()
    result = service.parse_message(data.get("message", ""))
    return jsonify({"success": True, "data": result})

@farm_bp.route("/process", methods=["POST"])
def process_message():
    data = request.get_json()
    service = get_service()
    result = service.process_message(data)
    return jsonify(result)

@farm_bp.route("/report", methods=["POST"])
def generate_report():
    data = request.get_json()
    service = get_service()
    result = service.generate_report(data.get("report_type"), data.get("date_range", {}))
    return jsonify({"success": True, "data": result})