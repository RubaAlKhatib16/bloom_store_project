from flask import Blueprint, request, jsonify, send_file, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from db import get_db_connection
import os
import uuid
from datetime import datetime
user_bp = Blueprint('user', __name__, url_prefix='/api/user')

UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@user_bp.route('/avatar', methods=['POST'])
@jwt_required()
def upload_avatar():
    user_id = get_jwt_identity()
    if 'avatar' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['avatar']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed. Use PNG, JPG, JPEG, GIF'}), 400

    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"avatar_{user_id}.{ext}"
    filepath = os.path.join(current_app.root_path, UPLOAD_FOLDER, filename)

   
    if os.path.exists(filepath):
        os.remove(filepath)

    file.save(filepath)
    relative_path = os.path.join(UPLOAD_FOLDER, filename).replace('\\', '/')

    conn = get_db_connection()
    cursor = conn.cursor()
  
    cursor.execute("UPDATE Users SET avatar = ? WHERE UserID = ?", (relative_path, user_id))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({
    "message": "Avatar uploaded successfully",
    "path": relative_path
}), 200

@user_bp.route('/avatar', methods=['GET'])
@jwt_required()
def get_avatar():
    user_id = get_jwt_identity()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT avatar FROM Users WHERE UserID = ?", (user_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if row and row[0]:
        full_path = os.path.join(current_app.root_path, row[0])
        if os.path.exists(full_path):
            return send_file(full_path, mimetype='image/jpeg')
    return '', 404

# ==================== إحصائيات المستخدم ====================
@user_bp.route('/stats', methods=['GET'])
@jwt_required()
def user_stats():
    user_id = get_jwt_identity()
    conn = get_db_connection()
    cursor = conn.cursor()
    
   
    cursor.execute("SELECT COUNT(*) FROM Orders WHERE UserID = ?", (user_id,))
    total_orders = cursor.fetchone()[0]
    
    
    cursor.execute("SELECT Points FROM Users WHERE UserID = ?", (user_id,))
    row = cursor.fetchone()
    points = row[0] if row and row[0] is not None else 0   
    
    # مستوى العضوية
    if points >= 500:
        member_tier = "Gold"
    elif points >= 200:
        member_tier = "Silver"
    else:
        member_tier = "Bronze"
    
    cursor.close()
    conn.close()
    
    return jsonify({
        'total_orders': total_orders,
        'new_this_month': 0,
        'active_subscriptions': 0,
        'loyalty_points': points,
        'member_tier': member_tier,
        'next_delivery': None
    })

# ==================== آخر الطلبات ====================
@user_bp.route('/recent_orders', methods=['GET'])
@jwt_required()
def recent_orders():
    user_id = get_jwt_identity()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    
    cursor.execute("""
        SELECT 
            o.OrderID,
            o.OrderDate,
            o.TotalAmount,
            o.Status,
            (SELECT TOP 1 f.ImageURL 
             FROM OrderItems oi 
             JOIN Flower f ON oi.FlowerID = f.FlowerID 
             WHERE oi.OrderID = o.OrderID) AS ImageURL,
            (SELECT TOP 1 f.FlowerName 
             FROM OrderItems oi 
             JOIN Flower f ON oi.FlowerID = f.FlowerID 
             WHERE oi.OrderID = o.OrderID) AS ProductName
        FROM Orders o
        WHERE o.UserID = ?
        ORDER BY o.OrderDate DESC
        OFFSET 0 ROWS FETCH NEXT 5 ROWS ONLY
    """, (user_id,))
    
    rows = cursor.fetchall()
    orders = []
    for row in rows:
        orders.append({
            'id': row.OrderID,
            'name': row.ProductName if row.ProductName else f"Order #{row.OrderID}",
            'date': row.OrderDate.strftime('%Y-%m-%d') if row.OrderDate else '',
            'total': float(row.TotalAmount) if row.TotalAmount else 0,
            'status': row.Status,
            'image': row.ImageURL if row.ImageURL else ''   
        })
    
    cursor.close()
    conn.close()
    return jsonify(orders)


# ==================== العناوين  ====================
@user_bp.route('/addresses', methods=['GET'])
@jwt_required()
def get_addresses():
    
    return jsonify([])


# ==================== وسائل الدفع  ====================
@user_bp.route('/payment', methods=['GET'])
@jwt_required()
def get_payment():
   
    return jsonify({'last4': '4458', 'expiry': '12/26', 'type': 'Demo'})


@user_bp.route('/reminders', methods=['GET'])
@jwt_required()
def get_reminders():
    user_id = get_jwt_identity()

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ReminderID, Title, OccasionType,
               ReminderDate, NotifyBeforeDays
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
            'notify_before_days': row.NotifyBeforeDays
        })

    cursor.close()
    conn.close()

    return jsonify(reminders), 200

from datetime import datetime, timedelta

