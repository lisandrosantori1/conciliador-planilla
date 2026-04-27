# Conciliador de Planillas

Aplicación web construida con **Streamlit** para comparar, filtrar y conciliar hasta 4 planillas de datos. Permite encontrar coincidencias, detectar diferencias y generar reportes descargables en Excel.

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

### Filtros avanzados
- Condiciones disponibles según tipo de dato:
  - **Número**: igual, distinto, mayor, menor, entre
  - **Texto**: contiene, empieza con, termina con, igual
  - **Fecha**: antes de, después de, igual
- Combinación de múltiples reglas con lógica **Y** (AND) u **O** (OR)

### Mapeo de columnas
- Columnas clave: elegís qué columna de cada tabla identifica las filas
- Las columnas pueden tener distinto nombre en cada tabla
- **Coincidencia aproximada (fuzzy)**: detecta variaciones con prefijos/sufijos
  - Ejemplo: `46348199` coincide con `K46348199`
- Columnas de comparación: detecta diferencias entre columnas mapeadas

### Conciliación
- Modos:
  - **1 tabla**: filtrado y descarga de registros
  - **2–4 tablas**: conciliación completa con selector de Tabla A y Tabla B
- Resultados: Coincidencias, Diferencias, Solo en A, Solo en B
- Normalización de decimales: `308743.8` y `308743,8` se tratan como igual

### Columnas calculadas
- Agregá columnas con operaciones entre columnas numéricas del resultado
- Operaciones: multiplicación `×`, suma `+`, resta `−`, división `÷`
- Preview de la fórmula antes de calcular
- Se incluyen en la descarga Excel

### Configuración de descarga
- Nombre del archivo personalizado
- Elegís qué hojas incluir: Coincidencias, Diferencias, Solo en A/B, tablas originales
- Selector de columnas para la hoja Coincidencias (columnas clave siempre incluidas)

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
docker compose up --build

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
│   ├── comparator.py       # Lógica de conciliación y comparación
│   ├── dtype_detector.py   # Detección automática de tipos de columna
│   ├── rule_labels.py      # Etiquetas de reglas para la UI
│   └── rules.py            # Motor de reglas de filtrado
├── ui/
│   ├── column_mapper.py    # Componente de mapeo de columnas A↔B
│   └── rule_builder.py     # Constructor visual de reglas
├── utils/
│   └── file_loader.py      # Carga de archivos con caché
├── tests/
│   ├── test_comparator.py
│   ├── test_dtype_detector.py
│   └── test_rules.py
├── proceso-uso.txt         # Guía de uso detallada con ejemplos
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## Requisitos

- Python 3.11+
- Ver `requirements.txt` para dependencias completas
