# routes/admin_routes.py
from flask import Blueprint

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/api/admin', methods=['GET'])
def admin_dashboard():
    return {"message": "Admin endpoint"}