@user_bp.route('/reminders', methods=['POST'])
@jwt_required()
def add_reminder():
    user_id = get_jwt_identity()
    data = request.json

    title = data.get('title')
    occasion_type = data.get('occasion_type')
    reminder_date_str = data.get('reminder_date')
    notify_before_days = int(data.get('notify_before_days', 3))

    if not all([title, occasion_type, reminder_date_str]):
        return jsonify({'error': 'Missing required fields'}), 400

    reminder_date = datetime.fromisoformat(reminder_date_str)
    notify_before = int(notify_before_days)
    notification_date = reminder_date - timedelta(days=notify_before)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO UserReminders
        (UserID, Title, OccasionType, ReminderDate, NotifyBeforeDays, NotificationDate)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, title, occasion_type, reminder_date, notify_before, notification_date))
    conn.commit()
    reminder_id = cursor.lastrowid

    # ✅ إذا كان الإشعار يجب أن يُرسل فوراً (NotificationDate <= الآن)
    if notification_date <= datetime.now():
        from app import send_immediate_notification  # سننشئ هذه الدالة
        send_immediate_notification(reminder_id, user_id, title, occasion_type, reminder_date)

    cursor.close()
    conn.close()

    return jsonify({'message': 'Reminder added successfully', 'id': reminder_id}), 201

@user_bp.route('/reminders/<int:reminder_id>', methods=['DELETE'])
@jwt_required()
def delete_reminder(reminder_id):
    user_id = get_jwt_identity()

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM UserReminders
        WHERE ReminderID = ?
        AND UserID = ?
    """, (reminder_id, user_id))

    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({
        'message': 'Reminder deleted successfully'
    }), 200

@user_bp.route('/notifications', methods=['GET'])
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


@user_bp.route('/notifications/mark-read', methods=['POST'])
@jwt_required()
def mark_notifications_read():
    user_id = get_jwt_identity()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Notifications SET IsRead = 1 WHERE UserID = ?", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'message': 'All notifications marked as read'})


@user_bp.route('/update', methods=['PUT'])
@jwt_required()
def update_user():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    new_username = data.get('username')
    new_email = data.get('email')
    
    if not new_username or not new_email:
        return jsonify({'error': 'Username and email are required'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        
        cursor.execute("SELECT UserID FROM Users WHERE Email = ? AND UserID != ?", (new_email, user_id))
        if cursor.fetchone():
            return jsonify({'error': 'Email already in use'}), 409
        
        cursor.execute("UPDATE Users SET UserName = ?, Email = ? WHERE UserID = ?", 
                       (new_username, new_email, user_id))
        conn.commit()
        return jsonify({'message': 'Profile updated successfully'}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

        
@user_bp.route('/points-history', methods=['GET'])
@jwt_required()
def get_points_history():
    user_id = get_jwt_identity()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT Points, Reason, OrderID, CreatedAt
        FROM PointsLog
        WHERE UserID = ?
        ORDER BY CreatedAt DESC
    """, (user_id,))
    
    rows = cursor.fetchall()
    history = []
    for row in rows:
        history.append({
            'points': row.Points,
            'reason': row.Reason,
            'order_id': row.OrderID,
            'created_at': row.CreatedAt.isoformat() if row.CreatedAt else ''
        })
    
    cursor.close()
    conn.close()
    return jsonify(history)


@user_bp.route('/orders/<int:order_id>', methods=['GET'])
@jwt_required()
def get_order_details(order_id):
    user_id = get_jwt_identity()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # جلب بيانات الطلب
    cursor.execute("""
        SELECT OrderID, OrderDate, Status, TotalAmount, DiscountApplied, ShippingAddress
        FROM Orders
        WHERE OrderID = ? AND UserID = ?
    """, (order_id, user_id))
    
    order_row = cursor.fetchone()
    if not order_row:
        cursor.close()
        conn.close()
        return jsonify({'error': 'Order not found'}), 404
    
    # جلب عناصر الطلب
    cursor.execute("""
        SELECT oi.Quantity, oi.Price, f.FlowerName, f.ImageURL
        FROM OrderItems oi
        JOIN Flower f ON oi.FlowerID = f.FlowerID
        WHERE oi.OrderID = ?
    """, (order_id,))
    
    items_rows = cursor.fetchall()
    items = []
    for row in items_rows:
        items.append({
            'name': row.FlowerName,
            'quantity': row.Quantity,
            'price': float(row.Price),
            'image': row.ImageURL
        })
    
    cursor.close()
    conn.close()
    
    return jsonify({
        'id': order_row.OrderID,
        'date': order_row.OrderDate.isoformat(),
        'status': order_row.Status,
        'total': float(order_row.TotalAmount),
        'discount': float(order_row.DiscountApplied or 0),
        'address': order_row.ShippingAddress,
        'items': items,
        'loyalty_points_earned': 10
    })