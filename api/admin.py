from flask import Blueprint, jsonify, request
from database.db import get_connection

admin_api = Blueprint("admin_api", __name__)


# ==============================
# Get AC Error Codes
# ==============================

@admin_api.route("/api/admin/ac-error-codes", methods=["GET"])
def get_ac_error_codes():

    try:

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                a.id,
                b.name AS brand_name,
                a.error_code,
                a.error_name,
                a.description,
                a.solution,
                a.status,
                a.created_at
            FROM ac_error_codes a
            INNER JOIN brands b
                ON a.brand_id = b.id
            ORDER BY a.id DESC
        """)

        data = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify({
            "status": True,
            "data": data
        }), 200

    except Exception as e:

        return jsonify({
            "status": False,
            "error": str(e)
        }), 500
        
# GET : /api/admin/ac-error-codes/<id>
@admin_api.route("/api/admin/ac-error-codes/<int:id>", methods=["GET"])
def get_single_ac_error_code(id):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            ac_error_codes.id,
            brands.name AS brand_name,
            ac_error_codes.error_code,
            ac_error_codes.error_name,
            ac_error_codes.description,
            ac_error_codes.solution,
            ac_error_codes.status,
            ac_error_codes.created_at

        FROM ac_error_codes

        LEFT JOIN brands 
        ON brands.id = ac_error_codes.brand_id

        WHERE ac_error_codes.id = %s
    """, (id,))

    error_code = cursor.fetchone()

    cursor.close()
    conn.close()

    if error_code:
        return jsonify({
            "status": True,
            "data": error_code
        })

    return jsonify({
        "status": False,
        "message": "AC Error Code not found"
    }), 404
    
# POST : /api/admin/ac-error-codes
@admin_api.route("/api/admin/ac-error-codes", methods=["POST"])
def add_ac_error_code():

    data = request.get_json()

    brand_id = data.get("brand_id")
    error_code = data.get("error_code")
    error_name = data.get("error_name")
    description = data.get("description")
    solution = data.get("solution")
    status = data.get("status", "Active")

    if not brand_id or not error_code or not error_name:
        return jsonify({
            "status": False,
            "message": "Required fields missing"
        }), 400


    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO ac_error_codes
        (
            brand_id,
            error_code,
            error_name,
            description,
            solution,
            status
        )
        VALUES (%s,%s,%s,%s,%s,%s)
    """, (
        brand_id,
        error_code,
        error_name,
        description,
        solution,
        status
    ))

    conn.commit()

    new_id = cursor.lastrowid

    cursor.close()
    conn.close()


    return jsonify({
        "status": True,
        "message": "AC Error Code added successfully",
        "id": new_id
    }), 201
    
# PUT : /api/admin/ac-error-codes/<id>
@admin_api.route("/api/admin/ac-error-codes/<int:id>", methods=["PUT"])
def update_ac_error_code(id):

    data = request.get_json()

    error_code = data.get("error_code")
    error_name = data.get("error_name")
    description = data.get("description")
    solution = data.get("solution")
    status = data.get("status")


    conn = get_connection()
    cursor = conn.cursor()


    # check record exists
    cursor.execute("""
        SELECT id 
        FROM ac_error_codes 
        WHERE id = %s
    """, (id,))

    record = cursor.fetchone()


    if not record:
        cursor.close()
        conn.close()

        return jsonify({
            "status": False,
            "message": "AC Error Code not found"
        }), 404



    cursor.execute("""
        UPDATE ac_error_codes
        SET
            error_code = %s,
            error_name = %s,
            description = %s,
            solution = %s,
            status = %s

        WHERE id = %s
    """, (
        error_code,
        error_name,
        description,
        solution,
        status,
        id
    ))


    conn.commit()

    cursor.close()
    conn.close()


    return jsonify({
        "status": True,
        "message": "AC Error Code updated successfully"
    })
    
# DELETE : /api/admin/ac-error-codes/<id>
@admin_api.route("/api/admin/ac-error-codes/<int:id>", methods=["DELETE"])
def delete_ac_error_code(id):

    conn = get_connection()
    cursor = conn.cursor()


    # Check record exists
    cursor.execute("""
        SELECT id 
        FROM ac_error_codes
        WHERE id = %s
    """, (id,))

    record = cursor.fetchone()


    if not record:
        cursor.close()
        conn.close()

        return jsonify({
            "status": False,
            "message": "AC Error Code not found"
        }), 404


    cursor.execute("""
        DELETE FROM ac_error_codes
        WHERE id = %s
    """, (id,))


    conn.commit()

    cursor.close()
    conn.close()


    return jsonify({
        "status": True,
        "message": "AC Error Code deleted successfully"
    })
    
# GET : /api/admin/pcb-error-codes
@admin_api.route("/api/admin/pcb-error-codes", methods=["GET"])
def get_pcb_error_codes():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            pcb_error_codes.id,
            pcb_companies.name AS company_name,
            pcb_models.model_number,
            pcb_error_codes.error_code,
            pcb_error_codes.error_name,
            pcb_error_codes.description,
            pcb_error_codes.solution,
            pcb_error_codes.status,
            pcb_error_codes.created_at

        FROM pcb_error_codes

        LEFT JOIN pcb_companies
        ON pcb_companies.id = pcb_error_codes.pcb_company_id

        LEFT JOIN pcb_models
        ON pcb_models.id = pcb_error_codes.pcb_model_id

        ORDER BY pcb_error_codes.id DESC
    """)

    errors = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify({
        "status": True,
        "data": errors
    })
