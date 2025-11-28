"""
Procesador de documentos con Gemini AI
Maneja extracción de datos y conciliación
"""

import os
import logging
import json
from typing import Optional, Dict, List
import google.generativeai as genai
import fitz  # PyMuPDF
from PIL import Image
import io
from logging_config import log_info, log_success, log_error, log_warning, EMOJI

logger = logging.getLogger(__name__)


class GeminiProcessor:
    """Procesador de documentos con Gemini AI"""
    
    def __init__(self, api_key: str, db_integrator=None):
        if not api_key:
            raise ValueError("GEMINI_API_KEY no configurada")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        self.db = db_integrator  # Referencia a DatabaseIntegrator para búsquedas
        log_success(logger, "Gemini AI configurado correctamente")
    
    def pdf_to_images(self, pdf_path: str) -> List[Image.Image]:
        """Convierte PDF a lista de imágenes PIL"""
        log_info(logger, f"Convirtiendo PDF a imágenes: {os.path.basename(pdf_path)}")
        images = []
        
        try:
            doc = fitz.open(pdf_path)
            log_info(logger, f"PDF tiene {len(doc)} página(s)")
            
            for i, page in enumerate(doc, 1):
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img_bytes = pix.tobytes("png")
                images.append(Image.open(io.BytesIO(img_bytes)))
                log_info(logger, f"  {EMOJI['check']} Página {i} convertida")
            
            log_success(logger, f"PDF convertido: {len(images)} imagen(es)")
            return images
            
        except Exception as e:
            log_error(logger, f"Error leyendo PDF: {e}")
            return []
    
    def extract_invoice_data(self, file_path: str) -> Optional[Dict]:
        """Extrae datos de una factura usando Gemini"""
        log_info(logger, f"{EMOJI['start']} Iniciando extracción de datos")
        log_info(logger, f"Archivo: {os.path.basename(file_path)}")
        
        # Importar configuración
        import db_config
        
        content_parts = []
        
        # Cargar imágenes
        if file_path.lower().endswith('.pdf'):
            images = self.pdf_to_images(file_path)
            if not images:
                log_error(logger, "No se pudieron cargar imágenes del PDF")
                return None
            
            log_info(logger, f"Procesando {len(images)} imagen(es) con Gemini AI...")
            for i, img in enumerate(images[:5], 1):
                content_parts.append(img)
                log_info(logger, f"  {EMOJI['bullet']} Imagen {i} agregada al prompt")
                
        elif file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            try:
                img = Image.open(file_path)
                content_parts.append(img)
                log_info(logger, "Imagen cargada correctamente")
            except Exception as e:
                log_error(logger, f"Error leyendo imagen: {e}")
                return None
        
        # Crear lista de CUITs a ignorar para el prompt
        cuits_ignorar = ', '.join(db_config.CUITS_PROPIOS)
        
        # Prompt para extracción - SIMPLIFICADO
        prompt = f"""
        Analiza esta factura argentina y extrae los datos en formato JSON.
        
        IMPORTANTE:
        - El PROVEEDOR es quien EMITE (arriba en la factura)
        - NO uses estos CUITs (son del receptor): {cuits_ignorar}
        - Extrae EXACTAMENTE lo que ves, no inventes datos
        - El CUIT debe tener 11 dígitos sin guiones
        
        JSON requerido:
        {{
          "cabecera": {{
            "proveedor": {{
              "nombre": "Razón Social del EMISOR",
              "cuit": "CUIT del EMISOR (11 dígitos, sin guiones)",
              "codigo_sistema": null
            }},
            "factura": {{
              "tipo_comprobante": "FACTURA A/B/C",
              "punto_emision": "0001",
              "numero_comprobante": "00012345",
              "fecha_emision": "YYYY-MM-DD",
              "fecha_vencimiento": "YYYY-MM-DD o null",
              "moneda": "ARS",
              "cotizacion": 1.0,
              "importe_total": 0.0,
              "importe_neto_gravado": 0.0,
              "importe_iva": 0.0,
              "importe_no_gravado": 0.0,
              "importe_exento": 0.0
            }},
            "orden_compra_vinculada": {{
              "numero": "número de OC o null",
              "encontrada_en_factura": true/false
            }},
            "impuestos": [
              {{"tipo": "PERCEP_IIBB", "monto": 0.0}}
            ],
            "observaciones": ""
          }},
          "items": [
            {{
              "linea": 1,
              "descripcion": "Descripción",
              "cantidad": 0.0,
              "precio_unitario": 0.0,
              "alicuota_iva": 21.0,
              "importe_neto": 0.0,
              "importe_iva": 0.0,
              "total_linea": 0.0
            }}
          ]
        }}
        
        Responde SOLO con JSON válido, sin markdown.
        """
        content_parts.append(prompt)
        
        try:
            log_info(logger, f"{EMOJI['search']} Enviando a Gemini AI para análisis...")
            response = self.model.generate_content(content_parts)
            
            log_info(logger, "Respuesta recibida, parseando JSON...")
            json_str = response.text.replace('```json', '').replace('```', '').strip()
            data = json.loads(json_str)
            
            # VALIDACIÓN 1: Verificar que el CUIT exista
            cuit_extraido = data['cabecera']['proveedor'].get('cuit')
            nombre_extraido = data['cabecera']['proveedor'].get('nombre', '')
            
            # Si no hay CUIT pero hay nombre, buscar en BD por nombre
            if (not cuit_extraido or cuit_extraido == 'null') and nombre_extraido:
                log_warning(logger, f"⚠️ CUIT no encontrado en factura")
                log_info(logger, f"🔍 Buscando proveedor en BD por nombre: {nombre_extraido}")
                
                # Buscar en BD
                proveedores_similares = self.db.buscar_proveedor_por_nombre(nombre_extraido)
                
                if proveedores_similares and len(proveedores_similares) > 0:
                    mejor_match = proveedores_similares[0]
                    
                    # COMPLETAR datos desde la BD
                    data['cabecera']['proveedor']['cuit'] = mejor_match.get('cuit', '')
                    data['cabecera']['proveedor']['codigo_sistema'] = mejor_match['codigo']
                    
                    log_success(logger, f"✅ Proveedor encontrado en BD:")
                    log_info(logger, f"   Código: {mejor_match['codigo']}")
                    log_info(logger, f"   Nombre BD: {mejor_match['nombre']}")
                    log_info(logger, f"   CUIT BD: {mejor_match.get('cuit', 'N/A')}")
                    log_info(logger, f"   Score: {mejor_match['score']}")
                    
                    cuit_extraido = mejor_match.get('cuit', '')
                    
                    if len(proveedores_similares) > 1:
                        log_warning(logger, f"⚠️ Se encontraron {len(proveedores_similares)} proveedores similares")
                        log_warning(logger, "Se seleccionó el de mayor coincidencia")
                else:
                    log_error(logger, f"❌ No se encontró proveedor en BD con nombre: {nombre_extraido}")
                    return None
            
            # Si aún no hay CUIT, error
            if not cuit_extraido or cuit_extraido == 'null':
                log_error(logger, f"❌ ERROR: No se pudo obtener el CUIT del proveedor")
                log_error(logger, f"Proveedor detectado: {nombre_extraido or 'N/A'}")
                return None
            
            cuit_limpio = str(cuit_extraido).replace('-', '').replace(' ', '')
            
            # Validar longitud
            if len(cuit_limpio) != 11:
                log_error(logger, f"❌ ERROR: CUIT inválido (debe tener 11 dígitos): {cuit_extraido}")
                log_error(logger, f"Longitud detectada: {len(cuit_limpio)} dígitos")
                return None
            
            # Validar que sea numérico
            if not cuit_limpio.isdigit():
                log_error(logger, f"❌ ERROR: CUIT contiene caracteres no numéricos: {cuit_extraido}")
                return None
            
            # Validar prefijo (debe empezar con 20, 23, 27, 30 o 33)
            prefijo = cuit_limpio[:2]
            if prefijo not in ['20', '23', '27', '30', '33']:
                log_error(logger, f"❌ ERROR: CUIT con prefijo inválido: {prefijo}")
                log_error(logger, f"CUIT completo: {cuit_extraido}")
                return None
            
            # VALIDACIÓN 2: Verificar que el CUIT no sea uno de los nuestros
            es_cuit_propio = cuit_limpio in [c.replace('-', '').replace(' ', '') for c in db_config.CUITS_PROPIOS]
            
            if es_cuit_propio:
                log_warning(logger, f"⚠️ Gemini detectó nuestro propio CUIT ({cuit_extraido}) como proveedor")
                log_warning(logger, "Intentando recuperar proveedor por NOMBRE en BD...")
                
                # Intentar buscar por nombre
                if nombre_extraido:
                    log_info(logger, f"🔍 Buscando proveedor en BD por nombre: {nombre_extraido}")
                    proveedores_similares = self.db.buscar_proveedor_por_nombre(nombre_extraido)
                    
                    if proveedores_similares and len(proveedores_similares) > 0:
                        mejor_match = proveedores_similares[0]
                        
                        # CORREGIR datos con los de la BD
                        data['cabecera']['proveedor']['cuit'] = mejor_match.get('cuit', '')
                        data['cabecera']['proveedor']['codigo_sistema'] = mejor_match['codigo']
                        
                        log_success(logger, f"✅ Proveedor corregido desde BD:")
                        log_info(logger, f"   Código: {mejor_match['codigo']}")
                        log_info(logger, f"   Nombre: {mejor_match['nombre']}")
                        log_info(logger, f"   CUIT Correcto: {mejor_match.get('cuit', 'N/A')}")
                    else:
                        log_error(logger, f"❌ No se pudo recuperar el proveedor por nombre: {nombre_extraido}")
                        return None
                else:
                    log_error(logger, "❌ Se detectó CUIT propio y no hay nombre para buscar")
                    return None
            
            # Log de datos extraídos
            log_success(logger, "Datos extraídos correctamente")
            log_info(logger, f"{EMOJI['user']} Proveedor: {data['cabecera']['proveedor']['nombre']}")
            log_info(logger, f"{EMOJI['document']} CUIT: {data['cabecera']['proveedor']['cuit']}")
            log_info(logger, f"{EMOJI['document']} Factura: {data['cabecera']['factura']['tipo_comprobante']} {data['cabecera']['factura']['punto_emision']}-{data['cabecera']['factura']['numero_comprobante']}")
            log_info(logger, f"{EMOJI['money']} Total: ${data['cabecera']['factura']['importe_total']:,.2f}")
            log_info(logger, f"{EMOJI['bullet']} Items: {len(data['items'])}")
            
            oc_num = data['cabecera']['orden_compra_vinculada']['numero']
            if oc_num:
                log_info(logger, f"{EMOJI['document']} OC vinculada: {oc_num}")
                log_info(logger, f"   (Gemini encontró este número de OC escrito en la factura)")
            else:
                log_warning(logger, "No se encontró número de OC en la factura")
            
            return data
            
        except json.JSONDecodeError as e:
            log_error(logger, f"Error parseando JSON: {e}")
            log_error(logger, f"Respuesta de Gemini: {response.text[:200]}...")
            return None
        except Exception as e:
            log_error(logger, f"Error en extracción: {e}")
            return None
    
    def reconcile_documents(self, invoice_path: str, oc_data: List[Dict]) -> Optional[Dict]:
        """Concilia factura con datos de OC de la base de datos"""
        log_info(logger, f"{EMOJI['start']} Iniciando conciliación inteligente")
        log_info(logger, f"Factura: {os.path.basename(invoice_path)}")
        log_info(logger, f"Items de OC en BD: {len(oc_data)}")
        
        content_parts = []
        
        # Cargar factura
        if invoice_path.endswith('.pdf'):
            invoice_imgs = self.pdf_to_images(invoice_path)
        else:
            invoice_imgs = [Image.open(invoice_path)]
        
        if not invoice_imgs:
            log_error(logger, "No se pudieron cargar imágenes de la factura")
            return None
        
        log_info(logger, f"Factura cargada: {len(invoice_imgs)} imagen(es)")
        
        content_parts.append("DOCUMENTO 1: FACTURA DEL PROVEEDOR")
        for i, img in enumerate(invoice_imgs[:3], 1):
            content_parts.append(img)
            log_info(logger, f"  {EMOJI['bullet']} Imagen {i} de factura agregada")
        
        # Datos de OC como texto
        oc_text = json.dumps(oc_data, indent=2, ensure_ascii=False)
        content_parts.append(f"DOCUMENTO 2: DATOS DE ORDEN DE COMPRA (BASE DE DATOS):\n{oc_text}")
        log_info(logger, "Datos de OC agregados al prompt")
        
        prompt = """
        Actúa como Auditor de Compras experto.
        Realiza una CONCILIACIÓN INTELIGENTE entre la Factura (imagen) y los datos de la Orden de Compra (JSON).
        
        Instrucciones:
        1. Identifica items facturados en la imagen.
        2. Busca su correspondencia en el JSON de la OC (usa lógica semántica).
        3. Verifica cantidades y precios.
        4. Detecta items no autorizados.
        
        Responde SOLO con JSON:
        {
            "resumen": "Explicación del resultado",
            "match_exitoso": boolean,
            "nro_orden_compra": "número de OC",
            "discrepancias": [
                {
                    "item_factura": "...",
                    "item_oc": "...",
                    "tipo_error": "Precio/Cantidad/No Encontrado",
                    "detalle": "..."
                }
            ],
            "items_ok": [
                {
                    "descripcion": "...",
                    "cantidad": 0,
                    "precio": 0,
                    "item_oc": 1
                }
            ]
        }
        
        NO uses markdown, SOLO JSON.
        """
        content_parts.append(prompt)
        
        try:
            log_info(logger, f"{EMOJI['search']} Enviando a Gemini AI para conciliación...")
            response = self.model.generate_content(content_parts)
            
            log_info(logger, "Respuesta recibida, parseando resultado...")
            json_str = response.text.replace('```json', '').replace('```', '').strip()
            data = json.loads(json_str)
            
            # Log de resultados
            if data.get('match_exitoso'):
                log_success(logger, "Conciliación exitosa - Todo coincide")
                log_info(logger, f"Items OK: {len(data.get('items_ok', []))}")
            else:
                log_warning(logger, "Conciliación con discrepancias")
                log_warning(logger, f"Discrepancias encontradas: {len(data.get('discrepancias', []))}")
                
                for i, disc in enumerate(data.get('discrepancias', []), 1):
                    log_warning(logger, f"  {i}. {disc['tipo_error']}: {disc['detalle']}")
            
            log_info(logger, f"Resumen: {data.get('resumen', 'N/A')}")
            return data
            
        except json.JSONDecodeError as e:
            log_error(logger, f"Error parseando JSON de conciliación: {e}")
            return None
        except Exception as e:
            log_error(logger, f"Error en conciliación: {e}")
            return None
