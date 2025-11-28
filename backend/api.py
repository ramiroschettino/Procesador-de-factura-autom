"""
API REST para el Sistema de Facturas IA
Expone endpoints para la interfaz web
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime
from app import FacturasIASystem
import logging

app = Flask(__name__)
CORS(app)

# Configuración
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'data', 'uploads')
PROCESSED_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'data', 'processed')
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Sistema
sistema = None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/api/health', methods=['GET'])
def health_check():
    """Verifica que el servicio esté funcionando"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Sube una factura u OC para procesar"""
    if 'factura' not in request.files:
        return jsonify({'error': 'No se envió archivo'}), 400
    
    factura_file = request.files['factura']
    
    if factura_file.filename == '':
        return jsonify({'error': 'Nombre de archivo vacío'}), 400
    
    if not allowed_file(factura_file.filename):
        return jsonify({'error': 'Tipo de archivo no permitido'}), 400
    
    # Guardar archivo
    factura_filename = secure_filename(factura_file.filename)
    factura_path = os.path.join(app.config['UPLOAD_FOLDER'], factura_filename)
    factura_file.save(factura_path)
    
    return jsonify({
        'message': 'Archivo subido correctamente',
        'factura': factura_filename
    })


@app.route('/api/process', methods=['POST'])
def process_invoice():
    """Procesa una factura completa"""
    data = request.json
    
    if not data or 'factura_filename' not in data:
        return jsonify({'error': 'Falta nombre de archivo'}), 400
    
    factura_path = os.path.join(app.config['UPLOAD_FOLDER'], data['factura_filename'])
    
    if not os.path.exists(factura_path):
        return jsonify({'error': 'Archivo de factura no encontrado'}), 404
    
    try:
        global sistema
        if sistema is None:
            sistema = FacturasIASystem()
        
        # Ya no pasamos oc_path, el sistema busca en BD
        result = sistema.process_invoice_file(factura_path)
        
        # Guardar resultado
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        result_filename = f"result_{timestamp}.json"
        result_path = os.path.join(PROCESSED_FOLDER, result_filename)
        
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error procesando factura: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/extract', methods=['POST'])
def extract_only():
    """Solo extrae datos de la factura (sin guardar en DB)"""
    data = request.json
    
    if not data or 'factura_filename' not in data:
        return jsonify({'error': 'Falta nombre de archivo'}), 400
    
    factura_path = os.path.join(app.config['UPLOAD_FOLDER'], data['factura_filename'])
    
    if not os.path.exists(factura_path):
        return jsonify({'error': 'Archivo no encontrado'}), 404
    
    try:
        global sistema
        if sistema is None:
            sistema = FacturasIASystem()
        
        invoice_data = sistema.gemini.extract_invoice_data(factura_path)
        
        if not invoice_data:
            return jsonify({'error': 'Error extrayendo datos'}), 500
        
        return jsonify({
            'success': True,
            'data': invoice_data
        })
        
    except Exception as e:
        logging.error(f"Error en extracción: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/reconcile', methods=['POST'])
def reconcile_only():
    """Solo concilia factura con OC de BD (sin guardar)"""
    data = request.json
    
    if not data or 'factura_filename' not in data:
        return jsonify({'error': 'Falta archivo de factura'}), 400
    
    factura_path = os.path.join(app.config['UPLOAD_FOLDER'], data['factura_filename'])
    nro_oc = data.get('nro_oc')  # Opcional: forzar nro OC
    
    if not os.path.exists(factura_path):
        return jsonify({'error': 'Archivo no encontrado'}), 404
    
    try:
        global sistema
        if sistema is None:
            sistema = FacturasIASystem()
        
        # 1. Extraer datos para obtener Nro OC si no se pasó
        if not nro_oc:
            invoice_data = sistema.gemini.extract_invoice_data(factura_path)
            if invoice_data:
                nro_oc = invoice_data['cabecera']['orden_compra_vinculada']['numero']
        
        if not nro_oc:
            return jsonify({'error': 'No se encontró número de OC en la factura'}), 400
            
        # 2. Buscar items en BD
        items_oc = sistema.db.obtener_items_oc(nro_oc)
        if not items_oc:
            return jsonify({'error': f'OC {nro_oc} no encontrada en BD'}), 404
            
        # 3. Conciliar
        reconciliation = sistema.gemini.reconcile_documents(factura_path, items_oc)
        
        if not reconciliation:
            return jsonify({'error': 'Error en conciliación'}), 500
        
        return jsonify({
            'success': True,
            'data': reconciliation
        })
        
    except Exception as e:
        logging.error(f"Error en conciliación: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/process_oc_auto', methods=['POST'])
def process_oc_auto():
    """
    🤖 AUTOMATIZACIÓN TOTAL: Procesa OC del proveedor y busca automáticamente en BD
    1. Extrae nombre y CUIT del proveedor de la OC (PDF)
    2. Busca por CUIT primero (más confiable), luego por nombre
    3. Retorna proveedores candidatos y sus OCs activas (filtradas)
    """
    data = request.json
    
    if not data or 'oc_filename' not in data:
        return jsonify({'error': 'Falta archivo de OC'}), 400
    
    oc_path = os.path.join(app.config['UPLOAD_FOLDER'], data['oc_filename'])
    
    if not os.path.exists(oc_path):
        return jsonify({'error': 'Archivo de OC no encontrado'}), 404
    
    try:
        global sistema
        if sistema is None:
            sistema = FacturasIASystem()
        
        # 1. Extraer proveedor de la OC con Gemini
        logging.info("🔍 Extrayendo proveedor de OC...")
        oc_data = sistema.gemini.extract_invoice_data(oc_path)
        
        if not oc_data or not oc_data.get('cabecera', {}).get('proveedor'):
            return jsonify({'error': 'No se pudo extraer el proveedor de la OC'}), 500
        
        proveedor_data = oc_data['cabecera']['proveedor']
        nombre_proveedor = proveedor_data.get('nombre', '')
        cuit_proveedor = proveedor_data.get('cuit', '')
        
        logging.info(f"📋 Datos extraídos - Nombre: {nombre_proveedor}, CUIT: {cuit_proveedor}")
        
        proveedores_encontrados = []
        match_type = None
        
        # 2. PRIORIDAD 1: Buscar por CUIT (más confiable)
        if cuit_proveedor:
            logging.info(f"🔍 Buscando por CUIT: {cuit_proveedor}")
            cod_prov = sistema.db.buscar_proveedor_por_cuit(cuit_proveedor)
            
            if cod_prov:
                # Obtener datos completos del proveedor
                query = "SELECT COD, NOMBRE, NOMBRE_CORTO, CUIT, CUIL, ESTADO, DOCUM_COMPLETA FROM ISMST_PERSONAS WHERE COD = ?"
                sistema.db.cursor.execute(query, cod_prov)
                row = sistema.db.cursor.fetchone()
                
                if row:
                    proveedores_encontrados.append({
                        'codigo': row.COD,
                        'nombre': row.NOMBRE,
                        'nombre_corto': row.NOMBRE_CORTO if row.NOMBRE_CORTO else '',
                        'cuit': row.CUIT if row.CUIT else '',
                        'cuil': row.CUIL if row.CUIL else '',
                        'estado': row.ESTADO,
                        'docum_completa': row.DOCUM_COMPLETA,
                        'activo': row.ESTADO == 'ACTIVO' and row.DOCUM_COMPLETA == 'SI',
                        'score': 100,
                        'match_type': 'CUIT_EXACTO'
                    })
                    match_type = 'CUIT_EXACTO'
                    logging.info(f"✅ Match por CUIT: {row.NOMBRE}")
        
        # 3. FALLBACK: Si no se encontró por CUIT, buscar por nombre
        if not proveedores_encontrados and nombre_proveedor:
            logging.info(f"🔍 Buscando por nombre: {nombre_proveedor}")
            proveedores_encontrados = sistema.db.buscar_proveedor_por_nombre(nombre_proveedor)
            match_type = 'NOMBRE_SIMILAR'
            
            if proveedores_encontrados:
                logging.info(f"✅ Encontrados {len(proveedores_encontrados)} proveedores similares")
                for prov in proveedores_encontrados:
                    prov['match_type'] = 'NOMBRE_SIMILAR'
        
        # 4. Si no se encontró nada
        if not proveedores_encontrados:
            return jsonify({
                'success': False,
                'message': f'No se encontraron proveedores con CUIT "{cuit_proveedor}" o nombre "{nombre_proveedor}"',
                'nombre_extraido': nombre_proveedor,
                'cuit_extraido': cuit_proveedor,
                'proveedores': []
            })
        
        # 5. Para cada proveedor, obtener sus OCs activas (filtradas)
        resultado = {
            'success': True,
            'nombre_extraido': nombre_proveedor,
            'cuit_extraido': cuit_proveedor,
            'match_type': match_type,
            'proveedores': []
        }
        
        for prov in proveedores_encontrados:
            # Usar el nuevo método optimizado
            ocs = sistema.db.obtener_ocs_activas_proveedor(prov['codigo'])
            
            resultado['proveedores'].append({
                **prov,
                'ordenes_compra': ocs,
                'tiene_ocs_activas': len(ocs) > 0,
                'ocs_con_pendientes': sum(1 for oc in ocs if oc['items_pendientes'] > 0)
            })
        
        # 6. Marcar como recomendado el mejor match
        if match_type == 'CUIT_EXACTO' and resultado['proveedores']:
            resultado['proveedores'][0]['recomendado'] = True
        elif match_type == 'NOMBRE_SIMILAR' and resultado['proveedores']:
            # Recomendar el de mayor score que tenga OCs con pendientes
            for prov in resultado['proveedores']:
                if prov['ocs_con_pendientes'] > 0:
                    prov['recomendado'] = True
                    break
        
        return jsonify(resultado)
        
    except Exception as e:
        logging.error(f"❌ Error en procesamiento automático de OC: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/history', methods=['GET'])
def get_history():
    """Obtiene historial de facturas procesadas"""
    try:
        results = []
        for filename in os.listdir(PROCESSED_FOLDER):
            if filename.endswith('.json'):
                filepath = os.path.join(PROCESSED_FOLDER, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Navegación segura para evitar errores con None
                    extraction = data.get('extraction')
                    preview = {}
                    if extraction and isinstance(extraction, dict):
                        cabecera = extraction.get('cabecera')
                        if cabecera and isinstance(cabecera, dict):
                            factura = cabecera.get('factura')
                            if factura and isinstance(factura, dict):
                                preview = factura
                    
                    results.append({
                        'filename': filename,
                        'timestamp': filename.replace('result_', '').replace('.json', ''),
                        'success': data.get('success', False),
                        'preview': preview,
                        'has_errors': len(data.get('errors', [])) > 0,
                        'error_message': data.get('errors', [None])[0] if data.get('errors') else None
                    })
        
        results.sort(key=lambda x: x['timestamp'], reverse=True)
        return jsonify(results)
        
    except Exception as e:
        logging.error(f"Error obteniendo historial: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/result/<filename>', methods=['GET'])
def get_result(filename):
    """Obtiene un resultado específico"""
    try:
        filepath = os.path.join(PROCESSED_FOLDER, filename)
        if not os.path.exists(filepath):
            return jsonify({'error': 'Resultado no encontrado'}), 404
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return jsonify(data)
        
    except Exception as e:
        logging.error(f"Error obteniendo resultado: {e}")
        return jsonify({'error': str(e)}), 500


# Servir frontend
@app.route('/')
def serve_frontend():
    frontend_path = os.path.join(os.path.dirname(__file__), '..', 'frontend')
    return send_from_directory(frontend_path, 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    frontend_path = os.path.join(os.path.dirname(__file__), '..', 'frontend')
    return send_from_directory(frontend_path, path)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
