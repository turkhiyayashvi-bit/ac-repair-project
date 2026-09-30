import mysql.connector

def get_connection():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",   # XAMPP default empty
        database="ac_pcb_repair"
    )
    return conn