from flask import Blueprint, jsonify, request
from database.db import get_connection
import random
from datetime import datetime, timedelta
import jwt
from functools import wraps
from google.oauth2 import id_token
from google.auth.transport import requests

auth_api = Blueprint("auth_api", __name__)

JWT_SECRET = "AC_PCB_REPAIR_SECRET_KEY"

GOOGLE_CLIENT_ID = "YOUR_GOOGLE_CLIENT_ID"

# ==============================
# JWT Token Required
# ==============================

def token_required(f):

    @wraps(f)
    def decorated(*args, **kwargs):

        token = request.headers.get("Authorization")

        if not token:

            return jsonify({
                "status": False,
                "message": "Token is missing"
            }), 401

        try:

            if token.startswith("Bearer "):
                token = token.split(" ")[1]

            data = jwt.decode(
                token,
                JWT_SECRET,
                algorithms=["HS256"]
            )

        except Exception:

            return jsonify({
                "status": False,
                "message": "Invalid Token"
            }), 401

        return f(data, *args, **kwargs)

    return decorated

# ==============================
# Technician Register API
# ==============================

@auth_api.route("/api/auth/register", methods=["POST"])
def register():

    try:

        data = request.get_json()

        name = data.get("name")
        email = data.get("email")
        phone = data.get("phone")
        city = data.get("city")
        state = data.get("state")

        if not name or not email:

            return jsonify({
                "status": False,
                "message": "Name and Email are required"
            }), 400

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Check Email Already Registered

        cursor.execute("""
            SELECT id
            FROM technicians
            WHERE email = %s
        """,
        (email,))

        technician = cursor.fetchone()

        if technician:

            cursor.close()
            conn.close()

            return jsonify({
                "status": False,
                "message": "Email already registered"
            }), 400

        # Insert Technician

        cursor.execute("""
            INSERT INTO technicians
            (
                name,
                email,
                phone,
                city,
                state,
                is_email_verified,
                is_approved,
                approval_status
            )
            VALUES
            (%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            name,
            email,
            phone,
            city,
            state,
            0,
            0,
            "Pending"
        ))

        conn.commit()

        # Generate OTP

        otp = str(random.randint(100000, 999999))

        expires_at = datetime.now() + timedelta(minutes=10)

        # Save OTP

        cursor.execute("""
            INSERT INTO otps
            (
                email,
                code,
                expires_at,
                is_used
            )
            VALUES
            (%s,%s,%s,%s)
        """,
        (
            email,
            otp,
            expires_at,
            0
        ))

        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({
            "status": True,
            "message": "Technician Registered Successfully",
            "otp": otp
        }), 200

    except Exception as e:

        return jsonify({
            "status": False,
            "error": str(e)
        }), 500
        
        # ==============================
# Verify OTP API
# ==============================

@auth_api.route("/api/auth/verify-otp", methods=["POST"])
def verify_otp():

    try:

        data = request.get_json()

        email = data.get("email")
        otp = data.get("otp")

        if not email or not otp:

            return jsonify({
                "status": False,
                "message": "Email and OTP are required"
            }), 400

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Check OTP

        cursor.execute("""
            SELECT *
            FROM otps
            WHERE email = %s
            AND code = %s
            AND is_used = 0
            ORDER BY id DESC
            LIMIT 1
        """,
        (
            email,
            otp
        ))

        otp_data = cursor.fetchone()

        if not otp_data:

            cursor.close()
            conn.close()

            return jsonify({
                "status": False,
                "message": "Invalid OTP"
            }), 400

        # Check OTP Expiry

        if datetime.now() > otp_data["expires_at"]:

            cursor.close()
            conn.close()

            return jsonify({
                "status": False,
                "message": "OTP Expired"
            }), 400

        # Mark OTP Used

        cursor.execute("""
            UPDATE otps
            SET is_used = 1
            WHERE id = %s
        """,
        (
            otp_data["id"],
        ))

        # Verify Technician Email

        cursor.execute("""
            UPDATE technicians
            SET is_email_verified = 1
            WHERE email = %s
        """,
        (
            email,
        ))

        # Get Technician Details

        cursor.execute("""
            SELECT
                id,
                name,
                email,
                is_approved
            FROM technicians
            WHERE email = %s
        """,
        (
            email,
        ))

        technician = cursor.fetchone()

        # Generate JWT Token

        token = jwt.encode(
            {
                "id": technician["id"],
                "email": technician["email"]
            },
            JWT_SECRET,
            algorithm="HS256"
        )

        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({
            "status": True,
            "message": "OTP Verified Successfully",
            "token": token,
            "technician": technician
        }), 200

    except Exception as e:

        return jsonify({
            "status": False,
            "error": str(e)
        }), 500
        
        # ==============================
# My Profile API
# ==============================

@auth_api.route("/api/auth/me", methods=["GET"])
@token_required
def my_profile(current_user):

    try:

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                id,
                name,
                email,
                phone,
                city,
                state,
                shop_name,
                is_email_verified,
                is_approved,
                approval_status,
                created_at
            FROM technicians
            WHERE id = %s
        """,
        (
            current_user["id"],
        ))

        technician = cursor.fetchone()

        cursor.close()
        conn.close()

        if not technician:

            return jsonify({
                "status": False,
                "message": "Technician not found"
            }), 404

        return jsonify({
            "status": True,
            "technician": technician
        }), 200

    except Exception as e:

        return jsonify({
            "status": False,
            "error": str(e)
        }), 500
        
        # ==============================
