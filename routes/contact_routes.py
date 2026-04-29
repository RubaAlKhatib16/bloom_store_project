from flask import Blueprint, request, jsonify
from db import get_db_connection

contact_bp = Blueprint('contact', __name__, url_prefix='/api')

@contact_bp.route('/contact', methods=['POST'])
def submit_contact():
    data = request.get_json()
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    subject = data.get('subject', '').strip()
    message = data.get('message', '').strip()
    
    if not all([name, email, subject, message]):
        return jsonify({'error': 'All fields are required'}), 400
    
    if '@' not in email:
        return jsonify({'error': 'Invalid email address'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Messages (Name, Email, Subject, Message)
        VALUES (?, ?, ?, ?)
    """, (name, email, subject, message))
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({'message': 'Message sent successfully. We will contact you soon.'}), 201