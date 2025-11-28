import pyodbc
import os
from dotenv import load_dotenv

# Cargar variables de entorno
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

print("="*60)
print("DIAGNÓSTICO DE BASE DE DATOS")
print("="*60)
print(f"Conectando a {DB_SERVER} / {DB_NAME}...")

try:
    conn = pyodbc.connect(CONNECTION_STRING)
    cursor = conn.cursor()
    print("[OK] Conexion exitosa.\n")
    
    cuit_buscado = '33611492419'
    print(f"[SEARCH] Buscando CUIT: {cuit_buscado} (SIN FILTROS)")
    
    # Query sin filtros de estado ni tipo
    query = f"SELECT * FROM ISMST_PERSONAS WHERE CUIT LIKE '%{cuit_buscado}%'"
    cursor.execute(query)
    
    columns = [column[0] for column in cursor.description]
    row = cursor.fetchone()
    
    if row:
        print("\n[FOUND] REGISTRO ENCONTRADO:")
        print("-" * 40)
        for i, value in enumerate(row):
            col_name = columns[i]
            print(f"{col_name.ljust(20)}: '{value}'")
            
        # Análisis de por qué falla la query original
        print("\n" + "="*60)
        print("ANALISIS DE FALLA")
        print("="*60)
        
        tipo_persona = row.TIPO_PERSONA
        estado = row.ESTADO
        cuit_bd = row.CUIT
        
        print(f"TIPO_PERSONA actual: '{tipo_persona}'")
        if tipo_persona not in ['P', 'C']:
            print("[ERROR] La query filtra por TIPO_PERSONA IN ('P', 'C')")
            print("   -> Este proveedor NO cumple con el filtro.")
        else:
            print("[OK] TIPO_PERSONA correcto.")
            
        print(f"ESTADO actual: '{estado}'")
        if estado != 'ACTIVO':
            print("[ERROR] La query filtra por ESTADO = 'ACTIVO'")
            print("   -> Este proveedor NO esta activo.")
        else:
            print("[OK] ESTADO correcto.")
            
        print(f"CUIT en BD: '{cuit_bd}'")
        if len(cuit_bd) > 11 and ' ' in cuit_bd:
            print("[WARN] El CUIT tiene espacios en blanco (se arreglo con TRIM).")
            
    else:
        print("\n[ERROR] NO SE ENCONTRO EL CUIT EN LA BASE DE DATOS.")
        print("Posibles causas:")
        print("1. Estamos conectados a la base de datos incorrecta.")
        print("2. El CUIT esta guardado con guiones o formato diferente.")
        
    conn.close()

except Exception as e:
    print(f"\n[ERROR] ERROR DE CONEXION: {e}")

input("\nPresiona ENTER para salir...")
