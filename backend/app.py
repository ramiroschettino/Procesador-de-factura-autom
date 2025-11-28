"""
Sistema Integrado de Procesamiento de Facturas con IA
Orquestador principal - Versión modularizada
"""

import os
import logging
from typing import Optional, Dict
from dotenv import load_dotenv

# Módulos propios
from gemini_processor import GeminiProcessor
from database_integrator import DatabaseIntegrator
from accounting import AccountingManager
import db_config
from logging_config import (
    setup_logging, log_section, log_step, log_info, log_success, 
    log_error, log_warning, log_database, EMOJI
)

# Configuración
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

# Configurar logging mejorado
logger = setup_logging()


class FacturasIASystem:
    """Sistema principal integrado"""
    
    def __init__(self):
        log_section(logger, "INICIALIZACIÓN DEL SISTEMA")
        
        try:
            log_step(logger, 1, "Conectando a Base de Datos")
            self.db = DatabaseIntegrator()
            
            log_step(logger, 2, "Inicializando Gemini AI")
            self.gemini = GeminiProcessor(API_KEY, self.db)
            
            log_step(logger, 3, "Inicializando módulo de Contabilidad")
            self.accounting = AccountingManager(self.db.cursor)
            
            log_success(logger, "Sistema inicializado correctamente")
            
        except Exception as e:
            log_error(logger, f"Error en inicialización: {e}")
            raise
    
    def process_invoice_file(self, file_path: str) -> Dict:
        """
        Procesa una factura completa:
        1. Extrae datos con Gemini
        2. Busca OC en BD (automáticamente por proveedor)
        3. Inserta en base de datos
        4. Genera asiento contable
        """
        log_section(logger, "PROCESAMIENTO COMPLETO DE FACTURA")
        log_info(logger, f"Archivo: {os.path.basename(file_path)}")
        
        result = {
            'success': False,
            'extraction': None,
            'reconciliation': None,
            'database': None,
            'errors': []
        }
        
        try:
            # ===== PASO 1: Extracción =====
            log_section(logger, "PASO 1: EXTRACCIÓN DE DATOS")
            
            invoice_data = self.gemini.extract_invoice_data(file_path)
            if not invoice_data:
                result['errors'].append("Error en extracción de datos")
                return result
            
            result['extraction'] = invoice_data
            
            # ===== PASO 2: Búsqueda Automática de OC =====
            # NOTA: Ignoramos el número de OC que Gemini extrae porque a veces lee mal
            # Siempre buscamos OCs activas del proveedor
            log_section(logger, "PASO 2: BÚSQUEDA AUTOMÁTICA DE OC")
            log_info(logger, "🔍 Buscando OCs abiertas del proveedor en la base de datos...")
            
            cuit_prov = invoice_data['cabecera']['proveedor']['cuit']
            nombre_prov = invoice_data['cabecera']['proveedor']['nombre']
            cod_prov = None
            
            # Buscar proveedor
            if cuit_prov:
                cod_prov = self.db.buscar_proveedor_por_cuit(cuit_prov)
            
            if not cod_prov and nombre_prov:
                matches = self.db.buscar_proveedor_por_nombre(nombre_prov)
                if matches:
                    cod_prov = matches[0]['codigo']
            
            if cod_prov:
                ocs_activas = self.db.obtener_ocs_activas_proveedor(cod_prov)
                if ocs_activas:
                    log_success(logger, f"✅ Se encontraron {len(ocs_activas)} OCs activas para este proveedor")
                    log_info(logger, "OCs encontradas:")
                    for oc in ocs_activas:
                        log_info(logger, f"  • OC {oc['nro_orden']} - Estado: {oc['estado']}")
                    log_warning(logger, "⚠️ Match automático de items pendiente de implementar")
                else:
                    log_warning(logger, "El proveedor no tiene OCs pendientes de facturar")
            else:
                log_warning(logger, "No se pudo identificar al proveedor para buscar OCs")
            
            # ===== PASO 3: Integración a BD =====
            log_section(logger, "PASO 3: INTEGRACIÓN A BASE DE DATOS")
            
            success, message = self._procesar_factura_en_bd(
                invoice_data,
                result.get('reconciliation')
            )
            
            result['database'] = {
                'success': success,
                'message': message
            }
            result['success'] = success
            
            if not success:
                result['errors'].append(message)
            
            return result
            
        except Exception as e:
            log_error(logger, f"Error en procesamiento: {e}")
            result['errors'].append(str(e))
            return result
    
    def _procesar_factura_en_bd(self, factura_data: Dict, conciliacion_data: Optional[Dict] = None) -> tuple:
        """Procesa e inserta factura en la base de datos"""
        try:
            log_step(logger, 1, "Iniciando transacción")
            log_database(logger, "BEGIN", "TRANSACTION", "")
            self.db.cursor.execute("BEGIN TRANSACTION")
            
            # Validar proveedor
            log_step(logger, 2, "Validando proveedor")
            cuit = factura_data['cabecera']['proveedor']['cuit']
            nombre_proveedor = factura_data['cabecera']['proveedor']['nombre']
            
            cod_proveedor = self.db.buscar_proveedor_por_cuit(cuit)
            
            # Si no encuentra por CUIT, buscar por nombre
            if not cod_proveedor:
                log_warning(logger, f"⚠️ Proveedor con CUIT {cuit} no encontrado")
                log_info(logger, f"🔍 Buscando por nombre: {nombre_proveedor}")
                
                proveedores_similares = self.db.buscar_proveedor_por_nombre(nombre_proveedor)
                
                if proveedores_similares and len(proveedores_similares) > 0:
                    mejor_match = proveedores_similares[0]
                    cod_proveedor = mejor_match['codigo']
                    
                    log_success(logger, f"✅ Proveedor encontrado por nombre:")
                    log_info(logger, f"   Código: {cod_proveedor}")
                    log_info(logger, f"   Nombre: {mejor_match['nombre']}")
                    log_info(logger, f"   Score: {mejor_match['score']}")
                    log_info(logger, f"   CUIT en BD: {mejor_match.get('cuit', 'N/A')}")
                    
                    if len(proveedores_similares) > 1:
                        log_warning(logger, f"⚠️ Se encontraron {len(proveedores_similares)} proveedores similares")
                        log_warning(logger, "Se seleccionó el de mayor coincidencia")
                else:
                    raise Exception(f"Proveedor no encontrado - CUIT: {cuit}, Nombre: {nombre_proveedor}")
            
            activo, msg = self.db.verificar_proveedor_activo(cod_proveedor)
            if not activo:
                raise Exception(f"Proveedor inválido: {msg}")
            
            log_success(logger, f"Proveedor validado: {cod_proveedor}")
            
            # Verificar si ya existe
            tipo_comprobante = self.accounting._mapear_tipo_comprobante(factura_data['cabecera']['factura']['tipo_comprobante'])
            punto_emision = factura_data['cabecera']['factura']['punto_emision']
            numero_comprobante = factura_data['cabecera']['factura']['numero_comprobante']
            
            archivo_existente = self.db.verificar_factura_existente(
                cod_proveedor, tipo_comprobante, punto_emision, numero_comprobante
            )
            
            if archivo_existente:
                raise Exception(f"La factura ya existe en el sistema (Archivo: {archivo_existente})")
            
            # Obtener siguiente número de archivo
            log_step(logger, 3, "Obteniendo siguiente número de archivo")
            log_database(logger, "SELECT", "ISMSV_DOCUMENTOS_CAB", "MAX(NRO_ARCHIVO) + 1")
            
            self.db.cursor.execute("""
                SELECT ISNULL(MAX(CAST(NRO_ARCHIVO AS INT)) + 1, 1) 
                FROM ISMSV_DOCUMENTOS_CAB
            """)
            nro_archivo = self.db.cursor.fetchone()[0]
            log_success(logger, f"Número de archivo: {nro_archivo}")
            
            # Insertar cabecera
            log_step(logger, 4, "Insertando cabecera de factura")
            cab = factura_data['cabecera']['factura']
            log_database(logger, "INSERT", "ISMST_DOCUMENTOS_CAB", f"NRO_ARCHIVO={nro_archivo}")
            
            # Normalizar fechas
            fecha_emision = self._normalizar_fecha(cab['fecha_emision'])
            fecha_vencimiento = self._normalizar_fecha(cab['fecha_vencimiento'])
            
            if not fecha_emision:
                log_warning(logger, "⚠️ Fecha de emisión inválida o nula, usando fecha actual")
                from datetime import datetime
                fecha_emision = datetime.now()
                
            if not fecha_vencimiento:
                fecha_vencimiento = fecha_emision
            
            log_info(logger, f"Fechas para BD: Emisión={fecha_emision}, Vto={fecha_vencimiento}")

            self.db.cursor.execute("""
                INSERT INTO ISMST_DOCUMENTOS_CAB (
                    COMPANIA, TIPO, NUMERO, EMISOR, RECEPTOR,
                    PUNTO_EMISION, FECHA, FECHA_PAGO_COBRO,
                    MONEDA, TIPO_CAMBIO, MONTO_TOTAL_FINAL, NRO_ARCHIVO,
                    ANULADO
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'NO')
            """, (
                db_config.COMPANIA,
                self.accounting._mapear_tipo_comprobante(cab['tipo_comprobante']),
                cab['numero_comprobante'],
                cod_proveedor,
                db_config.RECEPTOR,
                cab['punto_emision'][-4:],
                fecha_emision,
                fecha_vencimiento,
                cab['moneda'],
                cab['cotizacion'],
                cab['importe_total'],
                nro_archivo
            ))
            log_success(logger, "Cabecera insertada")
            
            # Insertar items
            log_step(logger, 5, f"Insertando {len(factura_data['items'])} items")
            for i, item in enumerate(factura_data['items'], 1):
                log_database(logger, "INSERT", "ISMST_DOCUMENTOS_ITEM", f"Item {item['linea']}")
                
                self.db.cursor.execute("""
                    INSERT INTO ISMST_DOCUMENTOS_ITEM (
                        COMPANIA, TIPO, NUMERO, EMISOR, RECEPTOR,
                        PUNTO_EMISION, ITEM, DESCRIPCION,
                        CANTIDAD, PRECIO
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    db_config.COMPANIA,
                    self.accounting._mapear_tipo_comprobante(cab['tipo_comprobante']),
                    cab['numero_comprobante'],
                    cod_proveedor,
                    db_config.RECEPTOR,
                    cab['punto_emision'][-4:],
                    item['linea'],
                    item['descripcion'],
                    item['cantidad'],
                    item['precio_unitario']
                ))
                log_success(logger, f"Item {i}/{len(factura_data['items'])} insertado: {item['descripcion'][:50]}")
            
            # Insertar impuestos
            if factura_data['cabecera']['impuestos']:
                log_step(logger, 6, f"Insertando {len(factura_data['cabecera']['impuestos'])} impuesto(s)")
                for impuesto in factura_data['cabecera']['impuestos']:
                    if impuesto['monto'] > 0:
                        log_database(logger, "INSERT", "ismsv_impuestos_documento", f"{impuesto['tipo']}")
                        
                        self.db.cursor.execute("""
                            INSERT INTO ismsv_impuestos_documento (
                                compania, tipo_doc, numero_doc, emisor, receptor,
                                item, cod_impuesto, valor, punto_emision
                            ) VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?)
                        """, (
                            db_config.COMPANIA,
                            self.accounting._mapear_tipo_comprobante(cab['tipo_comprobante']),
                            cab['numero_comprobante'],
                            cod_proveedor,
                            db_config.RECEPTOR,
                            impuesto['tipo'][:10],
                            impuesto['monto'],
                            cab['punto_emision'][-4:]
                        ))
                        log_success(logger, f"Impuesto insertado: {impuesto['tipo']} ${impuesto['monto']:,.2f}")
            
            # Commit de la factura ANTES del asiento contable
            log_step(logger, 7, "Confirmando transacción de factura")
            log_database(logger, "COMMIT", "TRANSACTION", "")
            self.db.cursor.execute("COMMIT TRANSACTION")
            log_success(logger, f"✅ Factura guardada exitosamente - Archivo: {nro_archivo}")
            
            # Log útil para verificar en la BD
            log_info(logger, f"📋 Para verificar en la BD, ejecuta:")
            log_info(logger, f"   SELECT * FROM ISMST_DOCUMENTOS_CAB WHERE NRO_ARCHIVO = '{nro_archivo}'")
            log_info(logger, f"   O bien: SELECT * FROM ISMST_DOCUMENTOS_CAB WHERE EMISOR = '{cod_proveedor}' AND NUMERO LIKE '%{cab['numero_comprobante']}%' ORDER BY FECHA DESC")
            
            # Generar Asiento Contable (DESACTIVADO temporalmente por error de ejercicio)
            log_step(logger, 8, "Generando asiento contable")
            log_warning(logger, "⚠️ Asiento contable DESACTIVADO temporalmente")
            log_warning(logger, "Motivo: Error en validación de ejercicio contable (trigger BD)")
            log_warning(logger, "Deberás generar el asiento manualmente")
            
            # TODO: Descomentar cuando se resuelva el problema del ejercicio
            # try:
            #     ejercicio = self.db.obtener_ejercicio(fecha_emision)
            #     self.accounting.generar_asiento_contable(
            #         factura_data, 
            #         cod_proveedor, 
            #         cab['numero_comprobante'], 
            #         fecha_emision,
            #         ejercicio
            #     )
            #     log_success(logger, "✅ Asiento contable generado correctamente")
            # except Exception as e:
            #     log_error(logger, f"⚠️ Error generando asiento contable: {e}")
            #     log_warning(logger, "La factura se guardó correctamente pero SIN asiento contable")
            
            return True, f"Factura procesada exitosamente. Archivo: {nro_archivo}"
            
        except Exception as e:
            log_error(logger, f"Error en procesamiento, haciendo ROLLBACK")
            log_database(logger, "ROLLBACK", "TRANSACTION", "")
            try:
                self.db.cursor.execute("ROLLBACK TRANSACTION")
            except:
                pass  # Ya se hizo rollback
            log_error(logger, f"❌ Error: {e}")
            return False, str(e)
    
    def _normalizar_fecha(self, fecha_str: str):
        """Devuelve objeto datetime para pyodbc"""
        if not fecha_str: return None
        try:
            from datetime import datetime
            fecha_str = fecha_str.strip()
            
            if '/' in fecha_str:
                dt = datetime.strptime(fecha_str, '%d/%m/%Y')
                log_info(logger, f"Fecha normalizada (DD/MM/YYYY): {fecha_str} -> {dt}")
                return dt
                
            if '-' in fecha_str:
                dt = datetime.strptime(fecha_str, '%Y-%m-%d')
                log_info(logger, f"Fecha normalizada (ISO): {fecha_str} -> {dt}")
                return dt
                
            return None
        except Exception as e:
            log_error(logger, f"Error normalizando fecha '{fecha_str}': {e}")
            return None
    
    def close(self):
        """Cierra conexiones"""
        log_info(logger, "Cerrando sistema...")
        self.db.close()
        log_success(logger, "Sistema cerrado correctamente")


def main():
    """Ejemplo de uso del sistema"""
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python app.py <ruta_factura>")
        return
    
    factura_path = sys.argv[1]
    
    system = FacturasIASystem()
    
    try:
        result = system.process_invoice_file(factura_path)
        
        print("\n" + "=" * 60)
        print("RESULTADO FINAL")
        print("=" * 60)
        import json
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    finally:
        system.close()


if __name__ == "__main__":
    main()
