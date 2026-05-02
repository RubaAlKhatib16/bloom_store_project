from flask import Blueprint, jsonify, request
from db import get_db_connection

flower_bp = Blueprint('flowers', __name__)


@flower_bp.route('/', methods=['GET'])
def get_flowers():
    limit = request.args.get('limit', None, type=int)
    occasion = request.args.get('occasion', None)

    conn = get_db_connection()
    cursor = conn.cursor()

    if limit:
        query = """
            SELECT TOP (?) FlowerID, FlowerName, Type, Price, Description, ImageURL, Category
            FROM Flower
            WHERE 1=1
        """
        params = [limit]
    else:
        query = """
            SELECT FlowerID, FlowerName, Type, Price, Description, ImageURL, Category
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
        flowers.append({
            "id": row.FlowerID,
            "name": row.FlowerName,
            "price": float(row.Price),
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
        SELECT FlowerID, FlowerName, Price, Description, ImageURL, Type
        FROM Flower
        WHERE LOWER(REPLACE(Category, '-', ' ')) = LOWER(?)
    """, (formatted_category,))

    rows = cursor.fetchall()

    flowers = []

    for row in rows:
        flowers.append({
            "id": row.FlowerID,
            "name": row.FlowerName,
            "price": float(row.Price),
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
            SELECT TOP ({limit}) FlowerID, FlowerName, Price, Description, ImageURL, Category
            FROM Flower
            WHERE IsBestSeller = 1
        """)
    except:
        cursor.execute(f"""
            SELECT TOP ({limit}) FlowerID, FlowerName, Price, Description, ImageURL, Category
            FROM Flower
            ORDER BY Price ASC
        """)

    rows = cursor.fetchall()

    flowers = []

    for row in rows:
        flowers.append({
            "id": row.FlowerID,
            "name": row.FlowerName,
            "price": float(row.Price),
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

    return jsonify({
        "id": flower[0],
        "name": flower[1],
        "description": flower[2],
        "price": float(flower[3]),
        "image_url": flower[4],
        "color": flower[5],
        "type": flower[6],
        "category": flower[7]
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
            Description,
            ImageURL,
            Category
        FROM Flower
        WHERE IsBouquet = 1 AND IsActive = 1
    """)

    rows = cursor.fetchall()

    bouquets = []

    for row in rows:
        bouquets.append({
            "id": row.FlowerID,
            "name": row.FlowerName,
            "price": float(row.Price),
            "description": row.Description or "",
            "image_url": row.ImageURL or "",
            "type": row.Type if row.Type else "Bouquet",
            "category": row.Category or "Bouquet"
        })

    cursor.close()
    conn.close()

    return jsonify(bouquets)