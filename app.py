from flask import Flask, render_template, request, redirect, url_for, session
from database.db import get_connection
import os
from werkzeug.utils import secure_filename
import csv
from flask import Response
from api.public import public_api
from api.auth import auth_api
from api.admin import admin_api
from api.technician import technician_api
from api.service import service_api
from api.booking import booking_api
from functools import wraps
from flask import session, redirect, url_for, flash
import random
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import render_template, request, redirect, url_for, session
import traceback
from flask import render_template, request, redirect, url_for, session
from services.notification import send_push_notification



print("RUNNING FILE:", __file__)

app = Flask(__name__, static_folder='static')
app.register_blueprint(public_api)
app.register_blueprint(auth_api)
app.register_blueprint(admin_api)
app.register_blueprint(technician_api)
app.register_blueprint(service_api)
app.register_blueprint(booking_api)
print(app.url_map)


# ✅ strong secret key (session issue fix)
app.secret_key = "ac_pcb_repair_super_secret_key_12345"


# 1. ---------------- LOGIN REQUIRED DECORATOR (અહીં અલગથી વ્યાખ્યાયિત કરો) ----------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# 2. ---------------- LOGIN ROUTE (આના પર @login_required ન મુકવું) ----------------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Simple login check
        if username == 'admin' and password == '1234':
            session['user'] = username
            return redirect(url_for('dashboard'))
        else:
            return render_template('admin/login.html', error="Invalid Username or Password")

    return render_template('admin/login.html')


# ---------------- DASHBOARD ROUTE ----------------
@app.route('/dashboard')
def dashboard():
    # Check user authentication session
    if 'user' not in session:
        return redirect(url_for('login'))

    # Initialize default variables
    users_count = 0
    tech_count = 0
    reports_count = 0
    repair_jobs_data = [0, 0, 0, 0, 0, 0, 0]
    brand_labels = ["No Data"]
    brand_counts = [0]

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # 1. Total Technicians Count
        try:
            cursor.execute("SELECT COUNT(*) AS total FROM technicians")
            res = cursor.fetchone()
            users_count = list(res.values())[0] if isinstance(res, dict) else (res[0] if res else 0)
        except Exception as e:
            print("DB ERROR (Total Technicians):", e)
            users_count = 0

        # 2. Approved / Active Technicians Count
        try:
            cursor.execute("""
                SELECT COUNT(*) AS total 
                FROM technicians 
                WHERE (is_approved = 1 OR is_approved = TRUE OR status = 'approved') 
                  AND (is_active = 1 OR is_active = TRUE)
            """)
            res = cursor.fetchone()
            tech_count = list(res.values())[0] if isinstance(res, dict) else (res[0] if res else 0)
        except Exception as e:
            # Fallback check if 'is_active' column does not exist
            try:
                cursor.execute("""
                    SELECT COUNT(*) AS total 
                    FROM technicians 
                    WHERE is_approved = 1 OR is_approved = TRUE OR status = 'approved'
                """)
                res = cursor.fetchone()
                tech_count = list(res.values())[0] if isinstance(res, dict) else (res[0] if res else 0)
            except Exception as inner_e:
                print("DB ERROR (Approved Technicians):", inner_e)
                tech_count = 0

        # 3. Pending Repair Jobs Count
        try:
            cursor.execute("""
                SELECT COUNT(*) AS total 
                FROM repair_jobs 
                WHERE status IN ('Received', 'Diagnosing', 'In Progress', 'Under Repair')
            """)
            res = cursor.fetchone()
            reports_count = list(res.values())[0] if isinstance(res, dict) else (res[0] if res else 0)
        except Exception as e:
            print("DB ERROR (Pending Repair Jobs):", e)
            reports_count = 0

        # 4. Repair Jobs Pipeline Status Breakdown
        try:
            status_list = [
                "Received",
                "Diagnosing",
                "In Progress",
                "Under Repair",
                "Testing",
                "Ready",
                "Delivered"
            ]

            cursor.execute("""
                SELECT status, COUNT(*) AS count
                FROM repair_jobs
                GROUP BY status
            """)
            rows = cursor.fetchall()
            
            # Helper logic to parse dict/tuple cursor output safely
            status_dict = {}
            for row in rows:
                if isinstance(row, dict):
                    status_dict[str(row.get('status')).strip()] = row.get('count', 0)
                elif isinstance(row, (tuple, list)):
                    status_dict[str(row[0]).strip()] = row[1]

            repair_jobs_data = [status_dict.get(s, 0) for s in status_list]
        except Exception as e:
            print("DB ERROR (Pipeline Status):", e)
            repair_jobs_data = [0, 0, 0, 0, 0, 0, 0]

        # 5. Brand-Wise Share Analysis
        try:
            cursor.execute("""
                SELECT b.name AS brand_name, COUNT(r.id) AS job_count
                FROM brands b
                LEFT JOIN repair_jobs r ON b.id = r.brand_id
                GROUP BY b.id, b.name
                ORDER BY b.name
            """)
            brands_data = cursor.fetchall()

            if brands_data:
                brand_labels = []
                brand_counts = []
                for b in brands_data:
                    if isinstance(b, dict):
                        brand_labels.append(b.get('brand_name', 'Unknown'))
                        brand_counts.append(b.get('job_count', 0))
                    elif isinstance(b, (tuple, list)):
                        brand_labels.append(b[0])
                        brand_counts.append(b[1])
            else:
                brand_labels = ["No Brand"]
                brand_counts = [0]
        except Exception as e:
            print("DB ERROR (Brand Share):", e)
            brand_labels = ["No Brand"]
            brand_counts = [0]

        cursor.close()
        conn.close()

    except Exception as e:
        return f"<h2>Dashboard Error: {str(e)}</h2>"

    return render_template(
        "admin/dashboard.html",
        total_users=users_count,
        active_tech=tech_count,
        pending_reports=reports_count,
        repair_jobs_data=repair_jobs_data,
        brand_labels=brand_labels,
        brand_counts=brand_counts
    )


# ---------------- USERS PAGE ROUTE ----------------
@app.route('/users')
def users():
    # Check user authentication session
    if 'user' not in session:
        return redirect(url_for('login'))

    users_data = []

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch all registered users
        cursor.execute("SELECT * FROM users")
        users_data = cursor.fetchall()

        cursor.close()
        conn.close()

    except Exception as e:
        print("DB ERROR (users):", e)

    return render_template('admin/users.html', users=users_data)

# ---------------- BRANDS PAGE ----------------
@app.route('/brands')
def brands():

    if 'user' not in session:
        return redirect(url_for('login'))

    brands_data = []

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM brands ORDER BY id DESC")
        brands_data = cursor.fetchall()

        cursor.close()
        conn.close()

    except Exception as e:
        print("DB ERROR (brands):", e)

    return render_template(
        "admin/brands.html",
        brands=brands_data
    )
    
    # ---------------- ADD BRAND PAGE ----------------
@app.route('/add_brand')
def add_brand():

    if 'user' not in session:
        return redirect(url_for('login'))

    return render_template("admin/add_brand.html")

