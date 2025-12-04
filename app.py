import dash
from dash import dcc, html, Input, Output, State, dash_table
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import plotly.graph_objs as go
import urllib.parse
import unicodedata
import dash_bootstrap_components as dbc  # <-- 1. IMPORTAR BOOTSTRAP
from dash.exceptions import PreventUpdate
import utils_reporte  # Módulo de reportes

# --- Configuración y Carga de Datos ---
# (Todo tu código de lógica de datos va aquí, no necesita cambios)

# Configuración por defecto
DEFAULT_SHEET_ID = "16wSqQKJiYZBbmgBNg4Wzi1mvCx5laEncsL5npXzH1Po"
SHEET_NAME_TEXT = "Respuestas de formulario 1"
SHEET_NAME_NUM = "Respuestas de formulario 1"

SHEET_ID = os.environ.get('SHEET_ID', DEFAULT_SHEET_ID)
SHEET_GID = os.environ.get('SHEET_GID')

# Mapeo de respuestas textuales a escala numérica (1-5)
LIKERT_MAP = {
    'muy en desacuerdo': 1,
    'en desacuerdo': 2,
    'neutral': 3,
    'de acuerdo': 4,
    'totalmente de acuerdo': 5,
}


# Utilidad: normalizar texto
def normalize_text(s):
    if s is None:
        return ''
    s = str(s)
    s = s.strip().lower()
    # quitar tildes
    s = ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))
    return s


# Función para cargar una pestaña de la hoja
def cargar_hoja_google(sheet_id=SHEET_ID, sheet_name=None, sheet_gid=None, creds_path='credentials.json'):
    # Intentar usar credenciales si existen
    if os.path.exists(creds_path):
        try:
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            credentials = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
            client = gspread.authorize(credentials)
            sh = client.open_by_key(sheet_id)
            if sheet_gid:
                gid_int = int(sheet_gid)
                worksheet = None
                for w in sh.worksheets():
                    props = w._properties if hasattr(w, '_properties') else {}
                    if props.get('sheetId') == gid_int:
                        worksheet = w
                        break
                if worksheet is None:
                    worksheet = sh.worksheet(sheet_name)
            else:
                worksheet = sh.worksheet(sheet_name)
            data = pd.DataFrame(worksheet.get_all_records())
            print(f"Cargada con credenciales: {sheet_name}")
            return data
        except Exception as e:
            print("Aviso: no se pudieron usar credenciales (o falló gspread):", e)
            # seguir a intentar lectura pública

    # Leer versión pública como CSV
    try:
        if sheet_gid:
            csv_url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={sheet_gid}'
        else:
            # codificar el nombre de la hoja para evitar espacios o caracteres especiales
            sheet_name_enc = urllib.parse.quote(sheet_name, safe='')
            csv_url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name_enc}'
        df = pd.read_csv(csv_url)
        # limpiar nombres de columnas (quitar espacios extra)
        df.columns = [c.strip() if isinstance(c, str) else c for c in df.columns]
        print(f"Cargada públicamente: {sheet_name}")
        return df
    except Exception as e:
        raise RuntimeError(f"No se pudo cargar la hoja '{sheet_name}' (credenciales o pública). Error: {e}")


# Función que convierte respuestas textuales a números usando LIKERT_MAP
def convertir_likert(df):
    df_conv = df.copy()
    for col in df_conv.columns:
        # intentar mapear valores textuales
        if df_conv[col].dtype == object:
            def map_val(v):
                if pd.isna(v):
                    return v
                s = str(v).strip()
                # normalizar texto (quitar tildes y pasar a minúsculas)
                s_norm = ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c)).lower()
                # intentar mapear texto Likert
                mapped = LIKERT_MAP.get(s_norm)
                if mapped is not None:
                    return mapped
                # intentar convertir a número si es posible
                try:
                    num = float(s)
                    return num
                except Exception:
                    return s

            df_conv[col] = df_conv[col].map(map_val)
    # intentar convertir columnas a numéricas donde tenga sentido
    for col in df_conv.columns:
        try:
            numeric = pd.to_numeric(df_conv[col], errors='coerce')
            # si la conversión produjo al menos algún valor numérico, usarlo
            if numeric.notna().sum() > 0:
                df_conv[col] = numeric
        except Exception:
            pass
    return df_conv


# Función para extraer solo las columnas de competencias (numéricas)
def columnas_competencias(df, exclude_cols):
    cols = [c for c in df.columns if c not in exclude_cols]
    numeric_cols = []
    for c in cols:
        # intentar convertir a numeric (sin modificar df)
        try:
            series = pd.to_numeric(df[c], errors='coerce')
            # si no todo es NaN, consideramos la columna como numérica
            if series.notna().sum() > 0:
                numeric_cols.append(c)
        except Exception:
            pass
    return numeric_cols


# --- Ejecución de Carga y Preparación de Datos ---

# Carga inicial de las dos pestañas
try:
    df_text = cargar_hoja_google(sheet_name=SHEET_NAME_TEXT)
except Exception as e:
    print('No pudo cargarse la pestaña de respuestas textuales:', e)
    df_text = pd.DataFrame()

try:
    df_num = cargar_hoja_google(sheet_name=SHEET_NAME_NUM)
