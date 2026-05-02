from flask import Blueprint, jsonify
from db import get_db_connection

occasion_bp = Blueprint('occasion', __name__)

@occasion_bp.route('/api/occasions', methods=['GET'])
def get_occasions():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            OccasionID,
            OccasionName,
            NameAr,
            Slug,
            Description,
            DescriptionAr,
            ImageURL,
            BadgeText,
            IsFeatured
        FROM Occasion
        WHERE OccasionName IS NOT NULL
    """)
    rows = cursor.fetchall()
    occasions = []
    for row in rows:
        
        name = row[1] if row[1] else "Unnamed"
        name_ar = row[2] if row[2] else name
        slug = row[3] if row[3] else name.lower().replace(' ', '-')
        description = row[4] if row[4] else f"Beautiful {name} arrangements for your special moments."
        description_ar = row[5] if row[5] else f"تنسيقات رائعة لمناسبات {name}"
        image_url = row[6] if row[6] else f"https://placehold.co/800x600?text={name}"
        badge_text = row[7] if row[7] else ""
        is_featured = bool(row[8]) if row[8] else False
        
        occasions.append({
            "id": row[0],
            "name": name,
            "name_ar": name_ar,
            "slug": slug,
            "description": description,
            "description_ar": description_ar,
            "image_url": image_url,
            "badge": badge_text,
            "is_featured": is_featured
        })
    
    cursor.close()
    conn.close()
    
   
    if not occasions:
        occasions = [
            {"id": 1, "name": "Wedding", "name_ar": "حفل زفاف", "slug": "wedding", 
             "description": "Ethereal white and cream arrangements for your fairytale day.", 
             "description_ar": "تنسيقات بيضاء وكريمية ليومك الخيالي.", 
             "image_url": "/static/images/imageoccasion/w.jpeg", "badge": "Popular", "is_featured": True},
            {"id": 2, "name": "Birthday", "name_ar": "عيد ميلاد", "slug": "birthday", 
             "description": "Vibrant blooms to make their day unforgettable.", 
             "description_ar": "أزهار نابضة بالحياة لجعل يومهم لا يُنسى.", 
             "image_url": "/static/images/imageoccasion/h.jpeg", "badge": "", "is_featured": False},
            {"id": 3, "name": "Graduation", "name_ar": "تخرج", "slug": "graduation", 
             "description": "Celebrate achievements and new beginnings.", 
             "description_ar": "احتفل بالإنجازات والبدايات الجديدة.", 
             "image_url": "/static/images/imageoccasion/g.jpeg", "badge": "", "is_featured": False},
            {"id": 4, "name": "Love", "name_ar": "حب", "slug": "love", 
             "description": "Romantic gestures for your special someone.", 
             "description_ar": "لفتات رومانسية لشخصك المميز.", 
             "image_url": "/static/images/imageoccasion/E.jpeg", "badge": "", "is_featured": False},
        ]
    
    return jsonify(occasions)