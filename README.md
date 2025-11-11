# 📊 Dashboard 360° - Sistema de Evaluación de Desempeño

## 🎯 Descripción General

Este sistema permite visualizar y analizar evaluaciones de desempeño 360° de manera interactiva. Carga datos desde Google Sheets (público o con credenciales), convierte respuestas en escala Likert a valores numéricos, aplica ponderaciones configurables y muestra los resultados en gráficas tipo dona por categorías de habilidades.

---

## 🚀 Instalación y Configuración

### Requisitos Previos
- Python 3.8 o superior
- Conexión a Internet (para cargar datos de Google Sheets)

### Instalación de Dependencias

```bash
# Crear entorno virtual (recomendado)
python -m venv .venv

# Activar entorno virtual
# En Windows:
.venv\Scripts\activate
# En Linux/Mac:
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### Contenido de `requirements.txt`
```
dash>=2.14.0
pandas>=2.0.0
gspread>=5.11.0
oauth2client>=4.1.3
plotly>=5.17.0
dash-bootstrap-components>=1.5.0
```

---

## ▶️ Ejecución

```bash
python app.py
```

Luego abre tu navegador en: **http://127.0.0.1:8051**

---

## 📖 Cómo Funciona el Sistema

### 1️⃣ **Carga de Datos desde Google Sheets**

El sistema puede cargar datos de dos formas:

#### **Opción A: Hoja Pública (Sin credenciales)**
- La aplicación construye una URL de exportación CSV usando el ID de la hoja
- Codifica el nombre de la pestaña para manejar espacios y caracteres especiales
- URL generada: `https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={NOMBRE_CODIFICADO}`

#### **Opción B: Con Credenciales (Opcional)**
Si existe un archivo `credentials.json`:
- Usa la API de Google Sheets mediante `gspread`
- Permite acceso a hojas privadas
- Requiere configurar una cuenta de servicio de Google Cloud

**Configuración por defecto:**
```python
DEFAULT_SHEET_ID = "16wSqQKJiYZBbmgBNg4Wzi1mvCx5laEncsL5npXzH1Po"
SHEET_NAME_TEXT = "Respuestas de formulario 1"  # Respuestas textuales
SHEET_NAME_NUM = "Base de Datos Limpia"          # Respuestas numéricas
```

---

### 2️⃣ **Conversión de Escala Likert a Valores Numéricos**

Las respuestas textuales se convierten automáticamente según esta escala:

| Respuesta Original      | Valor Numérico |
|-------------------------|----------------|
| Muy en Desacuerdo       | 1              |
| En Desacuerdo           | 2              |
| Neutral                 | 3              |
| De Acuerdo              | 4              |
| Totalmente de Acuerdo   | 5              |

**Proceso de conversión:**
```python
def convertir_likert(df):
    # Para cada columna de tipo texto:
    # 1. Convierte texto a minúsculas
    # 2. Busca coincidencia en LIKERT_MAP
    # 3. Si no hay coincidencia, intenta convertir a número
    # 4. Si falla, mantiene el texto original
    # 5. Al final, convierte todas las columnas numéricas posibles
```

---

### 3️⃣ **Detección Inteligente de Columnas**

El sistema identifica automáticamente las columnas clave:

#### **Normalización de Texto**
```python
def normalize_text(s):
    # 1. Convierte a minúsculas
    # 2. Elimina tildes/acentos
    # 3. Quita espacios extras