except Exception as e:
    print('No pudo cargarse la pestaña numérica:', e)
    df_num = pd.DataFrame()

# Si la primera pestaana tiene texto, convertirlo
if not df_text.empty:
    df_text = convertir_likert(df_text)

# Si la segunda ya tiene números, usarla tal cual; si está vacía, intentaremos usar la primera
if df_num.empty and not df_text.empty:
    df = df_text
else:
    # preferir df_num (ya numerizado en la hoja 'Base de Datos Limpia') pero aplicar conversión también por si
    df = df_num if not df_num.empty else df_text
    df = convertir_likert(df)

# Normalizar nombres de columnas y encontrar columnas clave
cols_map = {normalize_text(c): c for c in df.columns}
# candidatos para buscar
candidatos = {
    'evaluado': ['nombre del colaborador evaluado', 'evaluado', 'nombre colaborador evaluado'],
    'relacion': ['cual es tu relacion con el evaluado', 'cual es tu relacion con el evaluado?',
                 'relacion con el evaluado', 'relacion'],
    'timestamp': ['marca temporal', 'timestamp', 'fecha']
}

COL_EVALUADO = None
COL_RELACION = None
COL_TIMESTAMP = None
for key, variants in candidatos.items():
    for v in variants:
        norm = normalize_text(v)
        if norm in cols_map:
            if key == 'evaluado':
                COL_EVALUADO = cols_map[norm]
            elif key == 'relacion':
                COL_RELACION = cols_map[norm]
            elif key == 'timestamp':
                COL_TIMESTAMP = cols_map[norm]
            break

# Si no encontramos, intentar heurística por búsqueda parcial
if COL_EVALUADO is None:
    for k_norm, orig in cols_map.items():
        if 'evaluado' in k_norm or 'colaborador evaluado' in k_norm:
            COL_EVALUADO = orig
            break
if COL_RELACION is None:
    for k_norm, orig in cols_map.items():
        if 'relacion' in k_norm or 'relaci' in k_norm:
            COL_RELACION = orig
            break
if COL_TIMESTAMP is None:
    for k_norm, orig in cols_map.items():
        if 'marca' in k_norm or 'timestamp' in k_norm or 'fecha' in k_norm:
            COL_TIMESTAMP = orig
            break

# Preparar lista de columnas a excluir (metadatos)
exclude_list = [COL_TIMESTAMP, 'Nombre Completo:', COL_EVALUADO,
                '¿Cuáles son las 2 o 3 principales fortalezas que observas en este colaborador?',
                '¿Cuáles son las 2 o 3 principales áreas de oportunidad (a mejorar) que sugieres para este colaborador?',
                'Comentarios adicionales (opcional)', COL_RELACION]
# algunos de esos nombres pueden no existir en df; filtrarlos
exclude_list = [c for c in exclude_list if c is not None and c in df.columns]

# Determinar columnas de competencia
comp_cols = columnas_competencias(df, exclude_list)

# --- CATEGORIZACIÓN MEJORADA DE COMPETENCIAS ---
def categorizar_competencias_detallado(competencias):
    """
    Agrupa las competencias en categorías específicas de habilidades
    """
    categorias = {
        'Trabajo en Equipo': [],
        'Comunicación': [],
        'Liderazgo': [],
        'Toma de Decisiones': [],
        'Planeación': [],
        'Manejo de Recursos': [],
        'Capacidad de Negociación': [],
        'Innovación y Creatividad': [],
        'Gestión del Tiempo': [],
        'Calidad y Resultados': []
    }

    for comp in competencias:
        comp_lower = comp.lower()

        # Clasificación por palabras clave
        if any(palabra in comp_lower for palabra in ['equipo', 'colabora', 'trabajo en equipo']):
            categorias['Trabajo en Equipo'].append(comp)
        elif any(palabra in comp_lower for palabra in ['comunica', 'escucha', 'claridad', 'respeto']):
            categorias['Comunicación'].append(comp)
        elif any(palabra in comp_lower for palabra in ['liderazgo', 'manejo de', 'gestiona', 'subordin']):
            categorias['Liderazgo'].append(comp)
        elif any(palabra in comp_lower for palabra in ['decisiones', 'toma de']):
            categorias['Toma de Decisiones'].append(comp)
        elif any(palabra in comp_lower for palabra in ['planeación', 'planea', 'junta', 'seguimiento']):
            categorias['Planeación'].append(comp)
        elif any(palabra in comp_lower for palabra in ['recursos', 'manejo de', 'material']):
            categorias['Manejo de Recursos'].append(comp)
        elif any(palabra in comp_lower for palabra in ['negociación', 'negocia', 'flexibilidad', 'retroalimentación']):
            categorias['Capacidad de Negociación'].append(comp)
        elif any(palabra in comp_lower for palabra in ['innovadora', 'creatividad', 'idea', 'investiga', 'tendencia']):
            categorias['Innovación y Creatividad'].append(comp)
        elif any(palabra in comp_lower for palabra in ['tiempo', 'cumple', 'programa', 'forma']):
            categorias['Gestión del Tiempo'].append(comp)
        elif any(palabra in comp_lower for palabra in ['calidad', 'valor', 'resultado', 'estándar', 'mejora']):
            categorias['Calidad y Resultados'].append(comp)
        else:
            # Si no encaja, ponerla en la más genérica
            categorias['Calidad y Resultados'].append(comp)

    # Filtrar categorías vacías
    return {k: v for k, v in categorias.items() if v}