# GET : /api/admin/pcb-error-codes/<id>
@admin_api.route("/api/admin/pcb-error-codes/<int:id>", methods=["GET"])
def get_single_pcb_error_code(id):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            pcb_error_codes.id,
            pcb_companies.name AS company_name,
            pcb_models.model_number,
            pcb_models.pcb_number,
            pcb_error_codes.error_code,
            pcb_error_codes.error_name,
            pcb_error_codes.description,
            pcb_error_codes.solution,
            pcb_error_codes.status,
            pcb_error_codes.created_at

        FROM pcb_error_codes

        LEFT JOIN pcb_companies
        ON pcb_companies.id = pcb_error_codes.pcb_company_id

        LEFT JOIN pcb_models
        ON pcb_models.id = pcb_error_codes.pcb_model_id

        WHERE pcb_error_codes.id = %s

    """, (id,))


    error = cursor.fetchone()

    cursor.close()
    conn.close()


    if error:
        return jsonify({
            "status": True,
            "data": error
        })


    return jsonify({
        "status": False,
        "message": "PCB Error Code not found"
    }), 404
    
# POST : /api/admin/pcb-error-codes
@admin_api.route("/api/admin/pcb-error-codes", methods=["POST"])
def add_pcb_error_code():

    data = request.get_json()

    pcb_company_id = data.get("pcb_company_id")
    pcb_model_id = data.get("pcb_model_id")
    error_code = data.get("error_code")
    error_name = data.get("error_name")
    description = data.get("description")
    solution = data.get("solution")
    status = data.get("status", "Active")


    if not pcb_company_id or not pcb_model_id or not error_code or not error_name:
        return jsonify({
            "status": False,
            "message": "Required fields missing"
        }), 400


    conn = get_connection()
    cursor = conn.cursor()


    cursor.execute("""
        INSERT INTO pcb_error_codes
        (
            pcb_company_id,
            pcb_model_id,
            error_code,
            error_name,
            description,
            solution,
            status
        )

        VALUES (%s,%s,%s,%s,%s,%s,%s)

    """, (
        pcb_company_id,
        pcb_model_id,
        error_code,
        error_name,
        description,
        solution,
        status
    ))


    conn.commit()

    new_id = cursor.lastrowid


    cursor.close()
    conn.close()


    return jsonify({
        "status": True,
        "message": "PCB Error Code added successfully",
        "id": new_id
    }), 201
    
# PUT : /api/admin/pcb-error-codes/<id>
@admin_api.route("/api/admin/pcb-error-codes/<int:id>", methods=["PUT"])
def update_pcb_error_code(id):

    data = request.get_json()

    pcb_company_id = data.get("pcb_company_id")
    pcb_model_id = data.get("pcb_model_id")
    error_code = data.get("error_code")
    error_name = data.get("error_name")
    description = data.get("description")
    solution = data.get("solution")
    status = data.get("status")


    conn = get_connection()
    cursor = conn.cursor()


    # Check record exists
    cursor.execute("""
        SELECT id
        FROM pcb_error_codes
        WHERE id = %s
    """, (id,))


    record = cursor.fetchone()


    if not record:
        cursor.close()
        conn.close()

        return jsonify({
            "status": False,
            "message": "PCB Error Code not found"
        }), 404



    cursor.execute("""
        UPDATE pcb_error_codes
        SET
            pcb_company_id = %s,
            pcb_model_id = %s,
            error_code = %s,
            error_name = %s,
            description = %s,
            solution = %s,
            status = %s

        WHERE id = %s

    """, (
        pcb_company_id,
        pcb_model_id,
        error_code,
        error_name,
        description,
        solution,
        status,
        id
    ))


    conn.commit()

    cursor.close()
    conn.close()


    return jsonify({
        "status": True,
        "message": "PCB Error Code updated successfully"
    })
    
# DELETE : /api/admin/pcb-error-codes/<id>
@admin_api.route("/api/admin/pcb-error-codes/<int:id>", methods=["DELETE"])
def delete_pcb_error_code(id):

    conn = get_connection()
    cursor = conn.cursor()


    # Check record exists
    cursor.execute("""
        SELECT id
        FROM pcb_error_codes
        WHERE id = %s
    """, (id,))


    record = cursor.fetchone()


    if not record:
        cursor.close()
        conn.close()

        return jsonify({
            "status": False,
            "message": "PCB Error Code not found"
        }), 404



    cursor.execute("""
        DELETE FROM pcb_error_codes
        WHERE id = %s
    """, (id,))


    conn.commit()

    cursor.close()
    conn.close()


    return jsonify({
        "status": True,
        "message": "PCB Error Code deleted successfully"
    })
    
# ==============================
# PCB Companies CRUD API
# ==============================


# GET : /api/admin/pcb-companies
@admin_api.route("/api/admin/pcb-companies", methods=["GET"])
def get_pcb_companies():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)


    cursor.execute("""
        SELECT
            id,
            name,
            logo,
            status,
            created_at

        FROM pcb_companies

        ORDER BY id DESC
    """)


    companies = cursor.fetchall()


    cursor.close()
    conn.close()


    return jsonify({
        "status": True,
        "data": companies
    })



# GET : /api/admin/pcb-companies/<id>
@admin_api.route("/api/admin/pcb-companies/<int:id>", methods=["GET"])
def get_single_pcb_company(id):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)


    cursor.execute("""
        SELECT *
        FROM pcb_companies
        WHERE id = %s
    """,(id,))


    company = cursor.fetchone()


    cursor.close()
    conn.close()


    if company:

        return jsonify({
            "status": True,
            "data": company
        })


    return jsonify({
        "status": False,
        "message": "PCB Company not found"
    }),404



# POST : /api/admin/pcb-companies
@admin_api.route("/api/admin/pcb-companies", methods=["POST"])
def add_pcb_company():

    data = request.get_json()


    name = data.get("name")
    logo = data.get("logo")
    status = data.get("status","Active")


    if not name:

        return jsonify({
            "status":False,
            "message":"Company name required"
        }),400



    conn = get_connection()
    cursor = conn.cursor()


    cursor.execute("""
        INSERT INTO pcb_companies
        (
            name,
            logo,
            status
        )

        VALUES(%s,%s,%s)

    """,(
        name,
        logo,
        status
    ))


    conn.commit()


    new_id = cursor.lastrowid


    cursor.close()
    conn.close()



    return jsonify({

        "status":True,
        "message":"PCB Company added successfully",
        "id":new_id

    }),201




# PUT : /api/admin/pcb-companies/<id>
@admin_api.route("/api/admin/pcb-companies/<int:id>", methods=["PUT"])
def update_pcb_company(id):


    data=request.get_json()


    name=data.get("name")
    logo=data.get("logo")
    status=data.get("status")


    conn=get_connection()
    cursor=conn.cursor()



    cursor.execute("""
        SELECT id
        FROM pcb_companies
        WHERE id=%s

    """,(id,))


    company=cursor.fetchone()



    if not company:

        cursor.close()
        conn.close()

        return jsonify({

            "status":False,
            "message":"PCB Company not found"

        }),404




    cursor.execute("""
        UPDATE pcb_companies

        SET
            name=%s,
            logo=%s,
            status=%s

        WHERE id=%s

    """,(
        name,
        logo,
        status,
        id
    ))



    conn.commit()


    cursor.close()
    conn.close()



    return jsonify({

        "status":True,
        "message":"PCB Company updated successfully"

    })





# DELETE : /api/admin/pcb-companies/<id>
@admin_api.route("/api/admin/pcb-companies/<int:id>", methods=["DELETE"])
def delete_pcb_company(id):


    conn=get_connection()
    cursor=conn.cursor()



    cursor.execute("""
        SELECT id
        FROM pcb_companies
        WHERE id=%s

    """,(id,))


    company=cursor.fetchone()



    if not company:

        cursor.close()
        conn.close()


        return jsonify({

            "status":False,
            "message":"PCB Company not found"

        }),404




    cursor.execute("""
        DELETE FROM pcb_companies
        WHERE id=%s

    """,(id,))


    conn.commit()


    cursor.close()
    conn.close()



    return jsonify({

        "status":True,
        "message":"PCB Company deleted successfully"

    })
    
# ==============================
# PCB Models CRUD API
# ==============================


# GET : /api/admin/pcb-models
@admin_api.route("/api/admin/pcb-models", methods=["GET"])
def get_pcb_models():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)


    cursor.execute("""
        SELECT
            pcb_models.id,
            brands.name AS brand_name,
            pcb_models.model_number,
            pcb_models.pcb_number,
            pcb_models.ac_type,
            pcb_models.status,
            pcb_models.created_at

        FROM pcb_models

        LEFT JOIN brands
        ON brands.id = pcb_models.brand_id

        ORDER BY pcb_models.id DESC

    """)


    models = cursor.fetchall()


    cursor.close()
    conn.close()


    return jsonify({

        "status":True,
        "data":models

    })





# GET : /api/admin/pcb-models/<id>
@admin_api.route("/api/admin/pcb-models/<int:id>", methods=["GET"])
def get_single_pcb_model(id):

    conn=get_connection()
    cursor=conn.cursor(dictionary=True)



    cursor.execute("""
        SELECT
            pcb_models.*,
            brands.name AS brand_name

        FROM pcb_models

        LEFT JOIN brands
        ON brands.id = pcb_models.brand_id

        WHERE pcb_models.id=%s

    """,(id,))



    model=cursor.fetchone()



    cursor.close()
    conn.close()



    if model:

        return jsonify({

            "status":True,
            "data":model

        })



    return jsonify({

        "status":False,
        "message":"PCB Model not found"

    }),404





# POST : /api/admin/pcb-models
@admin_api.route("/api/admin/pcb-models", methods=["POST"])
def add_pcb_model():


    data=request.get_json()


    brand_id=data.get("brand_id")
    model_number=data.get("model_number")
    pcb_number=data.get("pcb_number")
    ac_type=data.get("ac_type")
    status=data.get("status","Active")
    approval_status=data.get("approval_status","Pending")



    if not brand_id or not model_number:

        return jsonify({

            "status":False,
            "message":"Required fields missing"

        }),400




    conn=get_connection()
    cursor=conn.cursor()



    cursor.execute("""
        INSERT INTO pcb_models

        (
            brand_id,
            model_number,
            pcb_number,
            ac_type,
            status
        )

        VALUES(%s,%s,%s,%s,%s)

    """,(
        brand_id,
        model_number,
        pcb_number,
        ac_type,
        status
    ))



    conn.commit()


    new_id=cursor.lastrowid



    cursor.close()
    conn.close()



    return jsonify({

        "status":True,
        "message":"PCB Model added successfully",
        "id":new_id

    }),201






# PUT : /api/admin/pcb-models/<id>
@admin_api.route("/api/admin/pcb-models/<int:id>", methods=["PUT"])
def update_pcb_model(id):


    data=request.get_json()


    brand_id=data.get("brand_id")
    model_number=data.get("model_number")
    pcb_number=data.get("pcb_number")
    ac_type=data.get("ac_type")
    status=data.get("status")



    conn=get_connection()
    cursor=conn.cursor()



    cursor.execute("""
        SELECT id
        FROM pcb_models
        WHERE id=%s

    """,(id,))


    model=cursor.fetchone()



    if not model:

        cursor.close()
        conn.close()


        return jsonify({

            "status":False,
            "message":"PCB Model not found"

        }),404




    cursor.execute("""
        UPDATE pcb_models

        SET
            brand_id=%s,
            model_number=%s,
            pcb_number=%s,
            ac_type=%s,
            status=%s

        WHERE id=%s

    """,(
        brand_id,
        model_number,
        pcb_number,
        ac_type,
        status,
        id
    ))



    conn.commit()



    cursor.close()
    conn.close()



    return jsonify({

        "status":True,
        "message":"PCB Model updated successfully"

    })







# DELETE : /api/admin/pcb-models/<id>
@admin_api.route("/api/admin/pcb-models/<int:id>", methods=["DELETE"])
def delete_pcb_model(id):


    conn=get_connection()
    cursor=conn.cursor()



    cursor.execute("""
        SELECT id
        FROM pcb_models
        WHERE id=%s

    """,(id,))



    model=cursor.fetchone()



    if not model:

        cursor.close()
        conn.close()


        return jsonify({

            "status":False,
            "message":"PCB Model not found"

        }),404





    cursor.execute("""
        DELETE FROM pcb_models
        WHERE id=%s

    """,(id,))



    conn.commit()



    cursor.close()
    conn.close()



    return jsonify({

        "status":True,
        "message":"PCB Model deleted successfully"

    })