from flask import Blueprint, request, jsonify
from db import get_db_connection
import datetime

consultation_bp = Blueprint('consultation', __name__)

@consultation_bp.route('/api/consultations', methods=['POST'])
def create_consultation():
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    full_name = data.get('fullName', '').strip()
    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip()
    occasion_type = data.get('occasionType', '').strip()
    preferred_date = data.get('preferredDate', '').strip()
    message = data.get('message', '').strip()

    if not full_name or not email:
        return jsonify({'error': 'Name and email are required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO Consultations (FullName, Email, Phone, OccasionType, PreferredDate, Message, Status)
            VALUES (?, ?, ?, ?, ?, ?, 'Pending')
        """, (full_name, email, phone, occasion_type, preferred_date if preferred_date else None, message))

        conn.commit()

        # Here you can add email notification code later
        return jsonify({'message': 'Consultation request sent successfully. We will contact you soon.'}), 201

    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@consultation_bp.route('/api/consultations', methods=['GET'])
def get_consultations():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT ConsultationID, FullName, Email, Phone, OccasionType, PreferredDate, Message, Status, CreatedAt FROM Consultations ORDER BY CreatedAt DESC")
    rows = cursor.fetchall()
    consultations = []
    for row in rows:
        consultations.append({
            "id": row[0],
            "fullName": row[1],
            "email": row[2],
            "phone": row[3],
            "occasionType": row[4],
            "preferredDate": row[5],
            "message": row[6],
            "status": row[7],
            "createdAt": row[8]
        })
    cursor.close()
    conn.close()
    return jsonify(consultations)