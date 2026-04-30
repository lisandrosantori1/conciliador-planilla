# Conciliador de Planillas

Aplicación web construida con **Streamlit** para comparar, filtrar y conciliar hasta 4 planillas de datos. Permite encontrar coincidencias, detectar diferencias, aplicar transformaciones y generar reportes descargables en Excel.

---

## Características

### Carga de archivos
- Formatos soportados: `.xlsx`, `.xls` (Excel 97–2003), `.xlsm`, `.csv`
- Selector de hoja para archivos Excel con múltiples pestañas
- Separador decimal configurable para CSV (punto `.` o coma `,`)
- Caché automático: recargar el mismo archivo no re-procesa los datos

### Detección de tipos de datos
- Detecta automáticamente: Texto, Número entero, Número decimal, Fecha
- Muestrea hasta 15 valores no-nulos para mayor precisión
- Reconoce números guardados como texto en Excel
- Override manual: podés corregir el tipo detectado por columna

### Modo filtro (1 tabla)
- Aplicar filtros para exportar un subconjunto de registros
- Secciones opcionales: código de comprobante, cambios de valor, filtros
- Descarga del resultado filtrado en Excel

### Mapeo de columnas (2+ tablas)
- **Columnas clave**: identifican qué fila de A corresponde a qué fila de B
  - Las columnas pueden tener distinto nombre en cada tabla
  - **Aproximado (fuzzy)**: detecta variaciones con prefijos/sufijos (`46348199` ↔ `K46348199`)
  - **Norm. CUIT/DNI**: elimina guiones/espacios antes de comparar (`20-12345678-9` ↔ `20123456789`)
  - **Clave compuesta**: podés agregar múltiples columnas clave; se deben cumplir todas
  - **Incluir columnas de Tabla B en Coincidencias**: muestra el valor original de B junto al de A
- **Columnas a comparar**: detectan diferencias entre columnas mapeadas en las coincidencias
  - También soportan **Aproximado** y **Norm. CUIT/DNI** para controlar cuándo un valor se considera "distinto"

### Conciliación
- Resultados: Coincidencias, Solo en A, Solo en B, Diferencias
- Normalización de decimales: `308743.8` y `308743,8` se tratan como igual
- Normalización de fechas: `26/01/2026` y `26/1/2026 00:00:00` se tratan como igual
- Filtros independientes para Tabla A y Tabla B antes de conciliar

### Constructor de código de comprobante (AFIP)
- Construye un código único a partir de tres columnas: **tipo**, **punto de venta** y **número**
- Formato: `pv.zfill(4) + nro.zfill(8) + letra_tipo`
- Ejemplo: punto=1, número=34, tipo="81 - Tique Factura A" → `000100000034A`
- Diccionario AFIP integrado con 97 tipos de comprobante
- Vista previa del resultado antes de aplicar
- Disponible para Tabla A y/o Tabla B antes de la conciliación

### Cambios de valor condicionales
- Modifica valores en columnas numéricas para las filas que cumplan una condición
- El resultado incluye **todas** las filas (no filtra), solo modifica las que coinciden
- Operaciones: `× -1` (cambiar signo), `×`, `+`, `−`, `÷`
- Disponible para Tabla A y Tabla B antes de conciliar, y para la tabla única en modo filtro

### Filtros avanzados
- Condiciones por tipo: igual, mayor, menor, entre, contiene, empieza con, termina con, antes de, después de
- Combinación con lógica **Y** (AND) u **O** (OR)
- **Transformaciones por regla**: dentro de cada regla, podés modificar columnas numéricas en las filas filtradas (× -1, ×, +, −, ÷)

### Columnas calculadas
- Agrega columnas nuevas al resultado de Coincidencias
- Soporta N operandos encadenados con `➕ Agregar operando`
- Operaciones: `×`, `+`, `−`, `÷`
- **Valor fijo**: usá un número constante como operando (ej: `÷ 100` para convertir porcentaje)
- Preview de la fórmula con paréntesis que reflejan el orden de evaluación
- Se incluyen en la descarga Excel

### Configuración de descarga
- Nombre del archivo personalizado
- Elegís qué hojas incluir: Coincidencias, Diferencias, Solo en A/B, tablas originales
- Selector de columnas para la hoja Coincidencias y Diferencias (columnas clave siempre incluidas)

---

## Inicio rápido

### Instalación local

```bash
git clone https://github.com/lisandrosantori1/conciliador-planilla.git
cd conciliador-planilla
pip install -r requirements.txt
streamlit run app.py
```

Accedé en `http://localhost:8501`

### Docker (recomendado para producción)

```bash
# Primera vez (construye la imagen)
docker compose up --build -d

# Siguientes veces
docker compose up -d

# Ver logs
docker logs -f conciliador

# Detener
docker compose down
```

---

## Ejecutar tests

```bash
python -m pytest tests/ -v
```

---

## Estructura del proyecto

```
conciliador-planilla/
├── app.py                  # Aplicación principal Streamlit
├── core/
│   ├── afip_tipos.py       # Diccionario AFIP: 97 tipos de comprobante
│   ├── comparator.py       # Lógica de conciliación y comparación
│   ├── dtype_detector.py   # Detección automática de tipos de columna
│   ├── rule_labels.py      # Etiquetas de reglas para la UI
│   └── rules.py            # Motor de reglas de filtrado
├── ui/
│   ├── column_mapper.py    # Componente de mapeo de columnas A↔B
│   └── rule_builder.py     # Constructor visual de reglas y transformaciones
├── utils/
│   └── file_loader.py      # Carga de archivos con caché
├── tests/
│   ├── test_comparator.py
│   ├── test_dtype_detector.py
│   └── test_rules.py
├── proceso-uso.md          # Guía de uso detallada para capacitación
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## Requisitos

- Python 3.11+
- Ver `requirements.txt` para dependencias completas
