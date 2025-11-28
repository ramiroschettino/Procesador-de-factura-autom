"""
Módulo de Contabilidad
Maneja generación de asientos contables y movimientos
"""

import logging
from typing import Dict
import db_config
from logging_config import (
    log_section, log_step, log_info, log_success, log_error, 
    log_warning, log_database, EMOJI
)

logger = logging.getLogger(__name__)


class AccountingManager:
    """Gestor de asientos contables"""
    
    def __init__(self, cursor):
        self.cursor = cursor
        log_info(logger, "AccountingManager inicializado")
    
    def generar_asiento_contable(self, factura_data: Dict, cod_proveedor: str, nro_comprobante: str, fecha_emision: str, ejercicio: str):
        """Genera el asiento contable de la factura"""
        log_section(logger, "GENERACIÓN DE ASIENTO CONTABLE")
        
        if not ejercicio:
            log_warning(logger, f"No se encontró ejercicio para fecha {fecha_emision}")
            log_warning(logger, "⚠️ ASIENTO NO GENERADO - Falta ejercicio contable")
            return
        
        log_info(logger, f"Ejercicio: {ejercicio}")
        
        try:
            # 1. Obtener siguiente número de asiento
            log_step(logger, 1, "Obteniendo siguiente número de asiento")
            log_database(logger, "SELECT", "ISMST_ASIENTOS", "MAX(AS_NRO) + 1")
            
            self.cursor.execute("SELECT ISNULL(MAX(AS_NRO), 0) + 1 FROM ISMST_ASIENTOS")
            nro_asiento = self.cursor.fetchone()[0]
            log_success(logger, f"Número de asiento: {nro_asiento}")
            
            descripcion = f"Factura {nro_comprobante} - Prov: {factura_data['cabecera']['proveedor']['nombre']}"
            
            # 2. Insertar Cabecera de Asiento
            log_step(logger, 2, "Insertando cabecera de asiento")
            log_database(logger, "INSERT", "ISMST_ASIENTOS", f"AS_NRO={nro_asiento}")
            
            self.cursor.execute("""
                INSERT INTO ISMST_ASIENTOS (
                    AS_NRO, AS_FECHAREG, AS_DESCRIPCION, AS_TIPOCOMP, 
                    AS_CLIENTE, AS_PROVEEDOR, AS_MODO, AS_CIERRE, 
                    AS_INTEGRABLE, AS_EMPRESA, AS_REVERSIBLE, AS_REVFECHA, 
                    AS_CONCEPTO, AS_EJERCICIO, AS_FECHAMOV
                ) VALUES (?, GETDATE(), ?, ?, 0, ?, 'Automático', '', 'Verdadero', ?, 'Falso', GETDATE(), 'Proveedores', ?, ?)
            """, (
                nro_asiento, 
                descripcion, 
                self._mapear_tipo_comprobante(factura_data['cabecera']['factura']['tipo_comprobante']),
                cod_proveedor,
                db_config.COMPANIA,
                ejercicio,
                fecha_emision
            ))
            log_success(logger, "Cabecera de asiento insertada")
            
            # 3. Generar Movimientos
            log_step(logger, 3, "Generando movimientos contables")
            
            total_debe = 0
            total_haber = 0
            
            # Movimiento 1: Pasivo (Proveedores) - HABER
            importe_total = factura_data['cabecera']['factura']['importe_total']
            log_info(logger, f"{EMOJI['money']} HABER - Cuenta Proveedores ({db_config.CUENTA_PROVEEDORES}): ${importe_total:,.2f}")
            self._insertar_movimiento(nro_asiento, db_config.CUENTA_PROVEEDORES, nro_comprobante, fecha_emision, descripcion, importe_total, 'HABER', ejercicio)
            total_haber += importe_total
            
            # Movimiento 2: IVA Crédito Fiscal - DEBE
            importe_iva = factura_data['cabecera']['factura']['importe_iva']
            if importe_iva > 0:
                log_info(logger, f"{EMOJI['money']} DEBE - IVA Crédito Fiscal ({db_config.CUENTA_IVA_CREDITO}): ${importe_iva:,.2f}")
                self._insertar_movimiento(nro_asiento, db_config.CUENTA_IVA_CREDITO, nro_comprobante, fecha_emision, "IVA Crédito Fiscal", importe_iva, 'DEBE', ejercicio)
                total_debe += importe_iva
            
            # Movimiento 3: Gasto/Activo (Neto Gravado) - DEBE
            importe_neto = factura_data['cabecera']['factura']['importe_neto_gravado']
            if importe_neto > 0:
                log_warning(logger, "⚠️ FUNCIONALIDAD INCONCLUSA: Usando cuenta de gasto por defecto")
                log_warning(logger, "TODO: Mapear producto → cuenta contable específica")
                log_info(logger, f"{EMOJI['money']} DEBE - Gasto/Compra ({db_config.CUENTA_GASTO_DEFECTO}): ${importe_neto:,.2f}")
                self._insertar_movimiento(nro_asiento, db_config.CUENTA_GASTO_DEFECTO, nro_comprobante, fecha_emision, "Gasto/Compra", importe_neto, 'DEBE', ejercicio)
                total_debe += importe_neto
            
            # Movimiento 4: Exento/No Gravado - DEBE
            importe_otros = factura_data['cabecera']['factura']['importe_no_gravado'] + factura_data['cabecera']['factura']['importe_exento']
            if importe_otros > 0:
                log_info(logger, f"{EMOJI['money']} DEBE - Conceptos No Gravados ({db_config.CUENTA_GASTO_DEFECTO}): ${importe_otros:,.2f}")
                self._insertar_movimiento(nro_asiento, db_config.CUENTA_GASTO_DEFECTO, nro_comprobante, fecha_emision, "Conceptos No Gravados", importe_otros, 'DEBE', ejercicio)
                total_debe += importe_otros
            
            # Movimiento 5: Percepciones - DEBE (INCONCLUSO)
            if factura_data['cabecera']['impuestos']:
                log_warning(logger, "⚠️ FUNCIONALIDAD INCONCLUSA: Tratamiento de percepciones en asientos")
                log_warning(logger, "TODO: Definir con Contabilidad si van como movimiento adicional o ya están en el total")
                
                for impuesto in factura_data['cabecera']['impuestos']:
                    if impuesto['monto'] > 0:
                        log_info(logger, f"{EMOJI['warning']} Percepción {impuesto['tipo']}: ${impuesto['monto']:,.2f} (NO contabilizada)")
                        # TODO: Descomentar cuando se defina la lógica
                        # self._insertar_movimiento(nro_asiento, CUENTA_PERCEPCION, nro_comprobante, fecha_emision, f"Percepción {impuesto['tipo']}", impuesto['monto'], 'DEBE', ejercicio)
                        # total_debe += impuesto['monto']
            
            # Verificar balance
            log_step(logger, 4, "Verificando balance del asiento")
            diferencia = abs(total_debe - total_haber)
            
            if diferencia < 0.01:  # Tolerancia de 1 centavo
                log_success(logger, f"✅ Asiento BALANCEADO")
                log_info(logger, f"   DEBE:  ${total_debe:,.2f}")
                log_info(logger, f"   HABER: ${total_haber:,.2f}")
                log_info(logger, f"   Diferencia: ${diferencia:.2f}")
            else:
                log_error(logger, f"❌ Asiento DESBALANCEADO")
                log_error(logger, f"   DEBE:  ${total_debe:,.2f}")
                log_error(logger, f"   HABER: ${total_haber:,.2f}")
                log_error(logger, f"   Diferencia: ${diferencia:.2f}")
                raise Exception(f"Asiento desbalanceado. Diferencia: ${diferencia:.2f}")
            
            log_success(logger, f"Asiento {nro_asiento} generado correctamente")
            
        except Exception as e:
            log_error(logger, f"Error generando asiento contable: {e}")
            raise
    
    def _insertar_movimiento(self, nro_asiento, cuenta, comprobante, fecha, descripcion, importe, posicion, ejercicio):
        """Helper para insertar movimiento contable"""
        log_database(logger, "INSERT", "ISMST_MOVIMIENTOS", f"AS_NRO={nro_asiento}, Cuenta={cuenta}, {posicion}")
        
        # TODO: FUNCIONALIDAD INCONCLUSA - Centro de Costos
        centro_costo = ''  # Por ahora vacío
        
        try:
            self.cursor.execute("""
                INSERT INTO ISMST_MOVIMIENTOS (
                    MO_ASNRO, MO_CUENTA, MO_COMPROBANTE, MO_FECHA, 
                    MO_DESCRIPCION, MO_IMPORTE, MO_POSICION, MO_CC, 
                    MO_FECHAEFECTIVA, MO_MNG, MO_EMPRESA, MO_EJERCICIO
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            """, (
                nro_asiento, cuenta, comprobante, fecha, 
                descripcion, importe, posicion, 
                centro_costo,  # INCONCLUSO
                fecha, db_config.COMPANIA, ejercicio
            ))
            log_success(logger, f"Movimiento insertado: {posicion} ${importe:,.2f}")
            
        except Exception as e:
            log_error(logger, f"Error insertando movimiento: {e}")
            raise
    
    def _mapear_tipo_comprobante(self, tipo_texto: str) -> str:
        """Mapea tipo de comprobante a código del sistema"""
        mapeo = {
            'FACTURA A': 'FACTT',  # Factura de Terceros
            'FACTURA B': 'FACTT',
            'FACTURA C': 'FACTT',
            'NOTA DE CREDITO A': 'NCTA', # Verificar si estas también son NCTT?
            'NOTA DE CREDITO B': 'NCTB',
            'NOTA DE CREDITO C': 'NCTC',
            'NOTA DE DEBITO A': 'NDTA',
            'NOTA DE DEBITO B': 'NDTB',
        }
        codigo = mapeo.get(tipo_texto.upper(), 'FACTT')
        log_info(logger, f"Tipo comprobante mapeado: '{tipo_texto}' → '{codigo}'")
        return codigo
