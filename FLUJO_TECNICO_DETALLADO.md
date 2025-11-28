# 📋 FLUJO TÉCNICO DETALLADO - Sistema de Facturas IA

## 🎯 Objetivo
Automatizar 100% el procesamiento de facturas de proveedores con mínima intervención humana.

---

## 🔵 FLUJO 1: Procesamiento de OC (Identificación Automática de Proveedor)

### Entrada
- PDF/Imagen de Orden de Compra del proveedor

### Paso 1: Extracción con IA
```
Gemini AI extrae:
- Nombre del proveedor: "APAHIE S.R.L"
- CUIT/CUIL (si está visible): "30715749447"
- Items de la OC
- Totales
```

### Paso 2: Búsqueda Inteligente de Proveedor

#### 2.1 Búsqueda por CUIT (Prioridad 1 - MÁS CONFIABLE)
```sql
SELECT COD, NOMBRE, CUIT, ESTADO, DOCUM_COMPLETA, TIPO_PERSONA
FROM ISMST_PERSONAS
WHERE (CUIT = ? OR CUIL = ?)
  AND TIPO_PERSONA IN ('P', 'C')  -- Proveedor o Cliente-Proveedor
  AND ESTADO = 'ACTIVO'
```

**Resultado:**
- ✅ **Si encuentra**: COD = 59549, NOMBRE = "APAHIE S.R.L"
- ❌ **Si NO encuentra**: Ir a Paso 2.2

#### 2.2 Búsqueda por Nombre (Fallback - Si no hay CUIT)
```sql
SELECT TOP 5 
    COD, NOMBRE, CUIT, CUIL, ESTADO, DOCUM_COMPLETA,
    -- Calcular score de similitud
    CASE 
        WHEN UPPER(NOMBRE) = UPPER(?) THEN 100  -- Match exacto
        WHEN UPPER(NOMBRE) LIKE UPPER(?) + '%' THEN 90  -- Comienza con
        WHEN UPPER(NOMBRE) LIKE '%' + UPPER(?) + '%' THEN 70  -- Contiene
        ELSE 50
    END AS SCORE
FROM ISMST_PERSONAS
WHERE TIPO_PERSONA IN ('P', 'C')
  AND ESTADO = 'ACTIVO'
  AND (
      UPPER(NOMBRE) LIKE '%' + UPPER(?) + '%'
      OR UPPER(NOMBRE_CORTO) LIKE '%' + UPPER(?) + '%'
  )
ORDER BY SCORE DESC, NOMBRE
```

**Ejemplo:**
- Busca: "APAHIE"
- Encuentra: "APAHIE S.R.L" (SCORE: 90)
- Encuentra: "APAHIE DISTRIBUIDORA" (SCORE: 70)

**Resultado:**
- ✅ **Si encuentra 1+**: Retorna lista ordenada por score
- ❌ **Si NO encuentra**: Error "Proveedor no encontrado"

### Paso 3: Búsqueda de OCs del Proveedor

#### 3.1 Query Optimizada (Últimas OCs activas)
```sql
SELECT TOP 20
    OC.NRO_ORDEN_COMPRA,
    OC.FECHA,
    OC.COD_PROVEEDOR,
    OC.ESTADO,
    OC.MONTO_TOTAL,
    OC.OBSERVACION,
    OC.TIPO,
    -- Calcular pendiente de facturar total
    (
        SELECT SUM(PENDIENTE_FACTURAR)
        FROM ISMST_ORDEN_COMPRA_ITEM
        WHERE NRO_ORDEN = OC.NRO_ORDEN_COMPRA
    ) AS PENDIENTE_TOTAL,
    -- Contar items pendientes
    (
        SELECT COUNT(*)
        FROM ISMST_ORDEN_COMPRA_ITEM
        WHERE NRO_ORDEN = OC.NRO_ORDEN_COMPRA
          AND PENDIENTE_FACTURAR > 0
    ) AS ITEMS_PENDIENTES
FROM ISMST_ORDEN_COMPRA_CAB OC
WHERE OC.COD_PROVEEDOR = ?
  AND OC.ESTADO IN ('ABIERTA', 'PARCIAL')  -- Excluir CERRADAS
  AND OC.FECHA >= DATEADD(MONTH, -6, GETDATE())  -- Últimos 6 meses
ORDER BY 
    CASE WHEN OC.ESTADO = 'ABIERTA' THEN 1 ELSE 2 END,  -- ABIERTAS primero
    OC.FECHA DESC  -- Más recientes primero
```

