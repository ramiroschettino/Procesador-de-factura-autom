# 📖 Guía del Sistema de Facturas IA - Para Usuarios

## 🎯 ¿Qué hace este sistema?

Este sistema **automatiza completamente** el procesamiento de facturas de proveedores. En lugar de que alguien tenga que tipear manualmente todos los datos de una factura, el sistema:

1. **Lee la factura** (como si fuera un humano leyendo un PDF)
2. **Busca al proveedor** en nuestra base de datos
3. **Verifica** si la factura coincide con alguna Orden de Compra que tengamos
4. **Guarda todo** en la base de datos
5. **Genera el asiento contable** automáticamente

---

## 🔵 FLUJO 1: Identificar Proveedor (desde una Factura)

### ¿Cuándo usar esto?
Cuando te llega una **FACTURA** de un proveedor y querés:
- Identificar automáticamente quién es ese proveedor en nuestro sistema
- Ver qué Órdenes de Compra tenemos **pendientes** con él
- Verificar si la factura podría corresponder a alguna OC existente

> **IMPORTANTE**: Este flujo **NO procesa ni guarda** la factura. Solo la usa para identificar al proveedor y mostrar sus OCs pendientes.

### ¿Qué hace el sistema?

#### Paso 1: Leer la Factura
- Subís el PDF de la **FACTURA** que te envió el proveedor
- La inteligencia artificial **lee el documento** y extrae:
  - Nombre del proveedor (ej: "APAHIE S.R.L")
  - CUIT del proveedor (ej: "30-71574944-7")

**Nota**: El sistema extrae más datos de la factura (items, totales, etc.) pero en este flujo solo usa el nombre y CUIT del proveedor.

#### Paso 2: Buscar en Nuestra Base de Datos

**Primero intenta por CUIT** (es más confiable):
- Busca en nuestra tabla de Personas/Proveedores si existe alguien con ese CUIT
- Verifica que el proveedor esté **ACTIVO** (no dado de baja)
- Verifica que tenga la **documentación completa**

**Si no encuentra por CUIT, busca por nombre**:
- Busca proveedores con nombres similares
- Por ejemplo, si la factura dice "APAHIE", encuentra "APAHIE S.R.L" o "APAHIE DISTRIBUIDORA"
- Le da un puntaje a cada coincidencia:
  - 100 = Match exacto
  - 90 = Comienza con ese nombre
  - 85 = El nombre corto comienza así
  - 70 = Contiene ese nombre
  - 65 = El nombre corto lo contiene

#### Paso 3: Mostrar las Órdenes de Compra que YA TENEMOS con ese Proveedor

Una vez identificado el proveedor, el sistema busca **en nuestras OCs**:
- **Órdenes de Compra ABIERTAS** (que todavía no se facturaron completamente)
- **Órdenes de Compra PARCIALES** (que se facturaron solo una parte)
- **De los últimos 6 meses** (para no mostrar cosas muy viejas)

Para cada OC te muestra:
- Número de OC
- Fecha
- Estado (ABIERTA/PARCIAL)
- Monto total
- **Cuánto falta facturar** (pendiente)
- **Cuántos items faltan facturar**

#### Paso 4: Recomendación Automática

El sistema marca como **"RECOMENDADO"**:
- Si encontró el proveedor por CUIT exacto (es casi seguro que es el correcto)
- Si la OC tiene items pendientes de facturar (probablemente es la que corresponde a esta factura)

### ¿Qué pasa si NO encuentra el proveedor?

Te muestra un mensaje: "No se encontraron proveedores con ese CUIT o nombre"

**Solución**: Tenés que crear el proveedor manualmente en el sistema primero.

### Ejemplo Práctico:

```
📄 Llega factura de "APAHIE S.R.L" CUIT 30-71574944-7
    ↓
🔍 Sistema busca por CUIT en nuestra BD
    ↓
✅ Encuentra: APAHIE S.R.L (Código: 59549)
    ↓
🔍 Busca OCs activas de ese proveedor
    ↓
📋 Muestra:
    • OC 111625 - $320,562.20 - Pendiente: $320,562.20 (2 items) ⭐ RECOMENDADO
    • OC 111580 - $150,000.00 - Pendiente: $75,000.00 (1 item)
    ↓
👤 Usuario decide: "Sí, es la OC 111625"
    ↓
➡️ Ahora puede usar FLUJO 2 para procesar la factura completa
```

---

## 🟢 FLUJO 2: Procesar Factura Completa

### ¿Cuándo usar esto?
Cuando te llega la **factura** de un proveedor y querés:
- Guardarla en el sistema
- Verificar que coincida con la Orden de Compra
- Generar el asiento contable automáticamente

### ¿Qué hace el sistema?

#### Paso 1: Leer la Factura

La inteligencia artificial lee el PDF de la factura y extrae **TODO**:

**Datos del Proveedor:**
- Nombre: "APAHIE S.R.L"
- CUIT: "30-71574944-7"
- Dirección

**Datos de la Factura:**
- Tipo: "FACTURA A"
- Punto de venta: "0001"
- Número: "00012345"
- Fecha de emisión
- Fecha de vencimiento
- Moneda (ARS, USD, etc.)

**Totales:**
- Importe Neto (sin IVA): $41,322.31
- IVA: $8,677.69
- **Total**: $50,000.00

**Items (cada renglón de la factura):**
- Descripción: "Jabón bactericida para manos x 5 lts"
- Cantidad: 4
- Precio unitario: $42,093.70
- IVA: 21%
- Total del item: $25,000.00

**Percepciones/Retenciones:**
- Percepción IIBB: $826.45

**Orden de Compra vinculada:**
- Si la factura menciona un número de OC, lo extrae (ej: "OC 111625")

#### Paso 2: Validar el Proveedor

El sistema busca al proveedor en nuestra base de datos:

1. **Busca por CUIT** (el más confiable)
2. Verifica que esté **ACTIVO**
3. Verifica que tenga **documentación completa**

**Si el proveedor NO existe o está inactivo:**
- ❌ **ERROR**: "Proveedor con CUIT 30-71574944-7 no encontrado"
- **Solución**: Crear/activar el proveedor primero

**Si todo está OK:**
- ✅ Obtiene el código interno del proveedor (ej: "59549")

#### Paso 3: Verificar la Orden de Compra (si existe)

Si la factura menciona una OC, el sistema:

1. **Busca la OC en nuestra base de datos**
   - Verifica que exista
   - Verifica que esté **ABIERTA** o **PARCIAL** (no CERRADA)
   - Verifica que pertenezca al mismo proveedor

2. **Obtiene los items de la OC**
   - Qué productos se pidieron
   - Cantidades
   - Precios acordados
   - **Cuánto falta facturar de cada item**

3. **Conciliación Inteligente**
   
   La IA compara la factura con la OC:
   
   **Verifica cada item:**
   - ¿El producto de la factura está en la OC?
   - ¿La cantidad facturada es menor o igual a lo pendiente?
   - ¿El precio es el mismo? (tolera pequeñas diferencias)
   
   **Detecta problemas:**
   - ❌ Item NO autorizado (está en factura pero no en OC)
   - ❌ Cantidad excedida (factura más de lo pendiente)
   - ❌ Precio diferente (más de 5% de diferencia)
   
   **Resultado:**
   - ✅ **Match exitoso**: Todo coincide
   - ⚠️ **Con discrepancias**: Hay diferencias (te las muestra)

#### Paso 4: Guardar en la Base de Datos

Si todo está OK, el sistema guarda:

**1. Cabecera de la Factura**
- En la tabla de Documentos
- Le asigna un número de archivo automático
- Estado: "PENDIENTE"

**2. Items de la Factura**
- Cada renglón se guarda por separado
- Con cantidades, precios, IVA, etc.

**3. Percepciones/Retenciones**
- Si hay percepciones de IIBB, IVA, etc.

**4. Relación con la OC**
- Vincula la factura con la OC
- Vincula cada item de la factura con el item correspondiente de la OC

