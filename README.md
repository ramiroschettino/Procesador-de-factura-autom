# 🤖 Sistema Integrado de Facturas IA

Sistema completo de procesamiento inteligente de facturas con interfaz web moderna.

## 🚀 Inicio Rápido

### Opción 1: Con archivos .bat (Recomendado)

1. **Configuración inicial** (solo la primera vez):
   ```cmd
   setup.bat
   ```

2. **Iniciar el backend** (en una ventana CMD):
   ```cmd
   run_backend.bat
   ```

3. **Abrir la interfaz web** (en otra ventana CMD):
   ```cmd
   run_web.bat
   ```

### Opción 2: Manual desde CMD

#### Configuración inicial:
```cmd
cd c:\Isms2\Compras\Facturas O.C\FacturasIA_Sistema

REM Crear entorno virtual
python -m venv venv

REM Activar entorno virtual
venv\Scripts\activate

REM Instalar dependencias
pip install -r requirements.txt
```

#### Ejecutar el sistema:

**Terminal 1 - Backend:**
```cmd
cd c:\Isms2\Compras\Facturas O.C\FacturasIA_Sistema
venv\Scripts\activate
cd backend
python api.py
```

**Terminal 2 - Navegador:**
```cmd
REM Abrir en el navegador
start http://localhost:5000
```

## 📦 ¿Qué incluye este sistema?

### ✨ Funcionalidades

1. **Extracción Inteligente de Facturas**
   - Sube PDF o imágenes de facturas
   - Gemini AI extrae todos los datos automáticamente
   - Detecta: proveedor, CUIT, items, totales, impuestos, OC vinculada

2. **Conciliación con Órdenes de Compra**
   - Compara factura vs OC automáticamente
   - Detecta discrepancias en precios y cantidades
   - Identifica items no autorizados

3. **Integración con Base de Datos**
   - Valida proveedor contra `ISMST_PERSONAS`
   - Verifica OC en `ismsv_orden_compra`
   - Inserta en `ISMST_DOCUMENTOS_CAB` y `ISMST_DOCUMENTOS_ITEM`
   - Actualiza pendientes de facturación

4. **Interfaz Web Moderna**
   - Drag & drop de archivos
   - Visualización en tiempo real
   - Historial de facturas procesadas
   - Diseño responsive y premium

### 🏗️ Arquitectura

```
┌─────────────────┐
│  Frontend Web   │  ← Interfaz moderna (HTML/CSS/JS)
│  (Puerto 5000)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   API Flask     │  ← Endpoints REST
│   (backend/)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  GeminiProcessor│  ← Extracción y conciliación con IA
│  DatabaseInteg. │  ← Integración con SQL Server
└─────────────────┘
```

## 🔧 Configuración

### Variables de Entorno (`.env`)

```env
# API Key de Gemini
GEMINI_API_KEY=AIzaSyBtjRLCMDPqQIWGtQoNGqJwjgBvtNxgPvY

# Base de Datos
DB_SERVER=10.1.1.17
DB_NAME=ISMS_MOLINO
DB_USER=testing
DB_PASSWORD=Test6740

# Configuración
COMPANIA=MOLINO
RECEPTOR=EMPRESA
```

## 📖 Uso de la Interfaz Web

1. **Cargar Factura**
   - Arrastra el PDF/imagen de la factura
   - O haz clic para seleccionar archivo

2. **Cargar OC (Opcional)**
   - Si quieres conciliar, sube también la orden de compra

3. **Procesar**
   - **"Procesar Completo"**: Extrae, concilia y guarda en BD
   - **"Solo Extraer Datos"**: Solo extrae sin guardar

4. **Ver Resultados**
   - Visualiza los datos extraídos
   - Revisa discrepancias de conciliación
   - Confirma guardado en base de datos

5. **Historial**
   - Consulta facturas procesadas anteriormente
   - Haz clic en cualquier item para ver detalles

## 🔍 Endpoints de la API

### `GET /api/health`
Verifica estado del servidor

### `POST /api/upload`
Sube archivos de factura y OC
```json
FormData: {
  "factura": File,
  "orden_compra": File (opcional)
}
```

### `POST /api/process`
Procesa factura completa (extrae + concilia + guarda)
```json
{
  "factura_filename": "factura.pdf",
  "oc_filename": "oc.pdf"
}
```

### `POST /api/extract`
Solo extrae datos de la factura
```json
{
  "factura_filename": "factura.pdf"
}
```

### `POST /api/reconcile`
Solo concilia factura con OC
```json
{
  "factura_filename": "factura.pdf",
  "oc_filename": "oc.pdf"
}
```

### `GET /api/history`
Obtiene historial de facturas procesadas

### `GET /api/result/<filename>`
Obtiene resultado específico

## 🆚 Comparación con Sistema Legacy

