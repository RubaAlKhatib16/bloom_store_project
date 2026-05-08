from flask import Blueprint, jsonify, request
from db import get_db_connection

flower_bp = Blueprint('flowers', __name__)


# ==================== دالة مساعدة لعرض حالة المخزون ====================
def get_stock_status(stock):
    """ترجع حالة المخزون النصية للعرض للعميل"""
    if stock is None:
        return {"status": "unknown", "text": "Check availability", "available": False}
    if stock <= 0:
        return {"status": "sold_out", "text": " Sold Out", "available": False}
    if stock <= 5:
        return {"status": "low_stock", "text": f" Only {stock} left!", "available": True}
    if stock <= 10:
        return {"status": "medium_stock", "text": f" {stock} in stock", "available": True}
    return {"status": "in_stock", "text": " In Stock", "available": True}


@flower_bp.route('/', methods=['GET'])
def get_flowers():
    limit = request.args.get('limit', None, type=int)
    occasion = request.args.get('occasion', None)

    conn = get_db_connection()
    cursor = conn.cursor()

    if limit:
        query = """
            SELECT TOP (?) FlowerID, FlowerName, Type, Price, Stock, Description, ImageURL, Category
            FROM Flower
            WHERE 1=1
        """
        params = [limit]
    else:
        query = """
            SELECT FlowerID, FlowerName, Type, Price, Stock, Description, ImageURL, Category
            FROM Flower
            WHERE 1=1
        """
        params = []

    if occasion:
        query += " AND Occasion = ? AND IsBouquet = 1"
        params.append(occasion)

    cursor.execute(query, params)
    rows = cursor.fetchall()

    flowers = []
    for row in rows:
        stock = row.Stock if hasattr(row, 'Stock') else row[4]  # التعامل مع stock
        stock_info = get_stock_status(stock)
        
        flowers.append({
            "id": row.FlowerID,
            "name": row.FlowerName,
            "price": float(row.Price),
            "stock": stock,  #  الكمية الفعلية
            "stock_status": stock_info["status"],  #  حالة المخزون النصية
            "stock_text": stock_info["text"],  #  النص المعروض للعميل
            "available": stock_info["available"],  #  هل المنتج متاح للشراء؟
            "description": row.Description or "",
            "image_url": row.ImageURL or "",
            "type": row.Type if row.Type else "Other",
            "category": row.Category if row.Category else "All"
        })

    cursor.close()
    conn.close()

    return jsonify(flowers)


