import os

# ===============================
# Project Configuration
# ===============================

class Config:

    # Flask Secret Key
    SECRET_KEY = "ac_pcb_repair_secret_key"

    # Upload Folder
    UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")

    # MySQL Configuration
    MYSQL_HOST = "localhost"
    MYSQL_USER = "root"
    MYSQL_PASSWORD = ""
    MYSQL_DATABASE = "ac_pcb_repair"

    # OTP Expiry (Minutes)
    OTP_EXPIRY = 10

    # PDF Folder
    PDF_FOLDER = os.path.join(os.getcwd(), "uploads")

    # Allowed Upload Extensions
    ALLOWED_EXTENSIONS = {
        "png",
        "jpg",
        "jpeg",
        "pdf"
    }