| Característica | VB6 (trunk) | Sistema IA |
|----------------|-------------|------------|
| Entrada datos | Manual | Automática (OCR + IA) |
| Validación OC | Manual | IA + Reglas |
| Interfaz | Windows Forms | Web moderna |
| Tiempo/factura | 10-15 min | 30 seg |
| Errores humanos | Frecuentes | Mínimos |
| Acceso remoto | No | Sí (web) |

## 🐛 Solución de Problemas

### ❌ Error: "API key not valid. Please pass a valid API key"

**Causa**: La API Key de Gemini en el archivo `.env` no es válida o ha expirado.

**Solución rápida**:

1. **Ejecuta el verificador automático**:
   ```cmd
   verificar_api_key.bat
   ```

2. **Si la API Key es inválida**, obtén una nueva:
   - Ve a: https://aistudio.google.com/app/apikey
   - Crea una nueva API Key
   - Copia la key generada

3. **Actualiza el archivo `.env`**:
   ```env
   GEMINI_API_KEY=TU_NUEVA_API_KEY_AQUI
   ```

4. **Reinicia el backend**:
   - Presiona `Ctrl+C` en la ventana del backend
   - Ejecuta `run_backend.bat` nuevamente

📖 **Guía detallada**: Ver `CONFIGURAR_API_KEY.md`

---

### ❌ Error: "Error obteniendo historial: 'NoneType' object has no attribute 'get'"

**Causa**: El endpoint `/api/history` intentaba acceder a datos de facturas que fallaron en el procesamiento.

**Solución**: ✅ **Ya está corregido** en la última versión del código.

Si sigues viendo este error:
1. Detén el backend (`Ctrl+C`)
2. Reinicia con `run_backend.bat`
3. El error ya no debería aparecer

---

### El backend no inicia
```cmd
# Verificar que el venv está activado
venv\Scripts\activate

# Reinstalar dependencias
pip install -r requirements.txt
```

### Error de conexión a BD
```cmd
# Verificar connection string en .env
# Probar conexión:
cd ..
python test_conexion_db.py
```

### La interfaz no carga
```cmd
# Verificar que el backend esté corriendo
# Debe mostrar: "Running on http://0.0.0.0:5000"

# Abrir en navegador:
start http://localhost:5000
```

### Verificación completa del sistema
```cmd
# Ejecuta el verificador de API Key
verificar_api_key.bat

# Esto te dirá:
# ✅ Si el archivo .env existe
# ✅ Si la API Key está configurada
# ✅ Si la API Key es válida
# ✅ Si puedes conectarte a Gemini
```

## 📁 Estructura de Archivos

```
FacturasIA_Sistema/
├── backend/
│   ├── app.py                  # Lógica principal (Gemini + DB)
│   ├── api.py                  # API REST con Flask
│   ├── gemini_processor.py     # Procesamiento con Gemini AI
│   ├── database_integrator.py  # Integración con SQL Server
│   ├── accounting.py           # Módulo de contabilidad
│   ├── db_config.py            # Configuración de BD
│   └── logging_config.py       # Configuración de logs
├── frontend/
│   ├── index.html              # Interfaz web
│   ├── styles.css              # Estilos premium
│   └── app.js                  # Lógica frontend
├── data/
│   ├── uploads/                # Archivos subidos
│   └── processed/              # Resultados JSON
├── config/
├── .env                        # Variables de entorno
├── requirements.txt            # Dependencias Python
├── setup.bat                   # Configuración inicial
├── run_backend.bat             # Iniciar backend
├── run_web.bat                 # Abrir interfaz
├── verificar_api_key.bat       # 🆕 Verificar API Key
├── verificar_api_key.py        # 🆕 Script de verificación
├── CONFIGURAR_API_KEY.md       # 🆕 Guía de configuración
├── GUIA_USUARIO.md             # Guía para usuarios
├── FLUJO_TECNICO_DETALLADO.md  # Documentación técnica
└── README.md                   # Este archivo
```

## 🔐 Seguridad

- ✅ API Key en `.env` (git-ignored)
- ✅ Validación de tipos de archivo
- ✅ Límite de tamaño (16MB)
- ✅ Transacciones con rollback
- ✅ Validación de proveedores

## 🚀 Próximas Mejoras

- [ ] Autenticación de usuarios
- [ ] Procesamiento por lotes
- [ ] Exportación a Excel
- [ ] Notificaciones por email
- [ ] Dashboard con estadísticas
- [ ] Integración con sistema de aprobaciones

## 📞 Soporte

- **Documentación del sistema legacy**: Ver `trunk/`
- **Ejemplos de integración**: Ver `integracion_ejemplo.py`
- **Pruebas de DB**: Ver `test_conexion_db.py`

---

**Sistema desarrollado para automatizar el procesamiento de facturas** 🤖✨
