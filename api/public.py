from flask import Blueprint, jsonify
from database.db import get_connection


public_api = Blueprint("public_api", __name__)


# ==========================
# GET ALL AC BRANDS
# /api/brands
# ==========================

@public_api.route("/api/brands", methods=["GET"])
def get_brands():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, name, logo_image
        FROM brands
        ORDER BY name ASC
    """)

    brands = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify({
        "status": True,
        "brands": brands
    })


# ==========================
# GET BRAND ERROR CODES
# /api/brands/<id>/error-codes
# ==========================

@public_api.route("/api/brands/<int:id>/error-codes", methods=["GET"])
def get_brand_error_codes(id):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            id,
            code,
            title,
            description,
            image
        FROM ac_error_codes
        WHERE brand_id = %s
    """, (id,))

    errors = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify({
        "status": True,
        "error_codes": errors
    })


# ==========================
# GET PCB COMPANIES
# /api/pcb-companies
# ==========================

@public_api.route("/api/pcb-companies", methods=["GET"])
def get_pcb_companies():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, name, logo
        FROM pcb_companies
        ORDER BY name ASC
    """)

    companies = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify({
        "status": True,
        "pcb_companies": companies
    })


# ==========================
# GET PCB MODELS BY COMPANY
# /api/pcb-companies/<id>/models
# ==========================

@public_api.route("/api/pcb-companies/<int:id>/models", methods=["GET"])
def get_pcb_models(id):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            id,
            name,
            photo,
            description
        FROM pcb_models
        WHERE pcb_company_id = %s
    """, (id,))

    models = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify({
        "status": True,
        "models": models
    })


# ==========================
# GET PCB MODEL DETAILS
# /api/pcb-models/<id>
# ==========================

@public_api.route("/api/pcb-models/<int:id>", methods=["GET"])
def get_pcb_model_details(id):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)


    # PCB Model
    cursor.execute("""
        SELECT *
        FROM pcb_models
        WHERE id = %s
    """, (id,))

    model = cursor.fetchone()


    if model is None:
        cursor.close()
        conn.close()

        return jsonify({
            "status": False,
            "message": "PCB Model not found"
        }), 404


    # Error Codes
    cursor.execute("""
        SELECT 
            id,
            code,
            description
        FROM pcb_error_codes
        WHERE pcb_model_id = %s
    """, (id,))

    errors = cursor.fetchall()


    # Brands using PCB
    cursor.execute("""
        SELECT 
            b.id,
            b.name
        FROM brands b
        JOIN pcb_model_brands pmb
        ON b.id = pmb.brand_id
        WHERE pmb.pcb_model_id = %s
    """, (id,))

    brands = cursor.fetchall()


    cursor.close()
    conn.close()


    return jsonify({
        "status": True,
        "model": model,
        "used_by_brands": brands,
        "error_codes": errors
    })


# ==========================
# GET WHATSAPP NUMBER
# /api/settings/whatsapp
# ==========================

@public_api.route("/api/settings/whatsapp", methods=["GET"])
def get_whatsapp():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT value
        FROM settings
        WHERE name = 'owner_whatsapp_number'
    """)

    whatsapp = cursor.fetchone()

    cursor.close()
    conn.close()


    return jsonify({
        "status": True,
        "whatsapp": whatsapp
    })