categorias_comp = categorizar_competencias_detallado(comp_cols)

# --- 2. INICIALIZAR APP CON TEMA BOOTSTRAP ---
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# Opciones de evaluados
if COL_EVALUADO and COL_EVALUADO in df.columns:
    evaluados_options = [{'label': n, 'value': n} for n in sorted(df[COL_EVALUADO].dropna().unique())]
else:
    evaluados_options = []


# Opciones de competencias
def short_label(col):
    s = col
    if len(s) > 40:
        return s[:37] + '...'
    return s


comp_options = [{'label': short_label(c), 'value': c} for c in comp_cols]

# --- 3. NUEVO LAYOUT CON BOOTSTRAP ---
app.layout = dbc.Container([
    # Header - Responsivo
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H2('Dashboard 360° - Evaluación de Desempeño',
                       className="text-dark fw-bold mb-2",
                       style={'fontSize': 'clamp(1.25rem, 4vw, 2rem)'}),  # Tamaño de fuente adaptable
                html.P('Análisis integral de competencias y habilidades',
                      className="text-secondary",
                      style={'fontSize': 'clamp(0.875rem, 2vw, 1rem)'})
            ], className="text-center", style={
                'backgroundColor': '#f8f9fa',
                'padding': 'clamp(15px, 4vw, 30px)',  # Padding adaptable
                'borderRadius': '10px',
                'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
            })
        ], xs=12, className="mb-3 mb-md-4")  # Margen adaptable
    ]),

    # Panel de Control - Adaptable
    dbc.Row([
        # Sidebar - Full width en móvil, lateral en desktop
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("Configuración", className="card-title text-primary mb-3",
                           style={'fontSize': 'clamp(1rem, 3vw, 1.25rem)'}),

                    # Selector de evaluado
                    html.Label('Evaluado:', className="fw-bold mb-2 small"),
                    dcc.Dropdown(
                        id='evaluado-dropdown',
                        options=evaluados_options,
                        value=evaluados_options[0]['value'] if evaluados_options else None,
                        className="mb-3",
                        style={'fontSize': 'clamp(0.75rem, 2vw, 1rem)'}
                    ),

                    html.Hr(),

                    # Ponderaciones compactas - Grid responsivo
                    html.Label('Ponderaciones (%):', className="fw-bold mb-2 small"),
                    html.Small('Se normalizan automáticamente', className="text-muted d-block mb-2"),

                    dbc.Row([
                        dbc.Col([
                            dbc.Label('Auto', className="small", style={'fontSize': 'clamp(0.7rem, 1.5vw, 0.875rem)'}),
                            dbc.Input(id='w-auto', type='number', value=5, min=0, max=100, step=1, size="sm")
                        ], xs=6, sm=3, className="mb-2 mb-sm-0"),  # 2 columnas en móvil, 4 en tablet+
                        dbc.Col([
                            dbc.Label('Jefe', className="small", style={'fontSize': 'clamp(0.7rem, 1.5vw, 0.875rem)'}),
                            dbc.Input(id='w-jefe', type='number', value=18, min=0, max=100, step=1, size="sm")
                        ], xs=6, sm=3, className="mb-2 mb-sm-0"),
                        dbc.Col([
                            dbc.Label('Colegas', className="small", style={'fontSize': 'clamp(0.7rem, 1.5vw, 0.875rem)'}),
                            dbc.Input(id='w-colegas', type='number', value=30, min=0, max=100, step=1, size="sm")
                        ], xs=6, sm=3),
                        dbc.Col([
                            dbc.Label('Subord.', className="small", style={'fontSize': 'clamp(0.7rem, 1.5vw, 0.875rem)'}),
                            dbc.Input(id='w-sub', type='number', value=47, min=0, max=100, step=1, size="sm")
                        ], xs=6, sm=3)
                    ])
                ], className="p-3")  # Padding fijo reducido para móviles
            ], className="shadow-sm mb-3"),

            # Tarjeta de calificación final
            dbc.Card([
                dbc.CardBody(html.Div(id='resultado-global'), className="p-3")
            ], className="shadow-sm mb-3"),

            # Botones de Descarga
            dbc.Card([
                dbc.CardBody([
                    html.H6("Exportar Reporte", className="card-title text-muted mb-3"),
                    dcc.Loading(
                        id="loading-download",
                        type="default",
                        children=[
                            dbc.Row([
                                dbc.Col(
                                    dbc.Button([html.I(className="fas fa-file-pdf me-2"), "PDF"], 
                                             id="btn-pdf", color="danger", outline=True, className="w-100"),
                                    width=6
                                ),
                                dbc.Col(
                                    dbc.Button([html.I(className="fas fa-file-word me-2"), "Word"], 
                                             id="btn-word", color="primary", outline=True, className="w-100"),
                                    width=6
                                )
                            ]),
                            dcc.Download(id="download-component")
                        ]
                    )
                ], className="p-3")
            ], className="shadow-sm")
        ], xs=12, sm=12, md=12, lg=3, xl=3, className="mb-3 mb-lg-0"),  # Full width en móvil/tablet, sidebar en desktop

        # Área de visualización - Adaptable
        dbc.Col([
            # Grid de gráficas de pastel por categoría
            html.Div(id='graficas-categorias')
        ], xs=12, sm=12, md=12, lg=9, xl=9)  # Full width en móvil/tablet, 9 cols en desktop
    ])
], fluid=True, className="bg-light p-2 p-sm-3 p-md-4", style={'minHeight': '100vh'})