**Resultado:**
```json
{
  "success": true,
  "proveedor": {
    "codigo": "59549",
    "nombre": "APAHIE S.R.L",
    "cuit": "30715749447",
    "match_type": "CUIT_EXACTO"  // o "NOMBRE_SIMILAR"
  },
  "ordenes_compra": [
    {
      "nro_orden": "111625",
      "fecha": "2025-11-19",
      "estado": "ABIERTA",
      "monto_total": 320562.20,
      "pendiente_total": 320562.20,
      "items_pendientes": 2,
      "observacion": "CONSERVACION Y LIMPIEZA...",
      "recomendado": true  // Si tiene pendientes > 0
    }
  ]
}
```

### Paso 4: Respuesta al Usuario
- Muestra proveedores encontrados (ordenados por score)
- Muestra OCs activas de cada proveedor
- Marca como "recomendado" si:
  - Match de CUIT exacto
  - OC tiene items pendientes de facturar
  - OC es reciente (< 3 meses)

**⚠️ IMPORTANTE**: Este flujo **NO INSERTA NADA** en la BD.

---

## 🟢 FLUJO 2: Procesamiento de FACTURA (Inserción + Asientos + Relaciones)

### Entrada
- PDF/Imagen de Factura del proveedor

### Paso 1: Extracción Completa con IA
```
Gemini AI extrae:
{
  "cabecera": {
    "proveedor": {
      "nombre": "APAHIE S.R.L",
      "cuit": "30715749447",
      "direccion": "CERRITO 1294 7 D"
    },
    "factura": {
      "tipo_comprobante": "FACTURA A",
      "punto_emision": "0001",
      "numero_comprobante": "00012345",
      "fecha_emision": "2025-11-27",
      "fecha_vencimiento": "2025-12-27",
      "moneda": "ARS",
      "cotizacion": 1.0,
      "importe_total": 50000.00,
      "importe_neto_gravado": 41322.31,
      "importe_iva": 8677.69,
      "importe_no_gravado": 0.00,
      "importe_exento": 0.00
    },
    "orden_compra_vinculada": {
      "numero": "111625",  // Extraído del PDF
      "encontrada_en_factura": true
    },
    "impuestos": [
      {"tipo": "PERCEP_IIBB", "monto": 826.45}
    ]
  },
  "items": [
    {
      "linea": 1,
      "descripcion": "Jabon bactericida para manos x 5 lts",
      "cantidad": 4.0,
      "precio_unitario": 42093.70,
      "alicuota_iva": 21.0,
      "importe_neto": 20661.16,
      "importe_iva": 4338.84,
      "total_linea": 25000.00
    },
    {
      "linea": 2,
      "descripcion": "DETERGENTE Concentrado",
      "cantidad": 4.0,
      "precio_unitario": 20085.50,
      "alicuota_iva": 21.0,
      "importe_neto": 20661.15,
      "importe_iva": 4338.85,
      "total_linea": 25000.00
    }
  ]
}
```

### Paso 2: Validación de Proveedor

#### 2.1 Búsqueda por CUIT (Prioridad 1)
```sql
SELECT COD, NOMBRE, ESTADO, DOCUM_COMPLETA, TIPO_PERSONA
FROM ISMST_PERSONAS
WHERE CUIT = '30715749447'
  AND TIPO_PERSONA IN ('P', 'C')
```

**Validaciones:**
- ✅ `ESTADO = 'ACTIVO'` (no 'BAJA')
- ✅ `DOCUM_COMPLETA = 'SI'`
- ❌ Si falla → **ERROR**: "Proveedor inactivo o documentación incompleta"