# Test API
# ==============================

@auth_api.route("/api/test", methods=["GET"])
def test():

    return jsonify({
        "message": "API Working"
    })
    
# ==============================
# Google Login API
# ==============================
@auth_api.route("/api/auth/google", methods=["POST"])
def google_login():

    try:

        data = request.get_json()

        token = data.get("token")

        if not token:

            return jsonify({
                "status": False,
                "message": "Google Token Required"
            }), 400

        idinfo = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            GOOGLE_CLIENT_ID
        )

        name = idinfo.get("name")
        email = idinfo.get("email")
        google_id = idinfo.get("sub")

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT *
            FROM technicians
            WHERE email = %s
        """, (email,))

        technician = cursor.fetchone()

        if technician:

            cursor.execute("""
                UPDATE technicians
                SET google_id = %s,
                    is_email_verified = 1
                WHERE id = %s
            """, (
                google_id,
                technician["id"]
            ))

            technician_id = technician["id"]

        else:

            cursor.execute("""
                INSERT INTO technicians
                (
                    name,
                    email,
                    phone,
                    city,
                    state,
                    google_id,
                    is_email_verified,
                    is_approved,
                    approval_status
                )
                VALUES
                (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                name,
                email,
                "",
                "",
                "",
                google_id,
                1,
                0,
                "Pending"
            ))

            technician_id = cursor.lastrowid

        conn.commit()

        cursor.close()
        conn.close()

        jwt_token = jwt.encode(
            {
                "id": technician_id,
                "email": email
            },
            JWT_SECRET,
            algorithm="HS256"
        )

        return jsonify({
            "status": True,
            "message": "Google Login Successful",
            "token": jwt_token
        }), 200

    except Exception as e:

        return jsonify({
            "status": False,
            "error": str(e)
        }), 500
        
# ==============================
# Admin Login API
# ==============================

@auth_api.route("/api/admin/login", methods=["POST"])
def admin_login():

    try:

        data = request.get_json()

        username = data.get("username")
        password = data.get("password")

        if not username or not password:

            return jsonify({
                "status": False,
                "message": "Username and Password are required"
            }), 400

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT *
            FROM users
            WHERE username = %s
            AND password = %s
            LIMIT 1
        """, (
            username,
            password
        ))

        user = cursor.fetchone()

        if not user:

            cursor.close()
            conn.close()

            return jsonify({
                "status": False,
                "message": "Invalid Username or Password"
            }), 401

        jwt_token = jwt.encode(
            {
                "id": user["id"],
                "username": user["username"],
                "role": user["role"]
            },
            JWT_SECRET,
            algorithm="HS256"
        )

        cursor.close()
        conn.close()

        return jsonify({
            "status": True,
            "message": "Login Successful",
            "token": jwt_token,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "role": user["role"]
            }
        }), 200

    except Exception as e:

        return jsonify({
            "status": False,
            "error": str(e)
        }), 500