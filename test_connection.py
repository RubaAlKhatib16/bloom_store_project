from db import get_db_connection

try:
    conn = get_db_connection()
    print("Connected Successfully 🎉")

except Exception as e:
    print("Error:", e)