# ---------------- SAVE BRAND ----------------
@app.route('/save_brand', methods=['POST'])
def save_brand():

    if 'user' not in session:
        return redirect(url_for('login'))

    name = request.form['name']
    status = request.form['status']

    logo = request.files['logo']

    filename = ""

    if logo:
        filename = secure_filename(logo.filename)

        logo.save(
            os.path.join(
                app.static_folder,
                "uploads",
                "brands",
                filename
            )
        )

    try:

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO brands
            (name, logo, status)
            VALUES(%s,%s,%s)
        """, (
            name,
            filename,
            status
        ))

        conn.commit()

        cursor.close()
        conn.close()

    except Exception as e:
        return str(e)

    return redirect(url_for('brands'))


# ---------------- EDIT BRAND ----------------
@app.route('/edit_brand/<int:id>')
def edit_brand(id):

    if 'user' not in session:
        return redirect(url_for('login'))

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM brands WHERE id=%s", (id,))
        brand = cursor.fetchone()

        cursor.close()
        conn.close()

    except Exception as e:
        return str(e)

    return render_template(
        "admin/edit_brand.html",
        brand=brand
    )
    
    # ---------------- UPDATE BRAND ----------------
@app.route('/update_brand/<int:id>', methods=['POST'])
def update_brand(id):

    if 'user' not in session:
        return redirect(url_for('login'))

    name = request.form['name']
    status = request.form['status']

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Old logo
        cursor.execute("SELECT logo FROM brands WHERE id=%s", (id,))
        old_logo = cursor.fetchone()[0]

        filename = old_logo

        # New logo upload
        if 'logo' in request.files:
            logo = request.files['logo']

            if logo.filename != "":

                filename = secure_filename(logo.filename)

                logo.save(
                    os.path.join(
                        app.static_folder,
                        "uploads",
                        "brands",
                        filename
                    )
                )

        cursor.execute("""
            UPDATE brands
            SET
                name=%s,
                logo=%s,
                status=%s
            WHERE id=%s
        """, (
            name,
            filename,
            status,
            id
        ))

        conn.commit()

        cursor.close()
        conn.close()

    except Exception as e:
        return str(e)

    return redirect(url_for('brands'))


# ---------------- DELETE BRAND ----------------

@app.route('/delete_brand/<int:id>')
def delete_brand(id):

    if 'user' not in session:
        return redirect(url_for('login'))

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # First delete PCB models belonging to this brand
        cursor.execute(
            "DELETE FROM pcb_models WHERE brand_id=%s",
            (id,)
        )

        # Then delete the brand
        cursor.execute(
            "DELETE FROM brands WHERE id=%s",
            (id,)
        )

        conn.commit()

        cursor.close()
        conn.close()

    except Exception as e:
        return str(e)

    return redirect(url_for('brands'))

# ---------------- AC ERROR CODE LIST ----------------
@app.route('/ac_error_codes')
def ac_error_codes():
    if 'user' not in session:
        return redirect(url_for('login'))

    error_codes = []
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                ac_error_codes.*,
                brands.name AS brand_name
            FROM ac_error_codes
            INNER JOIN brands ON ac_error_codes.brand_id = brands.id
            ORDER BY ac_error_codes.id DESC
        """)

        error_codes = cursor.fetchall()
        cursor.close()
        conn.close()

    except Exception as e:
        print("DB ERROR (AC Error Codes):", e)

    return render_template(
        "admin/ac_error_codes.html",
        error_codes=error_codes
    )


# ---------------- ADD AC ERROR CODE PAGE ----------------
@app.route('/add_ac_error_code')
def add_ac_error_code():
    if 'user' not in session:
        return redirect(url_for('login'))

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT id, name
            FROM brands
            WHERE status='Active'
            ORDER BY name ASC
        """)

        brands = cursor.fetchall()
        cursor.close()
        conn.close()

    except Exception as e:
        return str(e)

    return render_template(
        "admin/add_ac_error_code.html",
        brands=brands
    )


# ---------------- SAVE AC ERROR CODE (WITH OPTIONAL IMAGE SUPPORT) ----------------
@app.route('/save_ac_error_code', methods=['POST'])
def save_ac_error_code():
    if 'user' not in session:
        return redirect(url_for('login'))

    brand_id = request.form.get('brand_id')
    error_code = request.form.get('error_code')
    error_name = request.form.get('error_name')
    description = request.form.get('description', '')
    solution = request.form.get('solution', '')
    status = request.form.get('status', 'Active')

    filename = None

    # Check if optional image file was uploaded
    if 'image' in request.files:
        image_file = request.files['image']
        if image_file and image_file.filename != '':
            filename = secure_filename(image_file.filename)
            upload_dir = os.path.join(app.static_folder, "uploads")
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)
            image_file.save(os.path.join(upload_dir, filename))

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO ac_error_codes
            (brand_id, error_code, error_name, description, solution, status, image)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (brand_id, error_code, error_name, description, solution, status, filename))

        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        print("Save AC Error Code Error:", e)
        return str(e)

    return redirect(url_for('ac_error_codes'))


# ---------------- EDIT AC ERROR CODE ----------------
@app.route('/edit_ac_error_code/<int:id>')
def edit_ac_error_code(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Current Error Code
        cursor.execute("SELECT * FROM ac_error_codes WHERE id=%s", (id,))
        error = cursor.fetchone()

        # Active Brands
        cursor.execute("""
            SELECT id, name
            FROM brands
            WHERE status='Active'
            ORDER BY name
        """)
        brands = cursor.fetchall()

        cursor.close()
        conn.close()

    except Exception as e:
        return str(e)

    return render_template(
        "admin/edit_ac_error_code.html",
        error=error,
        brands=brands
    )


# ---------------- UPDATE AC ERROR CODE (UPDATED WITH IMAGE SUPPORT) ----------------
@app.route('/update_ac_error_code/<int:id>', methods=['POST'])
def update_ac_error_code(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    brand_id = request.form.get('brand_id')
    error_code = request.form.get('error_code')
    error_name = request.form.get('error_name')
    description = request.form.get('description', '')
    solution = request.form.get('solution', '')
    status = request.form.get('status', 'Active')

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # 1. Old Image Fetch
        cursor.execute("SELECT image FROM ac_error_codes WHERE id=%s", (id,))
        existing_row = cursor.fetchone()
        filename = existing_row['image'] if existing_row and 'image' in existing_row else None

        # 2. Check if NEW image file is uploaded
        if 'image' in request.files:
            image_file = request.files['image']
            if image_file and image_file.filename != '':
                filename = secure_filename(image_file.filename)
                upload_dir = os.path.join(app.static_folder, "uploads")
                if not os.path.exists(upload_dir):
                    os.makedirs(upload_dir)
                image_file.save(os.path.join(upload_dir, filename))

        cursor = conn.cursor()

        # 3. Update Database Record
        cursor.execute("""
            UPDATE ac_error_codes
            SET
                brand_id=%s,
                error_code=%s,
                error_name=%s,
                description=%s,
                solution=%s,
                status=%s,
                image=%s
            WHERE id=%s
        """, (
            brand_id,
            error_code,
            error_name,
            description,
            solution,
            status,
            filename,
            id
        ))

        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        print("Update AC Error Code Error:", e)
        return str(e)

    return redirect(url_for('ac_error_codes'))


# ---------------- DELETE AC ERROR CODE ----------------
@app.route('/delete_ac_error_code/<int:id>')
def delete_ac_error_code(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM ac_error_codes WHERE id=%s", (id,))

        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        return str(e)

    return redirect(url_for('ac_error_codes'))
# ---------------- PCB MODELS MASTER LIST ----------------
@app.route('/pcb_models')
def pcb_models():
    if 'user' not in session:
        return redirect(url_for('login'))

    pcb_models = []
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                pm.*,
                b.name AS brand_name
            FROM pcb_models pm
            LEFT JOIN brands b ON pm.brand_id = b.id
            ORDER BY pm.id DESC
        """)

        pcb_models = cursor.fetchall()
        cursor.close()
        conn.close()

    except Exception as e:
        print("DB ERROR (PCB Models):", e)

    return render_template(
        "admin/pcb_models.html",
        pcb_models=pcb_models
    )

# ---------------- ADD PCB MODEL ----------------
@app.route('/add_pcb_model')
def add_pcb_model():
    if 'user' not in session:
        return redirect(url_for('login'))

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT id, name
            FROM brands
            WHERE status='Active'
            ORDER BY name ASC
        """)
        brands = cursor.fetchall()

        cursor.close()
        conn.close()

    except Exception as e:
        return str(e)

    return render_template(
        "admin/add_pcb_model.html",
        brands=brands
    )

# ---------------- SAVE PCB MODEL ----------------
@app.route('/save_pcb_model', methods=['POST'])
def save_pcb_model():
    if 'user' not in session:
        return redirect(url_for('login'))

    brand_id = request.form.get('brand_id')
    model_number = request.form.get('model_number')
    pcb_number = request.form.get('pcb_number')
    ac_type = request.form.get('ac_type', 'Split')
    status = request.form.get('status', 'Active')

    try:
        conn = get_connection()
        cursor = conn.cursor()

        query = """
            INSERT INTO pcb_models 
            (brand_id, model_number, pcb_number, ac_type, status)
            VALUES (%s, %s, %s, %s, %s)
        """
        values = (brand_id, model_number, pcb_number, ac_type, status)

        cursor.execute(query, values)
        conn.commit()

        cursor.close()
        conn.close()

        return redirect(url_for('pcb_models'))

    except Exception as e:
        print("\n--- SAVE PCB MODEL ERROR ---", e, "\n")
        return str(e)

# ---------------- EDIT PCB MODEL PAGE ----------------
@app.route('/edit_pcb_model/<int:id>')
def edit_pcb_model(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # 1. Get current PCB Model Record
        cursor.execute("SELECT * FROM pcb_models WHERE id=%s", (id,))
        pcb = cursor.fetchone()

        # 2. Get Active Brands List
        cursor.execute("""
            SELECT id, name
            FROM brands
            WHERE status='Active'
            ORDER BY name ASC
        """)
        brands = cursor.fetchall()

        cursor.close()
        conn.close()

    except Exception as e:
        return str(e)

    return render_template(
        "admin/edit_pcb_model.html",
        pcb=pcb,
        brands=brands
    )

# ---------------- UPDATE PCB MODEL ACTION ----------------
@app.route('/update_pcb_model/<int:id>', methods=['POST'])
def update_pcb_model(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    brand_id = request.form.get('brand_id')
    model_number = request.form.get('model_number')
    pcb_number = request.form.get('pcb_number')
    ac_type = request.form.get('ac_type', 'Split')
    status = request.form.get('status', 'Active')

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE pcb_models 
            SET brand_id=%s, model_number=%s, pcb_number=%s, ac_type=%s, status=%s
            WHERE id=%s
        """, (brand_id, model_number, pcb_number, ac_type, status, id))

        conn.commit()
        cursor.close()
        conn.close()

        return redirect(url_for('pcb_models'))

    except Exception as e:
        print("\n--- UPDATE PCB MODEL ERROR ---", e, "\n")
        return str(e)
