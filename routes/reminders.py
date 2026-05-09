from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from db import get_db_connection
from datetime import datetime, timedelta

reminders_bp = Blueprint('reminders', __name__, url_prefix='/api/user')

@reminders_bp.route('/reminders', methods=['GET'])
@jwt_required()
def get_reminders():
    user_id = get_jwt_identity()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ReminderID, Title, OccasionType, ReminderDate, NotifyBeforeDays, NotificationDate
        FROM UserReminders
        WHERE UserID = ?
        ORDER BY ReminderDate ASC
    """, (user_id,))
    rows = cursor.fetchall()
    reminders = []
    for row in rows:
        reminders.append({
            'id': row.ReminderID,
            'title': row.Title,
            'occasion_type': row.OccasionType,
            'reminder_date': row.ReminderDate.isoformat(),
            'notify_before_days': row.NotifyBeforeDays,
            'notification_date': row.NotificationDate.isoformat() if row.NotificationDate else None
        })
    cursor.close()
    conn.close()
    return jsonify(reminders)

@reminders_bp.route('/reminders', methods=['POST'])
@jwt_required()
def save_reminder():
    user_id = get_jwt_identity()
    data = request.json
    title = data.get('title')
    occasion_type = data.get('occasion_type')
    reminder_date_str = data.get('reminder_date')
    notify_before_days = data.get('notify_before_days', 3)

    if not all([title, occasion_type, reminder_date_str]):
        return jsonify({'error': 'Missing required fields'}), 400

    reminder_date = datetime.fromisoformat(reminder_date_str)
    notify_before = int(notify_before_days)
    notification_date = reminder_date - timedelta(days=notify_before)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO UserReminders (UserID, Title, OccasionType, ReminderDate, NotifyBeforeDays, NotificationDate)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, title, occasion_type, reminder_date, notify_before, notification_date))
    conn.commit()
    reminder_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return jsonify({'message': 'Reminder saved', 'id': reminder_id}), 201

@reminders_bp.route('/reminders/<int:reminder_id>', methods=['DELETE'])
@jwt_required()
def delete_reminder(reminder_id):
    user_id = get_jwt_identity()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM UserReminders WHERE ReminderID = ? AND UserID = ?", (reminder_id, user_id))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'message': 'Reminder deleted'})