# --- Mapeo de Relaciones ---
def relacion_a_grupo(relacion):
    r = str(relacion).lower()
    if 'auto' in r or 'autoevalu' in r:
        return 'Autoevaluación'
    if 'jefe' in r or 'supervisor' in r:
        return 'Jefe Inmediato'
    if 'subordin' in r:
        return 'Subordinados'
    # tratar 'par' y 'cliente' como colegas por defecto
    if 'par' in r or 'compa' in r or 'cliente' in r:
        return 'Colegas'
    # fallback
    return 'Otros'

# Colores profesionales y armoniosos para las categorías
colores_categorias = {
    'Trabajo en Equipo': '#667eea',
    'Comunicación': '#36d1dc',
    'Liderazgo': '#f093fb',
    'Toma de Decisiones': '#fa709a',
    'Planeación': '#a8edea',
    'Manejo de Recursos': '#ffd166',
    'Capacidad de Negociación': '#9795f0',
    'Innovación y Creatividad': '#fbc2eb',
    'Gestión del Tiempo': '#38ef7d',
    'Calidad y Resultados': '#4facfe'
}

# --- 4. LÓGICA DE CÁLCULO (Refactorizado) ---
def calcular_datos_dashboard(evaluado, w_auto, w_jefe, w_colegas, w_sub):
    if evaluado is None:
        return None

    # Ponderaciones
    weights = {
        'Autoevaluación': float(w_auto or 0),
        'Jefe Inmediato': float(w_jefe or 0),
        'Colegas': float(w_colegas or 0),
        'Subordinados': float(w_sub or 0)
    }
    total = sum(weights.values())
    if total <= 0:
        return {'error': 'Ponderaciones deben sumar > 0'}

    weights_norm = {k: v / total for k, v in weights.items()}

    # Filtrar datos del evaluado
    df_eval = df[df[COL_EVALUADO] == evaluado]
    if df_eval.empty:
        return {'error': 'Sin datos'}

    df_eval = df_eval.copy()
    df_eval['grupo_ponderacion'] = df_eval[COL_RELACION].map(relacion_a_grupo)

    # Calcular promedios por grupo
    grupos = df_eval.groupby('grupo_ponderacion')[comp_cols].mean()

    # Conteo de evaluadores
    conteo_evaluadores = df_eval['grupo_ponderacion'].value_counts().to_dict()
    total_evaluadores = len(df_eval)

    # Calcular puntaje final por competencia
    final_por_comp = pd.Series(0.0, index=comp_cols)
    for grupo, peso in weights_norm.items():
        if grupo in grupos.index:
            final_por_comp = final_por_comp + grupos.loc[grupo].astype(float).fillna(0) * peso

    calificacion_final = final_por_comp.mean()

    # Promedios por categoría
    promedios_categorias = {}
    for categoria, comps_cat in categorias_comp.items():
        if comps_cat:
            promedios_categorias[categoria] = final_por_comp[comps_cat].mean()

    # --- GENERACIÓN DE FIGURAS ---
    
    # 1. Radar General
    fig_radar_general = go.Figure()
    categorias_list = list(promedios_categorias.keys())
    valores_list = list(promedios_categorias.values())
    
    # Cerrar polígono
    if categorias_list:
        categorias_radar = categorias_list + [categorias_list[0]]
        valores_radar = valores_list + [valores_list[0]]
        valores_estandar = [3.5] * len(categorias_radar)
        
        fig_radar_general.add_trace(go.Scatterpolar(
            r=valores_radar, theta=categorias_radar, fill='toself', name='Evaluación Actual',
            line=dict(color='#667eea', width=3), fillcolor='rgba(102, 126, 234, 0.3)'
        ))
        fig_radar_general.add_trace(go.Scatterpolar(
            r=valores_estandar, theta=categorias_radar, fill=None, name='Estándar Mínimo (3.5)',
            line=dict(color='#ff6b6b', width=2, dash='dash')
        ))
        
        fig_radar_general.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
            showlegend=True, margin=dict(t=20, b=80, l=20, r=20), height=400
        )

    # 2. Radar Avanzado
    fig_radar_avanzado = go.Figure()
    if categorias_list:
        # Capas de referencia
        fig_radar_avanzado.add_trace(go.Scatterpolar(
            r=[4.5]*len(categorias_radar), theta=categorias_radar, fill='toself', name='Sobresaliente',
            line=dict(color='#28a745', width=1, dash='dot'), fillcolor='rgba(40, 167, 69, 0.1)'
        ))
        fig_radar_avanzado.add_trace(go.Scatterpolar(
            r=[3.5]*len(categorias_radar), theta=categorias_radar, fill='toself', name='Aceptable',
            line=dict(color='#ffc107', width=1, dash='dot'), fillcolor='rgba(255, 193, 7, 0.1)'
        ))
        
        # Promedio Empresa
        promedios_empresa_cat = []
        for categoria, comps_cat in categorias_comp.items():
            if comps_cat:
                # Calcular promedio global de la empresa para estas competencias (scalar)
                prom = df[comps_cat].mean().mean()
                promedios_empresa_cat.append(prom)
        
        if promedios_empresa_cat:
            prom_empresa_radar = promedios_empresa_cat + [promedios_empresa_cat[0]]
            fig_radar_avanzado.add_trace(go.Scatterpolar(
                r=prom_empresa_radar, theta=categorias_radar, fill=None, name='Promedio Empresa',
                line=dict(color='#6c757d', width=2, dash='dash')
            ))

        # Evaluado
        fig_radar_avanzado.add_trace(go.Scatterpolar(
            r=valores_radar, theta=categorias_radar, fill='toself', name=evaluado,
            line=dict(color='#667eea', width=3), fillcolor='rgba(102, 126, 234, 0.3)'
        ))
        
        fig_radar_avanzado.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
            showlegend=True, height=500, margin=dict(t=40, b=40, l=40, r=180)
        )

    # 3. Matriz 9-Box
    # 3. Matriz 9-Box
    categorias_potencial = ['Liderazgo', 'Innovación y Creatividad', 'Toma de Decisiones']
    cats_presentes = [c for c in categorias_potencial if c in promedios_categorias]
    if cats_presentes:
        potencial = sum([promedios_categorias.get(cat, 0) for cat in cats_presentes]) / len(cats_presentes)
    else:
        potencial = 0
    desempeno = calificacion_final

    # Determinar cuadrante
    if desempeno >= 4.0 and potencial >= 4.0:
        cuadrante = "ESTRELLA"
        color_cuadrante = "#28a745"
        descripcion_cuadrante = "Alto desempeño y alto potencial - Talento clave"
        accion_rh = "Acción: Retener, desarrollar para posiciones de liderazgo senior"
    elif desempeno >= 4.0 and potencial < 4.0:
        cuadrante = "CONTRIBUIDOR SÓLIDO"
        color_cuadrante = "#17a2b8"
        descripcion_cuadrante = "Alto desempeño, potencial moderado - Experto técnico"
        accion_rh = "Acción: Reconocer expertise, considerar roles especializados"
    elif desempeno < 4.0 and potencial >= 4.0:
        cuadrante = "TALENTO EMERGENTE"
        color_cuadrante = "#ffc107"
        descripcion_cuadrante = "Potencial alto, desempeño en desarrollo"
        accion_rh = "Acción: Mentoring intensivo, asignar proyectos retadores"
    else:
        cuadrante = "EN DESARROLLO"
        color_cuadrante = "#dc3545"
        descripcion_cuadrante = "Requiere apoyo en desempeño y desarrollo"
        accion_rh = "Acción: Plan de mejora de 90 días con seguimiento semanal"

    fig_matriz = go.Figure()
    fig_matriz.add_hline(y=4.0, line_dash="dash", line_color="gray", opacity=0.5)
    fig_matriz.add_vline(x=4.0, line_dash="dash", line_color="gray", opacity=0.5)
    
    fig_matriz.add_trace(go.Scatter(
        x=[potencial], y=[desempeno], mode='markers+text',
        marker=dict(size=20, color=color_cuadrante, line=dict(width=2, color='white')),
        text=[evaluado[:15]], textposition="top center"
    ))
    
    fig_matriz.update_layout(
        xaxis_title="Potencial", yaxis_title="Desempeño",
        xaxis=dict(range=[0, 5]), yaxis=dict(range=[0, 5]),
        height=450, plot_bgcolor='white', margin=dict(t=20, b=60, l=60, r=20)
    )

    # 4. Comparativa
    fig_comparacion = go.Figure()
    colores_grupos = {'Autoevaluación': '#17a2b8', 'Jefe Inmediato': '#dc3545', 'Colegas': '#ffc107', 'Subordinados': '#28a745'}
    
    for grupo in grupos.index:
        promedios_grupo_cat = []
        for categoria, comps_cat in categorias_comp.items():
            if comps_cat:
                prom = grupos.loc[grupo][comps_cat].mean()
                promedios_grupo_cat.append(prom)
            else:
                promedios_grupo_cat.append(0)
        
        fig_comparacion.add_trace(go.Bar(
            name=grupo, x=categorias_list, y=promedios_grupo_cat,
            marker_color=colores_grupos.get(grupo, '#6c757d')
        ))
    
    fig_comparacion.update_layout(barmode='group', height=400, margin=dict(t=80, b=100, l=50, r=50))

    # 5. Gráficas de Pastel (Donas) por Categoría
    figs_categorias = {}
    for categoria, comps_cat in categorias_comp.items():
        if not comps_cat: continue
        promedio_cat = final_por_comp[comps_cat].mean()
        porcentaje = (promedio_cat / 5.0) * 100
        
        fig_pastel = go.Figure(data=[go.Pie(
            labels=['Logrado', 'Por mejorar'], values=[porcentaje, 100-porcentaje], hole=0.65,
            marker=dict(colors=[colores_categorias.get(categoria, '#667eea'), '#f0f0f0'], line=dict(color='white', width=2)),
            textinfo='none', hovertemplate='%{label}: %{value:.1f}%<extra></extra>'
        )])
        fig_pastel.update_layout(showlegend=False, height=180, margin=dict(t=5, b=5, l=5, r=5), paper_bgcolor='rgba(0,0,0,0)',
            annotations=[dict(text=f'<b style="font-size:20px">{promedio_cat:.2f}</b>', x=0.5, y=0.5, showarrow=False)])
        
        figs_categorias[f'cat_{categoria}'] = fig_pastel

    # Textos y KPIs
    categorias_bajas = [cat for cat, val in promedios_categorias.items() if val < 3.0]
    categorias_criticas = [cat for cat, val in promedios_categorias.items() if val < 2.5]
    
    if calificacion_final >= 4.5:
        estado_aptitud = "SOBRESALIENTE"
        color_aptitud = "#28a745"
        mensaje_aptitud = "Desempeño excepcional en todas las competencias"
        recomendacion_rh = "Talento clave - Considerar para roles de liderazgo estratégico"
    elif calificacion_final >= 4.0 and not categorias_bajas:
        estado_aptitud = "ALTO DESEMPEÑO"
        color_aptitud = "#28a745"
        mensaje_aptitud = "Cumple ampliamente con los estándares del puesto"
        recomendacion_rh = "Excelente desempeño - Considerar para promoción"
    elif calificacion_final >= 3.5 and not categorias_criticas:
        estado_aptitud = "CUMPLE EXPECTATIVAS"
        color_aptitud = "#17a2b8"
        mensaje_aptitud = "Desempeño satisfactorio acorde al puesto"
        recomendacion_rh = "Mantener nivel actual - Oportunidades de desarrollo"
    elif calificacion_final >= 2.5:
        estado_aptitud = "EN DESARROLLO"
        color_aptitud = "#ffc107"
        mensaje_aptitud = f"Oportunidades de crecimiento en: {', '.join(categorias_bajas[:2])}"
        recomendacion_rh = "Plan de desarrollo personalizado"
    else:
        estado_aptitud = "REQUIERE APOYO"
        color_aptitud = "#ff6b6b"
        mensaje_aptitud = f"Requiere apoyo inmediato en: {', '.join(categorias_criticas[:2])}"
        recomendacion_rh = "Plan de acción intensivo"

    # KPIs adicionales
    consistencia = max(0, min(5, 5 - (final_por_comp.std() * 2)))
    brecha_mejora = 5.0 - calificacion_final
    percentil = (df.groupby(COL_EVALUADO)[comp_cols].mean().mean(axis=1) < calificacion_final).mean() * 100
    nivel_cumplimiento = min(100, ((calificacion_final - 3.5) / 1.5) * 100) if calificacion_final >= 3.5 else (calificacion_final / 3.5) * 100

    return {
        'meta': {
            'evaluado': evaluado,
            'total_evaluadores': total_evaluadores,
            'conteo_evaluadores': conteo_evaluadores
        },
        'kpis': {
            'calificacion_final': calificacion_final,
            'consistencia': consistencia,
            'brecha_mejora': brecha_mejora,
            'percentil': percentil,
            'nivel_cumplimiento': nivel_cumplimiento
        },
        'figuras': {
            'radar_general': fig_radar_general,
            'radar_avanzado': fig_radar_avanzado,
            'matriz': fig_matriz,
            'comparacion': fig_comparacion,
            **figs_categorias
        },
        'textos': {
            'estado_aptitud': estado_aptitud,
            'color_aptitud': color_aptitud,
            'mensaje_aptitud': mensaje_aptitud,
            'recomendacion_rh': recomendacion_rh,
            'cuadrante': cuadrante,
            'color_cuadrante': color_cuadrante,
            'descripcion_cuadrante': descripcion_cuadrante,
            'accion_rh': accion_rh,
            'fortalezas': sorted(promedios_categorias.items(), key=lambda x: x[1], reverse=True)[:3],
            'mejoras': sorted(promedios_categorias.items(), key=lambda x: x[1])[:3]
        },
        'data_raw': {
            'final_por_comp': final_por_comp,
            'colores_categorias': colores_categorias,
            'promedios_categorias': promedios_categorias,
            'promedios_empresa_cat': promedios_empresa_cat if 'promedios_empresa_cat' in locals() else [],
            'promedios_por_grupo': {
                grupo: [grupos.loc[grupo][categorias_comp[cat]].mean() if categorias_comp[cat] else 0 for cat in promedios_categorias.keys()]
                for grupo in grupos.index
            }
        }
    }