**Resultado:**
- COD_PROVEEDOR = '59549'

### Paso 3: Verificación de OC (Si existe)

#### 3.1 Verificar OC en BD
```sql
SELECT 
    OC.NRO_ORDEN_COMPRA,
    OC.ESTADO,
    OC.COD_PROVEEDOR,
    OC.MONTO_TOTAL,
    OC.FECHA
FROM ISMST_ORDEN_COMPRA_CAB OC
WHERE OC.NRO_ORDEN_COMPRA = '111625'
```

**Validaciones:**
- ✅ OC existe
- ✅ `OC.ESTADO != 'CERRADA'`
- ✅ `OC.COD_PROVEEDOR = '59549'` (coincide con proveedor de factura)
- ❌ Si falla → **ERROR**: "OC no válida o no pertenece al proveedor"

#### 3.2 Obtener Items de OC para Conciliación
```sql
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
WHERE NRO_ORDEN = '111625'
  AND ESTADO != 'ANULADO'
ORDER BY NRO_ITEM
```

**Resultado:**
```json
[
  {
    "nro_item": 1,
    "cod_producto": "11382",
    "descripcion": "Jabon bactericida para manos x 5 lts",
    "cantidad_original": 4.0,
    "precio_unitario": 42093.70,
    "pendiente_facturar": 4.0,
    "alicuota_iva": 0.21
  },
  {
    "nro_item": 2,
    "cod_producto": "15578",
    "descripcion": "DETERGENTE Concentrado",
    "cantidad_original": 4.0,
    "precio_unitario": 20085.50,
    "pendiente_facturar": 4.0,
    "alicuota_iva": 0.21
  }
]
```

### Paso 4: Conciliación Inteligente (Gemini)

**Input a Gemini:**
- Imagen de la factura
- JSON de items de OC (desde BD)

**Prompt:**
```
Compara los items de la FACTURA con los items de la ORDEN DE COMPRA.
Usa lógica semántica para emparejar (ej: "Jabon" = "Jabón bactericida").
Verifica:
1. Cantidades (facturadas <= pendientes)
2. Precios (tolerancia ±5%)
3. Items no autorizados
```

**Output:**
```json
{
  "match_exitoso": true,
  "discrepancias": [],
  "items_ok": [
    {
      "item_factura": "Jabon bactericida para manos x 5 lts",
      "item_oc": "Jabon bactericida para manos x 5 lts",
      "nro_item_oc": 1,
      "cantidad_facturada": 4.0,
      "cantidad_pendiente": 4.0,
      "precio_factura": 42093.70,
      "precio_oc": 42093.70,
      "match": "EXACTO"
    },
    {
      "item_factura": "DETERGENTE Concentrado",
      "item_oc": "DETERGENTE Concentrado",
      "nro_item_oc": 2,
      "cantidad_facturada": 4.0,
      "cantidad_pendiente": 4.0,
      "precio_factura": 20085.50,
      "precio_oc": 20085.50,
      "match": "EXACTO"
    }
  ]
}
```

### Paso 5: Inserción en Base de Datos (TRANSACCIÓN)

```sql
BEGIN TRANSACTION
```

#### 5.1 Obtener Siguiente Número de Archivo
```sql
SELECT ISNULL(MAX(CAST(NRO_ARCHIVO AS INT)) + 1, 1) AS NEXT_NRO
FROM ISMST_DOCUMENTOS_CAB
```
**Resultado:** NRO_ARCHIVO = 12345

