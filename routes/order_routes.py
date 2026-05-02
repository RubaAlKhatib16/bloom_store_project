from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from db import get_db_connection

order_bp = Blueprint('order', __name__, url_prefix='/api/orders')

@order_bp.route('/', methods=['POST'])
@jwt_required()
def create_order():
    user_id = get_jwt_identity()
    data = request.get_json()

    full_name    = data.get('full_name')
    address      = data.get('address')
    city         = data.get('city')
    zip_code     = data.get('zip_code')
    phone        = data.get('phone')
    shipping_method = data.get('shipping_method', 'standard')
    payment_method  = data.get('payment_method', 'cod')

    if not all([full_name, address, city, zip_code, phone]):
        return jsonify({'error': 'All shipping fields are required'}), 400

    conn   = get_db_connection()
    cursor = conn.cursor()

    try:
        # ── 1. جلب عناصر السلة ──────────────────────────────────────
        cursor.execute("""
            SELECT
                CI.CartItemID,
                CI.FlowerID,
                CI.Quantity,
                F.Price,
                C.CartID
            FROM CartItems CI
            INNER JOIN Cart    C ON CI.CartID  = C.CartID
            INNER JOIN Flower  F ON CI.FlowerID = F.FlowerID
            WHERE C.UserID = ?
        """, (user_id,))

        cart_items = cursor.fetchall()

        if not cart_items:
            return jsonify({'error': 'Cart is empty'}), 400

        # ── 2. حساب المجاميع ────────────────────────────────────────
        subtotal      = sum(item[2] * float(item[3]) for item in cart_items)
        shipping_cost = 12.0 if shipping_method == 'standard' else 28.0
        tax           = subtotal * 0.10
        total         = subtotal + shipping_cost + tax

        shipping_address = f"{full_name}, {address}, {city}, {zip_code}, {phone}"

        # ── 3. إنشاء الطلب ─────────────────────────────────────────
       
        cursor.execute("""
            INSERT INTO Orders (
                UserID,
                ShippingAddress,
                TotalAmount,
                Status,
                PaymentMethod,
                ShippingMethod
            )
            VALUES (?, ?, ?, 'Pending', ?, ?)
        """, (
            user_id,
            shipping_address,
            total,
            payment_method,
            shipping_method
        ))

       
        cursor.execute("SELECT @@IDENTITY")
        order_id = int(cursor.fetchone()[0])

        # ── 4. إضافة عناصر الطلب ───────────────────────────────────
        for item in cart_items:
            flower_id = item[1]
            quantity  = item[2]
            price     = float(item[3])

            cursor.execute("""
                INSERT INTO OrderItems (
                    OrderID,
                    FlowerID,
                    Quantity,
                    Price
                )
                VALUES (?, ?, ?, ?)
            """, (order_id, flower_id, quantity, price))

        # ── 5. تفريغ السلة ─────────────────────────────────────────
        cursor.execute("""
            DELETE CI
            FROM CartItems CI
            INNER JOIN Cart C ON CI.CartID = C.CartID
            WHERE C.UserID = ?
        """, (user_id,))

        conn.commit()

        return jsonify({
            'message':  'Order created successfully',
            'order_id': order_id,
            'total':    round(total, 2)
        }), 201

    except Exception as e:
        conn.rollback()
        print(f"[ORDER ERROR] {e}")
        return jsonify({'error': 'Failed to create order', 'details': str(e)}), 500

    finally:
        cursor.close()
        conn.close()

@order_bp.route('/<int:order_id>', methods=['GET'])
@jwt_required()
def get_order_by_id(order_id):
    user_id = get_jwt_identity()
    conn = get_db_connection()
    cursor = conn.cursor()
    
        # تأكد إن الطلب يخص المستخدم
    cursor.execute("""
        SELECT o.OrderID, o.OrderDate, o.ShippingAddress, o.TotalAmount, o.Status, u.UserName, u.Email
        FROM Orders o
        JOIN Users u ON o.UserID = u.UserID
        WHERE o.OrderID = ? AND o.UserID = ?
    """, (order_id, user_id))
    
    row = cursor.fetchone()
    if not row:
        cursor.close()
        conn.close()
        return jsonify({'error': 'Order not found'}), 404
    
    order = {
        "id": row[0],
        "date": row[1],
        "shipping_address": row[2],
        "total": float(row[3]),
        "status": row[4],
        "customer_name": row[5],
        "customer_email": row[6]
    }
    
    # جلب عناصر الطلب
    cursor.execute("""
        SELECT oi.FlowerID, f.FlowerName, oi.Quantity, oi.Price, f.ImageURL
        FROM OrderItems oi
        JOIN Flower f ON oi.FlowerID = f.FlowerID
        WHERE oi.OrderID = ?
    """, (order_id,))
    
    items = []
    for item_row in cursor.fetchall():
        items.append({
            "id": item_row[0],
            "name": item_row[1],
            "quantity": item_row[2],
            "price": float(item_row[3]),
            "image_url": item_row[4]
        })
    
    order["items"] = items
    cursor.close()
    conn.close()
    
    return jsonify(order)