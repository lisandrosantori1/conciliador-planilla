# Guía de Uso — Conciliador de Planillas

**Última actualización:** 2026-04  
**Aplicación:** Conciliador General de Planillas (IT Concesionaria)

---

## Tabla de contenidos

1. [Carga de archivos](#1-carga-de-archivos)
2. [Corrección de tipos de datos](#2-corrección-de-tipos-de-datos)
3. [Modo filtro — una sola tabla](#3-modo-filtro--una-sola-tabla)
4. [Modo conciliación — dos o más tablas](#4-modo-conciliación--dos-o-más-tablas)
5. [Constructor de código de comprobante (AFIP)](#5-constructor-de-código-de-comprobante-afip)
6. [Cambios de valor condicionales](#6-cambios-de-valor-condicionales)
7. [Filtros avanzados y transformaciones por regla](#7-filtros-avanzados-y-transformaciones-por-regla)
8. [Mapeo de columnas — Columnas clave](#8-mapeo-de-columnas--columnas-clave)
9. [Mapeo de columnas — Columnas a comparar](#9-mapeo-de-columnas--columnas-a-comparar)
10. [Ejecutar conciliación y resultados](#10-ejecutar-conciliación-y-resultados)
11. [Columnas calculadas](#11-columnas-calculadas)
12. [Configuración y descarga del reporte](#12-configuración-y-descarga-del-reporte)
13. [Flujos completos de ejemplo](#13-flujos-completos-de-ejemplo)

---

## 1. Carga de archivos

Al abrir la aplicación aparecen **dos cargadores de archivo** (Tabla 1 y Tabla 2).  
Con los botones **➕ Tabla** y **➖ Tabla** podés agregar o quitar cargadores (hasta 4 en total).

### Formatos aceptados
| Formato | Extensión |
|---------|-----------|
| Excel moderno | `.xlsx`, `.xlsm` |
| Excel 97–2003 | `.xls` |
| CSV | `.csv` |

### Opciones al cargar
- **Excel con múltiples hojas**: aparece un selector de hoja debajo del cargador. Elegís cuál hoja cargar.
- **CSV**: aparece un selector de separador decimal:
  - **Punto "." (ej: 1.50)** — estándar anglosajón
  - **Coma "," (ej: 1,50)** — estándar europeo / argentino

Una vez cargado, se muestra la cantidad de filas y columnas detectadas.

> **Nota:** si recargás el mismo archivo sin cambios, la aplicación usa la versión en caché y no lo vuelve a procesar.

---

## 2. Corrección de tipos de datos

La aplicación detecta automáticamente el tipo de cada columna. El expander **🔧 Corregir tipos de datos detectados (opcional)** permite revisarlo y corregirlo si es necesario.

### Tipos disponibles
| Tipo | Descripción | Ejemplo |
|------|-------------|---------|
| **Texto** | Cadenas alfanuméricas | Nombres, códigos con letras |
| **Número entero** | Valores enteros | IDs, cantidades |
| **Número decimal** | Valores con decimales | Precios, montos |
| **Fecha** | Fechas en cualquier formato | DD/MM/AAAA, AAAA-MM-DD |

Las columnas con tipo modificado manualmente muestran un ✏️ en el selector.

> **Cuándo corregir:** si una columna de códigos como `"20123254"` fue detectada como "Número entero" pero puede contener letras en otros registros, cambiala a "Texto" para que los filtros y comparaciones funcionen correctamente.

---

## 3. Modo filtro — una sola tabla

Si cargás **una sola tabla**, la aplicación entra en **Modo filtro**. Las secciones opcionales aparecen una debajo de la otra, activadas con checkboxes.

### Orden de las secciones opcionales

#### 🔤 Construir columna de código de comprobante (opcional)
Activa el [Constructor AFIP](#5-constructor-de-código-de-comprobante-afip) para generar un código combinado antes de exportar.

#### 🔄 Cambios de valor condicionales (opcional)
Modifica valores en columnas numéricas para filas que cumplan una condición, sin filtrar el resultado. Ver sección [6](#6-cambios-de-valor-condicionales).

#### 🔍 Filtrar registros antes de exportar (opcional)
Activa el [constructor de filtros](#7-filtros-avanzados-y-transformaciones-por-regla) para seleccionar solo los registros que cumplan las condiciones.

### Ejecutar
- Si hay cambios de valor o filtros activos: botón **"Aplicar y ver resultado"**
- Sin ningún filtro ni cambio: botón **"📊 Ver todos los registros"**

El resultado se muestra en pantalla y se puede descargar en Excel con **📥 Descargar resultado**.

---

## 4. Modo conciliación — dos o más tablas

Con **dos o más tablas cargadas**, la aplicación muestra el modo conciliación.

### Paso 1 — Seleccionar tablas

Elegís cuál tabla cumple cada rol:
- **Tabla A — origen / referencia**: la tabla principal (tu tabla interna, por ejemplo)
- **Tabla B — destino / comparación**: la tabla contra la que comparás (la del proveedor, AFIP, etc.)

### Paso 2 — Secciones opcionales previas al mapeo

Antes del mapeo de columnas podés activar, **de forma independiente para A y para B**:

- **🔤 Construir código de comprobante en Tabla X (opcional)**: genera un código AFIP combinado en esa tabla antes de conciliar. Ver sección [5](#5-constructor-de-código-de-comprobante-afip).

### Paso 3 — Mapeo de columnas

Ver secciones [8](#8-mapeo-de-columnas--columnas-clave) y [9](#9-mapeo-de-columnas--columnas-a-comparar).

### Paso 4 — Secciones opcionales antes de conciliar

También de forma independiente para A y para B:

- **🔄 Cambios de valor en Tabla X antes de conciliar (opcional)**: modifica valores condicionalmente antes de que entren al proceso de conciliación. Ver sección [6](#6-cambios-de-valor-condicionales).
- **🔍 Filtrar registros de Tabla X antes de conciliar (opcional)**: filtra qué filas participan de la conciliación. Ver sección [7](#7-filtros-avanzados-y-transformaciones-por-regla).

### Paso 5 — Ejecutar y ver resultados

Botón **▶️ Ejecutar Conciliación**. Ver sección [10](#10-ejecutar-conciliación-y-resultados).

---

## 5. Constructor de código de comprobante (AFIP)

Esta sección genera una **columna nueva** combinando tres columnas de la tabla, siguiendo el formato de código de comprobante de AFIP.

### Formato del código resultante
```
[Punto de venta: 4 dígitos] + [Número de comprobante: 8 dígitos] + [Letra del tipo]
```
**Ejemplo:** punto de venta = `1`, número = `34`, tipo = `81 - Tique Factura A`  
→ código: `000100000034A`

### Campos a configurar

| Campo | Descripción | Ejemplo |
|-------|-------------|---------|
| **Columna tipo (descripción)** | Columna que contiene el tipo de comprobante. Puede ser el número solo o con descripción. | `81`, `81 - Tique Factura A` |
| **Punto de venta → 4 dígitos** | Columna con el número de punto de venta | `1` → `0001` |
| **Número de comprobante → 8 dígitos** | Columna con el número del comprobante | `34` → `00000034` |
| **Nombre columna resultado** | Nombre que tendrá la nueva columna generada | `Codigo_Comprobante` |

### Vista previa
La aplicación muestra automáticamente el código generado para la **primera fila** de la tabla, incluyendo qué letra del tipo fue asignada.

### Diccionario AFIP
La aplicación tiene **97 tipos de comprobante** integrados. No es necesario cargar ningún archivo externo. El código extrae el número del campo tipo (acepta `"81"` o `"81 - Tique Factura A"`), lo normaliza a 3 dígitos y busca la letra correspondiente.

> **Caso de uso:** tenés en una tabla las columnas separadas (Tipo, Pto. Venta, Número) y en la otra un código completo como `000100000034A`. Con esta sección construís el código en la primera tabla para poder conciliarla contra la segunda.

---

## 6. Cambios de valor condicionales

Permite **modificar el valor de una columna numérica** en las filas que cumplan una condición, sin filtrar el resultado. Todas las filas aparecen en el resultado; solo se modifica el valor en las que coinciden.

### Cómo agregar un cambio

Cada cambio se configura en una fila con los siguientes elementos:

```
[Columna condición] [Condición] [Valor a buscar]  →  [Columna a modificar] [Operación]
```

| Elemento | Descripción |
|----------|-------------|
| **Columna condición** | La columna que se evalúa para decidir si se aplica el cambio |
| **Condición** | La condición a cumplir (igual, mayor que, contiene, etc.) |
| **Valor a buscar** | El valor que debe tener la columna condición |
| **Columna a modificar** | La columna numérica cuyo valor se va a cambiar |
| **Operación** | La transformación a aplicar |

### Operaciones disponibles
| Operación | Resultado |
|-----------|-----------|
| `× -1 (cambiar signo)` | Multiplica por −1. Convierte positivos en negativos y viceversa |
| `×` + valor | Multiplica el valor de la columna por el número indicado |
| `+` + valor | Suma el número indicado al valor de la columna |
| `−` + valor | Resta el número indicado al valor de la columna |
| `÷` + valor | Divide el valor de la columna por el número indicado |

> **Caso de uso:** tenés una tabla de movimientos donde los débitos están como positivos pero necesitás que queden negativos para conciliar contra otra tabla. Condición: `Tipo = "DEBITO"` → Columna: `Importe` → Operación: `× -1`.

---

## 7. Filtros avanzados y transformaciones por regla

### Crear una regla de filtro

1. Hacé clic en **➕ Agregar regla**
2. Aparece un formulario con cuatro campos: **Columna** — **Condición** — **Valor** — botones Cancelar/Aplicar
3. Elegí la columna, la condición y el valor
4. Hacé clic en **✅ Aplicar** para agregar la regla

### Condiciones disponibles por tipo de dato

**Número entero / decimal:**
| Condición | Descripción |
|-----------|-------------|
| Igual a | Valor exacto |
| Mayor que | Todos los valores superiores al indicado |
| Menor que | Todos los valores inferiores al indicado |
| Entre | Rango desde/hasta (ambos extremos incluidos) |

**Texto:**
| Condición | Descripción |
|-----------|-------------|
| Contiene texto | La cadena aparece en cualquier posición (sin distinción mayúsculas/minúsculas) |
| Empieza con | El valor comienza con el texto indicado |
| Termina con | El valor termina con el texto indicado |
| Igual a | Coincidencia exacta |

**Fecha:**
| Condición | Descripción |
|-----------|-------------|
| Igual a | Fecha exacta. Atajos disponibles: Hoy, Ayer, Este mes, Mes pasado |
| Antes de | Fechas anteriores a la indicada |
| Después de | Fechas posteriores a la indicada |

### Combinar reglas
El selector **¿Cómo combinar las condiciones?** tiene dos opciones:
- **Y** (AND): se deben cumplir **todas** las reglas activas
- **O** (OR): alcanza con que se cumpla **al menos una** regla

### Editar y eliminar reglas
Las reglas aparecen listadas en **📋 Reglas actuales**. Podés:
- Editar directamente la columna, condición y valor de cualquier regla
- Eliminar una regla con el botón **❌**

### Transformaciones por regla

Dentro de cada regla activa hay un checkbox **"Modificar una o más columnas para estas filas"**.  
Al activarlo, podés agregar transformaciones numéricas que se aplican **solo a las filas que cumplen esa regla**.

Cada transformación tiene:
- **Columna a modificar**: la columna numérica que se va a cambiar
- **Operación**: `× -1`, `×`, `+`, `−`, `÷`
- **Valor** (cuando la operación lo requiere)

Con **➕ Agregar transformación** podés apilar múltiples modificaciones para la misma regla.

> **Diferencia con "Cambios de valor condicionales":**  
> Los cambios de valor modifican filas pero devuelven **todas las filas**.  
> Los filtros con transformaciones **filtran** las filas Y modifican las que cumplen la condición.  
> El resultado de los filtros solo incluye las filas que pasaron el filtro.

---

## 8. Mapeo de columnas — Columnas clave

Las columnas clave **identifican qué fila de Tabla A corresponde a qué fila de Tabla B**. Dos filas se consideran una coincidencia cuando sus valores en **todas** las columnas clave configuradas coinciden.

### Configuración básica

Cada fila del mapeo define un par de columnas:

```
Tabla A                ↔   Tabla B
[Nro. Doc. Vendedor ]      [CUIT            ]
```

Las columnas pueden tener **nombres distintos** en cada tabla.

### Checkbox: Aproximado

Activa la coincidencia por **contenido**: dos valores coinciden si uno contiene al otro (después de eliminar espacios al inicio/final). Se requiere mínimo 3 caracteres para evitar falsos positivos.

| Valor en A | Valor en B | ¿Coincide? |
|------------|------------|------------|
| `46348199` | `K46348199` | ✅ Sí (A está contenido en B) |
| `K68225187AB` | `68225187AB` | ✅ Sí (B está contenido en A) |
| `04589914AF` | `K04589914AF` | ✅ Sí |
| `12345678` | `87654321` | ❌ No |
| `AB` | `XABZ` | ❌ No (menos de 3 caracteres) |

> **Cuándo usar:** cuando los códigos en una tabla tienen un prefijo o sufijo que la otra tabla no tiene (ej: prefijo `K`, sufijo de letras, etc.).

### Checkbox: Norm. CUIT/DNI

Antes de comparar, elimina **guiones y espacios** del valor. Si el resultado es numérico, lo compara como número puro.

| Valor en A | Valor en B | ¿Coincide? |
|------------|------------|------------|
| `20-12345678-9` | `20123456789` | ✅ Sí |
| `20 12345678 9` | `20123456789` | ✅ Sí |
| `20123456789` | `20123456789` | ✅ Sí |

> **Cuándo usar:** cuando una tabla tiene CUIT/DNI con guiones y la otra sin guiones.

### Clave compuesta (múltiples columnas clave)

Podés agregar tantas columnas clave como necesites con **➕ Agregar columna clave**.  
Una fila aparece en **Coincidencias** solo si **todas** las columnas clave coinciden simultáneamente.

```
Tabla A                    ↔   Tabla B
[Nro. Doc. Vendedor   ]        [CUIT      ]  ← ambas deben coincidir
[Codigo_Comprobante   ]        [Número    ]  ← para que sea coincidencia
```

> **Cuándo usar:** cuando una sola columna no alcanza para identificar un registro de forma única (ej: mismo CUIT con distintos números de comprobante).

### Checkbox: Incluir columnas de Tabla B en Coincidencias (opcional)

Cuando está activo, el resultado de **Coincidencias** muestra el valor original de Tabla B junto al de Tabla A para cada columna clave.

```
Nro. Doc. Vendedor  |  CUIT              |  ...
20123456789         |  20-12345678-9     |  ...
```

> **Cuándo usar:** cuando usás coincidencia aproximada o normalización y querés ver exactamente qué valor tenía B en los registros que coincidieron.

---

## 9. Mapeo de columnas — Columnas a comparar

Las columnas a comparar **detectan diferencias** entre los registros que ya coincidieron. Son opcionales: si no agregás ninguna, el resultado solo mostrará coincidencias y faltantes, sin detectar diferencias.

### Configuración básica

Cada fila define qué columna de A se compara contra qué columna de B:

```
Tabla A                ↔   Tabla B
[Monto_Facturado  ]        [Importe_Pagado  ]
```

### Checkbox: Aproximado

Define qué cuenta como "igual" en la comparación:
- **Activado**: dos valores se consideran **iguales** si uno contiene al otro. No se reporta diferencia.
- **Desactivado** (predeterminado): se usa la comparación estándar (numérica o de texto).

> **Cuándo usar:** cuando querés que `"000100000034A"` y `"34"` se consideren **iguales** en la comparación de diferencias (ya coincidieron como clave fuzzy y no querés ver esa diferencia).

### Checkbox: Norm. CUIT/DNI

Define qué cuenta como "igual" en la comparación:
- **Activado**: se eliminan guiones/espacios antes de comparar. `"20-12345678-9"` y `"20123456789"` se consideran **iguales**.
- **Desactivado** (predeterminado): se comparan los valores tal como están.

### Normalización automática (siempre activa)

Independientemente de los checkboxes, la comparación siempre normaliza:
- **Decimales**: `308743.8` y `308743,8` se consideran iguales
- **Fechas**: `26/01/2026` y `26/1/2026 00:00:00` se consideran iguales

### Comparar las mismas columnas que se usaron como clave

Es válido usar la misma columna tanto en clave como en comparación. Esto es útil cuando:
- Usaste **coincidencia aproximada** como clave (ej: `"46348199"` coincidió con `"K46348199"`)
- Y además querés ver en **Diferencias** que los valores originales son distintos

En ese caso, en **Columnas clave** dejás el checkbox **Aproximado** activado, y en **Columnas a comparar** agregás la misma columna con **Aproximado desactivado**. El resultado mostrará la diferencia real entre `"46348199"` y `"K46348199"`.

---

## 10. Ejecutar conciliación y resultados

### Ejecutar

Hacé clic en **▶️ Ejecutar Conciliación**. Los resultados persisten en pantalla aunque hagas cambios en otras secciones.

### Métricas

Se muestran cuatro contadores:
| Métrica | Descripción |
|---------|-------------|
| ✅ **Coincidencias** | Filas que existen en ambas tablas con las mismas claves |
| 📌 **Solo en A** | Filas de Tabla A sin correspondencia en Tabla B |
| 📌 **Solo en B** | Filas de Tabla B sin correspondencia en Tabla A |
| ⚠️ **Diferencias** | Filas coincidentes donde alguna columna comparada tiene distinto valor |

### Vista previa

Las cuatro pestañas muestran las primeras 10 filas de cada grupo:
- **✅ Coincidencias**: filas que coincidieron en ambas tablas
- **📌 Solo en A**: filas que están en A pero no en B
- **📌 Solo en B**: filas que están en B pero no en A
- **⚠️ Diferencias**: para cada fila con diferencias, muestra las columnas involucradas con sus valores de A y de B

---

## 11. Columnas calculadas

Aparece después de ejecutar la conciliación. Permite **agregar columnas nuevas** al resultado de Coincidencias con operaciones entre columnas numéricas.

### Cómo agregar una columna calculada

1. Hacé clic en **➕ Agregar columna calculada**
2. Aparece un bloque con:
   - **Columna 1**: primer operando (columna numérica del resultado)
   - **Operación**: `×`, `+`, `−`, `÷`
   - **Columna 2 / Valor fijo**: segundo operando

### Valor fijo

Si activás el checkbox **"Valor fijo"**, en lugar de elegir una columna ingresás un número constante. Útil para:
- Convertir un porcentaje: `IVA ÷ 100`
- Aplicar un tipo de cambio fijo: `Monto_USD × 1050`

### Encadenar operandos (N operandos)

Con **➕ Agregar operando** podés agregar más pasos a la misma fórmula. Cada paso adicional opera sobre el resultado del anterior.

Los paréntesis en el preview muestran el orden de evaluación:

```
→ Total = (Precio_USD × Tipo_Cambio) × Cantidad
→ Neto  = (Precio × Cantidad) ÷ 100
```

### Aplicar

Hacé clic en **▶️ Calcular columnas**. Las columnas calculadas aparecen en la vista previa y se incluyen en la descarga.

> **Nota:** si dividís por 0 o por una columna con valores no numéricos, el resultado de esas filas queda en blanco (NaN).

---

## 12. Configuración y descarga del reporte

Abrí el expander **⚙️ Configuración de descarga (opcional)** para personalizar el archivo antes de descargarlo.

### Nombre del archivo
Escribís el nombre sin extensión. El archivo se descarga como `.xlsx`.  
Ejemplo: `conciliacion_enero_2026` → `conciliacion_enero_2026.xlsx`

### Hojas a incluir

| Hoja | Por defecto | Descripción |
|------|-------------|-------------|
| **Coincidencias** | Siempre | Filas que coincidieron en ambas tablas (con columnas calculadas si las hay) |
| **Diferencias** | ✅ Activado | Filas coincidentes con valores distintos en columnas comparadas |
| **Solo en A** | ☐ Desactivado | Filas que están solo en Tabla A |
| **Solo en B** | ☐ Desactivado | Filas que están solo en Tabla B |
| **Tabla A Original** | ☐ Desactivado | Tabla A completa tal como fue cargada (después de filtros y cambios) |
| **Tabla B Original** | ☐ Desactivado | Tabla B completa tal como fue cargada (después de filtros y cambios) |

### Columnas a incluir

- Las **columnas clave** siempre se incluyen en Coincidencias y Diferencias.
- Las demás columnas aparecen en un **selector múltiple** donde podés deseleccionar las que no necesitás.
- La selección aplica tanto a la hoja **Coincidencias** como a **Diferencias**.

### Descargar

Hacé clic en **📥 Descargar Reporte de Conciliación** para obtener el archivo Excel.

---

## 13. Flujos completos de ejemplo

---

### Ejemplo A — Conciliación de comprobantes AFIP

**Situación:**
- `ventas_sistema.xlsx`: columnas `Tipo_Comprobante`, `Pto_Vta`, `Nro_Comprobante`, `CUIT_Cliente`, `Monto`
- `afip_registros.xlsx`: columnas `Codigo_Comp` (formato `000100000034A`), `CUIT`, `Importe`

**Objetivo:** encontrar los comprobantes que están en el sistema pero no en AFIP, y detectar diferencias de monto.

**Pasos:**
1. Cargá `ventas_sistema.xlsx` como **Tabla 1** y `afip_registros.xlsx` como **Tabla 2**
2. Activá **🔤 Construir código de comprobante en Tabla 1**
   - Columna tipo: `Tipo_Comprobante`
   - Punto de venta: `Pto_Vta`
   - Número: `Nro_Comprobante`
   - Nombre resultado: `Codigo_Comp`
   - Verificá la vista previa (ej: `000100000034A`)
3. **Tabla A** = Tabla 1, **Tabla B** = Tabla 2
4. En **Columnas clave**:
   - `Codigo_Comp` ↔ `Codigo_Comp`
   - `CUIT_Cliente` ↔ `CUIT`, activar **Norm. CUIT/DNI**
5. En **Columnas a comparar**:
   - `Monto` ↔ `Importe`
6. Ejecutar Conciliación
7. En **⚙️ Configuración de descarga**: activar "Solo en A", poner nombre `conciliacion_afip_enero`
8. Resultado: comprobantes que no están en AFIP en la hoja "Solo en A"; diferencias de monto en "Diferencias"

---

### Ejemplo B — Conciliación con código de cliente variable

**Situación:**
- `sistema_ventas.xlsx`: columna `Cod_Vendedor` con valores `46348199`, `68225187`
- `padron_afip.xlsx`: columna `CUIT` con valores `20-46348199-9`, `20-68225187-5`

**Objetivo:** conciliar vendedores entre ambas tablas aunque los códigos tengan formato distinto.

**Pasos:**
1. Cargá ambas tablas
2. **Columnas clave**: `Cod_Vendedor` ↔ `CUIT`, activar **Aproximado** + **Norm. CUIT/DNI**
3. Activar **Incluir columnas de Tabla B en Coincidencias** para ver ambos valores
4. Ejecutar Conciliación
5. En Coincidencias aparecen ambos valores lado a lado para verificar que el matching fue correcto

---

### Ejemplo C — Conciliación con clave compuesta y comparación de montos

**Situación:**
- `facturas.xlsx`: columnas `CUIT`, `Codigo_Factura`, `Monto`
- `pagos.xlsx`: columnas `CUIT_Proveedor`, `Nro_Pago`, `Importe`

**Objetivo:** encontrar los pagos que coinciden con facturas (por CUIT + código) y detectar diferencias de monto.

**Pasos:**
1. Cargá ambas tablas
2. **Columnas clave** (clave compuesta):
   - `CUIT` ↔ `CUIT_Proveedor`, activar **Norm. CUIT/DNI**
   - `Codigo_Factura` ↔ `Nro_Pago` (hacé clic en ➕ Agregar columna clave)
3. **Columnas a comparar**:
   - `Monto` ↔ `Importe`
4. Ejecutar Conciliación
5. Coincidencias = facturas con pago registrado (ambas claves coinciden)
6. Solo en A = facturas sin pago
7. Diferencias = pagos donde el importe no coincide con la factura

---

### Ejemplo D — Ajuste de signo antes de conciliar

**Situación:**
- `extracto_banco.xlsx`: los débitos figuran como valores positivos
- `contabilidad.xlsx`: los débitos figuran como valores negativos
- Querés conciliar ambas tablas

**Pasos:**
1. Cargá ambas tablas
2. Activá **🔄 Cambios de valor en Tabla A antes de conciliar**
   - Columna condición: `Tipo` | Igual a | `DEBITO`
   - Columna a modificar: `Importe` | Operación: `× -1`
3. Configurar **Columnas clave** y **Columnas a comparar** normalmente
4. Ejecutar Conciliación
5. Ahora los débitos de A tienen signo negativo y coinciden con los de contabilidad

---

### Ejemplo E — Columna calculada con tipo de cambio

**Situación:**
- La conciliación encontró coincidencias entre una tabla en dólares y una en pesos
- Querés agregar el monto en pesos al reporte usando un tipo de cambio

**Pasos:**
1. Ejecutar la conciliación
2. En **🔢 Agregar columnas calculadas al resultado**:
   - Hacé clic en ➕ Agregar columna calculada
   - Columna 1: `Monto_USD`
   - Operación: `×`
   - Activar **Valor fijo**, ingresar `1050` (tipo de cambio)
   - Nombre: `Monto_ARS`
3. Hacé clic en ▶️ Calcular columnas
4. La columna `Monto_ARS` aparece en Coincidencias y en la descarga

---

### Ejemplo F — Filtrar tabla antes de exportar (modo filtro)

**Situación:** querés exportar solo las ventas de un vendedor específico con monto mayor a $10.000

**Pasos:**
1. Cargá `ventas.xlsx` como única tabla (modo filtro)
2. Activá **🔍 Filtrar registros antes de exportar**
3. Agregá regla 1: `Vendedor` | Contiene texto | `García`
4. Agregá regla 2: `Monto` | Mayor que | `10000`
5. Selector de lógica: **Y**
6. Hacé clic en **Aplicar y ver resultado**
7. **📥 Descargar resultado** → obtenés solo esas filas

---

## Notas importantes

- **Normalización de decimales**: el sistema considera `308743.8` y `308743,8` el mismo número, tanto para clave como para comparación.
- **Normalización de fechas**: `26/01/2026` y `26/1/2026 00:00:00` se tratan como la misma fecha.
- **Columnas con nombre repetido en Tabla B**: si el archivo tiene columnas duplicadas (pandas las renombra automáticamente como `Columna` y `Columna.1`), podés elegir cualquiera de las dos en el mapeo. El sistema las maneja correctamente.
- **Resultados persistentes**: los resultados de la conciliación se mantienen en pantalla aunque modifiques secciones opcionales. Para actualizar, volvé a hacer clic en ▶️ Ejecutar Conciliación.
