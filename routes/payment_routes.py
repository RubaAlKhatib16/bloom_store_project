from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from db import get_db_connection

payment_bp = Blueprint('payment', __name__, url_prefix='/api/payment')

@payment_bp.route('/mock', methods=['POST'])
@jwt_required()
def mock_payment():
    user_id = get_jwt_identity()
    data = request.get_json()
    order_id = data.get('order_id')
    amount = data.get('amount')
    success = data.get('success', True)

    if not order_id:
        return jsonify({'success': False, 'message': 'Order ID missing'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT UserID, Status FROM Orders WHERE OrderID = ?", (order_id,))
    order = cursor.fetchone()
    if not order or order[0] != user_id:
        cursor.close(); conn.close()
        return jsonify({'success': False, 'message': 'Order not found'}), 404
    if order[1] != 'pending':
        return jsonify({'success': False, 'message': f'Order already {order[1]}'}), 400

    if not success:
        return jsonify({'success': False, 'message': 'Payment declined'}), 402

   
    cursor.execute("UPDATE Orders SET Status = 'paid' WHERE OrderID = ?", (order_id,))
    
    cursor.execute("UPDATE Users SET Points = ISNULL(Points, 0) + 10 WHERE UserID = ?", (user_id,))
    conn.commit()

    cursor.close()
    conn.close()
    return jsonify({'success': True, 'message': 'Payment successful', 'order_id': order_id})