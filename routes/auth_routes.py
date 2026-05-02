import datetime

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db_connection
import re
import logging
from routes.utils import EMAIL_PATTERN, validate_password, is_valid_email

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# REGISTER 
@auth_bp.route("/users", methods=["POST"])
def register_user():                            
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    required_fields = ["username", "password", "email", "address"]
    for field in required_fields:
        if field not in data or not str(data[field]).strip():
            return jsonify({"error": f"{field} is required"}), 400

    if not re.match(EMAIL_PATTERN, data["email"]):
        return jsonify({"error": "Invalid email format"}), 400

    # Validate password 
    valid, msg = validate_password(data["password"])
    if not valid:
        return jsonify({"error": msg}), 400

    hashed_password = generate_password_hash(data["password"])  # hash it

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        
        cursor.execute("SELECT UserID FROM Users WHERE Email = ?", (data["email"],))
        if cursor.fetchone():
            return jsonify({"error": "Email already registered"}), 409

        cursor.execute("""
            INSERT INTO Users (UserName, Password, Email, Address, Role)
            OUTPUT INSERTED.UserID
            VALUES (?, ?, ?, ?, 'User')
        """, (
            data["username"].strip(),
            hashed_password,                    
            data["email"].strip(),
            data["address"].strip()
        ))
        user_id = cursor.fetchone()[0]          
        conn.commit()
        return jsonify({
            "message": "User registered successfully",
            "user_id": user_id
        }), 201

    except Exception:
        conn.rollback()
        return jsonify({"error": "Registration failed"}), 500
    finally:
        cursor.close()
        conn.close()



# LOGIN
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.json
    if not data or "email" not in data or "password" not in data:
        return jsonify({"error": "Email and password are required"}), 400

    if not is_valid_email(data["email"]):
        return jsonify({"error": "Invalid email format"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT UserID, Role, Password
            FROM Users
            WHERE Email = ?
        """, (data["email"],))
        user = cursor.fetchone()

        if not user or not check_password_hash(user[2], data["password"]):
            return jsonify({"error": "Invalid credentials"}), 401

        user_id, role = user[0], user[1]

        access_token = create_access_token(
            identity=str(user_id),
            additional_claims={"role": role},
            expires_delta=datetime.timedelta(minutes=120)
        )
        refresh_token = create_refresh_token(identity=str(user_id))

        return jsonify({
            "message": "Login successful",
            "access_token": access_token,
            "refresh_token": refresh_token
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()  
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


#REFRESH TOKEN
@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT Role FROM Users WHERE UserID = ?", (int(identity),))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "User not found"}), 404

        new_access_token = create_access_token(
            identity=identity,
            additional_claims={"role": row[0]}
        )
        return jsonify({"access_token": new_access_token}), 200

    except Exception as e:
        logging.exception("Token refresh failed")
        return jsonify({"error": "Could not refresh token"}), 500
    finally:
        cursor.close()
        conn.close()

# LOGOUT 
@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    from app import blocklist

  
    blocklist.add(get_jwt()["jti"])

    data = request.get_json(silent=True) or {}
    refresh_jti = data.get("refresh_jti")
    if refresh_jti:
        blocklist.add(refresh_jti)

    return jsonify({"message": "Logged out successfully"}), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    user_id = int(get_jwt_identity())
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT UserName, Email, Role, Points 
        FROM Users WHERE UserID = ?
    """, (user_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if not row:
        return jsonify({"error": "User not found"}), 404
    return jsonify({
        "username": row[0],
        "email": row[1],
        "role": row[2],
        "points": row[3] if row[3] is not None else 0
    })