# ---------------- DELETE PCB MODEL ----------------
@app.route('/delete_pcb_model/<int:id>')
def delete_pcb_model(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM pcb_models WHERE id=%s", (id,))

        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        return str(e)

    return redirect(url_for('pcb_models'))

# ---------------- PCB COMPANIES ----------------
@app.route('/pcb_companies')
def pcb_companies():

    if 'user' not in session:
        return redirect(url_for('login'))

    pcb_companies = []

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT *
            FROM pcb_companies
            ORDER BY id DESC
        """)

        pcb_companies = cursor.fetchall()

        cursor.close()
        conn.close()

    except Exception as e:
        print("DB ERROR (PCB Companies):", e)

    return render_template(
        "admin/pcb_companies.html",
        pcb_companies=pcb_companies
    )
    
    # ---------------- ADD PCB COMPANY ----------------
@app.route('/add_pcb_company')
def add_pcb_company():

    if 'user' not in session:
        return redirect(url_for('login'))

    return render_template("admin/add_pcb_company.html")

# ---------------- SAVE PCB COMPANY ----------------
@app.route('/save_pcb_company', methods=['POST'])
def save_pcb_company():

    if 'user' not in session:
        return redirect(url_for('login'))

    name = request.form['name']
    status = request.form['status']

    logo_name = ""

    if 'logo' in request.files:

        logo = request.files['logo']

        if logo.filename != "":

            logo_name = secure_filename(logo.filename)

            upload_path = os.path.join(
                app.static_folder,
                "uploads",
                "pcb_companies",
                logo_name
            )

            logo.save(upload_path)

    try:

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO pcb_companies
            (
                name,
                logo,
                status
            )
            VALUES
            (%s,%s,%s)
        """, (
            name,
            logo_name,
            status
        ))

        conn.commit()

        cursor.close()
        conn.close()

    except Exception as e:
        return str(e)

    return redirect(url_for('pcb_companies'))
# ---------------- EDIT PCB COMPANY ----------------
@app.route('/edit_pcb_company/<int:id>')
def edit_pcb_company(id):

    if 'user' not in session:
        return redirect(url_for('login'))

    try:

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM pcb_companies WHERE id=%s",
            (id,)
        )

        company = cursor.fetchone()

        cursor.close()
        conn.close()

    except Exception as e:
        return str(e)

    return render_template(
        "admin/edit_pcb_company.html",
        company=company
    )
    
    # ---------------- UPDATE PCB COMPANY ----------------
@app.route('/update_pcb_company/<int:id>', methods=['POST'])
def update_pcb_company(id):

    if 'user' not in session:
        return redirect(url_for('login'))

    name = request.form['name']
    status = request.form['status']

    try:

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Existing Logo
        cursor.execute(
            "SELECT logo FROM pcb_companies WHERE id=%s",
            (id,)
        )

        company = cursor.fetchone()

        logo_name = company['logo']

        # New Logo Upload
        if 'logo' in request.files:

            logo = request.files['logo']

            if logo.filename != "":

                logo_name = secure_filename(logo.filename)

                upload_path = os.path.join(
                    app.static_folder,
                    "uploads",
                    "pcb_companies",
                    logo_name
                )

                logo.save(upload_path)

        cursor = conn.cursor()

        cursor.execute("""
            UPDATE pcb_companies
            SET
                name=%s,
                logo=%s,
                status=%s
            WHERE id=%s
        """, (
            name,
            logo_name,
            status,
            id
        ))

        conn.commit()

        cursor.close()
        conn.close()

    except Exception as e:
        return str(e)

    return redirect(url_for('pcb_companies'))
# ---------------- DELETE PCB COMPANY ----------------
@app.route('/delete_pcb_company/<int:id>')
def delete_pcb_company(id):

    if 'user' not in session:
        return redirect(url_for('login'))

    try:

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM pcb_companies WHERE id=%s",
            (id,)
        )

        conn.commit()

        cursor.close()
        conn.close()

    except Exception as e:
        return str(e)

    return redirect(url_for('pcb_companies'))

# ---------------- PCB ERROR CODES ----------------
@app.route('/pcb_error_codes')
def pcb_error_codes():

    if 'user' not in session:
        return redirect(url_for('login'))

    pcb_error_codes = []

    try:

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                pec.*,
                pc.name AS company_name,
                pm.model_number
            FROM pcb_error_codes pec
            INNER JOIN pcb_companies pc
                ON pec.pcb_company_id = pc.id
            INNER JOIN pcb_models pm
                ON pec.pcb_model_id = pm.id
            ORDER BY pec.id DESC
        """)

        pcb_error_codes = cursor.fetchall()

        cursor.close()
        conn.close()

    except Exception as e:
        print("DB ERROR (PCB Error Codes):", e)

    return render_template(
        "admin/pcb_error_codes.html",
        pcb_error_codes=pcb_error_codes
    )
    # ---------------- ADD PCB ERROR CODE ----------------
@app.route('/add_pcb_error_code')
def add_pcb_error_code():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # PCB Companies
    cursor.execute("""
        SELECT id, name
        FROM pcb_companies
        WHERE status='Active'
        ORDER BY name ASC
    """)
    companies = cursor.fetchall()

    # PCB Models
    cursor.execute("""
        SELECT id, model_number
        FROM pcb_models
        WHERE status='Active'
        ORDER BY model_number ASC
    """)
    models = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "admin/add_pcb_error_code.html",
        companies=companies,
        models=models
    )
    # ---------------- SAVE PCB ERROR CODE ----------------
@app.route('/save_pcb_error_code', methods=['POST'])
def save_pcb_error_code():

    if 'user' not in session:
        return redirect(url_for('login'))

    pcb_company_id = request.form['pcb_company_id']
    pcb_model_id = request.form['pcb_model_id']
    error_code = request.form['error_code']
    error_name = request.form['error_name']
    description = request.form['description']
    solution = request.form['solution']
    status = request.form['status']

    try:

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
            VALUES
            (%s,%s,%s,%s,%s,%s,%s)
        """,(
            pcb_company_id,
            pcb_model_id,
            error_code,
            error_name,
            description,
            solution,
            status
        ))

        conn.commit()

        cursor.close()
        conn.close()

    except Exception as e:
        return str(e)

    return redirect(url_for('pcb_error_codes'))

# ---------------- EDIT PCB ERROR CODE ----------------
@app.route('/edit_pcb_error_code/<int:id>')
def edit_pcb_error_code(id):

    if 'user' not in session:
        return redirect(url_for('login'))

    try:

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Current PCB Error Code
        cursor.execute("""
            SELECT *
            FROM pcb_error_codes
            WHERE id=%s
        """, (id,))

        error = cursor.fetchone()

        # PCB Companies
        cursor.execute("""
            SELECT id,name
            FROM pcb_companies
            WHERE status='Active'
            ORDER BY name
        """)

        companies = cursor.fetchall()

        # PCB Models
        cursor.execute("""
            SELECT id,model_number
            FROM pcb_models
            WHERE status='Active'
            ORDER BY model_number
        """)

        models = cursor.fetchall()

        cursor.close()
        conn.close()

    except Exception as e:
        return str(e)

    return render_template(
        "admin/edit_pcb_error_code.html",
        error=error,
        companies=companies,
        models=models
    )
    
    # ---------------- UPDATE PCB ERROR CODE ----------------
@app.route('/update_pcb_error_code/<int:id>', methods=['POST'])
def update_pcb_error_code(id):

    if 'user' not in session:
        return redirect(url_for('login'))

    pcb_company_id = request.form['pcb_company_id']
    pcb_model_id = request.form['pcb_model_id']
    error_code = request.form['error_code']
    error_name = request.form['error_name']
    description = request.form['description']
    solution = request.form['solution']
    status = request.form['status']

    try:

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE pcb_error_codes
            SET
                pcb_company_id=%s,
                pcb_model_id=%s,
                error_code=%s,
                error_name=%s,
                description=%s,
                solution=%s,
                status=%s
            WHERE id=%s
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

    except Exception as e:
        return str(e)

    return redirect(url_for('pcb_error_codes'))

