from flask import Blueprint, jsonify, request
from database.db import get_connection

technician_api = Blueprint("technician_api", __name__)

# ==============================
# Technician CRUD API
# ==============================

# GET : /api/admin/technicians
@technician_api.route("/api/admin/technicians", methods=["GET"])
def get_technicians():
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
            experience,
            is_approved,
            status,
            created_at
        FROM technicians
        ORDER BY id DESC
    """)

    technicians = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify({
        "status": True,
        "data": technicians
    })

# GET Single Technician
@technician_api.route("/api/admin/technicians/<int:id>", methods=["GET"])
def get_single_technician(id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM technicians
        WHERE id = %s
    """, (id,))

    technician = cursor.fetchone()
    cursor.close()
    conn.close()

    if technician:
        return jsonify({
            "status": True,
            "data": technician
        })

    return jsonify({
        "status": False,
        "message": "Technician not found"
    }), 404

# POST Add Technician
@technician_api.route("/api/admin/technicians", methods=["POST"])
def add_technician():
    data = request.get_json()

    name = data.get("name")
    email = data.get("email")
    phone = data.get("phone")
    city = data.get("city")
    state = data.get("state")
    shop_name = data.get("shop_name")
    experience = data.get("experience")
    status = data.get("status", "Active")

    if not name or not phone:
        return jsonify({
            "status": False,
            "message": "Name and phone required"
        }), 400

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO technicians
        (
            name,
            email,
            phone,
            city,
            state,
            shop_name,
            experience,
            status
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        name,
        email,
        phone,
        city,
        state,
        shop_name,
        experience,
        status
    ))

    conn.commit()
    new_id = cursor.lastrowid

    cursor.close()
    conn.close()

    return jsonify({
        "status": True,
        "message": "Technician added successfully",
        "id": new_id
    }), 201

# PUT Update Technician
@technician_api.route("/api/admin/technicians/<int:id>", methods=["PUT"])
def update_technician(id):
    data = request.get_json()

    name = data.get("name")
    email = data.get("email")
    phone = data.get("phone")
    city = data.get("city")
    state = data.get("state")
    shop_name = data.get("shop_name")
    experience = data.get("experience")
    status = data.get("status")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE technicians
        SET
            name = %s,
            email = %s,
            phone = %s,
            city = %s,
            state = %s,
            shop_name = %s,
            experience = %s,
            status = %s
        WHERE id = %s
    """, (
        name,
        email,
        phone,
        city,
        state,
        shop_name,
        experience,
        status,
        id
    ))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({
        "status": True,
        "message": "Technician updated successfully"
    })

# DELETE Technician
@technician_api.route("/api/admin/technicians/<int:id>", methods=["DELETE"])
def delete_technician(id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM technicians
        WHERE id = %s
    """, (id,))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({
        "status": True,
        "message": "Technician deleted successfully"
    })
    
# ==============================
# Technician Approve / Reject API
# ==============================

@technician_api.route("/api/admin/technicians/<int:id>/status", methods=["PATCH"])
def update_technician_status(id):
    data = request.get_json()
    
    # 'approved', 'rejected', કે પછી અન્ય સ્ટેટસ માટે
    is_approved = data.get("is_approved")  # દા.ત., 1 (Approve) અથવા 0 (Reject)
    status = data.get("status")            # દા.ત., 'Active', 'Suspended', વગેરે

    if is_approved is None and status is None:
        return jsonify({
            "status": False,
            "message": "Please provide 'is_approved' or 'status' to update"
        }), 400

    conn = get_connection()
    cursor = conn.cursor()

    # ડાયનેમિક કવેરી બનાવવા માટે
    update_fields = []
    params = []

    if is_approved is not None:
        update_fields.append("is_approved = %s")
        params.append(is_approved)
        
    if status is not None:
        update_fields.append("status = %s")
        params.append(status)

    params.append(id)

    query = f"""
        UPDATE technicians
        SET {", ".join(update_fields)}
        WHERE id = %s
    """

    cursor.execute(query, tuple(params))
    conn.commit()
    
    cursor.close()
    conn.close()

    return jsonify({
        "status": True,
        "message": "Technician status updated successfully"
    })