#### 5.2 Insertar Cabecera de Factura
```sql
INSERT INTO ISMST_DOCUMENTOS_CAB (
    COMPANIA,           -- 'MOLINO' (desde .env)
    TIPO,               -- 'FACTA' (mapeado)
    NUMERO,             -- '00012345'
    EMISOR,             -- '59549' (proveedor)
    RECEPTOR,           -- 'EMPRESA' (desde .env)
    PUNTO_EMISION,      -- '0001'
    FECHA_EMISION,      -- '2025-11-27'
    FECHA_VENCIMIENTO,  -- '2025-12-27'
    MONEDA,             -- 'ARS'
    COTIZACION,         -- 1.0
    IMPORTE_TOTAL,      -- 50000.00
    NRO_ARCHIVO,        -- 12345
    ESTADO,             -- 'PENDIENTE'
    FECHA_CARGA         -- GETDATE()
) VALUES (
    'MOLINO', 'FACTA', '00012345', '59549', 'EMPRESA',
    '0001', '2025-11-27', '2025-12-27', 'ARS', 1.0,
    50000.00, 12345, 'PENDIENTE', GETDATE()
)
```

#### 5.3 Insertar Items de Factura
```sql
-- Item 1
INSERT INTO ISMST_DOCUMENTOS_ITEM (
    COMPANIA, TIPO, NUMERO, EMISOR, RECEPTOR, PUNTO_EMISION,
    NRO_ITEM, DESCRIPCION, CANTIDAD, PRECIO_UNITARIO,
    ALICUOTA_IVA, IMPORTE_NETO, IMPORTE_IVA, TOTAL_LINEA
) VALUES (
    'MOLINO', 'FACTA', '00012345', '59549', 'EMPRESA', '0001',
    1, 'Jabon bactericida para manos x 5 lts', 4.0, 42093.70,
    0.21, 20661.16, 4338.84, 25000.00
)

-- Item 2
INSERT INTO ISMST_DOCUMENTOS_ITEM (
    COMPANIA, TIPO, NUMERO, EMISOR, RECEPTOR, PUNTO_EMISION,
    NRO_ITEM, DESCRIPCION, CANTIDAD, PRECIO_UNITARIO,
    ALICUOTA_IVA, IMPORTE_NETO, IMPORTE_IVA, TOTAL_LINEA
) VALUES (
    'MOLINO', 'FACTA', '00012345', '59549', 'EMPRESA', '0001',
    2, 'DETERGENTE Concentrado', 4.0, 20085.50,
    0.21, 20661.15, 4338.85, 25000.00
)
```

#### 5.4 Insertar Impuestos/Percepciones
```sql
INSERT INTO ismsv_impuestos_documento (
    compania, tipo_doc, numero_doc, emisor, receptor,
    item, cod_impuesto, valor, punto_emision
) VALUES (
    'MOLINO', 'FACTA', '00012345', '59549', 'EMPRESA',
    0, 'PERCEP_IIBB', 826.45, '0001'
)
```

#### 5.5 Crear Relación Factura-OC (Cabecera)
```sql
INSERT INTO ISMST_RELACION_ENTRE_DOCUMENTOS (
    COMPANIA,
    TIPO1,              -- 'FACTA' (factura)
    NUMERO1,            -- '00012345'
    EMISOR1,            -- '59549'
    RECEPTOR1,          -- 'EMPRESA'
    PUNTO_EMISION1,     -- '0001'
    TIPO2,              -- 'OC' (orden de compra)
    NUMERO2,            -- '111625'
    EMISOR2,            -- '59549'
    RECEPTOR2,          -- 'EMPRESA'
    PUNTO_EMISION2,     -- NULL (OC no tiene pto emisión)
    COD_RELACION        -- 'FACTURA_OC'
) VALUES (
    'MOLINO',
    'FACTA', '00012345', '59549', 'EMPRESA', '0001',
    'OC', '111625', '59549', 'EMPRESA', NULL,
    'FACTURA_OC'
)
```

