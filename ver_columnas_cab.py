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
    
    print("\nCOLUMNAS DE ISMST_DOCUMENTOS_CAB (con tipos y tamaños):")
    print("-" * 80)
    
    # Query para obtener columnas con tipos y tamaños
    cursor.execute("""
        SELECT 
            COLUMN_NAME, 
            DATA_TYPE, 
            CHARACTER_MAXIMUM_LENGTH,
            NUMERIC_PRECISION
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = 'ISMST_DOCUMENTOS_CAB'
        ORDER BY ORDINAL_POSITION
    """)
    
    for row in cursor.fetchall():
        col_name = row[0]
        data_type = row[1]
        max_len = row[2] if row[2] else ''
        precision = row[3] if row[3] else ''
        
        if max_len:
            print(f"{col_name:30} {data_type:15} (max_len={max_len})")
        elif precision:
            print(f"{col_name:30} {data_type:15} (precision={precision})")
        else:
            print(f"{col_name:30} {data_type:15}")
        
    conn.close()
except Exception as e:
    print(f"Error: {e}")