# --- 4. CALLBACK MODIFICADO ---
@app.callback(
    Output('resultado-global', 'children'),
    Output('graficas-categorias', 'children'),
    Input('evaluado-dropdown', 'value'),
    Input('w-auto', 'value'),
    Input('w-jefe', 'value'),
    Input('w-colegas', 'value'),
    Input('w-sub', 'value')
)
def actualizar_panel(evaluado, w_auto, w_jefe, w_colegas, w_sub):
    try:
        datos = calcular_datos_dashboard(evaluado, w_auto, w_jefe, w_colegas, w_sub)
        
        if datos is None or 'error' in datos:
            msg = datos.get('error', 'Selecciona un evaluado') if datos else 'Selecciona un evaluado'
            resumen = html.P(msg, className="text-muted text-center")
            contenido = html.Div(msg, className="text-center text-muted p-5")
            return resumen, contenido

        # Desempaquetar datos
        meta = datos['meta']
        kpis = datos['kpis']
        figs = datos['figuras']
        textos = datos['textos']
        
        # --- RESUMEN CON TARJETA DE EVALUADORES ---
        resumen = html.Div([
            # Calificación Final
            html.H6("Calificación Final", className="text-muted mb-1"),
            html.H1(f"{kpis['calificacion_final']:.2f}", className='text-primary fw-bold mb-1', style={'fontSize': '2.5rem'}),
            html.Small('de 5.0', className="text-muted d-block mb-2"),
            html.Hr(className="my-2"),
            
            # Tarjeta de Evaluadores
            html.Div([
                html.H6("Evaluadores", className="text-muted mb-3 text-center"),
                html.Div([
                    html.Div([
                        html.I(className="fas fa-users", style={'fontSize': '24px', 'color': '#667eea'}),
                        html.H3(f"{meta['total_evaluadores']}", className='text-primary fw-bold mb-0 mt-2'),
                        html.Small('Total de evaluaciones', className='text-muted d-block')
                    ], className="text-center mb-3 p-2", style={'backgroundColor': '#f8f9fa', 'borderRadius': '8px'}),

                    # Desglose por tipo
                    html.Div([
                        html.Div([
                            html.Div([
                                html.Span('●', style={'color': '#6c757d', 'fontSize': '20px', 'marginRight': '8px'}),
                                html.Span(tipo, className='small fw-bold', style={'fontSize': '0.8rem'}),
                            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '4px'}),
                            html.Div([
                                html.Strong(str(cantidad), className='text-primary', style={'fontSize': '1.1rem'}),
                                html.Small(f" evaluacion{'es' if cantidad != 1 else ''}", className='text-muted ms-1')
                            ])
                        ], className='mb-2 pb-2', style={'borderBottom': '1px solid #e9ecef'})
                        for tipo, cantidad in sorted(meta['conteo_evaluadores'].items(), key=lambda x: x[1], reverse=True)
                    ])
                ])
            ])
        ], className="text-center")

        # --- TARJETAS DE KPIs ---
        tarjetas_kpis = dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className="fas fa-check-circle", style={'fontSize': '24px', 'color': '#667eea'}),
                            html.H6("Nivel de Cumplimiento", className="text-muted mt-2 mb-1", style={'fontSize': '11px'}),
                            html.H4(f"{kpis['nivel_cumplimiento']:.0f}%", className="fw-bold text-primary mb-0")
                        ], className="text-center")
                    ], className="p-2")
                ], className="shadow-sm border-0", style={'borderTop': '3px solid #667eea'})
            ], width=6, lg=3, className="mb-2"),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className="fas fa-balance-scale", style={'fontSize': '24px', 'color': '#36d1dc'}),
                            html.H6("Consistencia", className="text-muted mt-2 mb-1", style={'fontSize': '11px'}),
                            html.H4(f"{kpis['consistencia']:.1f}/5.0", className="fw-bold text-info mb-0")
                        ], className="text-center")
                    ], className="p-2")
                ], className="shadow-sm border-0", style={'borderTop': '3px solid #36d1dc'})
            ], width=6, lg=3, className="mb-2"),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className="fas fa-chart-line", style={'fontSize': '24px', 'color': '#f093fb'}),
                            html.H6("Percentil", className="text-muted mt-2 mb-1", style={'fontSize': '11px'}),
                            html.H4(f"Top {100 - kpis['percentil']:.0f}%", className="fw-bold text-success mb-0")
                        ], className="text-center")
                    ], className="p-2")
                ], className="shadow-sm border-0", style={'borderTop': '3px solid #f093fb'})
            ], width=6, lg=3, className="mb-2"),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className="fas fa-arrow-up", style={'fontSize': '24px', 'color': '#ffd166'}),
                            html.H6("Brecha de Mejora", className="text-muted mt-2 mb-1", style={'fontSize': '11px'}),
                            html.H4(f"{kpis['brecha_mejora']:.2f}", className="fw-bold text-warning mb-0")
                        ], className="text-center")
                    ], className="p-2")
                ], className="shadow-sm border-0", style={'borderTop': '3px solid #ffd166'})
            ], width=6, lg=3, className="mb-2")
        ], className="mb-3")

        # Tarjeta Aptitud
        tarjeta_aptitud = dbc.Card([
            dbc.CardBody([
                html.Div([
                    html.H4(textos['estado_aptitud'], className="fw-bold mt-2 mb-1", style={'color': textos['color_aptitud']}),
                    html.P(textos['mensaje_aptitud'], className="small text-muted mb-2"),
                    html.Hr(className="my-2"),
                    html.Div([
                        html.Small("📋 Recomendación RH:", className="fw-bold d-block text-dark mb-1"),
                        html.Small(textos['recomendacion_rh'], className="text-muted")
                    ], className="text-start px-2")
                ], className="text-center")
            ])
        ], className="shadow-sm border-0", style={'borderLeft': f"5px solid {textos['color_aptitud']}"})

        # Tarjeta Matriz
        tarjeta_matriz = dbc.Card([
            dbc.CardBody([
                html.H5("Matriz de Potencial vs. Desempeño", className="card-title text-primary mb-1"),
                dcc.Graph(figure=figs['matriz'], config={'displayModeBar': False}, style={'height': '450px'}),
                html.Div([
                    html.Div([
                        html.H6(textos['cuadrante'], className="fw-bold mb-1", style={'color': textos['color_cuadrante']}),
                        html.P(textos['descripcion_cuadrante'], className="small text-muted mb-2"),
                        html.P(textos['accion_rh'], className="small fw-bold text-dark mb-0")
                    ], className="p-3 rounded", style={'backgroundColor': '#f8f9fa'})
                ])
            ])
        ], className="shadow-sm")

        # Tabla Análisis
        tabla_analisis = dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.H6("🌟 Fortalezas", className="text-success fw-bold mb-3"),
                        html.Ul([html.Li([html.Strong(cat), f": {val:.2f}/5.0"], className="mb-2") for cat, val in textos['fortalezas']], className="mb-0")
                    ], width=6),
                    dbc.Col([
                        html.H6("📈 Áreas de Mejora", className="text-warning fw-bold mb-3"),
                        html.Ul([html.Li([html.Strong(cat), f": {val:.2f}/5.0"], className="mb-2") for cat, val in textos['mejoras']], className="mb-0")
                    ], width=6)
                ])
            ])
        ], className="shadow-sm")

        # --- ORGANIZAR LAYOUT ---
        contenido = html.Div([
            tarjetas_kpis,
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Análisis de Madurez por Habilidades", className="card-title text-primary mb-1"),
                            dcc.Graph(figure=figs['radar_avanzado'], config={'displayModeBar': False}, style={'height': '500px'})
                        ])
                    ], className="shadow-sm")
                ], width=12, lg=7, className="mb-3"),
                dbc.Col([tarjeta_matriz], width=12, lg=5, className="mb-3")
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Perfil de Competencias", className="card-title text-primary mb-3"),
                            dcc.Graph(figure=figs['radar_general'], config={'displayModeBar': False}, style={'height': '400px'})
                        ])
                    ], className="shadow-sm")
                ], width=12, lg=6, className="mb-3"),
                dbc.Col([tarjeta_aptitud, html.Div(style={'height': '15px'}), tabla_analisis], width=12, lg=6, className="mb-3")
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            dcc.Graph(figure=figs['comparacion'], config={'displayModeBar': False}, style={'height': '400px'})
                        ])
                    ], className="shadow-sm")
                ], width=12, className="mb-4")
            ])
        ])

        # Gráficas de Pastel (Donas)
        graficas = []
        colores_categorias = datos['data_raw']['colores_categorias']
        
        for categoria in categorias_comp.keys():
            fig_key = f'cat_{categoria}'
            if fig_key in figs:
                fig_pastel = figs[fig_key]
                
                graficas.append(dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([html.I(className="fas fa-star", style={'color': colores_categorias.get(categoria, '#667eea'), 'marginRight': '8px'}), html.Span(categoria, className="fw-bold")], className="text-center mb-2"),
                            dcc.Graph(figure=fig_pastel, config={'displayModeBar': False}, style={'height': '180px'})
                        ], className="p-2")
                    ], className="shadow-sm border-0", style={'borderTop': f'4px solid {colores_categorias.get(categoria, "#667eea")}'})
                ], width=6, lg=4, xl=3, className="mb-3"))

        contenido.children.append(dbc.Row(graficas))
        return resumen, contenido
    except Exception as e:
        import traceback
        traceback.print_exc()
        return html.Div(f"Error: {e}"), html.Div(f"Error detallado: {e}")