# ---------------- DELETE PCB ERROR CODE ----------------
@app.route('/delete_pcb_error_code/<int:id>')
def delete_pcb_error_code(id):

    if 'user' not in session:
        return redirect(url_for('login'))

    try:

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM pcb_error_codes WHERE id=%s",
            (id,)
        )

        conn.commit()

        cursor.close()
        conn.close()

    except Exception as e:
        return str(e)

    return redirect(url_for('pcb_error_codes'))

# ---------------- ADD USER ----------------
@app.route('/add_user')
def add_user():
    if 'user' not in session:
        return redirect(url_for('login'))

    return render_template('admin/add_user.html')


# ---------------- SAVE USER ----------------
@app.route('/save_user', methods=['POST'])
def save_user():
    if 'user' not in session:
        return redirect(url_for('login'))

    username = request.form['username']
    password = request.form['password']
    role = request.form['role']

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO users(username,password,role)
            VALUES(%s,%s,%s)
        """,(username,password,role))

        conn.commit()

        cursor.close()
        conn.close()

    except Exception as e:
        return str(e)

    return redirect(url_for('users'))

# ---------------- UPDATE USER ----------------
@app.route('/update_user/<int:id>', methods=['POST'])
def update_user(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    username = request.form['username']
    password = request.form['password']
    role = request.form['role']

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users
            SET username=%s, password=%s, role=%s
            WHERE id=%s
        """, (username, password, role, id))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        return str(e)

    return redirect(url_for('users'))

