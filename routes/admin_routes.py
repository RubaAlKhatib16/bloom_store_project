from flask import Blueprint, render_template, request, jsonify, session
from functools import wraps
from db import get_db_connection
import bcrypt
from datetime import datetime
import json
from flask_jwt_extended import jwt_required, get_jwt, verify_jwt_in_request

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            verify_jwt_in_request()
            claims = get_jwt()
            if claims.get('role') not in ('admin', 'Admin'):
                return jsonify({'error': 'Admin access required'}), 403
        except Exception:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/dashboard')
@admin_required
def admin_dashboard():
    return render_template('admin_dashboard.html')

# ==================== API: إدارة المنتجات ====================
@admin_bp.route('/products', methods=['GET'])
@admin_required
def admin_get_products():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT FlowerID, FlowerName, Type, Price, Stock, Category, Occasion, IsBouquet, ImageURL, IsActive
        FROM Flower
        ORDER BY FlowerID DESC
    """)
    rows = cursor.fetchall()
    products = []
    for row in rows:
        products.append({
            'id': row.FlowerID,
            'name': row.FlowerName,
            'type': row.Type,
            'price': float(row.Price),
            'stock': row.Stock,
            'category': row.Category,
            'occasion': row.Occasion,
            'is_bouquet': row.IsBouquet,
            'image_url': row.ImageURL,
            'is_active': row.IsActive
        })
    cursor.close()
    conn.close()
    return jsonify(products)

# إضافة منتج (مع رفع صورة)
from werkzeug.utils import secure_filename
import os
from flask import current_app

@admin_bp.route('/products', methods=['POST'])
@admin_required
def admin_add_product():
    data = request.form
    image = request.files.get('image')
    image_url = ''
    if image:
        filename = secure_filename(image.filename)
        import time
        filename = f"{int(time.time())}_{filename}"
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        image.save(os.path.join(upload_folder, filename))
        image_url = f'/static/uploads/{filename}'
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Flower (FlowerName, Type, Price, Stock, Category, Occasion, IsBouquet, ImageURL, IsActive, Description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data['name'], data.get('type', ''), float(data['price']), int(data.get('stock', 0)),
        data.get('category', ''), data.get('occasion', ''), int(data.get('is_bouquet', 0)),
        image_url, 1, data.get('description', '')
    ))
    conn.commit()
    flower_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return jsonify({'message': 'Product added', 'id': flower_id}), 201

# تعديل منتج
@admin_bp.route('/products/<int:product_id>', methods=['PUT'])
@admin_required
def admin_update_product(product_id):
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE Flower SET FlowerName=?, Type=?, Price=?, Stock=?, Category=?, Occasion=?, IsBouquet=?, IsActive=?
        WHERE FlowerID=?
    """, (
        data['name'], data.get('type', ''), data['price'], data.get('stock', 0),
        data.get('category', ''), data.get('occasion', ''), data.get('is_bouquet', 0),
        data.get('is_active', 1), product_id
    ))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'message': 'Updated'})

# حذف منتج
@admin_bp.route('/products/<int:product_id>', methods=['DELETE'])
@admin_required
def admin_delete_product(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Flower WHERE FlowerID=?", (product_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'message': 'Deleted'})

# ==================== API: إدارة الطلبات ====================
@admin_bp.route('/orders', methods=['GET'])
@admin_required
def admin_get_orders():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT o.OrderID, o.OrderDate, o.Status, o.TotalAmount, o.DiscountApplied, u.Username, u.Email, COUNT(oi.OrderItemID) as ItemCount
        FROM Orders o
        JOIN Users u ON o.UserID = u.UserID
        LEFT JOIN OrderItems oi ON o.OrderID = oi.OrderID
        GROUP BY o.OrderID, o.OrderDate, o.Status, o.TotalAmount, o.DiscountApplied, u.Username, u.Email
        ORDER BY o.OrderDate DESC
    """)
    rows = cursor.fetchall()
    orders = []
    for row in rows:
        orders.append({
            'id': row.OrderID,
            'date': row.OrderDate.isoformat() if row.OrderDate else '',
            'status': row.Status,
            'total': float(row.TotalAmount or 0),
            'discount': float(row.DiscountApplied or 0),
            'username': row.Username,
            'email': row.Email,
            'items': row.ItemCount
        })
    cursor.close()
    conn.close()
    return jsonify(orders)

@admin_bp.route('/orders/<int:order_id>/status', methods=['PUT'])
@admin_required
def admin_update_order_status(order_id):
    new_status = request.json.get('status')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Orders SET Status=? WHERE OrderID=?", (new_status, order_id))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'message': 'Status updated'})

# ==================== API: أكثر المنتجات مبيعاً ====================
@admin_bp.route('/best-sellers', methods=['GET'])
@admin_required
def admin_best_sellers():
    limit = request.args.get('limit', 5, type=int)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT TOP ({limit}) f.FlowerID, f.FlowerName, SUM(oi.Quantity) as TotalSold, SUM(oi.Price * oi.Quantity) as Revenue
        FROM OrderItems oi
        JOIN Flower f ON oi.FlowerID = f.FlowerID
        GROUP BY f.FlowerID, f.FlowerName
        ORDER BY TotalSold DESC
    """)
    rows = cursor.fetchall()
    sellers = []
    for row in rows:
        sellers.append({
            'id': row.FlowerID,
            'name': row.FlowerName,
            'total_sold': row.TotalSold,
            'revenue': float(row.Revenue)
        })
    cursor.close()
    conn.close()
    return jsonify(sellers)

