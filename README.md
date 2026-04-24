# Conciliador de Planillas

**Conciliador General de Planillas** es una aplicación web construida con Streamlit que compara dos archivos (planillas) para encontrar coincidencias, faltantes y diferencias. Ideal para procesos de reconciliación contable y administrativa.

## 🎯 Características

- 📊 Carga de archivos Excel (`.xlsx`) y CSV (`.csv`)
- 🔍 Detección automática de tipos de datos
- 📈 Comparación avanzada de tablas
- 🏷️ Constructor de reglas personalizadas
- 📋 Filtrado flexible de resultados
- 📁 Soporte para múltiples hojas en Excel

## 🚀 Inicio Rápido

### Usando Docker Compose (Recomendado)

```bash
# Clonar el repositorio
git clone https://github.com/tu-usuario/conciliador-planilla.git
cd conciliador-planilla

# Iniciar la aplicación
docker-compose up

# Acceder a la aplicación
# http://localhost:8501
```

### Instalación Local

```bash
# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt.txt

# Ejecutar la aplicación
streamlit run app.py
```

## 📦 Dependencias

- **streamlit** - Framework web interactivo
- **pandas** - Procesamiento y análisis de datos
- **numpy** - Computación numérica
- **openpyxl** - Manejo de archivos Excel

## 📁 Estructura del Proyecto

```
conciliador-planilla/
├── app.py                          # Punto de entrada de la aplicación
├── Dockerfile                      # Configuración Docker
├── docker-compose.yml              # Orquestación de contenedores
├── requirements.txt.txt            # Dependencias Python
├── .streamlit/
│   └── config.toml                # Configuración de Streamlit
├── core/
│   ├── comparator.py              # Lógica de comparación
│   ├── dtype_detector.py          # Detección de tipos de datos
│   ├── rule_labels.py             # Etiquetas de reglas
│   └── rules.py                   # Motor de reglas
├── ui/
│   ├── filters_ui.py              # Interfaz de filtros
│   └── rule_builder.py            # Constructor de reglas
├── utils/
│   ├── file_loader.py             # Carga de archivos
│   └── helpers.py                 # Funciones auxiliares
├── tests/                          # Pruebas unitarias
├── coverage/                       # Reportes de cobertura
└── README.md                       # Este archivo
```

## 🐳 Docker

### Build de la imagen

```bash
docker build -t conciliador-planilla:latest .
```

### Ejecutar contenedor

```bash
docker run -p 8501:8501 conciliador-planilla:latest
```

### Desarrollo con hot-reload

```bash
docker-compose up --build
```

## 💻 Uso

1. **Subir Tabla A** - Carga el archivo de referencia (ej: Administración)
2. **Subir Tabla B** - Carga el archivo a comparar (ej: Movimientos)
3. **Configurar comparación** - Selecciona columnas clave y reglas
4. **Revisar resultados** - Visualiza coincidencias, faltantes y diferencias
5. **Descargar reporte** - Exporta los resultados en Excel

## 🛠️ Desarrollo

### Crear un entorno de desarrollo

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt.txt
```

### Ejecutar tests

```bash
pytest tests/
```

### Generar reporte de cobertura

```bash
pytest --cov=core --cov=ui --cov=utils tests/
```

## 📝 Licencia

Este proyecto está bajo licencia MIT. Ver archivo `LICENSE` para más detalles.

## 👤 Autor

**Lisandro Santori**

- GitHub: [@tu-usuario](https://github.com/tu-usuario)

## 📞 Soporte

Para reportar errores o sugerir mejoras, abre un [issue](https://github.com/tu-usuario/conciliador-planilla/issues) en el repositorio.

---

**Última actualización:** Abril 2026