# ---------------- DELETE USER ----------------
@app.route('/delete_user/<int:id>')
def delete_user(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM users WHERE id=%s", (id,))
        conn.commit()

        cursor.close()
        conn.close()

    except Exception as e:
        return str(e)

    return redirect(url_for('users'))

# ---------------- REPORTS & ANALYTICS INTEGRATED ----------------
@app.route('/reports')
def reports():
    if 'user' not in session:
        return redirect(url_for('login'))

    reports_data = []
    status_data = []
    pcb_data = []
    technician_data = []

    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')
    status_filter = request.args.get('status', '')

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # 1. Reports Table Query with Technician Name JOIN
        query = """
            SELECT r.*, t.name as technician_name 
            FROM reports r
            LEFT JOIN technicians t ON r.technician_id = t.id
            WHERE 1=1
        """
        params = []

        if from_date:
            query += " AND DATE(r.created_at) >= %s"
            params.append(from_date)
            
        if to_date:
            query += " AND DATE(r.created_at) <= %s"
            params.append(to_date)

        if status_filter:
            query += " AND r.status = %s"
            params.append(status_filter)

        query += " ORDER BY r.id DESC"
        cursor.execute(query, tuple(params))
        reports_data = cursor.fetchall()

        # 2. Status Wise Count for Chart
        cursor.execute("SELECT status, COUNT(*) as total FROM repair_jobs GROUP BY status")
        status_data = cursor.fetchall()

        # 3. PCB Company Wise Count for Chart
        cursor.execute("SELECT pcb_company, COUNT(*) as total FROM repair_jobs GROUP BY pcb_company")
        pcb_data = cursor.fetchall()

        # 4. Technician City Wise Count for Chart
        cursor.execute("SELECT city, COUNT(*) as total FROM technicians GROUP BY city")
        technician_data = cursor.fetchall()

        cursor.close()
        conn.close()

    except Exception as e:
        print("Reports Route Error:", e)

    return render_template(
        "admin/reports.html",
        reports=reports_data,
        status_data=status_data,
        pcb_data=pcb_data,
        technician_data=technician_data
    )
# ---------------- REPORT ADD ----------------

@app.route('/add_report')
def add_report():
    # Check user login session
    if 'user' not in session:
        return redirect(url_for('login'))

    technicians = []
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch technician list to populate the dropdown
        cursor.execute("SELECT id, name FROM technicians")
        technicians = cursor.fetchall()

        cursor.close()
        conn.close()
    except Exception as e:
        print("Error fetching technicians for add report:", e)

    return render_template("admin/add_report.html", technicians=technicians)


# ---------------- REPORT SAVE ----------------

@app.route('/save_report', methods=['POST'])
def save_report():
    # Check user login session
    if 'user' not in session:
        return redirect(url_for('login'))

    # Safe Form extraction using .get()
    customer_name = request.form.get('customer_name', '')
    phone = request.form.get('phone', '')
    technician_id = request.form.get('technician_id')
    complaint = request.form.get('complaint', '')
    status = request.form.get('status', '')

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Insert new report record into database
        cursor.execute("""
            INSERT INTO reports
            (customer_name, phone, technician_id, complaint, status)
            VALUES (%s, %s, %s, %s, %s)
        """, (customer_name, phone, technician_id, complaint, status))

        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        print("Error saving report:", e)
        return str(e)

    return redirect(url_for('reports'))


# ---------------- REPORT EDIT ----------------

@app.route('/edit_report/<int:id>')
def edit_report(id):
    # Check user login session
    if 'user' not in session:
        return redirect(url_for('login'))

    report = None
    technicians_data = []

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch single report record by ID
        cursor.execute("SELECT * FROM reports WHERE id=%s", (id,))
        report = cursor.fetchone()

        # Fetch active technicians list
        cursor.execute("SELECT id, name FROM technicians")
        technicians_data = cursor.fetchall()

        cursor.close()
        conn.close()

    except Exception as e:
        print("Error fetching edit report data:", e)

    return render_template(
        "admin/edit_report.html",
        report=report,
        technicians=technicians_data
    )


# ---------------- REPORT UPDATE ----------------

@app.route('/update_report/<int:id>', methods=['POST'])
def update_report(id):
    # Check user login session
    if 'user' not in session:
        return redirect(url_for('login'))

    # Safe Form extraction using .get()
    customer_name = request.form.get('customer_name', '')
    phone = request.form.get('phone', '')
    technician_id = request.form.get('technician_id')
    complaint = request.form.get('complaint', '')
    status = request.form.get('status', '')

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Update report record by ID
        cursor.execute("""
            UPDATE reports
            SET customer_name=%s,
                phone=%s,
                technician_id=%s,
                complaint=%s,
                status=%s
            WHERE id=%s
        """, (customer_name, phone, technician_id, complaint, status, id))

        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        print("Error updating report:", e)
        return str(e)

    return redirect(url_for('reports'))


# ---------------- REPORT DELETE ----------------

@app.route('/delete_report/<int:id>')
def delete_report(id):
    # Check user login session
    if 'user' not in session:
        return redirect(url_for('login'))

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Delete report record by ID
        cursor.execute("DELETE FROM reports WHERE id=%s", (id,))

        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        print("Error deleting report:", e)
        return str(e)

    return redirect(url_for('reports'))
# ---------------- REPORT CHART DATA ----------------

@app.route('/report_chart_data')
def report_chart_data():

    if 'user' not in session:
        return redirect(url_for('login'))


    conn = get_connection()
    cursor = conn.cursor(dictionary=True)


    # Status wise repair jobs
    cursor.execute("""
        SELECT status, COUNT(*) as total
        FROM repair_jobs
        GROUP BY status
    """)
    status_data = cursor.fetchall()



    # PCB company wise repair jobs
    cursor.execute("""
        SELECT pcb_company, COUNT(*) as total
        FROM repair_jobs
        GROUP BY pcb_company
    """)
    pcb_data = cursor.fetchall()



    # Technician count city wise
    cursor.execute("""
        SELECT city, COUNT(*) as total
        FROM technicians
        GROUP BY city
    """)
    technician_data = cursor.fetchall()



    cursor.close()
    conn.close()


    return render_template(
        'admin/report_charts.html',
        status_data=status_data,
        pcb_data=pcb_data,
        technician_data=technician_data
    )

# ---------------- TECHNICIAN LIST ----------------
@app.route('/technicians')
@login_required
def technicians():
    conn = None
    technicians_list = []
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM technicians ORDER BY id DESC")
        technicians_list = cursor.fetchall()
        cursor.close()
    except Exception as e:
        flash(f"Error fetching technicians: {e}", "danger")
        technicians_list = []
    finally:
        if conn:
            conn.close()

    return render_template(
        "admin/technician.html",
        technicians=technicians_list
    )


# ---------------- ADD TECHNICIAN ----------------
@app.route('/add_technician')
@login_required
def add_technician():
    return render_template("admin/add_technician.html")


# ---------------- SAVE TECHNICIAN ----------------
@app.route('/save_technician', methods=['POST'])
@login_required
def save_technician():
    name = request.form.get('name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    city = request.form.get('city')
    state = request.form.get('state')
    shop_name = request.form.get('shop_name')
    experience = request.form.get('experience')
    status = request.form.get('status', 'Active')
    is_email_verified = request.form.get('is_email_verified', 0)
    is_approved = request.form.get('is_approved', 0)
    marketing_consent = request.form.get('marketing_consent', 0)

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO technicians
            (
                name, email, phone, city, state, shop_name, 
                experience, status, is_email_verified, 
                is_approved, marketing_consent
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            name, email, phone, city, state, shop_name,
            experience, status, is_email_verified,
            is_approved, marketing_consent
        ))

        conn.commit()
        cursor.close()
        flash("Technician added successfully!", "success")

    except Exception as e:
        if conn:
            conn.rollback()
        flash(f"Failed to save technician: {e}", "danger")
    finally:
        if conn:
            conn.close()

    return redirect(url_for('technicians'))


# ---------------- EDIT TECHNICIAN ----------------
@app.route('/edit_technician/<int:id>')
@login_required
def edit_technician(id):
    conn = None
    technician = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM technicians WHERE id=%s", (id,))
        technician = cursor.fetchone()
        cursor.close()

        if not technician:
            flash("Technician not found!", "warning")
            return redirect(url_for('technicians'))

    except Exception as e:
        flash(f"Error loading technician details: {e}", "danger")
        return redirect(url_for('technicians'))
    finally:
        if conn:
            conn.close()

    return render_template(
        "admin/edit_technician.html",
        technician=technician
    )


# ---------------- UPDATE TECHNICIAN ----------------
@app.route('/update_technician/<int:id>', methods=['POST'])
@login_required
def update_technician(id):
    name = request.form.get('name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    city = request.form.get('city')
    state = request.form.get('state')
    shop_name = request.form.get('shop_name')
    experience = request.form.get('experience')
    status = request.form.get('status', 'Active')

    # જો Status Active પસંદ કરો તો is_approved ને ૧ કરવું અને Inactive પસંદ કરો તો ૦ કરવું
    is_approved = 1 if status == 'Active' else 0

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE technicians
            SET
                name=%s,
                email=%s,
                phone=%s,
                city=%s,
                state=%s,
                shop_name=%s,
                experience=%s,
                status=%s,
                is_approved=%s
            WHERE id=%s
        """, (
            name, email, phone, city, state, shop_name, experience, status, is_approved, id
        ))

        conn.commit()
        cursor.close()
        flash("Technician updated successfully!", "success")

    except Exception as e:
        if conn:
            conn.rollback()
        flash(f"Failed to update technician: {e}", "danger")
    finally:
        if conn:
            conn.close()

    return redirect(url_for('technicians'))

# ---------------- DELETE TECHNICIAN ----------------
@app.route('/delete_technician/<int:id>', methods=['GET', 'POST'])
@login_required
def delete_technician(id):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM technicians WHERE id=%s", (id,))
        conn.commit()
        cursor.close()
        flash("Technician deleted successfully!", "success")

    except Exception as e:
        if conn:
            conn.rollback()
        flash(f"Failed to delete technician: {e}", "danger")
    finally:
        if conn:
            conn.close()

    return redirect(url_for('technicians'))


# ---------------- TECHNICIAN APPROVAL LIST ----------------
@app.route('/technician_approval')
@login_required
def technician_approval():
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '').strip()

    conn = None
    technicians_list = []
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT id, name, email, phone, city, state, is_approved
            FROM technicians
            WHERE 1=1
        """
        params = []

        if search:
            query += " AND (name LIKE %s OR city LIKE %s OR state LIKE %s)"
            keyword = f"%{search}%"
            params.extend([keyword, keyword, keyword])

        if status == "Approved":
            query += " AND is_approved=%s"
            params.append(1)
        elif status == "Not Approved":
            query += " AND is_approved=%s"
            params.append(0)

        query += " ORDER BY id DESC"

        cursor.execute(query, tuple(params))
        technicians_list = cursor.fetchall()

        for tech in technicians_list:
            tech["is_approved"] = int(tech["is_approved"])

        cursor.close()
    except Exception as e:
        flash(f"Error loading approvals: {e}", "danger")
    finally:
        if conn:
            conn.close()

    return render_template(
        "admin/technician_approval.html",
        technicians=technicians_list
    )


# ---------------- APPROVE TECHNICIAN ----------------
@app.route('/approve_technician/<int:id>')
@login_required
def approve_technician(id):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE technicians SET is_approved = 1 WHERE id = %s", (id,))
        conn.commit()
        cursor.close()
        flash("Technician approved successfully!", "success")
    except Exception as e:
        if conn:
            conn.rollback()
        flash(f"Approval failed: {e}", "danger")
    finally:
        if conn:
            conn.close()

    return redirect(url_for('technician_approval'))


# ---------------- REJECT TECHNICIAN ----------------
@app.route('/reject_technician/<int:id>')
@login_required
def reject_technician(id):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE technicians SET is_approved = 0 WHERE id = %s", (id,))
        conn.commit()
        cursor.close()
        flash("Technician request rejected.", "info")
    except Exception as e:
        if conn:
            conn.rollback()
        flash(f"Rejection failed: {e}", "danger")
    finally:
        if conn:
            conn.close()

    return redirect(url_for('technician_approval'))


# ---------------- EXPORT TECHNICIANS CSV ----------------
@app.route('/export_technicians')
@login_required
def export_technicians():
    conn = None
    technicians_list = []
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, name, email, phone, city, state,
            CASE WHEN is_approved = 1 THEN 'Approved' ELSE 'Not Approved' END AS status
            FROM technicians
            ORDER BY id DESC
        """)
        technicians_list = cursor.fetchall()
        cursor.close()
    except Exception as e:
        flash(f"Error generating CSV: {e}", "danger")
        return redirect(url_for('technicians'))
    finally:
        if conn:
            conn.close()

    class Echo:
        def write(self, value):
            return value

    def generate():
        data = csv.writer(Echo())
        yield data.writerow(["ID", "Name", "Email", "Phone", "City", "State", "Status"])
        for tech in technicians_list:
            yield data.writerow([
                tech["id"], tech["name"], tech["email"],
                tech["phone"], tech["city"], tech["state"], tech["status"]
            ])

    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=technicians.csv"}
    )
   # ---------------- REPAIR JOB LIST ----------------
@app.route('/repair_jobs')
def repair_jobs():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)

    cursor.execute("""
        SELECT
            repair_jobs.*,
            technicians.name AS technician_name,
            technicians.phone AS technician_phone
        FROM repair_jobs
        LEFT JOIN technicians ON repair_jobs.technician_id = technicians.id
        ORDER BY repair_jobs.id DESC
    """)

    jobs_list = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template(
        "admin/repair_jobs.html",
        repair_jobs=jobs_list
    )


# ---------------- ADD REPAIR JOB (VIEW FORM) ----------------
@app.route('/add_repair_job')
def add_repair_job():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)

    cursor.execute("""
        SELECT id, name, phone
        FROM technicians
        WHERE is_approved = 1
        ORDER BY name ASC
    """)

    technicians = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template(
        "admin/add_repair_job.html",
        technicians=technicians
    )


# ---------------- SAVE REPAIR JOB ----------------
@app.route('/save_repair_job', methods=['POST'])
def save_repair_job():
    if 'user' not in session:
        return redirect(url_for('login'))

    technician_id = request.form.get('technician_id') or None
    phone = request.form.get('phone') or None
    pcb_company = request.form.get('pcb_company')
    pcb_model = request.form.get('pcb_model')
    ac_brand = request.form.get('ac_brand')
    reported_fault = request.form.get('reported_fault')
    diagnosis = request.form.get('diagnosis')
    work_done = request.form.get('work_done')
    parts_replaced = request.form.get('parts_replaced')
    assigned_staff = request.form.get('assigned_staff')
    status = request.form.get('status', 'Received')
    received_date = request.form.get('received_date') or None
    expected_date = request.form.get('expected_date') or None
    completed_date = request.form.get('completed_date') or None
    remarks = request.form.get('remarks')

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO repair_jobs
            (
                technician_id,
                phone,
                pcb_company,
                pcb_model,
                ac_brand,
                reported_fault,
                diagnosis,
                work_done,
                parts_replaced,
                assigned_staff,
                status,
                received_date,
                expected_date,
                completed_date,
                remarks
            )
            VALUES
            (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            technician_id,
            phone,
            pcb_company,
            pcb_model,
            ac_brand,
            reported_fault,
            diagnosis,
            work_done,
            parts_replaced,
            assigned_staff,
            status,
            received_date,
            expected_date,
            completed_date,
            remarks
        ))

        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        return f"<pre>{traceback.format_exc()}</pre>"

    return redirect(url_for('repair_jobs'))


# ---------------- EDIT REPAIR JOB (VIEW FORM) ----------------
@app.route('/edit_repair_job/<int:job_id>')
def edit_repair_job(job_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True, buffered=True)
        cursor.execute("SELECT * FROM repair_jobs WHERE id = %s", (job_id,))
        job = cursor.fetchone()

        cursor.execute("SELECT id, name, phone FROM technicians WHERE is_approved = 1 ORDER BY name ASC")
        technicians = cursor.fetchall()
        cursor.close()
        conn.close()

        if not job:
            return "Job Not Found", 404

        return render_template("admin/edit_repair_job.html", job=job, technicians=technicians)
    except Exception as e:
        return f"<pre>{traceback.format_exc()}</pre>"


# ---------------- UPDATE REPAIR JOB (SAVE CHANGES) ----------------
@app.route('/update_repair_job/<int:job_id>', methods=['POST'])
def update_repair_job(job_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    try:
        tech_id = request.form.get('technician_id') or None
        phone = request.form.get('phone') or None
        pcb_company = request.form.get('pcb_company')
        pcb_model = request.form.get('pcb_model')
        ac_brand = request.form.get('ac_brand')
        reported_fault = request.form.get('reported_fault')
        diagnosis = request.form.get('diagnosis')
        work_done = request.form.get('work_done')
        parts_replaced = request.form.get('parts_replaced')
        assigned_staff = request.form.get('assigned_staff')
        status = request.form.get('status')
        received_date = request.form.get('received_date') or None
        expected_date = request.form.get('expected_date') or None
        completed_date = request.form.get('completed_date') or None
        remarks = request.form.get('remarks')

        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
            UPDATE repair_jobs 
            SET technician_id=%s, phone=%s, pcb_company=%s, pcb_model=%s, ac_brand=%s, 
                reported_fault=%s, diagnosis=%s, work_done=%s, parts_replaced=%s, 
                assigned_staff=%s, status=%s, received_date=%s, expected_date=%s, 
                completed_date=%s, remarks=%s 
            WHERE id=%s
        """
        values = (tech_id, phone, pcb_company, pcb_model, ac_brand, reported_fault, 
                  diagnosis, work_done, parts_replaced, assigned_staff, status, 
                  received_date, expected_date, completed_date, remarks, job_id)
        
        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('repair_jobs'))
    except Exception as e:
        return f"<pre>{traceback.format_exc()}</pre>"


# ---------------- DELETE REPAIR JOB ROUTE ----------------
@app.route('/delete_repair_job/<int:job_id>')
def delete_repair_job(job_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM repair_jobs WHERE id = %s", (job_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('repair_jobs'))
    except Exception as e:
        return f"<pre>{traceback.format_exc()}</pre>"


# ---------------- UPDATE STATUS REPAIR JOBS ----------------
@app.route('/update_status/<int:job_id>', methods=['GET'])
def update_status(job_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True, buffered=True)
        cursor.execute("SELECT * FROM repair_jobs WHERE id = %s", (job_id,))
        job = cursor.fetchone()
        cursor.close()
        conn.close()
        if job:
            return render_template('admin/update_status.html', job=job)
        return "Job Not Found", 404
    except Exception as e:
        return str(e)
# ---------------- SETTINGS (OWNER WHATSAPP & APP CONFIG) ----------------
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    # Check user login session
    # Redirect to login page if user is not in session
    if 'user' not in session:
        return redirect(url_for('login'))

    # Open database connection
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Handle form submission (POST request)
    if request.method == 'POST':
        
        # 1. Handle WhatsApp Configuration Form
        if 'owner_whatsapp_number' in request.form or 'whatsapp' in request.form:
            # Fetch WhatsApp number and default message from form
            whatsapp = request.form.get('owner_whatsapp_number') or request.form.get('whatsapp')
            default_msg = request.form.get('whatsapp_default_message', '')

            # Insert or Update WhatsApp Number
            if whatsapp:
                cursor.execute("""
                    INSERT INTO settings (`key`, `value`) 
                    VALUES ('owner_whatsapp_number', %s) 
                    ON DUPLICATE KEY UPDATE `value`=%s
                """, (whatsapp, whatsapp))

            # Insert or Update Default Message
            if default_msg:
                cursor.execute("""
                    INSERT INTO settings (`key`, `value`) 
                    VALUES ('whatsapp_default_message', %s) 
                    ON DUPLICATE KEY UPDATE `value`=%s
                """, (default_msg, default_msg))

        # 2. Handle General App Config Form
        elif 'app_support_email' in request.form:
            support_email = request.form.get('app_support_email')
            otp_expiry = request.form.get('otp_expiry_minutes')

            # Insert or Update Support Email
            if support_email:
                cursor.execute("""
                    INSERT INTO settings (`key`, `value`) 
                    VALUES ('app_support_email', %s) 
                    ON DUPLICATE KEY UPDATE `value`=%s
                """, (support_email, support_email))

            # Insert or Update OTP Expiry Time
            if otp_expiry:
                cursor.execute("""
                    INSERT INTO settings (`key`, `value`) 
                    VALUES ('otp_expiry_minutes', %s) 
                    ON DUPLICATE KEY UPDATE `value`=%s
                """, (otp_expiry, otp_expiry))

        # Commit database changes
        conn.commit()

    # Fetch all settings from database and convert to dictionary
    cursor.execute("SELECT `key`, `value` FROM settings")
    rows = cursor.fetchall()

    # Create dynamic dictionary: {'owner_whatsapp_number': '918866147354', ...}
    settings_dict = {row['key']: row['value'] for row in rows}

    # Close cursor and database connection
    cursor.close()
    conn.close()

    # Render template with settings dictionary and fallback whatsapp variable
    return render_template(
        'admin/settings.html',
        settings=settings_dict,
        whatsapp=settings_dict.get('owner_whatsapp_number', '')
    )
    # ---------------- REPAIR STATUS HISTORY ----------------

@app.route('/repair_history/<int:repair_job_id>')
def repair_history(repair_job_id):

    # Login check
    if 'user' not in session:
        return redirect(url_for('login'))


    # Database connection
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)


    # Particular repair job ni badhi status history fetch karo
    cursor.execute("""
        SELECT *
        FROM repair_status_history
        WHERE repair_job_id=%s
        ORDER BY id DESC
    """, (repair_job_id,))


    history = cursor.fetchall()


    # Close connection
    cursor.close()
    conn.close()


    # History page open karo
    return render_template(
        'admin/repair_history.html',
        history=history,
        repair_job_id=repair_job_id
    )
    
    # ---------------- STAFF USERS ----------------

@app.route('/staff_users')
def staff_users():

    # Login check
    if 'user' not in session:
        return redirect(url_for('login'))


    # Database connection
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)


    # Only staff users fetch
    cursor.execute("""
        SELECT *
        FROM users
        WHERE role='staff'
        ORDER BY id DESC
    """)


    staff = cursor.fetchall()


    # Close connection
    cursor.close()
    conn.close()


    return render_template(
        'admin/staff_users.html',
        staff=staff
    )
    
    # ---------------- ROLES & PERMISSIONS ----------------