# ==================== API: المستخدمين والنقاط ====================
@admin_bp.route('/users', methods=['GET'])
@admin_required
def admin_get_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT UserID, Username, Email, Points, Role FROM Users ORDER BY UserID DESC")
    rows = cursor.fetchall()
    users = []
    for row in rows:
        users.append({
            'id': row.UserID,
            'username': row.Username,
            'email': row.Email,
            'points': row.Points,
            'role': row.Role,
            
        })
    cursor.close()
    conn.close()
    return jsonify(users)

@admin_bp.route('/users/<int:user_id>/points', methods=['PUT'])
@admin_required
def admin_update_user_points(user_id):
    points = request.json.get('points', 0)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Users SET Points = ? WHERE UserID = ?", (points, user_id))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'message': 'Points updated'})

# ==================== API: إدارة كوبونات الخصم ====================
@admin_bp.route('/coupons', methods=['GET'])
@admin_required
def admin_get_coupons():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Coupons ORDER BY CouponID DESC")
    rows = cursor.fetchall()
    coupons = []
    for row in rows:
        coupons.append({
            'id': row.CouponID,
            'code': row.Code,
            'discount_percent': row.DiscountPercent,
            'valid_from': row.ValidFrom.isoformat(),
            'valid_to': row.ValidTo.isoformat(),
            'is_active': row.IsActive,
            'usage_limit': row.UsageLimit,
            'used_count': row.UsedCount
        })
    cursor.close()
    conn.close()
    return jsonify(coupons)

@admin_bp.route('/coupons', methods=['POST'])
@admin_required
def admin_add_coupon():
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Coupons (Code, DiscountPercent, ValidFrom, ValidTo, IsActive, UsageLimit)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        data['code'], data['discount_percent'],
        datetime.fromisoformat(data['valid_from']), datetime.fromisoformat(data['valid_to']),
        data.get('is_active', 1), data.get('usage_limit')
    ))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'message': 'Coupon added'}), 201

@admin_bp.route('/coupons/<int:coupon_id>', methods=['DELETE'])
@admin_required
def admin_delete_coupon(coupon_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Coupons WHERE CouponID=?", (coupon_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'message': 'Coupon deleted'})

# ==================== CONSULTATIONS ====================
@admin_bp.route('/consultations', methods=['GET'])
@admin_required
def get_consultations():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ConsultationID, FullName, Email, Phone,
               OccasionType, PreferredDate,
               Message, Status, CreatedAt
        FROM Consultations
        ORDER BY CreatedAt DESC
    """)
    rows = cursor.fetchall()
    consultations = []
    for row in rows:
        consultations.append({
            "id": row.ConsultationID,
            "name": row.FullName,
            "email": row.Email,
            "phone": row.Phone,
            "occasion": row.OccasionType,
            "preferred_date": str(row.PreferredDate) if row.PreferredDate else "",
            "message": row.Message,
            "status": row.Status,
            "created_at": str(row.CreatedAt) if row.CreatedAt else ""
        })
    cursor.close()
    conn.close()
    return jsonify(consultations)

@admin_bp.route('/api/consultations/<int:consultation_id>', methods=['DELETE'])
@admin_required
def delete_consultation(consultation_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM consultations WHERE id = ?", (consultation_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'message': 'Consultation deleted'})
# ==================== API: إحصائيات سريعة (cards) ====================
@admin_bp.route('/stats', methods=['GET'])
@admin_required
def admin_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    # عدد المستخدمين
    cursor.execute("SELECT COUNT(*) FROM Users")
    user_count = cursor.fetchone()[0]
    # عدد الطلبات
    cursor.execute("SELECT COUNT(*) FROM Orders")
    order_count = cursor.fetchone()[0]
    # عدد المنتجات
    cursor.execute("SELECT COUNT(*) FROM Flower")
    product_count = cursor.fetchone()[0]
    # إجمالي المبيعات (حسب الطلبات المدفوعة)
    cursor.execute("SELECT ISNULL(SUM(TotalAmount), 0) FROM Orders WHERE Status IN ('paid','shipped','delivered')")
    total_revenue = float(cursor.fetchone()[0])
    cursor.close()
    conn.close()
    return jsonify({
        'users': user_count,
        'orders': order_count,
        'products': product_count,
        'revenue': total_revenue
    })