```

#### **Columnas Detectadas**
- **Evaluado**: Busca "nombre del colaborador evaluado", "evaluado", etc.
- **Relación**: Busca "cual es tu relacion con el evaluado", "relacion", etc.
- **Timestamp**: Busca "marca temporal", "timestamp", "fecha", etc.

#### **Competencias Numéricas**
Se consideran competencias todas las columnas que:
1. No son metadatos (timestamp, nombre, comentarios)
2. Pueden convertirse a valores numéricos
3. Tienen al menos un valor no nulo

---

### 4️⃣ **Categorización Automática de Competencias**

Las competencias se agrupan en **10 categorías** mediante análisis de palabras clave:

| Categoría                    | Palabras Clave                                      | Color      |
|------------------------------|-----------------------------------------------------|------------|
| 🤝 Trabajo en Equipo         | equipo, colabora, trabajo en equipo                | #667eea    |
| 💬 Comunicación              | comunica, escucha, claridad, respeto               | #36d1dc    |
| 👔 Liderazgo                 | liderazgo, manejo de, gestiona, subordin           | #f093fb    |
| 🎯 Toma de Decisiones        | decisiones, toma de                                 | #fa709a    |
| 📅 Planeación                | planeación, planea, junta, seguimiento             | #a8edea    |
| 📦 Manejo de Recursos        | recursos, manejo de, material                       | #ffd166    |
| 🤝 Capacidad de Negociación  | negociación, negocia, flexibilidad, retroaliment.  | #9795f0    |
| 💡 Innovación y Creatividad  | innovadora, creatividad, idea, investiga, tendencia| #fbc2eb    |
| ⏰ Gestión del Tiempo        | tiempo, cumple, programa, forma                     | #38ef7d    |
| ⭐ Calidad y Resultados      | calidad, valor, resultado, estándar, mejora        | #4facfe    |

**Ejemplo:**
```python
# Competencia: "[Comunica con claridad y respeto con sus compañeros]"
# Contiene "comunica" → Se clasifica en "Comunicación"
```

---

### 5️⃣ **Mapeo de Relaciones a Grupos**

Las relaciones se normalizan a 4 grupos principales:

```python
"Soy yo mismo (Autoevaluación)"          → Autoevaluación
"Soy su Jefe / Supervisor directo"       → Jefe Inmediato
"Soy un Par (compañero del mismo nivel)" → Colegas
"Soy un Subordinado (le reporto)"        → Subordinados
"Soy un Cliente Interno"                 → Colegas (por defecto)
```

---

### 6️⃣ **Cálculo de Ponderaciones**

#### **Fórmula de Cálculo**

**Paso 1: Normalizar ponderaciones**
```
Total = Auto% + Jefe% + Colegas% + Subordinados%
Auto_normalizado = Auto% / Total
Jefe_normalizado = Jefe% / Total
...
```

**Paso 2: Calcular promedios por grupo**
```
Para cada grupo (Auto, Jefe, Colegas, Subordinados):
    Promedio_Grupo = Media de todas las evaluaciones de ese grupo
```

**Paso 3: Aplicar ponderaciones**
```
Para cada competencia:
    Puntaje_Final = (Promedio_Auto × Peso_Auto) + 
                    (Promedio_Jefe × Peso_Jefe) + 
                    (Promedio_Colegas × Peso_Colegas) + 
                    (Promedio_Subordinados × Peso_Subordinados)
```

**Paso 4: Calcular calificación final**
```
Calificación_Final = Media de todos los Puntajes_Finales de competencias
```

#### **Ejemplo Práctico**

**Configuración:**
- Autoevaluación: 5%
- Jefe: 18%
- Colegas: 30%
- Subordinados: 47%

**Datos de ejemplo para "Trabajo en Equipo":**
- Autoevaluación: 4.0
- Jefe: 3.5
- Colegas (promedio de 2): 4.2
- Subordinados (promedio de 3): 3.8

**Cálculo:**
```
Normalizar: Total = 5 + 18 + 30 + 47 = 100%
Auto = 5/100 = 0.05
Jefe = 18/100 = 0.18
Colegas = 30/100 = 0.30
Subordinados = 47/100 = 0.47

Puntaje_Final = (4.0 × 0.05) + (3.5 × 0.18) + (4.2 × 0.30) + (3.8 × 0.47)
              = 0.20 + 0.63 + 1.26 + 1.79
              = 3.88
```

---

### 7️⃣ **Visualización con Gráficas de Dona**

#### **Conversión a Porcentaje Visual**
```python
Porcentaje_Logrado = (Puntaje / 5.0) × 100
Porcentaje_Faltante = 100 - Porcentaje_Logrado
```

**Ejemplo:**
- Puntaje: 3.88
- Porcentaje Logrado: (3.88 / 5.0) × 100 = 77.6%
- Porcentaje Faltante: 22.4%

#### **Componentes de la Gráfica**
- **Parte de color**: Representa el nivel logrado
- **Parte gris claro**: Representa el margen de mejora
- **Número central**: Puntaje numérico (ej: 3.88 de 5.0)
- **Badge inferior**: Número de competencias en esa categoría

---

## 🎨 Paleta de Colores

Hemos usado una paleta profesional y armoniosa:

```css
Trabajo en Equipo:          #667eea  /* Morado azulado */
Comunicación:               #36d1dc  /* Turquesa */
Liderazgo:                  #f093fb  /* Rosa suave */
Toma de Decisiones:         #fa709a  /* Rosa coral */
Planeación:                 #a8edea  /* Menta */
Manejo de Recursos:         #ffd166  /* Amarillo cálido */
Capacidad de Negociación:   #9795f0  /* Lavanda */
Innovación y Creatividad:   #fbc2eb  /* Rosa pastel */
Gestión del Tiempo:         #38ef7d  /* Verde brillante */
Calidad y Resultados:       #4facfe  /* Azul cielo */
```

---

## 🔧 Configuración Avanzada

### Cambiar el ID de Google Sheets

Edita las siguientes líneas en `app.py`:
```python
DEFAULT_SHEET_ID = "TU_SHEET_ID_AQUI"
SHEET_NAME_TEXT = "Nombre de tu pestaña"
SHEET_NAME_NUM = "Nombre de tu pestaña numérica"
```

### Usar Variables de Entorno

```bash
# Windows
set SHEET_ID=TU_SHEET_ID
set SHEET_NAME=Nombre de tu pestaña
python app.py