@app.route('/roles')
def roles():

    # Login check
    if 'user' not in session:
        return redirect(url_for('login'))


    conn = get_connection()
    cursor = conn.cursor(dictionary=True)


    # Fetch all roles
    cursor.execute("""
        SELECT *
        FROM roles
        ORDER BY id DESC
    """)

    roles = cursor.fetchall()


    cursor.close()
    conn.close()


    return render_template(
        'admin/roles.html',
        roles=roles
    )
    
    # ---------------- EDIT USER PAGE (ડેટાબેઝ એરર ફિક્સ કરવા માટે VIP કર્સર) ----------------
@app.route('/edit_user/<int:id>')
def edit_user(id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True) # dictionary=True હોવું બહુ જરૂરી છે
        cursor.execute("SELECT * FROM users WHERE id=%s", (id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not user:
            return "User Not Found", 404
            
        return render_template("admin/edit_user.html", user=user)
    except Exception as e:
        return str(e)

    
# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
# ----------------- EMAIL OTP SENDER FUNCTION -----------------
def send_otp_email(to_email, otp_code):
    """
    Sends a 6-digit OTP code to technician's email using SMTP (.md Section 3 & 8)
    """
    sender_email = "your_email@gmail.com"       # Your Email ID
    sender_password = "your_app_password"       # Gmail App Password

    subject = "Your Email Verification OTP - AC PCB Repair Portal"
    
    body = f"""Hello Technician,

Your 6-digit OTP for email verification on AC PCB Repair Service Portal is:

========================
        {otp_code}
========================

This OTP is valid for 10 minutes. Please do not share it with anyone.

Regards,
AC PCB Repair Team
"""

    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print(f"[SUCCESS] OTP Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send OTP Email: {e}")
        return False


# ---------------- USER SIDE ROUTES (.MD COMPLIANT 1 TO 10) ----------------

# 1. USER HOME PORTAL
@app.route('/')
@app.route('/user')
def user_home():
    return render_template("user/index.html")


# 2. PUBLIC AC ERROR CODES SEARCH (NO LOGIN) - ALIASED ROUTES TO PREVENT 404
@app.route('/user/ac_codes')
@app.route('/user/ac_error_codes')
def user_ac_codes():
    brand_id = request.args.get('brand_id', '')
    search = request.args.get('search', request.args.get('query', '')).strip()
    
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True, buffered=True)
        
        query = """
            SELECT ac_error_codes.*, brands.name AS brand_name 
            FROM ac_error_codes 
            LEFT JOIN brands ON ac_error_codes.brand_id = brands.id 
            WHERE 1=1
        """
        params = []
        
        if brand_id:
            query += " AND ac_error_codes.brand_id = %s"
            params.append(brand_id)
            
        if search:
            query += " AND (ac_error_codes.error_code LIKE %s OR ac_error_codes.error_name LIKE %s OR ac_error_codes.description LIKE %s)"
            p = f"%{search}%"
            params.extend([p, p, p])
            
        query += " ORDER BY ac_error_codes.id DESC"
        cursor.execute(query, tuple(params))
        error_codes = cursor.fetchall()
        
        cursor.execute("SELECT id, name FROM brands ORDER BY name ASC")
        brands = cursor.fetchall()
        
        cursor.close()
        conn.close()
        return render_template("user/ac_codes.html", error_codes=error_codes, brands=brands)
    except Exception as e:
        print("AC Error Codes Route Log Error:", e)
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
        return render_template("user/ac_codes.html", error_codes=[], brands=[])


# 3. PUBLIC PCB ERROR CODES & MODELS (.MD COMPLIANT) - ALIASED ROUTES TO PREVENT 404
@app.route('/user/pcb_codes')
@app.route('/user/pcb_error_codes')
def user_pcb_codes():
    company_id = request.args.get('company_id', '')
    search_query = request.args.get('query', '').strip()
    
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True, buffered=True)
        
        # 1. Fetch PCB Companies for Filter Dropdown
        cursor.execute("SELECT id, name FROM pcb_companies ORDER BY name ASC")
        pcb_companies = cursor.fetchall()

        # 2. Fetch PCB Models
        query = """
            SELECT pcb_models.*, pcb_companies.name as company_name 
            FROM pcb_models 
            LEFT JOIN pcb_companies ON pcb_models.brand_id = pcb_companies.id 
            WHERE 1=1
        """
        params = []
        
        if company_id:
            query += " AND pcb_models.brand_id = %s"
            params.append(company_id)

        if search_query:
            query += " AND (pcb_models.model_name LIKE %s OR pcb_companies.name LIKE %s)"
            p = f"%{search_query}%"
            params.extend([p, p])
            
        query += " ORDER BY pcb_models.id DESC"
        cursor.execute(query, tuple(params))
        pcb_models = cursor.fetchall()
        
        # 3. Fetch Associated Error Codes for Each PCB Model
        for model in pcb_models:
            cursor.execute("""
                SELECT * FROM pcb_error_codes 
                WHERE pcb_model_id = %s 
                ORDER BY id DESC
            """, (model['id'],))
            model['error_codes'] = cursor.fetchall()
        
        # 4. Fetch Owner WhatsApp Number from Settings
        whatsapp_number = "918866147354"
        try:
            cursor.execute("SELECT `value` FROM settings WHERE `key`='owner_whatsapp_number'")
            row = cursor.fetchone()
            if row and row.get('value'):
                whatsapp_number = row['value']
        except Exception as e:
            print("WhatsApp Setting Fetch Error:", e)
        
        cursor.close()
        conn.close()
        
        return render_template(
            "user/pcb_codes.html", 
            pcb_models=pcb_models, 
            pcb_companies=pcb_companies, 
            whatsapp_number=whatsapp_number
        )

    except Exception as e:
        print("PCB Codes Route Log Error:", e)
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
        return render_template("user/pcb_codes.html", pcb_models=[], pcb_companies=[], whatsapp_number="918866147354")


