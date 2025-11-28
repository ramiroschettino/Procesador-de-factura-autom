"""
Integrador con Base de Datos SQL Server
Maneja todas las operaciones de BD con logging detallado
"""

import logging
import pyodbc
from typing import Optional, Dict, List, Tuple
import db_config
from logging_config import (
    log_info, log_success, log_error, log_warning, 
    log_database, log_found, log_not_found, EMOJI
)

logger = logging.getLogger(__name__)


class DatabaseIntegrator:
    """Integrador con base de datos SQL Server"""
    
    def __init__(self):
        log_info(logger, f"{EMOJI['database']} Conectando a base de datos...")
        log_info(logger, f"Servidor: {db_config.CONNECTION_STRING.split(';')[0]}")
        
        try:
            self.conn = pyodbc.connect(db_config.CONNECTION_STRING)
            self.cursor = self.conn.cursor()
            log_success(logger, "Conexión a BD establecida")
        except Exception as e:
            log_error(logger, f"Error conectando a BD: {e}")
            raise
    
    def buscar_proveedor_por_cuit(self, cuit: str) -> Optional[str]:
        """Busca código de proveedor por CUIT (PRIORIDAD 1 - MÁS CONFIABLE)"""
        log_info(logger, f"{EMOJI['search']} Buscando proveedor por CUIT: {cuit}")
        # Usamos LIKE y TRIM para evitar problemas con espacios en blanco en la BD (char/nchar)
        # Y relajamos TIPO_PERSONA para incluir 'RI' o vacíos, y arreglamos ESTADO con TRIM
        query = """
            SELECT TOP 1 COD 
            FROM ISMST_PERSONAS 
            WHERE (RTRIM(LTRIM(CUIT)) = ? OR RTRIM(LTRIM(CUIL)) = ? OR CUIT LIKE ? OR CUIL LIKE ?) 
              AND RTRIM(LTRIM(ESTADO)) = 'ACTIVO'
              AND (
                  RTRIM(LTRIM(TIPO_PERSONA)) IN ('P', 'C', 'RI') 
                  OR TIPO_PERSONA IS NULL 
                  OR RTRIM(LTRIM(TIPO_PERSONA)) = ''
              )
        """
        
        try:
            # Probamos exacto y con patrón LIKE por si acaso
            patron = f"{cuit}%"
            self.cursor.execute(query, cuit, cuit, patron, patron)
            result = self.cursor.fetchone()
            
            if result:
                log_found(logger, "Proveedor", f"COD={result[0].strip()}")
                return result[0].strip()
            else:
                log_not_found(logger, "Proveedor", f"CUIT={cuit}")
                return None
                
        except Exception as e:
            log_error(logger, f"Error en búsqueda por CUIT: {e}")
            return None
    
    def _normalizar_texto(self, texto: str) -> str:
        """Elimina tildes y caracteres especiales para búsqueda"""
        import unicodedata
        if not texto: return ""
        # Normalizar a NFD (descompone caracteres)
        s = unicodedata.normalize('NFD', texto)
        # Filtrar caracteres no-spacing mark (tildes, diéresis)
        s = "".join(c for c in s if unicodedata.category(c) != 'Mn')
        # Convertir a mayúsculas y limpiar espacios
        return s.upper().strip()

    def buscar_proveedor_por_nombre(self, nombre: str) -> List[Dict]:
        """Busca proveedores por similitud de nombre (FALLBACK INTELIGENTE)"""
        nombre_limpio = self._normalizar_texto(nombre)
        log_info(logger, f"{EMOJI['search']} Buscando proveedor por nombre: '{nombre}' (Normalizado: '{nombre_limpio}')")
        
        # Estrategia 1: Búsqueda exacta o muy similar (LIKE %NOMBRE%)
        # Nota: SQL Server suele ser Case Insensitive pero Accent Sensitive depende del Collation.
        # Para asegurar, buscamos con y sin tildes si es posible, o asumimos que la BD está en mayúsculas sin tildes.
        
        palabras = nombre_limpio.split()
        if not palabras: return []
        
        # Construir patrón de búsqueda flexible: %PALABRA1%PALABRA2%
        patron_flexible = "%" + "%".join(palabras) + "%"
        
        # Si tiene más de 2 palabras, intentar también con las 2 primeras para mayor amplitud
        patron_corto = "%" + "%".join(palabras[:2]) + "%" if len(palabras) > 2 else patron_flexible
        
        log_database(logger, "SELECT", "ISMST_PERSONAS", f"WHERE NOMBRE LIKE '{patron_flexible}' OR '{patron_corto}'")
        
        query = """
            SELECT TOP 5 
                COD, NOMBRE, NOMBRE_CORTO, CUIT, CUIL, ESTADO, DOCUM_COMPLETA,
                CASE 
                    -- Coincidencia exacta (ignorando tildes/case en Python, aquí confiamos en SQL)
                    WHEN UPPER(NOMBRE) = ? THEN 100
                    -- Contiene todas las palabras en orden
                    WHEN UPPER(NOMBRE) LIKE ? THEN 90
                    -- Contiene las primeras 2 palabras (si aplica)
                    WHEN UPPER(NOMBRE) LIKE ? THEN 70
                    -- Coincidencia en nombre corto
                    WHEN UPPER(NOMBRE_CORTO) LIKE ? THEN 85
                    ELSE 50
                END AS SCORE
            FROM ISMST_PERSONAS 
            WHERE RTRIM(LTRIM(ESTADO)) = 'ACTIVO'
              AND (
                  RTRIM(LTRIM(TIPO_PERSONA)) IN ('P', 'C', 'RI') 
                  OR TIPO_PERSONA IS NULL 
                  OR RTRIM(LTRIM(TIPO_PERSONA)) = ''
              )
              AND (
                  UPPER(NOMBRE) LIKE ? 
                  OR UPPER(NOMBRE) LIKE ?
                  OR UPPER(NOMBRE_CORTO) LIKE ?
              )
            ORDER BY SCORE DESC, NOMBRE
        """
        
        try:
            # Parámetros para el CASE y el WHERE
            # 1. Exacto (nombre_limpio)
            # 2. Flexible (patron_flexible)
            # 3. Corto (patron_corto)
            # 4. Nombre corto (patron_flexible)
            # WHERE:
            # 5. Flexible
            # 6. Corto
            # 7. Nombre corto flexible
            
            params = (
                nombre_limpio, 
                patron_flexible, 
                patron_corto, 
                patron_flexible,
                patron_flexible,
                patron_corto,
                patron_flexible
            )
            
            self.cursor.execute(query, params)
            results = []
            
            for row in self.cursor.fetchall():
                # Normalizar nombre de BD para comparar mejor si hiciera falta
                nombre_bd = row.NOMBRE.strip()
                
                prov = {
                    'codigo': row.COD.strip(),
                    'nombre': nombre_bd,
                    'nombre_corto': row.NOMBRE_CORTO.strip() if row.NOMBRE_CORTO else '',
                    'cuit': row.CUIT.strip() if row.CUIT else '',
                    'cuil': row.CUIL.strip() if row.CUIL else '',
                    'estado': row.ESTADO.strip(),
                    'docum_completa': row.DOCUM_COMPLETA.strip(),
                    'activo': row.ESTADO.strip() == 'ACTIVO' and row.DOCUM_COMPLETA.strip() == 'SI',
                    'score': row.SCORE
                }
                results.append(prov)
                log_info(logger, f"  {EMOJI['bullet']} {prov['nombre']} (Score: {prov['score']}, COD: {prov['codigo']})")
            
            if results:
                log_success(logger, f"Encontrados {len(results)} proveedor(es) similar(es)")
            else:
                log_warning(logger, f"No se encontraron proveedores similares a: {nombre_limpio}")
                
                # INTENTO FINAL: Buscar solo por la primera palabra si es larga (>3 chars)
                if len(palabras[0]) > 3:
                    primera_palabra = palabras[0]
                    log_info(logger, f"🔍 Intento final: Buscando solo por '{primera_palabra}'")
                    return self._buscar_por_palabra_clave(primera_palabra)
            
            return results
            
        except Exception as e:
            log_error(logger, f"Error en búsqueda por nombre: {e}")
            return []

    def _buscar_por_palabra_clave(self, palabra: str) -> List[Dict]:
        """Búsqueda simple por una sola palabra clave"""
        query = """
            SELECT TOP 3 COD, NOMBRE, NOMBRE_CORTO, CUIT, CUIL, ESTADO, DOCUM_COMPLETA, 40 AS SCORE
            FROM ISMST_PERSONAS 
            WHERE RTRIM(LTRIM(ESTADO)) = 'ACTIVO'
              AND (RTRIM(LTRIM(TIPO_PERSONA)) IN ('P', 'C', 'RI') OR TIPO_PERSONA IS NULL OR RTRIM(LTRIM(TIPO_PERSONA)) = '')
              AND UPPER(NOMBRE) LIKE ?
        """
        try:
            self.cursor.execute(query, f"%{palabra}%")
            results = []
            for row in self.cursor.fetchall():
                prov = {
                    'codigo': row.COD.strip(),
                    'nombre': row.NOMBRE.strip(),
                    'nombre_corto': row.NOMBRE_CORTO.strip() if row.NOMBRE_CORTO else '',
                    'cuit': row.CUIT.strip() if row.CUIT else '',
                    'cuil': row.CUIL.strip() if row.CUIL else '',
                    'estado': row.ESTADO.strip(),
                    'docum_completa': row.DOCUM_COMPLETA.strip(),
                    'activo': True,
                    'score': 40
                }
                results.append(prov)
                log_info(logger, f"  {EMOJI['bullet']} {prov['nombre']} (Score: 40, COD: {prov['codigo']})")
            return results
        except Exception:
            return []
    
    def obtener_ocs_activas_proveedor(self, cod_proveedor: str) -> List[Dict]:
        """Obtiene OCs activas del proveedor con filtrado inteligente"""
        log_info(logger, f"{EMOJI['search']} Buscando OCs activas del proveedor: {cod_proveedor}")
        log_database(logger, "SELECT", "ISMST_ORDEN_COMPRA_CAB", f"WHERE COD_PROVEEDOR = {cod_proveedor}")
        
        query = """
            SELECT TOP 20
                OC.NRO_ORDEN_COMPRA,
                OC.FECHA,
                OC.COD_PROVEEDOR,
                OC.ESTADO,
                OC.MONTO_TOTAL,
                OC.OBSERVACION,
                OC.TIPO,
                (
                    SELECT SUM(ISNULL(PENDIENTE_FACTURAR, 0))
                    FROM ISMST_ORDEN_COMPRA_ITEM
                    WHERE NRO_ORDEN = OC.NRO_ORDEN_COMPRA
                ) AS PENDIENTE_TOTAL,
                (
                    SELECT COUNT(*)
                    FROM ISMST_ORDEN_COMPRA_ITEM
                    WHERE NRO_ORDEN = OC.NRO_ORDEN_COMPRA
                      AND ISNULL(PENDIENTE_FACTURAR, 0) > 0
                ) AS ITEMS_PENDIENTES
            FROM ISMST_ORDEN_COMPRA_CAB OC
            WHERE OC.COD_PROVEEDOR = ?
              AND OC.ESTADO IN ('ABIERTA', 'PARCIAL')
              AND OC.FECHA >= DATEADD(MONTH, -6, GETDATE())
            ORDER BY 
                CASE WHEN OC.ESTADO = 'ABIERTA' THEN 1 ELSE 2 END,
                OC.FECHA DESC
        """
        
        try:
            self.cursor.execute(query, cod_proveedor)
            ocs = []
            
            for row in self.cursor.fetchall():
                oc = {
                    'nro_orden': row.NRO_ORDEN_COMPRA,
                    'fecha': str(row.FECHA),
                    'estado': row.ESTADO.strip(),
                    'monto_total': float(row.MONTO_TOTAL) if row.MONTO_TOTAL else 0,
                    'pendiente_total': float(row.PENDIENTE_TOTAL) if row.PENDIENTE_TOTAL else 0,
                    'items_pendientes': int(row.ITEMS_PENDIENTES) if row.ITEMS_PENDIENTES else 0,
                    'observacion': row.OBSERVACION.strip() if row.OBSERVACION else '',
                    'tipo': row.TIPO.strip() if row.TIPO else '',
                    'recomendado': (row.ITEMS_PENDIENTES or 0) > 0
                }
                ocs.append(oc)
                
                status = "⭐ RECOMENDADO" if oc['recomendado'] else ""
                log_info(logger, f"  {EMOJI['bullet']} OC {oc['nro_orden']} - ${oc['monto_total']:,.2f} - Pendiente: ${oc['pendiente_total']:,.2f} ({oc['items_pendientes']} items) {status}")
            
            if ocs:
                log_success(logger, f"Encontradas {len(ocs)} OC(s) activa(s)")
            else:
                log_warning(logger, f"No se encontraron OCs activas para el proveedor {cod_proveedor}")
            
            return ocs
            
        except Exception as e:
            log_error(logger, f"Error obteniendo OCs activas: {e}")
            return []
    
    def verificar_proveedor_activo(self, cod_proveedor: str) -> Tuple[bool, str]:
        """Verifica que el proveedor esté activo y con documentación completa"""
        log_info(logger, f"{EMOJI['search']} Verificando estado del proveedor: {cod_proveedor}")
        log_database(logger, "SELECT", "ISMST_PERSONAS", f"WHERE COD = {cod_proveedor}")
        
        query = "SELECT DOCUM_COMPLETA, ESTADO FROM ISMST_PERSONAS WHERE COD = ?"
        
        try:
            self.cursor.execute(query, cod_proveedor)
            result = self.cursor.fetchone()
            
            if not result:
                log_not_found(logger, "Proveedor", cod_proveedor)
                return False, "Proveedor no encontrado"
            
            docum = result[0].strip() if result[0] else ""
            estado = result[1].strip() if result[1] else ""
            
            log_info(logger, f"  Estado: {estado}, Documentación: {docum}")
            
            if docum != "SI":
                log_warning(logger, "Documentación incompleta")
                return False, "Documentación incompleta"
            
            if estado == "BAJA":
                log_warning(logger, "Proveedor dado de BAJA")
                return False, "Proveedor dado de baja"
            
            log_success(logger, "Proveedor activo y con documentación completa")
            return True, "OK"
            
        except Exception as e:
            log_error(logger, f"Error verificando proveedor: {e}")
            return False, str(e)
    
    def obtener_items_oc(self, nro_oc: str) -> List[Dict]:
        """Obtiene los items de la OC desde la base de datos"""
        log_info(logger, f"{EMOJI['search']} Obteniendo items de OC: {nro_oc}")
        log_database(logger, "SELECT", "ISMST_ORDEN_COMPRA_ITEM", f"WHERE NRO_ORDEN = {nro_oc}")
        
        query = """
            SELECT 
                NRO_ITEM,
                COD_PRODUCTO,
                DESCRIPCION,
                CANTIDAD,
                PRECIO_UNIT,
                PENDIENTE_FACTURAR,
                ALICUOTA_IVA,
                ESTADO
            FROM ISMST_ORDEN_COMPRA_ITEM
            WHERE NRO_ORDEN = ?
              AND ESTADO != 'ANULADO'
            ORDER BY NRO_ITEM
        """
        
        try:
            self.cursor.execute(query, nro_oc)
            items = []
            
            for row in self.cursor.fetchall():
                item = {
                    "nro_item": row.NRO_ITEM,
                    "cod_producto": row.COD_PRODUCTO.strip() if row.COD_PRODUCTO else "",
                    "descripcion": row.DESCRIPCION.strip() if row.DESCRIPCION else "",
                    "cantidad_original": float(row.CANTIDAD) if row.CANTIDAD else 0,
                    "precio_unitario": float(row.PRECIO_UNIT) if row.PRECIO_UNIT else 0,
                    "pendiente": float(row.PENDIENTE_FACTURAR) if row.PENDIENTE_FACTURAR else 0,
                    "alicuota_iva": float(row.ALICUOTA_IVA) if row.ALICUOTA_IVA else 0
                }
                items.append(item)
                
                log_info(logger, f"  {EMOJI['bullet']} Item {item['nro_item']}: {item['descripcion'][:50]} - Pendiente: {item['pendiente']}")
            
            if items:
                log_success(logger, f"Encontrados {len(items)} item(s) en OC {nro_oc}")
            else:
                log_warning(logger, f"No se encontraron items en OC {nro_oc}")
            
            return items
            
        except Exception as e:
            log_error(logger, f"Error obteniendo items de OC: {e}")
            return []
    
    def verificar_oc_existe(self, nro_oc: str) -> Tuple[bool, str, Optional[str]]:
        """Verifica OC y retorna (existe, mensaje, cod_proveedor)"""
        log_info(logger, f"{EMOJI['search']} Verificando OC: {nro_oc}")
        log_database(logger, "SELECT", "ISMST_ORDEN_COMPRA_CAB", f"WHERE NRO_ORDEN_COMPRA = {nro_oc}")
        
        # Usamos TRIM y LIKE para mayor robustez
        query = """
            SELECT TOP 1 ESTADO, COD_PROVEEDOR 
            FROM ISMST_ORDEN_COMPRA_CAB 
            WHERE RTRIM(LTRIM(NRO_ORDEN_COMPRA)) = ? 
               OR NRO_ORDEN_COMPRA LIKE ?
        """
        
        try:
            patron = f"%{nro_oc}%"
            self.cursor.execute(query, nro_oc, patron)
            result = self.cursor.fetchone()
            
            if not result:
                log_not_found(logger, "OC", nro_oc)
                return False, "OC no encontrada en base de datos", None
            
            estado = result[0].strip() if result[0] else ""
            cod_prov = result[1].strip() if result[1] else ""
            
            log_info(logger, f"  Estado: {estado}, Proveedor: {cod_prov}")
            
            if estado == 'CERRADA':
                log_warning(logger, "La OC está CERRADA")
                return False, "La OC está CERRADA", None
            
            log_success(logger, f"OC {nro_oc} encontrada y activa")
            return True, "OK", cod_prov
            
            return True, "OK", cod_prov
            
        except Exception as e:
            log_error(logger, f"Error verificando OC: {e}")
            return False, str(e), None

    def verificar_factura_existente(self, cod_proveedor: str, tipo: str, punto_emision: str, numero: str) -> Optional[str]:
        """Verifica si la factura ya existe en la BD. Retorna NRO_ARCHIVO si existe."""
        log_info(logger, f"{EMOJI['search']} Verificando duplicados: {tipo} {punto_emision}-{numero} (Prov: {cod_proveedor})")
        log_database(logger, "SELECT", "ISMST_DOCUMENTOS_CAB", f"WHERE EMISOR={cod_proveedor} AND TIPO={tipo} AND PUNTO_EMISION={punto_emision} AND NUMERO={numero}")
        
        # Usamos TRIM y LIKE para manejar espacios/padding
        query = """
            SELECT TOP 1 NRO_ARCHIVO, FECHA, PUNTO_EMISION, NUMERO FROM ISMST_DOCUMENTOS_CAB 
            WHERE EMISOR = ? 
              AND TIPO = ? 
              AND (
                  RTRIM(LTRIM(PUNTO_EMISION)) = ? 
                  OR PUNTO_EMISION LIKE ?
              )
              AND (
                  RTRIM(LTRIM(NUMERO)) = ? 
                  OR NUMERO LIKE ?
              )
              AND ANULADO = 'NO'
        """
        try:
            # Patrones LIKE para campos con padding
            patron_punto = f"{punto_emision}%"
            patron_numero = f"{numero}%"
            
            self.cursor.execute(query, 
                cod_proveedor, tipo, 
                punto_emision, patron_punto,
                numero, patron_numero
            )
            result = self.cursor.fetchone()
            if result:
                nro_archivo = result[0]
                fecha = result[1]
                punto_bd = result[2].strip() if result[2] else ''
                numero_bd = result[3].strip() if result[3] else ''
                log_warning(logger, f"⚠️ ⚠️ FACTURA YA EXISTE:")
                log_warning(logger, f"   Archivo: {nro_archivo}")
                log_warning(logger, f"   Fecha: {fecha}")
                log_warning(logger, f"   En BD: {punto_bd}-{numero_bd}")
                return nro_archivo
            else:
                log_success(logger, "✅ Factura no existe, se puede procesar")
            return None
        except Exception as e:
            log_error(logger, f"Error verificando duplicados: {e}")
            return None
    
    def obtener_ejercicio(self, fecha_doc: str) -> Optional[str]:
        """Obtiene el ejercicio contable para una fecha"""
        log_info(logger, f"{EMOJI['search']} Buscando ejercicio contable para fecha: {fecha_doc}")
        log_database(logger, "SELECT", "ISMST_EJERCICIOS", f"WHERE fecha BETWEEN inicio y fin")
        
        query = "SELECT EJER_COD FROM ISMST_EJERCICIOS WHERE EJER_FECHAINICIO <= ? AND EJER_FECHAFIN >= ?"
        
        try:
            self.cursor.execute(query, fecha_doc, fecha_doc)
            result = self.cursor.fetchone()
            
            if result:
                ejercicio = result[0].strip()
                log_found(logger, "Ejercicio", ejercicio)
                return ejercicio
            else:
                log_not_found(logger, "Ejercicio", f"para fecha {fecha_doc}")
                return None
                
        except Exception as e:
            log_error(logger, f"Error obteniendo ejercicio: {e}")
            return None
    
    def close(self):
        """Cierra la conexión a la base de datos"""
        log_info(logger, "Cerrando conexión a BD...")
        try:
            self.cursor.close()
            self.conn.close()
            log_success(logger, "Conexión cerrada correctamente")
        except Exception as e:
            log_error(logger, f"Error cerrando conexión: {e}")