**5. Actualizar Pendientes de la OC**
- Descuenta las cantidades facturadas de los pendientes
- Si se facturó todo, **cierra la OC automáticamente**

#### Paso 5: Generar Asiento Contable Automático

El sistema crea el asiento contable siguiendo las reglas contables:

**Obtiene el ejercicio contable:**
- Según la fecha de la factura, determina a qué ejercicio pertenece (ej: 2025)

**Genera el número de asiento:**
- Obtiene el siguiente número disponible (ej: 50001)

**Crea la cabecera del asiento:**
- Descripción: "Factura 00012345 - APAHIE S.R.L"
- Tipo: FACTURA A
- Proveedor: 59549
- Modo: **Automático** (para diferenciarlo de los manuales)
- Ejercicio: 2025
- Fecha: 2025-11-27

**Crea los movimientos contables:**

El asiento tiene que estar **balanceado** (DEBE = HABER):

**HABER (lo que debemos):**
- Cuenta: Proveedores (210101)
- Importe: $50,000.00 (el total de la factura)

**DEBE (lo que gastamos/compramos):**
- Cuenta: IVA Crédito Fiscal (110501)
- Importe: $8,677.69 (el IVA que podemos recuperar)

- Cuenta: Gastos/Compras (520101)
- Importe: $41,322.31 (el neto de la compra)

**Verificación:**
- DEBE: $8,677.69 + $41,322.31 = $50,000.00 ✅
- HABER: $50,000.00 ✅
- **BALANCEADO** ✅

> **NOTA**: Las cuentas contables específicas para cada tipo de gasto están **PENDIENTES DE DEFINIR** con el área de Contabilidad. Por ahora usa cuentas por defecto.

#### Paso 6: Confirmación Final

Si todo salió bien:
- ✅ Factura guardada (Archivo: 12345)
- ✅ Asiento contable generado (Asiento: 50001)
- ✅ OC actualizada (pendientes descontados)
- ✅ Relaciones creadas

**Todo esto en una sola transacción**: Si algo falla, **nada** se guarda (hace rollback).

---

## ⚠️ Casos Especiales y Errores

### Error: "Proveedor no encontrado"
**Causa**: El CUIT de la factura no existe en nuestra base de datos.
**Solución**: Crear el proveedor en el sistema primero.

### Error: "Proveedor inactivo"
**Causa**: El proveedor está dado de BAJA.
**Solución**: Reactivar el proveedor.

### Error: "Documentación incompleta"
**Causa**: Al proveedor le falta documentación.
**Solución**: Completar la documentación del proveedor.

### Error: "OC no encontrada"
**Causa**: La factura menciona una OC que no existe en nuestro sistema.
**Solución**: 
- Verificar el número de OC
- O procesar la factura sin OC (si corresponde)

### Error: "OC cerrada"
**Causa**: La OC ya fue facturada completamente.
**Solución**: Verificar si la factura es correcta o si corresponde a otra OC.

### Error: "OC no pertenece al proveedor"
**Causa**: La OC es de otro proveedor.
**Solución**: Verificar los datos de la factura.

### Warning: "Conciliación con discrepancias"
**Causa**: Hay diferencias entre la factura y la OC.
**Qué hacer**: 
- Revisar las discrepancias mostradas
- Decidir si aceptar o rechazar la factura
- Contactar al proveedor si es necesario

### Warning: "No se encontró ejercicio contable"
**Causa**: No hay un ejercicio contable definido para la fecha de la factura.
**Efecto**: 
- La factura se guarda igual
- Pero **NO** se genera el asiento contable
**Solución**: Crear el ejercicio contable para ese período.

---

## 🔄 Flujo Visual Simplificado

