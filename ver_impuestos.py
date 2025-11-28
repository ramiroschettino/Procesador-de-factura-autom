import pyodbc
import os
from dotenv import load_dotenv

load_dotenv()

DB_SERVER = os.getenv('DB_SERVER', '10.1.1.17')
DB_NAME = os.getenv('DB_NAME', 'ISMS_MOLINO')
DB_USER = os.getenv('DB_USER', 'testing')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'Test6740')

CONNECTION_STRING = (
    f"Driver={{SQL Server}};"
    f"Server={DB_SERVER};"
    f"Database={DB_NAME};"
    f"UID={DB_USER};"
    f"PWD={DB_PASSWORD};"
    f"TrustServerCertificate=yes;"
)

print("Conectando...")
try:
    conn = pyodbc.connect(CONNECTION_STRING)
    cursor = conn.cursor()
    
    print("\nCOLUMNAS DE ismsv_impuestos_documento:")
    print("-" * 40)
    
    # Query para obtener columnas y tipos
    cursor.execute("SELECT TOP 0 * FROM ismsv_impuestos_documento")
    columns = [column[0] for column in cursor.description]
    
    for col in columns:
        print(col)
        
    conn.close()
except Exception as e:
    print(f"Error: {e}")