# --- CALLBACK DE DESCARGA ---
@app.callback(
    Output("download-component", "data"),
    Input("btn-pdf", "n_clicks"),
    Input("btn-word", "n_clicks"),
    State('evaluado-dropdown', 'value'),
    State('w-auto', 'value'),
    State('w-jefe', 'value'),
    State('w-colegas', 'value'),
    State('w-sub', 'value'),
    prevent_initial_call=True
)
def descargar_reporte(n_pdf, n_word, evaluado, w_auto, w_jefe, w_colegas, w_sub):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    datos = calcular_datos_dashboard(evaluado, w_auto, w_jefe, w_colegas, w_sub)
    if datos is None or 'error' in datos:
        raise PreventUpdate

    print(f"Callback descarga activado: {button_id}")
    
    try:
        if button_id == "btn-pdf":
            print("Generando PDF...")
            pdf_buffer = utils_reporte.generar_pdf(datos)
            if pdf_buffer:
                print("PDF generado correctamente, enviando...")
                return dcc.send_bytes(pdf_buffer.read(), f"Reporte_360_{evaluado}.pdf")
            else:
                print("Error: generar_pdf retornó None")
        
        elif button_id == "btn-word":
            print("Generando Word...")
            word_buffer = utils_reporte.generar_word(datos)
            if word_buffer:
                print("Word generado correctamente, enviando...")
                return dcc.send_bytes(word_buffer.read(), f"Reporte_360_{evaluado}.docx")
            else:
                print("Error: generar_word retornó None")
    except Exception as e:
        print(f"Excepción en generación de reporte: {e}")
        import traceback
        traceback.print_exc()
            
    return None

if __name__ == '__main__':
    app.run(debug=True, port=8051)
