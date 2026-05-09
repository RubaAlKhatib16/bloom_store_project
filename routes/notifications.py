from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from db import get_db_connection
from datetime import datetime

notifications_bp = Blueprint('notifications', __name__, url_prefix='/api/user')

@notifications_bp.route('/notifications', methods=['GET'])
@jwt_required()
def get_notifications():
    user_id = get_jwt_identity()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT NotificationID, Title, Message, CreatedAt, IsRead
        FROM Notifications
        WHERE UserID = ?
        ORDER BY CreatedAt DESC
    """, (user_id,))
    rows = cursor.fetchall()
    notifications = []
    unread_count = 0
    for row in rows:
        notifications.append({
            'id': row.NotificationID,
            'title': row.Title,
            'message': row.Message,
            'created_at': row.CreatedAt.isoformat(),
            'is_read': row.IsRead
        })
        if not row.IsRead:
            unread_count += 1
    cursor.close()
    conn.close()
    return jsonify({'notifications': notifications, 'unread_count': unread_count})

@notifications_bp.route('/notifications/mark-read', methods=['POST'])
@jwt_required()
def mark_as_read():
    user_id = get_jwt_identity()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Notifications SET IsRead = 1 WHERE UserID = ?", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'message': 'All notifications marked as read'})