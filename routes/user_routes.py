from flask import Blueprint, request, jsonify, send_file, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from db import get_db_connection
import os
import uuid

user_bp = Blueprint('user', __name__)

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

    # حذف الصورة القديمة إن وجدت
    if os.path.exists(filepath):
        os.remove(filepath)

    file.save(filepath)
    relative_path = os.path.join(UPLOAD_FOLDER, filename).replace('\\', '/')

    conn = get_db_connection()
    cursor = conn.cursor()
    # استخدام اسم العمود "avatar" وليس "avatar_path"
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
    # استخدام اسم العمود "avatar"
    cursor.execute("SELECT avatar FROM Users WHERE UserID = ?", (user_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if row and row[0]:
        full_path = os.path.join(current_app.root_path, row[0])
        if os.path.exists(full_path):
            return send_file(full_path, mimetype='image/jpeg')
    return '', 404


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
        # التحقق من عدم وجود بريد إلكتروني مكرر
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