```
📄 FACTURA LLEGA
    ↓
🤖 IA LEE TODO
    ↓
🔍 BUSCA PROVEEDOR POR CUIT
    ↓
✅ ¿Existe y está activo?
    ↓ SÍ
🔍 BUSCA LA OC (si la factura la menciona)
    ↓
⚖️ COMPARA FACTURA vs OC
    ↓
✅ ¿Todo coincide?
    ↓ SÍ
💾 GUARDA EN BASE DE DATOS:
    • Factura (cabecera + items)
    • Percepciones
    • Relación Factura-OC
    • Actualiza pendientes de OC
    ↓
💰 GENERA ASIENTO CONTABLE:
    • Proveedores (HABER)
    • IVA Crédito (DEBE)
    • Gastos (DEBE)
    ↓
✅ ¡LISTO!
```

---

## 📊 ¿Qué Tablas se Usan?

**Solo para CONSULTAR (leer):**
- `ISMST_PERSONAS`: Proveedores
- `ISMST_ORDEN_COMPRA_CAB`: Órdenes de Compra
- `ISMST_ORDEN_COMPRA_ITEM`: Items de las OCs
- `ISMST_EJERCICIOS`: Ejercicios contables

**Para GUARDAR (escribir):**
- `ISMST_DOCUMENTOS_CAB`: Cabecera de facturas
- `ISMST_DOCUMENTOS_ITEM`: Items de facturas
- `ismsv_impuestos_documento`: Percepciones
- `ISMST_RELACION_ENTRE_DOCUMENTOS`: Vínculo Factura-OC
- `ISMST_RELACION_ENTRE_DOCUMENTOS_ITEM`: Vínculo items
- `ISMST_ASIENTOS`: Cabecera de asientos contables
- `ISMST_MOVIMIENTOS`: Movimientos contables (debe/haber)

**Para ACTUALIZAR:**
- `ISMST_ORDEN_COMPRA_ITEM`: Descuenta los pendientes
- `ISMST_ORDEN_COMPRA_CAB`: Cierra la OC si se facturó todo

---

## 🤔 Preguntas Frecuentes

### ¿Qué pasa si la factura no menciona ninguna OC?
El sistema igual la procesa, pero:
- No hace conciliación
- No actualiza pendientes de OC
- Solo guarda la factura y genera el asiento

### ¿Puedo procesar una factura sin guardarla?
Sí, hay un botón "Solo Extraer Datos" que:
- Lee la factura
- Te muestra todos los datos extraídos
- Pero **NO** guarda nada en la base de datos

### ¿Qué pasa si hay un error a mitad del proceso?
**Nada se guarda**. El sistema usa transacciones:
- Si algo falla, hace ROLLBACK
- La base de datos queda como estaba antes
- Tenés que corregir el error y volver a procesar

### ¿Cómo sé si el asiento está bien?
El sistema verifica automáticamente que:
- DEBE = HABER (balanceado)
- Todas las cuentas existan
- Los importes sean correctos

### ¿Puedo ver el historial de facturas procesadas?
Sí, hay una pestaña "Historial" que muestra:
- Todas las facturas procesadas
- Fecha y hora
- Si fue exitoso o hubo error
- Podés hacer clic para ver los detalles

---

## 🚧 Funcionalidades Pendientes

Estas funcionalidades están **en desarrollo** y se completarán próximamente:

### 1. Centro de Costos
**Estado**: INCONCLUSO
**Qué falta**: Determinar automáticamente el centro de costo para cada movimiento contable.

### 2. Cuentas Contables por Producto
**Estado**: INCONCLUSO
**Qué falta**: Mapear cada producto a su cuenta contable específica (en vez de usar una cuenta genérica de "Gastos").

### 3. Percepciones en Asientos
**Estado**: INCONCLUSO
**Qué falta**: Definir cómo se contabilizan las percepciones (IIBB, IVA, etc.) en el asiento.

### 4. Remitos
**Estado**: PENDIENTE DE DEFINIR
**Qué falta**: Integrar el flujo de remitos (¿llegan antes que la factura? ¿cómo se vinculan?).

---

**Documento creado:** 2025-11-27  
**Versión:** 1.1 (Corregido FLUJO 1)  
**Audiencia:** Usuarios no técnicos  
**Autor:** Sistema IA