#### 5.6 Crear Relación Factura-OC (Items)
```sql
-- Relación Item 1 Factura -> Item 1 OC
INSERT INTO ISMST_RELACION_ENTRE_DOCUMENTOS_ITEM (
    TIPO1, NUMERO1, EMISOR1, RECEPTOR1, PUNTO_EMISION1,
    COD1, ITEM1,
    TIPO2, NUMERO2, EMISOR2, RECEPTOR2, PUNTO_EMISION2,
    COD2, ITEM2
) VALUES (
    'FACTA', '00012345', '59549', 'EMPRESA', '0001',
    '11382', 1,  -- Producto y item de factura
    'OC', '111625', '59549', 'EMPRESA', NULL,
    '11382', 1   -- Producto y item de OC
)

-- Relación Item 2 Factura -> Item 2 OC
INSERT INTO ISMST_RELACION_ENTRE_DOCUMENTOS_ITEM (
    TIPO1, NUMERO1, EMISOR1, RECEPTOR1, PUNTO_EMISION1,
    COD1, ITEM1,
    TIPO2, NUMERO2, EMISOR2, RECEPTOR2, PUNTO_EMISION2,
    COD2, ITEM2
) VALUES (
    'FACTA', '00012345', '59549', 'EMPRESA', '0001',
    '15578', 2,
    'OC', '111625', '59549', 'EMPRESA', NULL,
    '15578', 2
)
```

#### 5.7 Actualizar Pendiente de OC
```sql
-- Actualizar item 1 de OC
UPDATE ISMST_ORDEN_COMPRA_ITEM
SET PENDIENTE_FACTURAR = PENDIENTE_FACTURAR - 4.0
WHERE NRO_ORDEN = '111625' AND NRO_ITEM = 1

-- Actualizar item 2 de OC
UPDATE ISMST_ORDEN_COMPRA_ITEM
SET PENDIENTE_FACTURAR = PENDIENTE_FACTURAR - 4.0
WHERE NRO_ORDEN = '111625' AND NRO_ITEM = 2

-- Si todos los items tienen PENDIENTE = 0, cerrar OC
UPDATE ISMST_ORDEN_COMPRA_CAB
SET ESTADO = 'CERRADA'
WHERE NRO_ORDEN_COMPRA = '111625'
  AND NOT EXISTS (
      SELECT 1 FROM ISMST_ORDEN_COMPRA_ITEM
      WHERE NRO_ORDEN = '111625' AND PENDIENTE_FACTURAR > 0
  )
```

### Paso 6: Generación de Asiento Contable Automático

#### 6.1 Obtener Ejercicio Contable
```sql
SELECT EJER_COD
FROM ISMST_EJERCICIOS
WHERE EJER_FECHAINICIO <= '2025-11-27'
  AND EJER_FECHAFIN >= '2025-11-27'
```
**Resultado:** EJER_COD = '2025'

#### 6.2 Obtener Siguiente Número de Asiento
```sql
SELECT ISNULL(MAX(AS_NRO), 0) + 1 AS NEXT_ASIENTO
FROM ISMST_ASIENTOS
```
**Resultado:** AS_NRO = 50001

#### 6.3 Insertar Cabecera de Asiento
```sql
INSERT INTO ISMST_ASIENTOS (
    AS_NRO,             -- 50001
    AS_FECHAREG,        -- GETDATE()
    AS_DESCRIPCION,     -- 'Factura 00012345 - APAHIE S.R.L'
    AS_TIPOCOMP,        -- 'FACTA'
    AS_CLIENTE,         -- 0
    AS_PROVEEDOR,       -- '59549'
    AS_MODO,            -- 'Automático'
    AS_CIERRE,          -- ''
    AS_INTEGRABLE,      -- 'Verdadero'
    AS_EMPRESA,         -- 'MOLINO'
    AS_REVERSIBLE,      -- 'Falso'
    AS_REVFECHA,        -- GETDATE()
    AS_CONCEPTO,        -- 'Proveedores'
    AS_EJERCICIO,       -- '2025'
    AS_FECHAMOV         -- '2025-11-27'
) VALUES (
    50001, GETDATE(), 'Factura 00012345 - APAHIE S.R.L',
    'FACTA', 0, '59549', 'Automático', '', 'Verdadero',
    'MOLINO', 'Falso', GETDATE(), 'Proveedores', '2025', '2025-11-27'
)
```

#### 6.4 Insertar Movimientos Contables

