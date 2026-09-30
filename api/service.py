from flask import Blueprint, jsonify, request
from database.db import get_connection

service_api = Blueprint("service_api", __name__)

# ==============================
# Service CRUD API
# ==============================

# GET : All Services
@service_api.route("/api/admin/services", methods=["GET"])
def get_services():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM services
        ORDER BY id DESC
    """)

    services = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify({
        "status": True,
        "data": services
    })

# POST : Add Service
@service_api.route("/api/admin/services", methods=["POST"])
def add_service():
    data = request.get_json()

    name = data.get("name")
    description = data.get("description")
    price = data.get("price")
    category_id = data.get("category_id")

    if not name or not price:
        return jsonify({
            "status": False,
            "message": "Service name and price are required"
        }), 400

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO services (name, description, price, category_id)
        VALUES (%s, %s, %s, %s)
    """, (name, description, price, category_id))

    conn.commit()
    new_id = cursor.lastrowid
    cursor.close()
    conn.close()

    return jsonify({
        "status": True,
        "message": "Service added successfully",
        "id": new_id
    }), 201

# PUT : Update Service
@service_api.route("/api/admin/services/<int:id>", methods=["PUT"])
def update_service(id):
    data = request.get_json()

    name = data.get("name")
    description = data.get("description")
    price = data.get("price")
    category_id = data.get("category_id")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE services
        SET name = %s, description = %s, price = %s, category_id = %s
        WHERE id = %s
    """, (name, description, price, category_id, id))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({
        "status": True,
        "message": "Service updated successfully"
    })

# DELETE : Delete Service
@service_api.route("/api/admin/services/<int:id>", methods=["DELETE"])
def delete_service(id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM services
        WHERE id = %s
    """, (id,))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({
        "status": True,
        "message": "Service deleted successfully"
    })