# 4. TECHNICIAN REGISTER (GENERATES & SENDS EMAIL OTP)
@app.route('/user/register', methods=['GET', 'POST'])
def user_register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        shop_name = request.form.get('shop_name', '').strip()
        city = request.form.get('city', '').strip()
        state = request.form.get('state', '').strip()

        otp_code = str(random.randint(100000, 999999))
        expires_at = datetime.now() + timedelta(minutes=10)

        # Terminal Log for Demo Testing
        print("\n==========================================")
        print(f"  [REGISTER OTP] Email: {email} | OTP Code: {otp_code}")
        print("==========================================\n")

        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True, buffered=True)

            cursor.execute("SELECT id FROM technicians WHERE email=%s", (email,))
            existing_tech = cursor.fetchone()

            if not existing_tech:
                cursor.execute("""
                    INSERT INTO technicians (name, email, phone, shop_name, city, state, is_email_verified, is_approved)
                    VALUES (%s, %s, %s, %s, %s, %s, 0, 0)
                """, (name, email, phone, shop_name, city, state))
                conn.commit()

            cursor.execute("""
                INSERT INTO otps (email, code, expires_at, is_used)
                VALUES (%s, %s, %s, 0)
            """, (email, otp_code, expires_at))
            conn.commit()

            cursor.close()
            conn.close()

            try:
                send_otp_email(email, otp_code)
            except Exception as mail_err:
                print("Mail Send Warning:", mail_err)

            return redirect(url_for('user_verify_otp', email=email))

        except Exception as e:
            print("Register Route Error Log:", e)
            return f"Registration Error: {str(e)}"

    return render_template("user/register.html")


# 5. VERIFY EMAIL OTP (100% WORKING & DEMO BYPASS READY)
@app.route('/user/verify_otp', methods=['GET', 'POST'])
def user_verify_otp():
    email = request.args.get('email', request.form.get('email', '')).strip()

    if request.method == 'POST':
        otp_code = request.form.get('otp_code', '').strip()

        # ---------------- DEMO TESTING BYPASS (123456) ----------------
        if otp_code == "123456":
            try:
                conn = get_connection()
                cursor = conn.cursor(dictionary=True, buffered=True)
                
                if email:
                    cursor.execute("UPDATE technicians SET is_email_verified=1 WHERE email=%s", (email,))
                    conn.commit()
                    cursor.execute("SELECT * FROM technicians WHERE email=%s", (email,))
                    tech = cursor.fetchone()
                else:
                    cursor.execute("SELECT * FROM technicians ORDER BY id DESC LIMIT 1")
                    tech = cursor.fetchone()

                cursor.close()
                conn.close()

                if tech:
                    session['user'] = tech.get('name', 'Technician')
                    session['tech_id'] = tech.get('id', 0)
                    session['is_approved'] = tech.get('is_approved', 0)

                    if tech.get('is_approved'):
                        return redirect(url_for('user_track_repair'))
                    else:
                        return redirect(url_for('user_pending_approval'))
                
                return redirect(url_for('user_pending_approval'))

            except Exception as bypass_err:
                print("Bypass Exec Warning:", bypass_err)
                return redirect(url_for('user_pending_approval'))

        # ---------------- ORIGINAL DATABASE OTP CHECK ----------------
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True, buffered=True)

            cursor.execute("""
                SELECT * FROM otps 
                WHERE email=%s AND code=%s AND is_used=0 AND expires_at > NOW()
                ORDER BY id DESC LIMIT 1
            """, (email, otp_code))
            otp_record = cursor.fetchone()

            if otp_record:
                cursor.execute("UPDATE otps SET is_used=1 WHERE id=%s", (otp_record['id'],))
                cursor.execute("UPDATE technicians SET is_email_verified=1 WHERE email=%s", (email,))
                conn.commit()

                cursor.execute("SELECT * FROM technicians WHERE email=%s", (email,))
                tech = cursor.fetchone()

                cursor.close()
                conn.close()

                if tech:
                    session['user'] = tech['name']
                    session['tech_id'] = tech['id']
                    session['is_approved'] = tech['is_approved']

                    if tech['is_approved']:
                        return redirect(url_for('user_track_repair'))
                    else:
                        return redirect(url_for('user_pending_approval'))

            cursor.close()
            conn.close()
            return "Invalid or Expired OTP. Please try again or use '123456' for testing."

        except Exception as e:
            print("Verify OTP Route Error Log:", e)
            return f"Verification Error: {str(e)}"

    return render_template("user/verify_otp.html", email=email)