**Movimiento 1: HABER - Pasivo (Proveedores)**
```sql
INSERT INTO ISMST_MOVIMIENTOS (
    MO_ASNRO,           -- 50001
    MO_CUENTA,          -- '210101' (Proveedores - desde .env)
    MO_COMPROBANTE,     -- '00012345'
    MO_FECHA,           -- '2025-11-27'
    MO_DESCRIPCION,     -- 'Factura 00012345 - APAHIE S.R.L'
    MO_IMPORTE,         -- 50000.00 (TOTAL)
    MO_POSICION,        -- 'HABER'
    MO_CC,              -- '' (centro de costo)
    MO_FECHAEFECTIVA,   -- '2025-11-27'
    MO_MNG,             -- 0
    MO_EMPRESA,         -- 'MOLINO'
    MO_EJERCICIO        -- '2025'
) VALUES (
    50001, '210101', '00012345', '2025-11-27',
    'Factura 00012345 - APAHIE S.R.L',
    50000.00, 'HABER', '', '2025-11-27', 0, 'MOLINO', '2025'
)
```

**Movimiento 2: DEBE - IVA Crédito Fiscal**
```sql
INSERT INTO ISMST_MOVIMIENTOS (
    MO_ASNRO, MO_CUENTA, MO_COMPROBANTE, MO_FECHA,
    MO_DESCRIPCION, MO_IMPORTE, MO_POSICION, MO_CC,
    MO_FECHAEFECTIVA, MO_MNG, MO_EMPRESA, MO_EJERCICIO
) VALUES (
    50001, '110501', '00012345', '2025-11-27',
    'IVA Crédito Fiscal', 8677.69, 'DEBE', '',
    '2025-11-27', 0, 'MOLINO', '2025'
)
```

**Movimiento 3: DEBE - Gasto/Compra**
```sql
INSERT INTO ISMST_MOVIMIENTOS (
    MO_ASNRO, MO_CUENTA, MO_COMPROBANTE, MO_FECHA,
    MO_DESCRIPCION, MO_IMPORTE, MO_POSICION, MO_CC,
    MO_FECHAEFECTIVA, MO_MNG, MO_EMPRESA, MO_EJERCICIO
) VALUES (
    50001, '520101', '00012345', '2025-11-27',
    'Gasto/Compra', 41322.31, 'DEBE', '',
    '2025-11-27', 0, 'MOLINO', '2025'
)
```

**Movimiento 4: DEBE - Percepción IIBB**
```sql
INSERT INTO ISMST_MOVIMIENTOS (
    MO_ASNRO, MO_CUENTA, MO_COMPROBANTE, MO_FECHA,
    MO_DESCRIPCION, MO_IMPORTE, MO_POSICION, MO_CC,
    MO_FECHAEFECTIVA, MO_MNG, MO_EMPRESA, MO_EJERCICIO
) VALUES (
    50001, '520101', '00012345', '2025-11-27',
    'Percepción PERCEP_IIBB', 826.45, 'DEBE', '',
    '2025-11-27', 0, 'MOLINO', '2025'
)
```

**Verificación de Balance:**
```
DEBE:  8677.69 + 41322.31 + 826.45 = 50826.45 ❌ ERROR!
HABER: 50000.00

CORRECCIÓN: El total de percepciones ya está incluido en el total
```

**Balance Correcto:**
```
DEBE:  8677.69 (IVA) + 41322.31 (Neto) = 50000.00 ✅
HABER: 50000.00 ✅
```

### Paso 7: COMMIT de Transacción
```sql
COMMIT TRANSACTION
```

**✅ Resultado Final:**
- Factura registrada en `ISMST_DOCUMENTOS_CAB` (NRO_ARCHIVO: 12345)
- Items guardados en `ISMST_DOCUMENTOS_ITEM` (2 items)
- Percepciones en `ismsv_impuestos_documento`
- Relación Factura-OC creada en `ISMST_RELACION_ENTRE_DOCUMENTOS`
- Relación items en `ISMST_RELACION_ENTRE_DOCUMENTOS_ITEM`
- OC actualizada (pendientes descontados)
- Asiento contable generado (AS_NRO: 50001)
- Movimientos contables balanceados

