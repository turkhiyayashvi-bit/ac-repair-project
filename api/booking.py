from flask import Blueprint, jsonify, request
from database.db import get_connection

booking_api = Blueprint("booking_api", __name__)

# ==============================
# Booking Management API
# ==============================

# GET : All Bookings
@booking_api.route("/api/admin/bookings", methods=["GET"])
def get_bookings():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM bookings
        ORDER BY id DESC
    """)

    bookings = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify({
        "status": True,
        "data": bookings
    })

# PATCH : Update Booking Status (e.g., Pending, Confirmed, Completed, Cancelled)
@booking_api.route("/api/admin/bookings/<int:id>/status", methods=["PATCH"])
def update_booking_status(id):
    data = request.get_json()
    status = data.get("status")

    if not status:
        return jsonify({
            "status": False,
            "message": "Status is required"
        }), 400

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE bookings
        SET status = %s
        WHERE id = %s
    """, (status, id))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({
        "status": True,
        "message": "Booking status updated successfully"
    })