from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from db import get_db_connection

cart_bp = Blueprint('cart', __name__)

# ========== إضافة منتج للسلة ==========
@cart_bp.route('/add', methods=['POST'])
@jwt_required()
def add_to_cart():
    user_id = get_jwt_identity()
    data = request.get_json()
    flower_id = data.get('flower_id')
    quantity = data.get('quantity', 1)

    if not flower_id:
        return jsonify({'error': 'Flower ID is required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    # تحقق من وجود الزهرة
    cursor.execute("SELECT FlowerID FROM Flower WHERE FlowerID = ?", (flower_id,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({'error': 'Product not found'}), 404

    # جيب أو أنشئ سلة نشطة للمستخدم
    cursor.execute("""
        SELECT CartID FROM Cart 
        WHERE UserID = ? AND IsActive = 1
    """, (user_id,))
    cart = cursor.fetchone()

    if cart:
        cart_id = cart[0]
    else:
        cursor.execute("""
            INSERT INTO Cart (UserID, IsActive, CreatedAt)
            OUTPUT INSERTED.CartID
            VALUES (?, 1, GETDATE())
        """, (user_id,))
        cart_id = cursor.fetchone()[0]

    # تحقق إذا المنتج موجود في CartItems
    cursor.execute("""
        SELECT CartItemID, Quantity FROM CartItems 
        WHERE CartID = ? AND FlowerID = ?
    """, (cart_id, flower_id))
    existing = cursor.fetchone()

    if existing:
        cursor.execute("""
            UPDATE CartItems SET Quantity = Quantity + ?
            WHERE CartItemID = ?
        """, (quantity, existing[0]))
    else:
        cursor.execute("""
            INSERT INTO CartItems (CartID, FlowerID, Quantity)
            VALUES (?, ?, ?)
        """, (cart_id, flower_id, quantity))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'message': 'Product added to cart successfully'}), 200


# ========== جلب السلة ==========
@cart_bp.route('/', methods=['GET'])
@jwt_required()
def get_cart():
    user_id = get_jwt_identity()
    conn = get_db_connection()
    cursor = conn.cursor()

    # جيب السلة النشطة
    cursor.execute("""
        SELECT c.CartID FROM Cart c
        WHERE c.UserID = ? AND c.IsActive = 1
    """, (user_id,))
    cart = cursor.fetchone()

    if not cart:
        cursor.close()
        conn.close()
        return jsonify({"items": [], "total": 0.0, "item_count": 0}), 200

    cart_id = cart[0]

    cursor.execute("""
        SELECT ci.CartItemID, ci.FlowerID, ci.Quantity,
               f.FlowerName, f.Price, f.ImageURL
        FROM CartItems ci
        JOIN Flower f ON ci.FlowerID = f.FlowerID
        WHERE ci.CartID = ?
    """, (cart_id,))

    rows = cursor.fetchall()
    items = []
    total = 0.0

    for row in rows:
        price = float(row[4]) if row[4] else 0.0
        qty = int(row[2])
        subtotal = price * qty
        total += subtotal
        items.append({
            "cart_item_id": row[0],
            "flower_id": row[1],
            "quantity": qty,
            "name": row[3],
            "price": price,
            "image_url": row[5],
            "subtotal": subtotal
        })

    cursor.close()
    conn.close()

    return jsonify({
        "cart_id": cart_id,
        "items": items,
        "total": round(total, 2),
        "item_count": len(items)
    }), 200


# ========== تحديث الكمية ==========
@cart_bp.route('/update/<int:cart_item_id>', methods=['PUT'])
@jwt_required()
def update_cart_item(cart_item_id):
    user_id = get_jwt_identity()
    data = request.get_json()
    quantity = data.get('quantity', 1)

    if quantity < 1:
        return jsonify({'error': 'Quantity must be at least 1'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    # تأكد إن العنصر يخص المستخدم
    cursor.execute("""
        SELECT ci.CartItemID FROM CartItems ci
        JOIN Cart c ON ci.CartID = c.CartID
        WHERE ci.CartItemID = ? AND c.UserID = ? AND c.IsActive = 1
    """, (cart_item_id, user_id))

    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({'error': 'Item not found'}), 404

    cursor.execute("UPDATE CartItems SET Quantity = ? WHERE CartItemID = ?", (quantity, cart_item_id))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'message': 'Cart updated successfully'}), 200


# ========== حذف منتج ==========
@cart_bp.route('/remove/<int:cart_item_id>', methods=['DELETE'])
@jwt_required()
def remove_from_cart(cart_item_id):
    user_id = get_jwt_identity()
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE ci FROM CartItems ci
        JOIN Cart c ON ci.CartID = c.CartID
        WHERE ci.CartItemID = ? AND c.UserID = ? AND c.IsActive = 1
    """, (cart_item_id, user_id))

    affected = cursor.rowcount
    conn.commit()
    cursor.close()
    conn.close()

    if affected == 0:
        return jsonify({'error': 'Item not found'}), 404

    return jsonify({'message': 'Item removed'}), 200


# ========== تفريغ السلة ==========
@cart_bp.route('/clear', methods=['DELETE'])
@jwt_required()
def clear_cart():
    user_id = get_jwt_identity()
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE ci FROM CartItems ci
        JOIN Cart c ON ci.CartID = c.CartID
        WHERE c.UserID = ? AND c.IsActive = 1
    """, (user_id,))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'message': 'Cart cleared'}), 200