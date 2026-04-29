# routes/reminders.py
from flask import Blueprint

reminders_bp = Blueprint('reminders', __name__)

@reminders_bp.route('/api/reminders', methods=['GET'])
def get_reminders():
    return {"message": "Reminders endpoint"}