# 6. RESEND OTP (WITH TERMINAL LOGGING)
@app.route('/user/resend_otp')
def user_resend_otp():
    email = request.args.get('email', '')
    if email:
        otp_code = str(random.randint(100000, 999999))
        expires_at = datetime.now() + timedelta(minutes=10)

        # 📌 Terminal log for quick demo testing
        print("\n==========================================")
        print(f"  [DEMO RESEND OTP] Email: {email} | Code: {otp_code}")
        print("==========================================\n")

        try:
            conn = get_connection()
            cursor = conn.cursor(buffered=True)
            cursor.execute("""
                INSERT INTO otps (email, code, expires_at, is_used)
                VALUES (%s, %s, %s, 0)
            """, (email, otp_code, expires_at))
            conn.commit()
            cursor.close()
            conn.close()

            # Attempt email send
            send_otp_email(email, otp_code)
        except Exception as e:
            print("Resend OTP Database/Email Log Error:", e)

    return redirect(url_for('user_verify_otp', email=email))

# 7. PENDING APPROVAL SCREEN
@app.route('/user/pending_approval')
def user_pending_approval():
    return render_template("user/pending_approval.html")


# --------------------------------------------------------------------------------
# 8. APPROVED TECHNICIAN LIVE REPAIR TRACKING (.MD COMPLIANT)
# --------------------------------------------------------------------------------
@app.route('/user/track_repair')
def user_track_repair():
    search_query = request.args.get('query', '').strip()
    jobs = []
    
    # Default Settings
    owner_whatsapp = "8866147354"
    owner_phone = "8866147354"
    
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True, buffered=True)
        
        # 1. Fetch Dynamic Contact Settings
        cursor.execute("SELECT `key`, `value` FROM settings WHERE `key` IN ('owner_whatsapp_number', 'contact_phone')")
        setting_rows = cursor.fetchall()
        for s in setting_rows:
            if s['key'] == 'owner_whatsapp_number' and s['value']:
                owner_whatsapp = s['value']
            elif s['key'] == 'contact_phone' and s['value']:
                owner_phone = s['value']

        # 2. Perform Search by Job ID or Phone Number
        if search_query:
            # Clean ID (Removes #JOB-, JOB-, etc.)
            clean_id = search_query.upper().replace("#JOB-", "").replace("JOB-", "").replace("#", "").strip()
            
            if clean_id.isdigit() and len(clean_id) <= 6:
                # Query Search by Job ID
                query = """
                    SELECT 
                        repair_jobs.*, 
                        technicians.name AS technician_name, 
                        technicians.phone AS technician_phone
                    FROM repair_jobs
                    LEFT JOIN technicians ON repair_jobs.technician_id = technicians.id
                    WHERE repair_jobs.id = %s
                """
                cursor.execute(query, (int(clean_id),))
            else:
                # Query Search by Registered Phone Number
                query = """
                    SELECT 
                        repair_jobs.*, 
                        technicians.name AS technician_name, 
                        technicians.phone AS technician_phone
                    FROM repair_jobs
                    LEFT JOIN technicians ON repair_jobs.technician_id = technicians.id
                    WHERE repair_jobs.phone = %s 
                       OR technicians.phone = %s
                    ORDER BY repair_jobs.id DESC
                """
                cursor.execute(query, (search_query, search_query))
            
            jobs = cursor.fetchall()

        cursor.close()
        conn.close()
            
    except Exception as e:
        print("Track Repair Route Error Log:", e)
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
        
    return render_template(
        "user/track_repair.html", 
        jobs=jobs, 
        owner_whatsapp=owner_whatsapp, 
        owner_phone=owner_phone
    )


# 9. BROWSE PCB MODELS & COMPATIBILITY PAGE (.MD COMPLIANT)
@app.route('/user/pcb_models')
def user_pcb_models():
    """Renders PCB models catalog with filter functionality by company or model name."""
    search_query = request.args.get('query', '').strip()
    pcb_models_list = []
    
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True, buffered=True)
        
        if search_query:
            query = """
                SELECT * FROM pcb_models 
                WHERE pcb_company LIKE %s OR model_name LIKE %s OR board_type LIKE %s
                ORDER BY id DESC
            """
            search_param = f"%{search_query}%"
            cursor.execute(query, (search_param, search_param, search_param))
        else:
            query = "SELECT * FROM pcb_models ORDER BY id DESC"
            cursor.execute(query)
            
        pcb_models_list = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        print("PCB Models Route Error Log:", e)
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
            
    return render_template("user/pcb_models.html", pcb_models=pcb_models_list)


# 10. ABOUT & CONTACT US PAGE (.MD COMPLIANT)
@app.route('/user/contact')
def user_contact():
    """Renders shop location, business hours, and store contact info dynamically from database settings."""
    contact_info = {
        'shop_name': 'AC PCB Repairing Center',
        'contact_phone': '+91 88661 47354',
        'owner_whatsapp_number': '918866147354',
        'shop_address': 'Shop No. 12, Tech Market, Near Main Station',
        'business_hours': 'Monday - Saturday: 09:00 AM - 08:00 PM',
        'google_map_embed': ''
    }
    
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True, buffered=True)
        
        cursor.execute("SELECT `key`, `value` FROM settings")
        setting_rows = cursor.fetchall()
        for s in setting_rows:
            if s['key'] in contact_info and s['value']:
                contact_info[s['key']] = s['value']
                
        cursor.close()
        conn.close()
    except Exception as e:
        print("Contact Route Error Log:", e)
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
            
    return render_template("user/contact.html", contact=contact_info)

# ---------------- ESTIMATE BILL GENERATOR ROUTE (.MD COMPLIANT) ----------------
@app.route('/user/generate_estimate', methods=['GET', 'POST'])
def user_generate_estimate():
    if 'user' not in session:
        flash("Please verify your email with OTP to access Estimate Bill Generator.", "warning")
        return redirect(url_for('user_register'))

    tech_name = session.get('user', '')
    tech_id = session.get('tech_id', 0)
    tech_phone = ""

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True, buffered=True)
        if tech_id:
            cursor.execute("SELECT phone FROM technicians WHERE id = %s", (tech_id,))
            tech = cursor.fetchone()
            if tech and tech.get('phone'):
                tech_phone = tech['phone']
        cursor.close()
        conn.close()
    except Exception as e:
        print("Estimate Tech Details Fetch Error:", e)

    return render_template(
        "user/estimate.html",
        tech_name=tech_name,
        tech_phone=tech_phone
    )


# ---------------- SAVE REPAIR JOB STATUS & PUSH NOTIFICATION ----------------
@app.route('/save_status/<int:job_id>', methods=['POST'])
def save_status(job_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    new_status = request.form.get('status')
    note = request.form.get('note', '')
    changed_by = session.get('user', 'Admin')
    
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True, buffered=True)
        
        # 1. Update main repair job status
        cursor.execute("UPDATE repair_jobs SET status = %s WHERE id = %s", (new_status, job_id))
        
        # 2. Add entry in repair status history timeline
        cursor.execute("""
            INSERT INTO repair_status_history (repair_job_id, status, note, changed_by) 
            VALUES (%s, %s, %s, %s)
        """, (job_id, new_status, note, changed_by))
        
        # 3. Fetch Technician details and FCM Token for notification
        cursor.execute("""
            SELECT r.id, r.pcb_model, t.fcm_token, t.name 
            FROM repair_jobs r
            LEFT JOIN technicians t ON r.technician_id = t.id
            WHERE r.id = %s
        """, (job_id,))
        job_info = cursor.fetchone()

        conn.commit()
        cursor.close()
        conn.close()

        # 4. Trigger Push Notification to Technician Mobile/App
        if job_info and job_info.get('fcm_token'):
            fcm_token = job_info['fcm_token']
            pcb_model = job_info.get('pcb_model') or 'PCB Unit'
            
            title = f"Repair Status Updated: Job #{job_id}"
            body = f"Your job for {pcb_model} is now '{new_status}'."
            
            send_push_notification(
                fcm_token=fcm_token,
                title=title,
                body=body,
                data_payload={"job_id": str(job_id), "status": str(new_status)}
            )

        return redirect(url_for('repair_jobs'))

    except Exception as e:
        print("Save Status Exception:", e)
        return str(e)
# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)