# جلب الفئات
@flower_bp.route('/categories', methods=['GET'])
def get_categories():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT Category, COUNT(*) as count, MIN(ImageURL) as image_url
        FROM Flower
        WHERE Category IS NOT NULL AND Category != 'All'
        GROUP BY Category
    """)

    rows = cursor.fetchall()

    categories = []

    for row in rows:
        cat_name = row.Category

        categories.append({
            "name": cat_name,
            "slug": cat_name.lower().replace(' ', '-'),
            "count": row.count,
            "image_url": row.image_url or "",
            "description": f"Explore our {cat_name} collection."
        })

    cursor.close()
    conn.close()

    return jsonify(categories)


@flower_bp.route('/category/<category>', methods=['GET'])
def get_flowers_by_category(category):
    conn = get_db_connection()
    cursor = conn.cursor()

    formatted_category = category.replace('-', ' ')

    cursor.execute("""
        SELECT FlowerID, FlowerName, Price, Stock, Description, ImageURL, Type
        FROM Flower
        WHERE LOWER(REPLACE(Category, '-', ' ')) = LOWER(?)
    """, (formatted_category,))

    rows = cursor.fetchall()

    flowers = []

    for row in rows:
        stock = row.Stock if hasattr(row, 'Stock') else row[3]
        stock_info = get_stock_status(stock)
        
        flowers.append({
            "id": row.FlowerID,
            "name": row.FlowerName,
            "price": float(row.Price),
            "stock": stock,  #  الكمية الفعلية
            "stock_status": stock_info["status"],
            "stock_text": stock_info["text"],
            "available": stock_info["available"],
            "description": row.Description or "",
            "image_url": row.ImageURL or "",
            "type": row.Type if row.Type else "Other"
        })

    cursor.close()
    conn.close()

    return jsonify(flowers)


@flower_bp.route('/featured', methods=['GET'])
def get_featured_flowers():
    limit = request.args.get('limit', default=3, type=int)

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(f"""
            SELECT TOP ({limit}) FlowerID, FlowerName, Price, Stock, Description, ImageURL, Category
            FROM Flower
            WHERE IsBestSeller = 1
        """)
    except:
        cursor.execute(f"""
            SELECT TOP ({limit}) FlowerID, FlowerName, Price, Stock, Description, ImageURL, Category
            FROM Flower
            ORDER BY Price ASC
        """)

    rows = cursor.fetchall()

    flowers = []

    for row in rows:
        stock = row.Stock if hasattr(row, 'Stock') else row[3]
        stock_info = get_stock_status(stock)
        
        flowers.append({
            "id": row.FlowerID,
            "name": row.FlowerName,
            "price": float(row.Price),
            "stock": stock,  #  الكمية الفعلية
            "stock_status": stock_info["status"],
            "stock_text": stock_info["text"],
            "available": stock_info["available"],
            "description": row.Description or "",
            "image_url": row.ImageURL or "",
            "category": row.Category if row.Category else "All"
        })

    cursor.close()
    conn.close()

    return jsonify(flowers)


@flower_bp.route('/<int:flower_id>', methods=['GET'])
def get_flower_details(flower_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            FlowerID,
            FlowerName,
            Description,
            Price,
            Stock,
            ImageURL,
            Color,
            Type,
            Category
        FROM Flower
        WHERE FlowerID = ?
    """, (flower_id,))

    flower = cursor.fetchone()

    cursor.close()
    conn.close()

    if not flower:
        return jsonify({'error': 'Flower not found'}), 404

    stock = flower[4]  # Stock في المركز الخامس
    stock_info = get_stock_status(stock)

    return jsonify({
        "id": flower[0],
        "name": flower[1],
        "description": flower[2],
        "price": float(flower[3]),
        "stock": stock,  #  الكمية الفعلية
        "stock_status": stock_info["status"],
        "stock_text": stock_info["text"],
        "available": stock_info["available"],
        "image_url": flower[5],
        "color": flower[6],
        "type": flower[7],
        "category": flower[8]
    }), 200


@flower_bp.route('/bouquets', methods=['GET'])
def get_bouquets():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            FlowerID,
            FlowerName,
            Type,
            Price,
            Stock,
            Description,
            ImageURL,
            Category
        FROM Flower
        WHERE IsBouquet = 1 AND IsActive = 1
    """)

    rows = cursor.fetchall()

    bouquets = []

    for row in rows:
        stock = row.Stock if hasattr(row, 'Stock') else row[4]
        stock_info = get_stock_status(stock)
        
        bouquets.append({
            "id": row.FlowerID,
            "name": row.FlowerName,
            "price": float(row.Price),
            "stock": stock,  #  الكمية الفعلية
            "stock_status": stock_info["status"],
            "stock_text": stock_info["text"],
            "available": stock_info["available"],
            "description": row.Description or "",
            "image_url": row.ImageURL or "",
            "type": row.Type if row.Type else "Bouquet",
            "category": row.Category or "Bouquet"
        })

    cursor.close()
    conn.close()

    return jsonify(bouquets)


# ====================  API التحقق من المخزون قبل الدفع ====================
@flower_bp.route('/check-stock', methods=['POST'])
def check_stock():
    """التحقق من توفر المنتجات قبل إتمام الطلب"""
    data = request.get_json()
    items = data.get('items', [])  # [{id: 1, quantity: 2}, ...]
    
    if not items:
        return jsonify({'error': 'No items provided'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    stock_status = []
    all_available = True
    
    for item in items:
        flower_id = item.get('id')
        quantity = item.get('quantity', 1)
        
        cursor.execute("SELECT FlowerName, Stock FROM Flower WHERE FlowerID = ?", (flower_id,))
        row = cursor.fetchone()
        
        if not row:
            stock_status.append({
                'id': flower_id,
                'available': False,
                'message': 'Product not found'
            })
            all_available = False
        else:
            stock = row.Stock if hasattr(row, 'Stock') else row[1]
            available = stock >= quantity
            
            stock_status.append({
                'id': flower_id,
                'name': row.FlowerName,
                'requested': quantity,
                'available_stock': stock,
                'available': available,
                'message': 'In stock' if available else f'Only {stock} left in stock'
            })
            if not available:
                all_available = False
    
    cursor.close()
    conn.close()
    
    return jsonify({
        'all_available': all_available,
        'items': stock_status
    })