---

## 📊 Resumen de Tablas Afectadas

| Tabla | Operación | Cuándo | Datos Clave |
|-------|-----------|--------|-------------|
| `ISMST_PERSONAS` | SELECT | Validar proveedor | COD, CUIT, ESTADO |
| `ISMST_ORDEN_COMPRA_CAB` | SELECT | Verificar OC | NRO_ORDEN, ESTADO, COD_PROVEEDOR |
| `ISMST_ORDEN_COMPRA_ITEM` | SELECT | Obtener items OC | PENDIENTE_FACTURAR |
| `ISMST_ORDEN_COMPRA_ITEM` | UPDATE | Descontar pendiente | PENDIENTE_FACTURAR -= cantidad |
| `ISMST_ORDEN_COMPRA_CAB` | UPDATE | Cerrar OC si completa | ESTADO = 'CERRADA' |
| `ISMST_DOCUMENTOS_CAB` | INSERT | Guardar factura | NRO_ARCHIVO, IMPORTE_TOTAL |
| `ISMST_DOCUMENTOS_ITEM` | INSERT | Guardar items | NRO_ITEM, CANTIDAD, PRECIO |
| `ismsv_impuestos_documento` | INSERT | Guardar percepciones | cod_impuesto, valor |
| `ISMST_RELACION_ENTRE_DOCUMENTOS` | INSERT | Vincular Factura-OC | TIPO1='FACTA', TIPO2='OC' |
| `ISMST_RELACION_ENTRE_DOCUMENTOS_ITEM` | INSERT | Vincular items | ITEM1, ITEM2 |
| `ISMST_EJERCICIOS` | SELECT | Obtener ejercicio | EJER_COD |
| `ISMST_ASIENTOS` | INSERT | Crear asiento | AS_NRO, AS_DESCRIPCION |
| `ISMST_MOVIMIENTOS` | INSERT | Crear movimientos | MO_POSICION (DEBE/HABER) |

---

## 🤖 Nivel de Automatización

### ✅ 100% Automático (Sin intervención)
1. Extracción de datos de PDF
2. Búsqueda de proveedor por CUIT
3. Validación de proveedor
4. Verificación de OC
5. Conciliación de items
6. Inserción en BD
7. Generación de asientos contables
8. Actualización de pendientes
9. Relación entre documentos

### ⚠️ Requiere Confirmación (Casos especiales)
1. Si NO se encuentra CUIT → Usuario elige de lista de nombres similares
2. Si hay discrepancias en conciliación → Usuario decide si continuar
3. Si NO hay ejercicio contable → Usuario debe crear ejercicio primero

### ❌ Requiere Intervención Manual
1. Proveedor nuevo (no existe en BD) → Crear en sistema
2. OC no existe → Crear OC primero o procesar sin OC
3. Documentación incompleta → Completar datos del proveedor

---

## 🔄 Próximos Pasos de Implementación

1. **Actualizar código con búsqueda por CUIT primero**
2. **Implementar filtrado inteligente de OCs**
3. **Agregar inserción de relaciones entre documentos**
4. **Crear interfaz web para visualizar todo el flujo**
5. **Agregar manejo de remitos (ISMST_RELACION_ENTRE_DOCUMENTOS con TIPO2='REMT')**

---

## ❓ Preguntas Pendientes

1. **Remitos**: ¿Cómo se vinculan? ¿Factura -> Remito -> OC o Factura -> OC directamente?
2. **Centro de Costos**: ¿Cómo se determina el CC para los movimientos contables?
3. **Cuentas Contables**: ¿Hay una tabla de mapeo Producto -> Cuenta Contable?
4. **Tolerancia de Precios**: ¿Qué % de diferencia es aceptable en la conciliación?
5. **Percepciones**: ¿Van en el balance del asiento o son informativas?

---

**Documento creado:** 2025-11-27  
**Versión:** 1.0  
**Autor:** Sistema IA + Usuario