# Linux/Mac
export SHEET_ID=TU_SHEET_ID
export SHEET_NAME=Nombre de tu pestaña
python app.py
```

### Cambiar Puerto de la Aplicación

En `app.py`, línea final:
```python
app.run(debug=True, port=8051)  # Cambia 8051 por el puerto deseado
```

---

## 📊 Estructura de Datos Esperada

### Columnas Requeridas

1. **Marca temporal** (opcional): Fecha/hora de la evaluación
2. **Nombre Completo**: Nombre del evaluador
3. **Nombre del Colaborador Evaluado**: Persona evaluada
4. **¿Cuál es tu relación con el Evaluado?**: Tipo de evaluador
5. **Competencias** (múltiples columnas): Preguntas de evaluación

### Formato de Respuestas

**Opción 1: Texto Likert**
```
Muy en Desacuerdo
En Desacuerdo
Neutral
De Acuerdo
Totalmente de Acuerdo
```

**Opción 2: Valores Numéricos**
```
1, 2, 3, 4, 5
```

---

## 🛠️ Solución de Problemas

### Error: "plotly.js did not load"
```bash
pip uninstall -y dash plotly dash-bootstrap-components
pip install dash==2.14.2 plotly==5.18.0 dash-bootstrap-components==1.5.0
```

### Error: "No se pudo cargar la hoja"
1. Verifica que la hoja de Google Sheets sea pública
2. Comprueba el ID de la hoja en la URL
3. Verifica el nombre exacto de las pestañas

### No aparecen evaluados en el dropdown
1. Revisa que la columna "Nombre del Colaborador Evaluado" exista
2. Verifica que haya datos en esa columna
3. Comprueba los mensajes en la consola al iniciar la app

### Las categorías están vacías
Las competencias deben contener palabras clave reconocibles. Ajusta la función `categorizar_competencias_detallado()` para incluir tus propias palabras clave.

---

## 📈 Interpretación de Resultados

### Escala de Calificación
- **1.00 - 2.00**: Necesita mejora urgente
- **2.01 - 3.00**: Por debajo del esperado
- **3.01 - 4.00**: Cumple con lo esperado
- **4.01 - 5.00**: Supera expectativas

### Análisis por Categoría
Cada gráfica de dona muestra:
- **Verde/Color fuerte**: Porcentaje logrado
- **Gris claro**: Margen de mejora
- **Número central**: Calificación exacta

### Ponderaciones Recomendadas
- **Jefe Inmediato**: 30-40% (visión estratégica)
- **Colegas**: 25-35% (trabajo en equipo)
- **Subordinados**: 25-35% (liderazgo)
- **Autoevaluación**: 5-10% (autoconocimiento)

---

## 🤝 Contribuciones

Para agregar nuevas categorías, edita:
```python
def categorizar_competencias_detallado(competencias):
    categorias = {
        'Tu Nueva Categoría': [],
        # ... otras categorías
    }
    
    # Agrega condiciones de clasificación
    if any(palabra in comp_lower for palabra in ['palabras', 'clave']):
        categorias['Tu Nueva Categoría'].append(comp)
```

Y agrega el color en el callback:
```python
colores_categorias = {
    'Tu Nueva Categoría': '#CODIGO_HEX',
    # ... otros colores
}
```

---

## 📝 Licencia

Este proyecto es de código abierto y está disponible para uso personal y comercial.

---

## 🎓 Créditos

Desarrollado con:
- **Dash/Plotly**: Framework de visualización interactiva
- **Pandas**: Procesamiento de datos
- **Bootstrap**: Estilos y componentes UI
- **Google Sheets API**: Integración con hojas de cálculo

---

## 📞 Soporte

Para preguntas o problemas:
1. Revisa la sección de Solución de Problemas
2. Verifica que todas las dependencias estén instaladas
3. Comprueba los mensajes de error en la consola

---

**¡Dashboard 360° - Evaluación de Desempeño Visual e Intuitiva!** 🚀

