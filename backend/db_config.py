import os
from dotenv import load_dotenv

load_dotenv()

# Configuración de Base de Datos
DB_SERVER = os.getenv('DB_SERVER', 'servertesting')  # Cambiado a nombre del servidor
DB_NAME = os.getenv('DB_NAME', 'ISMS_MOLINO')
DB_USER = os.getenv('DB_USER', 'testing')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'Test6740')

# Connection String
CONNECTION_STRING = (
    f"Driver={{SQL Server}};"
    f"Server={DB_SERVER};"
    f"Database={DB_NAME};"
    f"UID={DB_USER};"
    f"PWD={DB_PASSWORD};"
    f"TrustServerCertificate=yes;"
)

# Configuración de Negocio
COMPANIA = os.getenv('COMPANIA', 'MOLINO')
RECEPTOR = os.getenv('RECEPTOR', 'EMPRESA')

# CUITs de nuestras empresas (RECEPTOR) - NO son proveedores
# Estos CUITs deben ser IGNORADOS al buscar el proveedor
CUITS_PROPIOS = [
    '30543400713',  # Molino Chabacuco
    '30-54340071-3',  # Molino Chabacuco (con guiones)
    '30715139096',  # Nutripet
    '30-71513909-6',  # Nutripet (con guiones)
    '30678143373',  # CUIT detectado erróneamente (alucinación)
    '30-67814337-3'  # CUIT detectado erróneamente (con guiones)
]

# Cuentas Contables (Por defecto)
CUENTA_PROVEEDORES = os.getenv('CUENTA_PROVEEDORES', '210101') # Pasivo
CUENTA_IVA_CREDITO = os.getenv('CUENTA_IVA_CREDITO', '110501') # Activo
CUENTA_GASTO_DEFECTO = os.getenv('CUENTA_GASTO_DEFECTO', '520101') # Gasto
