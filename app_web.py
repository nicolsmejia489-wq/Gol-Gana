import streamlit as st
import sqlite3
import pandas as pd
import random
import easyocr
import cloudinary
import cloudinary.uploader
import io
import numpy as np
from PIL import Image
import cv2
import re  # Para expresiones regulares (encontrar números difíciles)
from thefuzz import fuzz # Para comparación flexible de nombres
import json
import os
import streamlit as st
from sqlalchemy import create_engine, text
import time
import motor_colores
import motor_grafico
from io import BytesIO
import PIL.Image
import requests
import extcolors
from difflib import SequenceMatcher





# --- BLINDAJE VISUAL V2: FORZAR MODO OSCURO TOTAL ---
st.markdown("""
    <style>
        /* 1. FONDO GENERAL */
        .stApp {
            background-color: #0E1117;
            color: white;
        }
        
        /* 2. ARREGLO DE INPUTS (PIN, Nombres, Números) */
        div[data-baseweb="input"] {
            background-color: #262730 !important;
            border: 1px solid #444 !important;
        }
        div[data-baseweb="input"] > div {
            background-color: transparent !important;
            color: white !important;
        }
        input { color: white !important; }
        
        /* 3. ARREGLO DE BOTONES (Contactar DT, Guardar) */
        /* Ataca tanto a botones normales como a link_buttons */
        button[kind="secondary"], div[data-testid="stLinkButton"] a {
            background-color: #262730 !important;
            color: white !important;
            border: 1px solid #555 !important;
        }
        /* Efecto Hover para que se note que es botón */
        button[kind="secondary"]:hover, div[data-testid="stLinkButton"] a:hover {
            border-color: #FFD700 !important;
            color: #FFD700 !important;
        }

        /* 4. ARREGLO DE EXPANDERS (Reportar Marcador) */
        /* El encabezado del expander */
        div[data-testid="stExpander"] details summary {
            background-color: #262730 !important;
            color: white !important;
            border-radius: 5px;
        }
        /* El contenido interno del expander */
        div[data-testid="stExpander"] details {
            border-color: #444 !important;
            background-color: #0E1117 !important; 
        }
        /* Texto del título del expander */
        div[data-testid="stExpander"] p {
            color: white !important;
        }

        /* 5. ARREGLO DE FILE UPLOADER (Subir Foto) */
        div[data-testid="stFileUploader"] section {
            background-color: #262730 !important;
        }
        div[data-testid="stFileUploader"] span {
            color: #ccc !important;
        }

        /* 6. Textos generales */
        p, label, h1, h2, h3 {
            color: white !important;
        }
    </style>
""", unsafe_allow_html=True)







# 1. CONFIGURACIÓN PRINCIPAL
st.set_page_config(
    page_title="Gol-Gana Pro", 
    layout="centered", 
    initial_sidebar_state="collapsed"
)


# --- 1. CONEXIÓN (Siempre al principio) ---
try:
    conn = st.connection("postgresql", type="sql")
except Exception as e:
    st.error(f"Error de conexión: {e}")
    conn = None

# --- 2. INICIALIZACIÓN DE VARIABLES (Valores de Respaldo) ---
color_maestro = "#FFD700"  # Dorado por defecto
fondo_url = "https://res.cloudinary.com/dlvczeqlp/image/upload/v1769056355/fondos_dinamicos/fondo_activo_golgana.png"

# --- 3. LÓGICA DE IDENTIDAD (Si hay conexión) ---
if conn is not None:
    try:
        with conn.connect() as db:
            # Buscamos el equipo activo en la configuración
            res_conf = db.execute(text("SELECT valor FROM configuracion WHERE clave = 'equipo_activo'")).fetchone()
            equipo_nombre = res_conf[0] if res_conf else "Sistema"

            # Buscamos el color principal de ese equipo
            res_eq = db.execute(
                text("SELECT color_principal FROM equipos WHERE nombre = :nom"),
                {"nom": equipo_nombre}
            ).fetchone()
            
            if res_eq and res_eq[0]:
                color_maestro = res_eq[0]
                
            # Buscamos el fondo dinámico actual
            res_f = db.execute(text("SELECT valor FROM configuracion WHERE clave = 'fondo_url'")).fetchone()
            if res_f:
                fondo_url = res_f[0]
    except Exception as e:
        pass # Mantiene los valores por defecto si la consulta falla





# --- 2. GESTIÓN DE CONEXIÓN ---
@st.cache_resource
def get_db_connection():
    try:
        if "connections" not in st.secrets or "postgresql" not in st.secrets["connections"]:
            return None
        db_url = st.secrets["connections"]["postgresql"]["url"]
        return create_engine(db_url, pool_pre_ping=True)
    except:
        return None

conn = get_db_connection()

# --- 3. RECUPERACIÓN EXCLUSIVA DEL FONDO ---
# Fondo por defecto (Estadio base)
fondo_actual = "https://res.cloudinary.com/dlvczeqlp/image/upload/v1/assets/fondo_base.jpg"
fondo_url = "https://res.cloudinary.com/dlvczeqlp/image/upload/v1769049958/fondos_dinamicos/fondo_web_v2.png"




if conn:
    try:
        with conn.connect() as db:
            df_config = pd.read_sql(text("SELECT clave, valor FROM configuracion"), db)
            if not df_config.empty:
                row_f = df_config[df_config['clave'] == 'fondo_url']
                if not row_f.empty:
                    fondo_actual = row_f['valor'].values[0]
    except:
        pass




# --- INYECCIÓN DE CSS GLOBAL DINÁMICO ---
plantilla_estilo = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@200;400;700&display=swap');

    /* Fuente y Fondo */
    * { font-family: 'Oswald', sans-serif !important; color: #ffffff !important; }
    
    [data-testid="stAppViewContainer"] {
        background-image: url("URL_FONDO") !important;
        background-size: cover !important;
        background-attachment: fixed !important;
    }

    /* Acentos con el Color del Equipo Insignia */
    [data-testid="stDecoration"] { background: COLOR_MAESTRO !important; }
    
    div[data-baseweb="tab-highlight"] { background-color: COLOR_MAESTRO !important; }
    
    button[data-baseweb="tab"][aria-selected="true"] p { color: COLOR_MAESTRO !important; }

    div.stButton > button { 
        border: 1px solid COLOR_MAESTRO !important; 
        background-color: rgba(0,0,0,0.6) !important;
    }
    
    div.stButton > button:hover { 
        background-color: COLOR_MAESTRO !important; 
        color: #000000 !important; 
    }
</style>
"""

# El único punto de control: Reemplazamos los marcadores con las variables de la DB
css_final = plantilla_estilo.replace("URL_FONDO", fondo_url).replace("COLOR_MAESTRO", color_maestro)
st.markdown(css_final, unsafe_allow_html=True)






# 2. CONEXIÓN A NEON (POSTGRESQL) - La parte más importante
@st.cache_resource
def get_db_connection():
    try:
        # Verifica que exista el secreto antes de intentar conectar
        if "connections" not in st.secrets or "postgresql" not in st.secrets["connections"]:
            st.error("❌ Faltan los datos de conexión en .streamlit/secrets.toml")
            return None
            
        db_url = st.secrets["connections"]["postgresql"]["url"]
        
        # Creamos el motor
        engine = create_engine(db_url, pool_pre_ping=True)
        
        # Probamos una conexión rápida para ver si funciona
        with engine.connect() as test_conn:
            pass
            
        return engine
    except Exception as e:
        st.error(f"❌ Error crítico conectando a Neon: {e}")
        return None

# Inicializamos la variable global 'conn'
conn = get_db_connection()

# BLOQUE DE SEGURIDAD: Si la conexión falló, detenemos la app aquí
# Esto evita el error 'NoneType has no attribute connect' más adelante
if conn is None:
    st.warning("La aplicación se detuvo porque no hay conexión a la base de datos.")
    st.stop()





# 2. CONEXIÓN A NEON (POSTGRESQL) - La parte más importante
@st.cache_resource
def get_db_connection():
    try:
        # Verifica que exista el secreto antes de intentar conectar
        if "connections" not in st.secrets or "postgresql" not in st.secrets["connections"]:
            st.error("❌ Faltan los datos de conexión en .streamlit/secrets.toml")
            return None
            
        db_url = st.secrets["connections"]["postgresql"]["url"]
        
        # Creamos el motor
        engine = create_engine(db_url, pool_pre_ping=True)
        
        # Probamos una conexión rápida para ver si funciona
        with engine.connect() as test_conn:
            pass
            
        return engine
    except Exception as e:
        st.error(f"❌ Error crítico conectando a Neon: {e}")
        return None

# Inicializamos la variable global 'conn'
conn = get_db_connection()

# BLOQUE DE SEGURIDAD: Si la conexión falló, detenemos la app aquí
# Esto evita el error 'NoneType has no attribute connect' más adelante
if conn is None:
    st.warning("La aplicación se detuvo porque no hay conexión a la base de datos.")
    st.stop()



# 3. CONFIGURACIÓN CLOUDINARY
# (Toma las claves de secrets.toml para mayor seguridad)
cloudinary.config(
    cloud_name = st.secrets["cloudinary"]["cloud_name"],
    api_key = st.secrets["cloudinary"]["api_key"],
    api_secret = st.secrets["cloudinary"]["api_secret"],
    secure = True
)

# Constantes de Lógica
ADMIN_PIN = "2025"












##### ALGORITMO IA #####
##NORMALIZAR Y SUBIR ESCUDO##


def procesar_y_subir_escudo(archivo_imagen, nombre_equipo):
    try:
        # Subir a Cloudinary pidiendo eliminación de fondo (IA)
        # 'background_removal': 'cloudinary_ai' hace la magia
        resultado = cloudinary.uploader.upload(
            archivo_imagen,
            folder="escudos_torneo",
            public_id=f"escudo_{nombre_equipo.replace(' ', '_')}",
            background_removal="cloudinary_ai", 
            format="png" # Forzamos PNG para mantener la transparencia
        )
        # Retornamos la URL de la imagen ya procesada
        return resultado['secure_url']
    except Exception as e:
        st.error(f"Error procesando imagen con IA: {e}")
        # Si falla la IA, intentamos subirla normal sin procesar
        resultado_fallback = cloudinary.uploader.upload(archivo_imagen)
        return resultado_fallback['secure_url']
















###############  FUNCION LEER RESULTADO DE FOTO - EN PRUEBA
# Cargamos el motor una vez (Cache)
@st.cache_resource
def obtener_lector():
    # 'en' funciona mejor para números y nombres universales que 'es'
    return easyocr.Reader(['en'], gpu=False)

def similitud(a, b):
    """Calcula qué tan parecidas son dos palabras (0 a 1)."""
    return SequenceMatcher(None, a.upper(), b.upper()).ratio()

def limpiar_texto_ocr(texto):
    """Quita caracteres raros que el OCR confunde."""
    return re.sub(r'[^A-Z0-9\- ]', '', texto.upper())

def leer_marcador_ia(imagen_bytes, local_real, visitante_real):
    try:
        # 1. CORRECCIÓN DE LECTURA DE ARCHIVO
        # Usamos getvalue() directamente y rebobinamos por seguridad
        imagen_bytes.seek(0)
        file_bytes = np.asarray(bytearray(imagen_bytes.getvalue()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        
        if img is None: return None, "Error: Imagen corrupta."

        # 2. PRE-PROCESAMIENTO INTELIGENTE (CLAHE)
        # Convertimos a escala de grises
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Aplicamos CLAHE (Contrast Limited Adaptive Histogram Equalization)
        # Esto es MUCHO mejor que un threshold fijo para pantallas con brillo/reflejos
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        gray = clahe.apply(gray)
        
        # Opcional: Reducir ruido
        gray = cv2.fastNlMeansDenoising(gray, h=10)

        # 3. LECTURA ESPACIAL (EasyOCR)
        reader = obtener_lector()
        # detail=1 devuelve: [ [[x1,y1], [x2,y2]...], "texto", confianza ]
        # Leemos solo la mitad superior para optimizar (asumiendo que nadie toma foto al suelo)
        alto, ancho = gray.shape
        zona_interes = gray[0:int(alto*0.6), :] 
        
        resultados = reader.readtext(zona_interes, detail=1)

        # 4. LÓGICA DE ANCLAJE
        # Vamos a buscar dónde están los equipos y los números
        candidatos_local = []
        candidatos_visita = []
        candidatos_numeros = []

        # Palabras clave limpias de la BD
        keywords_local = local_real.upper().split()
        keywords_visita = visitante_real.upper().split()

        for (bbox, texto, prob) in resultados:
            texto_limpio = limpiar_texto_ocr(texto)
            if not texto_limpio: continue

            # Coordenadas del centro de la palabra (Eje X)
            # bbox = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
            centro_x = (bbox[0][0] + bbox[1][0]) / 2

            # A. ¿Es un número (posible gol)?
            if re.match(r'^\d+$', texto_limpio) and int(texto_limpio) < 25:
                candidatos_numeros.append({'val': int(texto_limpio), 'x': centro_x, 'conf': prob})
                continue
            
            # B. ¿Es el marcador completo (ej: "3-1")?
            match_completo = re.match(r'(\d+)\s*[-]\s*(\d+)', texto_limpio)
            if match_completo:
                return (int(match_completo.group(1)), int(match_completo.group(2))), "Marcador Directo Detectado"

            # C. ¿Es el equipo LOCAL?
            # Si alguna palabra coincide con el nombre del local
            if any(similitud(k, texto_limpio) > 0.8 for k in keywords_local):
                candidatos_local.append({'x': centro_x, 'conf': prob})
            
            # D. ¿Es el equipo VISITANTE?
            if any(similitud(k, texto_limpio) > 0.8 for k in keywords_visita):
                candidatos_visita.append({'x': centro_x, 'conf': prob})

        # 5. TRIANGULACIÓN DEL RESULTADO
        # Ordenamos los números encontrados de izquierda a derecha
        candidatos_numeros.sort(key=lambda k: k['x'])
        
        # Caso Ideal: Encontramos números sueltos
        if len(candidatos_numeros) >= 2:
            
            # Si encontramos la posición de los equipos, usamos esa info
            x_local = candidatos_local[0]['x'] if candidatos_local else 0
            x_visita = candidatos_visita[0]['x'] if candidatos_visita else ancho
            
            # Filtramos números que estén "entre" los equipos (geográficamente)
            # O si no hay equipos, tomamos los dos más centrales o claros
            
            goles_finales = []
            
            # Estrategia: Tomar los dos números con mayor confianza que estén cerca uno del otro
            # Pero respetando el orden izquierda (Local) -> derecha (Visita)
            
            # Si detectamos equipos, validamos que los números estén en medio
            numeros_validos = []
            for n in candidatos_numeros:
                # Un número válido suele estar a la derecha del nombre local (si existe)
                # y a la izquierda del nombre visitante (si existe)
                # Damos un margen de error de pixeles
                es_valido = True
                if candidatos_local and n['x'] < x_local: es_valido = False
                if candidatos_visita and n['x'] > x_visita: es_valido = False
                
                if es_valido:
                    numeros_validos.append(n)
            
            # Si el filtro fue muy agresivo y nos quedamos sin nada, volvemos a todos los números
            if len(numeros_validos) < 2:
                numeros_validos = candidatos_numeros

            # Tomamos los 2 primeros (Izquierda -> Derecha)
            if len(numeros_validos) >= 2:
                gl = numeros_validos[0]['val']
                gv = numeros_validos[1]['val']
                return (gl, gv), "Lectura por Posición"

        return None, "No se pudo triangular el marcador. Intenta tomar la foto más cerca."

    except Exception as e:
        return None, f"Error Visión: {str(e)}"
        
#####FIN IA






def generar_calendario():
    import random
    try:
        with conn.connect() as db:
            # 1. LIMPIEZA CRÍTICA: Borramos partidos previos
            # Sin esto, los partidos de intentos fallidos o anteriores se acumulan
            db.execute(text("DELETE FROM partidos"))
            
            # 2. Obtener solo los equipos reales aprobados
            res = db.execute(text("SELECT nombre FROM equipos WHERE estado = 'aprobado' AND nombre != 'Sistema'"))
            equipos = [row[0] for row in res.fetchall()]
            n_reales = len(equipos)

            if n_reales < 2:
                st.error("Se necesitan al menos 2 equipos para generar un calendario.")
                return

            # 3. DETERMINAR CUPOS PARA PLAY-OFFS
            if 25 <= n_reales <= 32: cupos = 16
            elif 16 <= n_reales <= 24: cupos = 8
            elif 8 <= n_reales < 16: cupos = 4
            else: cupos = 2

            # Guardamos los cupos en la tabla 'config'
            db.execute(text("""
                INSERT INTO config (clave, valor) 
                VALUES ('cupos_clasificados', :v) 
                ON CONFLICT (clave) DO UPDATE SET valor = :v
            """), {"v": str(cupos)})

            # 4. PREPARACIÓN ROUND ROBIN
            random.shuffle(equipos)
            equipos_sorteo = equipos.copy()
            
            # Si es impar, añadimos un 'Descanso' (None) para que el algoritmo sea par
            if n_reales % 2 != 0:
                equipos_sorteo.append(None)

            n = len(equipos_sorteo)
            indices = list(range(n))

            # 5. GENERACIÓN DE 3 JORNADAS REALES
            for jor in range(1, 4):
                # Emparejamiento por extremos (1° vs último, 2° vs penúltimo...)
                for i in range(n // 2):
                    idx_l = indices[i]
                    idx_v = indices[n - 1 - i]
                    
                    loc = equipos_sorteo[idx_l]
                    vis = equipos_sorteo[idx_v]

                    # Solo insertamos si ninguno es 'None' (el que descanse no tiene partido)
                    if loc and vis:
                        db.execute(text("""
                            INSERT INTO partidos (local, visitante, jornada, estado) 
                            VALUES (:l, :v, :j, 'Programado')
                        """), {"l": loc, "v": vis, "j": jor})
                
                # ROTACIÓN BERGER (Mantiene el índice 0 fijo y rota el resto)
                # Esto garantiza que NO se repitan partidos en las primeras jornadas
                indices = [indices[0]] + [indices[-1]] + indices[1:-1]

            # 6. ACTUALIZAR FASE Y CONFIRMAR
            db.execute(text("UPDATE config SET valor = 'clasificacion' WHERE clave = 'fase_actual'"))
            db.commit()
            
    except Exception as e:
        st.error(f"Error crítico en el calendario: {e}")
        
###FIN GENERAR CALENDARIO




#####EN DESARROLLO/PRUEBA
# --- FUNCIÓN GRÁFICA: TARJETA DE PARTIDO (MODO LABORATORIO) ---
def renderizar_tarjeta_partido(local, visita, escudo_l, escudo_v, marcador_texto, color_tema, url_fondo):
    if not color_tema: color_tema = "#FFD700"
    
    estilo = f"""
    <style>
        .card-container {{
            position: relative;
            width: 100%;
            
            /* TANTEAR: Ancho máximo en PC. */
            max-width: 840px; 
            
            /* TANTEAR: Altura de la barra en PC. Si quieres que sea mas "gorda", sube a 120px */
            height: 108px;    
            
            /* TANTEAR: El '15px' es el espacio vacio entre una tarjeta y otra */
            margin: 0 auto 15px auto; 
            
            background-image: url('{url_fondo}');
            background-size: 100% 100%;
            background-repeat: no-repeat;
            
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-family: 'Oswald', sans-serif;
            color: white;
            
            /* EFECTO DE SOMBRA / COLOR */
            box-shadow: 
                0 4px 6px -2px rgba(0,0,0,0.5), 
                /* TANTEAR: El '10px' es qué tan difuminado está el color abajo. El '{color_tema}60' es la transparencia (60 es suave, 99 es fuerte) */
                0 2px 10px -3px {color_tema}60; 
            
            /* TANTEAR: El '1px' es el grosor de la línea de color inferior. */
            border-bottom: 1px solid {color_tema}30;

            transition: transform 0.2s, box-shadow 0.2s;
        }}
        
        .card-container:hover {{
            transform: translateY(-2px); 
            box-shadow: 
                0 6px 8px -2px rgba(0,0,0,0.6),
                0 4px 15px -3px {color_tema}80; 
        }}

        /* --- ZONAS (OJO: Las sumas de width deben dar cerca de 100%) --- */
        
        .zona-equipo {{
            /* TANTEAR: Espacio horizontal para Nombre + Escudo. Si subes esto, baja la .zona-centro */
            width: 60%; 
            height: 100%;
            display: flex;
            align-items: center;
            
            /* TANTEAR: Espacio entre el Escudo y el Nombre */
            gap: 3px; 
            overflow: hidden; 
        }}
        
        .zona-centro {{
            /* TANTEAR: Espacio para el marcador. Si los números no caben, sube a 10% o 12% */
            width: 12%; 
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            
            /* TANTEAR: Tamaño del número del marcador en PC */
            font-size: 30px; 
            font-weight: bold;
            text-shadow: 0 2px 4px black;
            color: {color_tema}; 
            padding-top: 6px;
            z-index: 2;
        }}
        
        /* --- TEXTOS --- */
        
        .txt-local {{ 
            text-align: right; width: 100%; 
            
            /* TANTEAR: Tamaño del nombre del equipo en PC. */
            font-size: 17px; 
            font-weight: 500;
            text-transform: uppercase; 
            
            /* TANTEAR: Distancia entre el final del nombre y el marcador central */
            padding-right: 5px; 
            line-height: 1.1; 
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis; letter-spacing: 0.5px;
        }}
        .txt-visit {{ 
            text-align: left; width: 100%; 
            
            /* TANTEAR: Igual que arriba, tamaño del nombre visitante */
            font-size: 17px; 
            font-weight: 500;
            text-transform: uppercase; 
            
            /* TANTEAR: Distancia entre el marcador central y el inicio del nombre */
            padding-left: 2px; 
            line-height: 1.1; 
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis; letter-spacing: 0.5px;
        }}
        
        .logo-img {{
            /* TANTEAR: Tamaño del escudo en PC. Si cambias 46px, cambia min-width también */
            width: 46px; height: 50px; min-width: 50px; 
            object-fit: contain; filter: drop-shadow(0 3px 3px black);
        }}
        
        /* TANTEAR: Relleno izquierdo (distancia del borde izquierdo al primer escudo) */
        .pad-l {{ padding-left: 10px; }}
        
        /* TANTEAR: Relleno derecho (distancia del borde derecho al segundo escudo) */
        .pad-r {{ padding-right: 10px; justify-content: flex-end; }}


        /* --- ¡AQUI EMPIEZA LO IMPORTANTE PARA EL MOVIL! --- */
        @media (max-width: 480px) {{
            
            /* TANTEAR: Altura de la tarjeta en celular. Prueba 90px si se ve muy apretado */
            .card-container {{ height: 84px; }} 
            
            /* TANTEAR: Tamaño de letra en celular. Si los nombres se cortan mucho, baja a 10px */
            .txt-local, .txt-visit {{ font-size: 13px; }} 
            
            /* TANTEAR: Tamaño del escudo en celular. Prueba 30px o 38px */
            .logo-img {{ width: 34px; height: 38px; min-width: 34px; }} 
            
            /* TANTEAR: Tamaño del marcador en celular y ancho de la zona central */
            .zona-centro {{ font-size: 20px; width: 20%; }} 
            
            /* TANTEAR: Ancho para equipos en celular. (43% + 43% + 10% = 96%) */
            .zona-equipo {{ width: 50%; }}
            
            /* TANTEAR: Márgenes laterales en celular. Si están muy pegados al borde, sube a 20px */
            .pad-l {{ padding-left: 15px; }}
            .pad-r {{ padding-right: 15px; }}
        }}
    </style>
    """

    html = f"""
    <div class="card-container">
        <div class="zona-equipo pad-l">
            <img src="{escudo_l}" class="logo-img">
            <div class="txt-local">{local}</div>
        </div>
        <div class="zona-centro">{marcador_texto}</div>
        <div class="zona-equipo pad-r">
            <div class="txt-visit">{visita}</div>
            <img src="{escudo_v}" class="logo-img">
        </div>
    </div>
    """
    return estilo + html
####FIN DESARROLLO/PRUEBA






############FUNCIÓN EN PRUEBA DATOS FUTUROS
def actualizar_historial_post_partido(equipo_local, equipo_visitante, goles_l, goles_v, conn):
    """
    Se ejecuta AUTOMÁTICAMENTE después de guardar un resultado.
    Actualiza la racha y el ganador.
    """
    # 1. Determinar Ganador y Letra de Racha
    if goles_l > goles_v:
        ganador = equipo_local
        res_l, res_v = 'W', 'L' # W=Win, L=Loss
    elif goles_v > goles_l:
        ganador = equipo_visitante
        res_l, res_v = 'L', 'W'
    else:
        ganador = 'Empate'
        res_l, res_v = 'D', 'D' # D=Draw

    with conn.connect() as db:
        # 2. Guardar el ganador explícito en el partido (Facilita consultas futuras del Oráculo)
        # Asumimos que ya tienes el ID del partido o usas los nombres para filtrar
        db.execute(text("""
            UPDATE partidos 
            SET ganador = :g 
            WHERE local = :l AND visitante = :v AND estado = 'Finalizado'
        """), {"g": ganador, "l": equipo_local, "v": equipo_visitante})

        # 3. Actualizar la Racha de los Equipos (Concatenación simple)
        # Esto agrega la nueva letra al final de la cadena existente
        # Para el Local
        db.execute(text("""
            UPDATE equipos 
            SET racha_actual = CONCAT(COALESCE(racha_actual, ''), :r, ',') 
            WHERE nombre = :n
        """), {"r": res_l, "n": equipo_local})

        # Para el Visitante
        db.execute(text("""
            UPDATE equipos 
            SET racha_actual = CONCAT(COALESCE(racha_actual, ''), :r, ',') 
            WHERE nombre = :n
        """), {"r": res_v, "n": equipo_visitante})
        
        db.commit()

#######FUNCIÓN EN PRUEBA








# --- 3. NAVEGACIÓN (Inicialización de Estado) ---
if "reg_estado" not in st.session_state: st.session_state.reg_estado = "formulario"
if "pin_usuario" not in st.session_state: st.session_state.pin_usuario = ""

####################PORTADA EN PRUEBA

URL_PORTADA = "https://res.cloudinary.com/dlvczeqlp/image/upload/v1769050565/a906a330-8b8c-4b52-b131-8c75322bfc10_hwxmqb.png" 



# --- ESTILO CSS INYECTADO ---
st.markdown(f"""
    <style>
    /* Eliminamos el espacio blanco superior que Streamlit pone por defecto */
    .stAppHeader {{
        display: none;
    }}
    .block-container {{
        padding-top: 0rem !important;
    }}

    .main-banner {{
        width: 100%;
        height: 200px;
        background-image: linear-gradient(rgba(0,0,0,0.3), rgba(0,0,0,0.3)), url("{URL_PORTADA}");
        background-size: cover;
        background-position: center;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 25px;
        border-bottom: 5px solid #FFD700;
    }}

    .banner-title {{
        color: white;
        font-family: 'Impact', sans-serif;
        font-size: 3.5rem;
        text-shadow: 3px 3px 15px rgba(0,0,0,0.9);
        letter-spacing: 3px;
    }}
    </style>

    <div class="main-banner">
        <h1 class="banner-title"></h1>
    </div>
""", unsafe_allow_html=True)





######FIN PRUEBA



# --- NAVEGACIÓN (Botones originales) ---
c_nav1, c_nav2 = st.columns(2)
with c_nav1:
    if st.button("🔙 Inicio"):
        st.session_state.reg_estado = "formulario"
        st.session_state.pin_usuario = ""
        st.rerun()
#with c_nav2:
 #   if st.button("🔄 Refrescar"): 
  #      st.rerun()

# --- CAMPO DE PIN Y BOTÓN DE ENTRAR ---
pin_input = st.text_input("🔑 PIN de Acceso", value=st.session_state.pin_usuario, type="password")
btn_entrar = st.button("🔓 Entrar", use_container_width=True)





# --- OBTENER FASE ACTUAL (Versión Neon) ---
try:
    with conn.connect() as connection:
        # Usamos text() para la consulta SQL segura
        # Nota: En Neon la columna se llama 'clave', no 'llave'
        query_fase = text("SELECT valor FROM config WHERE clave = 'fase_actual'")
        result = connection.execute(query_fase)
        
        # .scalar() obtiene el valor limpio directamente
        fase_actual = result.scalar()
        
        if not fase_actual:
            fase_actual = "inscripcion" # Valor por defecto si falla
except Exception as e:
    st.error(f"Error al leer la fase: {e}")
    fase_actual = "inscripcion"

    
# --- 1. ESTADO INICIAL ---
rol = "espectador"
equipo_usuario = None

# --- 2. BOTÓN ENTRAR (Solo guarda y recarga) ---
if btn_entrar:
    st.session_state.pin_usuario = pin_input
    st.rerun()

# --- 3. VALIDACIÓN CENTRALIZADA ---
# Si hay un PIN en memoria, validamos quién es (Admin o DT)
if st.session_state.pin_usuario:
    
    # A. Es Admin?
    if st.session_state.pin_usuario == ADMIN_PIN:
        rol = "admin"

    # B. Es DT? (Consultamos Neon)
    else:
        try:
            with conn.connect() as db:
                query = text("SELECT nombre FROM equipos WHERE pin = :p AND estado = 'aprobado'")
                result = db.execute(query, {"p": st.session_state.pin_usuario}).fetchone()
                
                if result:
                    rol = "dt"
                    equipo_usuario = result[0]
                else:
                    # PIN incorrecto: Avisamos y borramos
                    st.toast("⚠️ PIN incorrecto o no aprobado", icon="❌")
                    st.session_state.pin_usuario = ""
                    time.sleep(1)
                    st.rerun()
        except Exception as e:
            st.error(f"Error de conexión: {e}")

# (Opcional para debug: Si ves esto, es que el rol ya cambió)
# st.write(f"DEBUG: Rol asignado -> {rol}")





# --- DEFINICIÓN DINÁMICA DE PESTAÑAS ---
if fase_actual == "inscripcion":
    # Fase inicial: No hay partidos, hay inscripciones
    titulos = ["📊 Posiciones", "📝 Inscripción", "⚙️ Gestión"]
else:
    # Fase de juego: Se cambia Inscripción por Calendario/Partidos
    titulos = ["📊 Posiciones", "📅 Partidos", "⚙️ Gestión"]

tabs = st.tabs(titulos)



# --- PESTAÑA 0: POSICIONES (Siempre igual) ---
with tabs[0]:
    st.subheader("🏆 Tabla de Clasificación")
    # Tu código para mostrar la tabla de posiciones aquí...

# --- PESTAÑA 1: INSCRIPCIÓN O PARTIDOS (Dinámica) ---
with tabs[1]:
    if fase_actual == "inscripcion":
        st.subheader("📝 Registro de Equipos")
        # Aquí va tu código del Formulario de Inscripción para usuarios
        # y la lista de equipos ya inscritos.
    else:
        st.subheader("📅 Calendario Oficial")
        # Aquí va tu código para mostrar las Jornadas y Resultados
        # que ven los espectadores y Dts.

# --- PESTAÑA 2: GESTIÓN (ADMIN O DT) ---
with tabs[2]:
    if rol == "admin":
        # --- BLOQUE DE GESTIÓN ADMIN (El que ya pulimos) ---
        st.header("👑")
        # Aquí pegas todo el código de: Aprobaciones, Radio de Tareas, 
        # Directorio de Equipos y Botones de Iniciar/Reiniciar.
        
    elif rol == "dt":
        # --- BLOQUE DE GESTIÓN DT ---
        st.header(f"⚽ Gestión: {equipo_usuario}")
        if fase_actual == "inscripcion":
            st.info("👋 ¡Hola DT! Tu equipo ya está aprobado. El torneo aún no comienza, espera a que se genere el calendario.")
        else:
            st.success("✅ Torneo en curso. Aquí podrás reportar tus marcadores.")
            # Próximo paso: Formulario de reporte para el DT
            
    else:
        # Lo que ve alguien que no ha puesto un PIN válido
        st.markdown("### 🔒 Acceso Restringido")
        st.info("Esta sección es solo para **Administradores** o **Directores Técnicos** registrados.")
        st.write("Por favor, ingresa tu PIN en la parte superior para acceder a las funciones de gestión.")





# --- TAB: CLASIFICACIÓN (Versión Alineación Elite) ---
with tabs[0]:
    try:
        # A. VALIDACIÓN DE SEGURIDAD
        if 'color_maestro' not in locals() and 'color_maestro' not in globals():
            color_maestro = "#FFD700" 

        # 1. Obtener datos de Neon
        df_eq = pd.read_sql_query("SELECT nombre, escudo FROM equipos WHERE estado = 'aprobado'", conn)
        
        if df_eq.empty:
            st.info("No hay equipos todavía.")
        else:
            mapa_escudos = dict(zip(df_eq['nombre'], df_eq['escudo']))
            stats = {e: {'PJ':0, 'PTS':0, 'GF':0, 'GC':0} for e in df_eq['nombre']}
            df_p = pd.read_sql_query("SELECT * FROM partidos WHERE goles_l IS NOT NULL", conn)
            
            for _, f in df_p.iterrows():
                if f['local'] in stats and f['visitante'] in stats:
                    l, v = f['local'], f['visitante']
                    gl, gv = int(f['goles_l']), int(f['goles_v'])
                    stats[l]['PJ'] += 1; stats[v]['PJ'] += 1
                    stats[l]['GF'] += gl; stats[l]['GC'] += gv
                    stats[v]['GF'] += gv; stats[v]['GC'] += gl
                    
                    if gl > gv: 
                        stats[l]['PTS'] += 3
                    elif gv > gl: 
                        stats[v]['PTS'] += 3
                    else: 
                        stats[l]['PTS'] += 1; stats[v]['PTS'] += 1
            
            df_f = pd.DataFrame.from_dict(stats, orient='index').reset_index()
            df_f.columns = ['EQ', 'PJ', 'PTS', 'GF', 'GC']
            df_f['DG'] = df_f['GF'] - df_f['GC']
            df_f = df_f.sort_values(by=['PTS', 'DG', 'GF'], ascending=False).reset_index(drop=True)
            df_f.insert(0, 'POS', range(1, len(df_f) + 1))

            # 2. DISEÑO DE TABLA (Espaciado Estandarizado)
            plantilla_tabla = """
            <style>
                .tabla-pro { 
                    width: 100%; border-collapse: collapse; table-layout: fixed; 
                    background-color: rgba(0,0,0,0.5); font-family: 'Oswald', sans-serif; 
                    border: 1px solid COLOR_MAESTRO !important;
                }
                .tabla-pro th { 
                    background-color: #111; color: #ffffff !important; 
                    padding: 4px 1px; font-size: 11px; 
                    border-bottom: 2px solid COLOR_MAESTRO !important; 
                    text-align: center; height: 32px !important; 
                }
                .tabla-pro td { 
                    padding: 0px 1px !important; text-align: center; 
                    vertical-align: middle !important; border-bottom: 1px solid #222; 
                    font-size: 13px; color: white; height: 30px !important; 
                }
                /* Contenedor del escudo para estandarizar espacio */
                .escudo-wrapper {
                    display: inline-block;
                    width: 25px; /* Ancho fijo para el área del escudo */
                    text-align: center;
                    margin-right: 12px; /* Espacio estándar hacia el texto */
                    vertical-align: middle;
                }
            </style>
            """
            
            estilo_tabla_final = plantilla_tabla.replace("COLOR_MAESTRO", color_maestro)

            tabla_html = '<table class="tabla-pro"><thead><tr>'
            tabla_html += '<th style="width:8%">POS</th>'
            tabla_html += '<th style="width:47%; text-align:left; padding-left:10px">EQUIPO</th>'
            tabla_html += '<th style="width:10%">PTS</th>'
            tabla_html += '<th style="width:9%">PJ</th>'
            tabla_html += '<th style="width:9%">GF</th>'
            tabla_html += '<th style="width:9%">GC</th>'
            tabla_html += '<th style="width:8%">DG</th>'
            tabla_html += '</tr></thead><tbody>'

            for _, r in df_f.iterrows():
                url = mapa_escudos.get(r['EQ'])
                
                # Definimos el contenido del escudo
                if url:
                    img_html = f'<img src="{url}" style="height:22px; width:22px; object-fit:contain; vertical-align:middle;">'
                else:
                    img_html = '<span style="font-size:16px;"> </span>'
                
                # Envolvemos el escudo en el contenedor de ancho fijo
                escudo_final = f'<div class="escudo-wrapper">{img_html}</div>'
                
                tabla_html += "<tr>"
                tabla_html += f"<td>{r['POS']}</td>"
                # Aplicamos el escudo y el nombre con el nuevo wrapper
                tabla_html += f"<td style='text-align:left; padding-left:10px; font-weight:bold; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>"
                tabla_html += f"{escudo_final}{r['EQ']}</td>"
                
                tabla_html += f"<td style='color:{color_maestro}; font-weight:bold;'>{r['PTS']}</td>"
                tabla_html += f"<td>{r['PJ']}</td>"
                tabla_html += f"<td>{r['GF']}</td>"
                tabla_html += f"<td>{r['GC']}</td>"
                tabla_html += f"<td style='font-size:11px; color:#888;'>{r['DG']}</td>"
                tabla_html += "</tr>"

            tabla_html += "</tbody></table>"

            st.markdown(estilo_tabla_final + tabla_html, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Error al cargar la clasificación: {e}")
        

            

# --- TAB: REGISTRO (Versión Restaurada con Guardado Real en Neon) ---
if fase_actual == "inscripcion":
    with tabs[1]:
        # 1. Inicialización de estados
        if "datos_temp" not in st.session_state:
            st.session_state.datos_temp = {"n": "", "wa": "", "pin": "", "pref": "+57", "escudo_obj": None}
        if "reg_estado" not in st.session_state:
            st.session_state.reg_estado = "formulario"

        # --- ESTADO: ÉXITO ---
        if st.session_state.reg_estado == "exito":
            st.success("✅ ¡Inscripción recibida! Se estara revisando tu solicitud.")
            if st.button("Nuevo Registro"): 
                st.session_state.datos_temp = {"n": "", "wa": "", "pin": "", "pref": "+57", "escudo_obj": None}
                st.session_state.reg_estado = "formulario"
                st.rerun()
        
        # --- ESTADO: CONFIRMAR ---
        elif st.session_state.reg_estado == "confirmar":
            d = st.session_state.datos_temp
            st.warning("⚠️ **Confirma tus datos antes de enviar:**")
            
            col_info, col_img = st.columns([2, 1])
            with col_info:
                st.write(f"**Equipo:** {d['n']}")
                st.write(f"**WhatsApp:** {d['pref']} {d['wa']}")
                st.write(f"**PIN de Acceso:** {d['pin']}") # Visible como pediste
            
            with col_img:
                if d['escudo_obj']: st.image(d['escudo_obj'], width=100)
                else: st.write("🛡️ Sin escudo")

            c1, c2 = st.columns(2)
            
            # --- BOTÓN DE CONFIRMACIÓN (Aquí es donde se guarda en la DB) ---
            if c1.button("✅ Confirmar y Enviar"):
                url_escudo = None
                
                # 1. Subida a Cloudinary
                if d['escudo_obj']:
                    with st.spinner("Subiendo escudo..."):
                        try:
                            res = cloudinary.uploader.upload(d['escudo_obj'], folder="escudos_pendientes")
                            url_escudo = res['secure_url']
                        except Exception as e: 
                            st.error(f"Error en Cloudinary: {e}")
                
                # 2. Inserción en Neon (Postgres)
                try:
                    with conn.connect() as db:
                        query_insert = text("""
                            INSERT INTO equipos (nombre, celular, prefijo, pin, escudo, estado) 
                            VALUES (:n, :c, :p, :pi, :e, 'pendiente')
                        """)
                        db.execute(query_insert, {
                            "n": d['n'], 
                            "c": d['wa'], 
                            "p": d['pref'], 
                            "pi": d['pin'], 
                            "e": url_escudo
                        })
                        db.commit()
                    
                    st.session_state.reg_estado = "exito"
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar en la base de datos: {e}")

            if c2.button("✏️ Editar Datos"): 
                st.session_state.reg_estado = "formulario"
                st.rerun()
        
        # --- ESTADO: FORMULARIO ---
        else:
            d = st.session_state.datos_temp
            
            with st.form("reg_preventivo"):
                nom = st.text_input("Nombre Equipo", value=d['n']).strip()
                
                paises = {"Colombia": "+57", "EEUU": "+1", "México": "+52", "Ecuador": "+593", "Panamá": "+507", "Perú": "+51", "Argentina": "+54", "Chile": "+56", "Venezuela": "+58"}
                opciones = [f"{p} ({pref})" for p, pref in paises.items()]
                
                try:
                    idx_pref = [d['pref'] in opt for opt in opciones].index(True)
                except:
                    idx_pref = 0

                pais_sel = st.selectbox("País", opciones, index=idx_pref)
                tel = st.text_input("WhatsApp", value=d['wa']).strip()
                # PIN Visible
                pin_r = st.text_input("PIN de Acceso (4 dígitos)", max_chars=4, value=d['pin']).strip()
                
                archivo_escudo = st.file_uploader("🛡️ Escudo (Opcional)", type=['png', 'jpg', 'jpeg'])
                
                if st.form_submit_button("Siguiente", use_container_width=True):
                    if not nom or not tel or len(pin_r) < 4: 
                        st.error("Completa todos los campos correctamente.")
                    else:
                        # --- VALIDACIÓN DE DUPLICADOS CONTRA EQUIPOS APROBADOS ---
                        try:
                            with conn.connect() as db:
                                query = text("SELECT nombre, pin FROM equipos WHERE (nombre = :n OR pin = :p) AND estado = 'aprobado'")
                                check = db.execute(query, {"n": nom, "p": pin_r}).fetchone()
                                
                                if check:
                                    if check[0].lower() == nom.lower():
                                        st.error(f"❌ El nombre '{nom}' ya está ocupado.")
                                    else:
                                        st.error("❌ Este PIN ya está en uso. Elige otro.")
                                else:
                                    # Guardamos temporalmente y vamos a Confirmar
                                    st.session_state.datos_temp = {
                                        "n": nom, "wa": tel, "pin": pin_r, 
                                        "pref": pais_sel.split('(')[-1].replace(')', ''),
                                        "escudo_obj": archivo_escudo if archivo_escudo else d['escudo_obj']
                                    }
                                    st.session_state.reg_estado = "confirmar"
                                    st.rerun()
                        except Exception as e:
                            st.error(f"Error de conexión: {e}")






# --- 5. CALENDARIO Y GESTIÓN DE PARTIDOS (CORREGIDO) ---
elif fase_actual == "clasificacion":
    with tabs[1]:
      # st.subheader("📅 Calendario Oficial")
        
        # URL de Fondo (Asegúrate de tener la URL correcta aquí si usas imagen)
        URL_PLANTILLA_FONDO = "https://res.cloudinary.com/..." 
        placeholder_escudo = "https://cdn-icons-png.flaticon.com/512/5329/5329945.png"

        try:
            # Leemos los partidos
            df_p = pd.read_sql_query("SELECT * FROM partidos ORDER BY jornada ASC", conn)
            # Leemos escudos
            df_escudos = pd.read_sql_query("SELECT nombre, escudo FROM equipos", conn)
            escudos_dict = dict(zip(df_escudos['nombre'], df_escudos['escudo']))
        except Exception as e:
            st.error(f"Error al cargar partidos: {e}")
            df_p = pd.DataFrame()

        if not df_p.empty:
            j_tabs = st.tabs(["Jornada 1", "Jornada 2", "Jornada 3"])
            
            for i, jt in enumerate(j_tabs):
                with jt:
                    df_j = df_p[df_p['jornada'] == (i + 1)]
                    
                    if df_j.empty:
                        st.info("No hay partidos programados para esta fecha.")
                    
                    for _, p in df_j.iterrows():
                        # 1. Preparar Escudos
                        esc_l = escudos_dict.get(p['local']) or placeholder_escudo
                        esc_v = escudos_dict.get(p['visitante']) or placeholder_escudo
                        
                        # 2. Preparar Marcador (CORRECCIÓN ANTI-ERROR)
                        # Usamos pd.notna() para validar que no sea NaN (Not a Number)
                        try:
                            if pd.notna(p['goles_l']) and pd.notna(p['goles_v']):
                                txt_marcador = f"{int(p['goles_l'])} - {int(p['goles_v'])}"
                            else:
                                txt_marcador = "VS"
                        except ValueError:
                            txt_marcador = "VS"
                        
                        # 3. Construir la Tarjeta HTML
                        # Asegúrate de tener la función 'renderizar_tarjeta_partido' definida arriba en tu código
                        html_tarjeta = renderizar_tarjeta_partido(
                            local=p['local'],
                            visita=p['visitante'],
                            escudo_l=esc_l,
                            escudo_v=esc_v,
                            marcador_texto=txt_marcador,
                            color_tema=color_maestro,
                            url_fondo=URL_PLANTILLA_FONDO
                        )
                        
                        st.markdown(html_tarjeta, unsafe_allow_html=True)
                        
                        # 4. Evidencias (Opcional)
                        if p.get('url_foto_l') or p.get('url_foto_v'):
                            with st.expander(f"📷 Ver evidencia {p['local']} vs {p['visitante']}"):
                                c1, c2 = st.columns(2)
                                if p['url_foto_l']: c1.image(p['url_foto_l'])
                                if p['url_foto_v']: c2.image(p['url_foto_v'])
                            st.write("") # Espacio
        else:
            st.info("El calendario se mostrará cuando inicie el torneo.")



            
# --- TAB: MIS PARTIDOS (DT - FLUJO MEJORADO CON ORIGEN DE DATOS) ---
if rol == "dt":
    with tabs[2]:
        st.subheader(f"🏟️ Mis Partidos: {equipo_usuario}")
        
        try:
            # 1. CONSULTA
            query_mis = text("SELECT * FROM partidos WHERE (local=:eq OR visitante=:eq) ORDER BY jornada ASC")
            mis = pd.read_sql_query(query_mis, conn, params={"eq": equipo_usuario})
            
            if mis.empty:
                st.info("Aún no tienes partidos asignados.")
            
            ultima_jornada_vista = -1

            for _, p in mis.iterrows():
                
                # --- A. SEPARADOR JORNADA ---
                if p['jornada'] != ultima_jornada_vista:
                    st.divider()
                    c_spacer, c_title, c_spacer2 = st.columns([1, 2, 1])
                    with c_title:
                        st.header(f"JORNADA {p['jornada']}")
                    ultima_jornada_vista = p['jornada']

                es_local = (p['local'] == equipo_usuario)
                rival = p['visitante'] if es_local else p['local']
                
                with st.container(border=True):
                    # 1. INFO RIVAL
                    c_riv, c_wa = st.columns([3, 1])
                    with c_riv:
                        st.caption("Tu Rival")
                        st.subheader(f"{rival}")
                    with c_wa:
                        link_wa = None
                        try:
                            with conn.connect() as db:
                                r = db.execute(text("SELECT prefijo, celular FROM equipos WHERE nombre=:n"), {"n": rival}).fetchone()
                                if r and r[0] and r[1]:
                                    num = f"{str(r[0]).replace('+', '')}{r[1]}"
                                    link_wa = f"https://wa.me/{num}"
                        except: pass
                        if link_wa:
                            st.link_button("💬 Chat", link_wa, type="primary")
                        else:
                            st.caption("🚫")

                    st.markdown("<div style='height:1px; background-color:#333; margin: 15px 0;'></div>", unsafe_allow_html=True)

                    # 2. ZONA DE ACCIÓN
                    # Extraemos el método de registro (por defecto Algoritmo si es nulo)
                    metodo = p['metodo_registro'] if 'metodo_registro' in p and pd.notna(p['metodo_registro']) else "Algoritmo"

                    if p['estado'] == 'Finalizado':
                        st.success(f"✅ Finalizado ({metodo}): {int(p['goles_l'])} - {int(p['goles_v'])}")
                        
                        # BOTÓN DE CORRECCIÓN: No resetea goles, solo cambia estado
                        if st.button("❌ ¿Marcador Incorrecto?", key=f"err_{p['id']}", use_container_width=True):
                            try:
                                with conn.connect() as db:
                                    # Mantenemos los goles, solo cambiamos estado y conflicto
                                    q = text("UPDATE partidos SET estado='Revision', conflicto=1 WHERE id=:id")
                                    db.execute(q, {"id": p['id']})
                                    db.commit()
                                st.warning("Partido marcado como incorrecto. Se mantiene el marcador para revisión del Admin.")
                                time.sleep(1.5)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al reportar: {e}")

                    elif p['estado'] == 'Revision':
                        st.warning(f"⏳ En Revisión: {int(p['goles_l']) if pd.notna(p['goles_l']) else '?'} - {int(p['goles_v']) if pd.notna(p['goles_v']) else '?'}")
                        st.caption("El Administrador está verificando este resultado.")

                    else:
                        st.caption("📸 CARGAR RESULTADO")
                        tipo_carga = st.radio("Método:", ["Ocultar", "Usar Cámara", "Subir Foto"], horizontal=True, label_visibility="collapsed", key=f"radio_{p['id']}")
                        
                        foto = None
                        if tipo_carga == "Usar Cámara":
                            foto = st.camera_input("Toma la foto", key=f"cam_{p['id']}")
                        elif tipo_carga == "Subir Foto":
                            foto = st.file_uploader("Selecciona imagen", type=['jpg','png','jpeg'], key=f"upl_{p['id']}")

                        if foto:
                            st.image(foto, width=200)
                            
                            if st.button("📤 ENVIAR AHORA", key=f"send_{p['id']}", type="primary", use_container_width=True):
                                with st.spinner("🔍 Analizando imagen..."):
                                    
                                    res_ia, msg_ia = leer_marcador_ia(foto, p['local'], p['visitante'])

                                    if res_ia:
                                        gl_ia, gv_ia = res_ia
                                        st.info(f"🔢 Resultado Detectado: {gl_ia} - {gv_ia}")

                                        try:
                                            foto.seek(0)
                                            res_c = cloudinary.uploader.upload(foto, folder="gol_gana_evidencias")
                                            url = res_c['secure_url']
                                            cf = "url_foto_l" if es_local else "url_foto_v"

                                            with conn.connect() as db:
                                                gl_ex = int(p['goles_l']) if pd.notna(p['goles_l']) else None
                                                gv_ex = int(p['goles_v']) if pd.notna(p['goles_v']) else None

                                                if gl_ex is not None:
                                                    # Verificamos coincidencia con reporte previo
                                                    if gl_ex != gl_ia or gv_ex != gv_ia:
                                                        # Conflicto: Goles nulos para forzar revisión manual
                                                        q = text(f"UPDATE partidos SET goles_l=NULL, goles_v=NULL, conflicto=1, {cf}=:u, ia_goles_l=:gl, ia_goles_v=:gv, estado='Revision', metodo_registro='Algoritmo' WHERE id=:id")
                                                        db.execute(q, {"u": url, "gl": gl_ia, "gv": gv_ia, "id": p['id']})
                                                        st.warning("⚠️ Los resultados no coinciden. Admin notificado.")
                                                    else:
                                                        # Coincidencia: Finalizado
                                                        q = text(f"UPDATE partidos SET {cf}=:u, conflicto=0, estado='Finalizado', metodo_registro='Algoritmo' WHERE id=:id")
                                                        db.execute(q, {"u": url, "id": p['id']})
                                                        st.balloons()
                                                        st.success("✅ Verificado y Finalizado.")
                                                else:
                                                    # Primer reporte: Finalizado directo (Algoritmo)
                                                    q = text(f"UPDATE partidos SET goles_l=:gl, goles_v=:gv, {cf}=:u, ia_goles_l=:gl, ia_goles_v=:gv, estado='Finalizado', conflicto=0, metodo_registro='Algoritmo' WHERE id=:id")
                                                    db.execute(q, {"gl": gl_ia, "gv": gv_ia, "u": url, "id": p['id']})
                                                    st.balloons()
                                                    st.success("✅ Resultado registrado con éxito.")
                                                
                                                db.commit()
                                            
                                            time.sleep(2)
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Error BD: {e}")
                                    else:
                                        st.error(f"❌ {msg_ia}")

        except Exception as e:
            st.error(f"Error carga: {e}")


            

  
  
# --- TAB: GESTIÓN ADMIN (Completo con Gestor de Resultados) ---
if rol == "admin":
    with tabs[2]:
        st.header("⚙️ Panel de Control Admin")
        
        # --- 1. SECCIÓN DE APROBACIONES (Sin cambios) ---
        st.subheader("📩 Equipos por Aprobar")
        try:
            pend = pd.read_sql_query(text("SELECT * FROM equipos WHERE estado='pendiente'"), conn)
            res_count = pd.read_sql_query(text("SELECT count(*) FROM equipos WHERE estado='aprobado' AND nombre != 'Sistema'"), conn)
            aprobados_count = res_count.iloc[0,0]
            st.write(f"**Progreso: {aprobados_count}/32 Equipos**")
        except Exception as e:
            st.error(f"Error leyendo base de datos: {e}")
            pend = pd.DataFrame() 

        if not pend.empty:
            for _, r in pend.iterrows():
                with st.container():
                    col_img, col_data, col_btn = st.columns([1, 2, 1], vertical_alignment="center")
                    prefijo = str(r.get('prefijo', '')).replace('+', '')
                    wa_link = f"https://wa.me/{prefijo}{r['celular']}"
                    
                    with col_img:
                        if r['escudo']: st.image(r['escudo'], width=60)
                        else: st.write("❌")

                    with col_data:
                        st.markdown(f"**{r['nombre']}**")
                        st.markdown(f"<a href='{wa_link}' style='color: #25D366; text-decoration: none; font-weight: bold; font-size: 0.9em;'>📞 Contactar DT</a>", unsafe_allow_html=True)
                    
                    with col_btn:
                        if st.button(f"✅", key=f"aprob_{r['nombre']}", use_container_width=True):
                            url_final = r['escudo']
                            if url_final:
                                with st.spinner("🤖 Limpiando escudo..."):
                                    try:
                                        res_ia = cloudinary.uploader.upload(url_final, background_removal="cloudinary_ai", folder="escudos_limpios", format="png")
                                        url_final = f"{res_ia['secure_url']}?v={int(time.time())}"
                                    except: pass
                            
                            with st.spinner("🎨 Extrayendo ADN..."):
                                color_adn = motor_colores.obtener_color_dominante(url_final)
                            
                            with conn.connect() as db:
                                db.execute(text("UPDATE equipos SET estado='aprobado', escudo=:e, color_principal=:c WHERE nombre=:n"),
                                           {"e": url_final, "c": color_adn, "n": r['nombre']})
                                db.commit()
                            st.rerun()
                st.markdown("---") 
        else:
            st.info("No hay equipos pendientes.")

        st.divider()

        # --- 2. SELECCIÓN DE TAREA ---
        opcion_admin = st.radio("Tarea:", ["⚽ Resultados", "🛠️ Directorio de Equipos", "🎨 Diseño Web"], horizontal=True, key="adm_tab")
        
 # --- A. OPCIÓN: RESULTADOS (ADMIN - GHOST EDITION BLINDADO) ---
if opcion_admin == "⚽ Resultados":
    st.subheader("📝 Gestión de Resultados")
    
    # 1. Filtro de Emergencia
    solo_revision = st.toggle("🚨 Ver solo partidos en Revisión / Conflicto", value=False)
    
    # CSS para la plantilla
    st.markdown("""
    <style>
        .ghost-card-admin {
            background: rgba(255, 255, 255, 0.03);
            border-radius: 12px;
            padding: 12px;
            margin-bottom: 10px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .revision-glow {
            border: 2px solid #FF4B4B !important;
            background: rgba(255, 75, 75, 0.08) !important;
        }
    </style>
    """, unsafe_allow_html=True)

    try:
        df_partidos = pd.read_sql_query("SELECT * FROM partidos ORDER BY jornada ASC, id ASC", conn)
        df_escudos = pd.read_sql_query("SELECT nombre, escudo FROM equipos", conn)
        escudos_dict = dict(zip(df_escudos['nombre'], df_escudos['escudo']))
    except:
        df_partidos = pd.DataFrame()
        escudos_dict = {}

    placeholder_escudo = "https://cdn-icons-png.flaticon.com/512/5329/5329945.png"

    if df_partidos.empty:
        st.warning("No hay partidos.")
    else:
        # Aplicar filtro de revisión si está activo
        if solo_revision:
            df_partidos = df_partidos[(df_partidos['estado'] == 'Revision') | (df_partidos['conflicto'] == 1)]

        jornadas = sorted(df_partidos['jornada'].unique())
        tabs_j = st.tabs([f"Jornada {int(j)}" for j in jornadas])
        
        for i, tab in enumerate(tabs_j):
            with tab:
                df_j = df_partidos[df_partidos['jornada'] == jornadas[i]]
                
                if df_j.empty:
                    st.info("No hay partidos que requieran revisión en esta jornada.")
                
                for _, row in df_j.iterrows():
                    rev = row['estado'] == 'Revision' or row['conflicto'] == 1
                    clase = "ghost-card-admin revision-glow" if rev else "ghost-card-admin"
                    
                    # Validación segura de escudos para evitar el AttributeError
                    esc_l = escudos_dict.get(row['local'])
                    if not esc_l or pd.isna(esc_l): esc_l = placeholder_escudo
                    
                    esc_v = escudos_dict.get(row['visitante'])
                    if not esc_v or pd.isna(esc_v): esc_v = placeholder_escudo

                    st.markdown(f'<div class="{clase}">', unsafe_allow_html=True)
                    
                    col_esc_l, col_nom_l, col_gl, col_vs, col_gv, col_nom_v, col_esc_v, col_acc = st.columns(
                        [0.6, 2.2, 0.8, 0.3, 0.8, 2.2, 0.6, 1.4], vertical_alignment="center"
                    )
                    
                    with col_esc_l: st.image(esc_l, width=30)
                    with col_nom_l: st.markdown(f"<div style='text-align:right; font-size:13px; font-weight:bold;'>{row['local']}</div>", unsafe_allow_html=True)
                    
                    with col_gl:
                        v_l = int(row['goles_l']) if pd.notna(row['goles_l']) else None
                        g_l = st.number_input("L", value=v_l, min_value=0, max_value=25, label_visibility="collapsed", key=f"ad_gl_{row['id']}")
                    
                    with col_vs: st.markdown("<div style='text-align:center; opacity:0.5;'>-</div>", unsafe_allow_html=True)
                    
                    with col_gv:
                        v_v = int(row['goles_v']) if pd.notna(row['goles_v']) else None
                        g_v = st.number_input("V", value=v_v, min_value=0, max_value=25, label_visibility="collapsed", key=f"ad_gv_{row['id']}")
                    
                    with col_nom_v: st.markdown(f"<div style='text-align:left; font-size:13px; font-weight:bold;'>{row['visitante']}</div>", unsafe_allow_html=True)
                    with col_esc_v: st.image(esc_v, width=30)

                    with col_acc:
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("💾", key=f"sv_{row['id']}", help="Finalizar"):
                                with conn.connect() as db:
                                    db.execute(text("""
                                        UPDATE partidos SET goles_l=:l, goles_v=:v, 
                                        estado='Finalizado', conflicto=0, metodo_registro='Manual' 
                                        WHERE id=:id
                                    """), {"l": g_l, "v": g_v, "id": row['id']})
                                    db.commit()
                                st.rerun()
                        with c2:
                            url = row['url_foto_l'] if pd.notna(row['url_foto_l']) else row['url_foto_v']
                            if url:
                                with st.popover("👁️", help="Ver Evidencia"):
                                    st.image(url, caption=f"Evidencia: {row['metodo_registro']}")
                            else:
                                st.button("🚫", key=f"no_{row['id']}", disabled=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)

                        

        # --- A. OPCIÓN: DIRECTORIO ---
        if opcion_admin == "🛠️ Directorio de Equipos":
            st.subheader("📋 Directorio de Equipos")
            
            try:
                df_maestro = pd.read_sql_query(text("SELECT * FROM equipos ORDER BY nombre"), conn)
            except:
                df_maestro = pd.DataFrame()

            if not df_maestro.empty:
                for _, eq in df_maestro.iterrows():
                    estado_icon = "✅" if eq['estado'] == 'aprobado' else "⏳"
                    escudo_mini = f'<img src="{eq["escudo"]}" width="20" style="vertical-align:middle; margin-right:5px">' if eq['escudo'] else ""
                    st.markdown(f"{estado_icon} {escudo_mini} **{eq['nombre']}** | 🔑 {eq['pin']} | 📞 {eq['prefijo']} {eq['celular']}", unsafe_allow_html=True)
                
                st.markdown("---")
                st.subheader("✏️ Gestión y Edición")
                equipo_sel = st.selectbox("Selecciona equipo:", df_maestro['nombre'].tolist())
                
                if equipo_sel:
                    datos_sel = df_maestro[df_maestro['nombre'] == equipo_sel].iloc[0]

                    with st.form("edit_master_form"):
                        col1, col2 = st.columns(2)
                        new_name = col1.text_input("Nombre del Equipo", datos_sel['nombre'])
                        new_pin = col2.text_input("PIN de acceso", str(datos_sel['pin']))
                        
                        st.write("**🛡️ Actualizar Escudo**")
                        if datos_sel['escudo']:
                            st.image(datos_sel['escudo'], width=100, caption="Escudo Actual")
                            
                        nuevo_escudo_img = st.file_uploader("Subir nuevo escudo", type=['png', 'jpg', 'jpeg'])
                        quitar_escudo = st.checkbox("❌ Eliminar escudo actual")
                        
                        if st.form_submit_button("💾 Guardar Cambios", use_container_width=True):
                            url_final = datos_sel['escudo']
                            if quitar_escudo: url_final = None
                            elif nuevo_escudo_img:
                                res_std = cloudinary.uploader.upload(nuevo_escudo_img, folder="escudos_limpios")
                                url_final = res_std['secure_url']

                            try:
                                with conn.connect() as db:
                                    db.execute(
                                        text("UPDATE equipos SET nombre=:nn, pin=:np, escudo=:ne WHERE nombre=:viejo"),
                                        {"nn": new_name, "np": new_pin, "ne": url_final, "viejo": equipo_sel}
                                    )
                                    db.commit()
                                st.success(f"✅ ¡{new_name} actualizado!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error actualizando: {e}")

                    if st.button(f"✖️ Eliminar: {equipo_sel}", use_container_width=True):
                        with conn.connect() as db:
                            db.execute(text("DELETE FROM equipos WHERE nombre = :n"), {"n": equipo_sel})
                            db.commit()
                        st.error(f"Equipo eliminado.")
                        st.rerun()
            else:
                st.info("No hay equipos registrados.")

        # --- C. OPCIÓN: DISEÑO WEB ---
        elif opcion_admin == "🎨 Diseño Web":
            st.subheader("🎨 Personalización Maestro")
            st.info("Cambia la identidad visual de toda la web en un clic.")
            
            with conn.connect() as db:
                equipos_dispo = db.execute(text("SELECT nombre, escudo, color_principal FROM equipos WHERE (estado = 'aprobado' AND escudo IS NOT NULL) OR nombre ='Sistema'")).fetchall()

            if not equipos_dispo:
                st.warning("No hay equipos con ADN completo para diseñar.")
            else:
                dict_equipos = {eq[0]: {"escudo": eq[1], "color": eq[2]} for eq in equipos_dispo}
                nombre_sel = st.selectbox("Equipo Inspiración:", list(dict_equipos.keys()))
                
                info_sel = dict_equipos[nombre_sel]
                col_prev, col_action = st.columns([1, 2])
                
                with col_prev:
                    st.image(info_sel['escudo'], width=80, caption=f"Color: {info_sel['color']}")
                
                with col_action:
                    if st.button(f"✨ Vestir Web de {nombre_sel}", type="primary", use_container_width=True):
                        try:
                            color_a_usar = info_sel['color'] if info_sel['color'] else "#FFD700"
                            
                            with st.spinner("🧑‍🎨 Construyendo nueva piel para la web..."):
                                img_pil = motor_grafico.construir_portada(color_a_usar, info_sel['escudo'])
                                buffer = BytesIO()
                                img_pil.save(buffer, format="PNG")
                                buffer.seek(0)
                            
                            with st.spinner("☁️ Sincronizando con la nube..."):
                                res = cloudinary.uploader.upload(
                                    buffer, 
                                    folder="fondos_dinamicos",
                                    public_id=f"fondo_activo_golgana",
                                    overwrite=True
                                )
                                url_fondo_nueva = f"{res['secure_url']}?v={int(time.time())}"
                                
                                with conn.connect() as db:
                                    def update_cfg(k, v):
                                        # IMPORTANTE: Asegúrate si tu tabla es 'config' o 'configuracion'
                                        db.execute(text("INSERT INTO config (clave, valor) VALUES (:k, :v) ON CONFLICT (clave) DO UPDATE SET valor = :v"), {"k": k, "v": v})
                                    
                                    update_cfg('fondo_url', url_fondo_nueva)
                                    update_cfg('color_primario', color_a_usar)
                                    update_cfg('equipo_activo', nombre_sel)
                                    db.commit()
                            
                            st.balloons()
                            st.success("¡Identidad actualizada! Refresca la web para ver los cambios.")
                            time.sleep(1)
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Error en motor gráfico: {e}")

        # --- 3. ACCIONES MAESTRAS ---
        st.divider()
        st.subheader("🚀 Control Global")
        
        col_torneo, col_reset = st.columns(2)
        
        with col_torneo:
            if fase_actual == "inscripcion":
                if st.button("🏁 INICIAR TORNEO", use_container_width=True, type="primary"):
                    if aprobados_count >= 2:
                        try:
                            generar_calendario() 
                            st.rerun()
                        except NameError:
                            st.error("Función generar_calendario no encontrada")
                    else:
                        st.error("Mínimo 2 equipos aprobados.")
        
        with col_reset:
            if st.button("🚨 REINICIAR TODO", use_container_width=True):
                with conn.connect() as db:
                    db.execute(text("DELETE FROM equipos"))
                    db.execute(text("DELETE FROM partidos"))
                    # Asegúrate de usar 'config' si esa es tu tabla definitiva
                    db.execute(text("UPDATE config SET valor = 'inscripcion' WHERE clave = 'fase_actual'"))
                    db.commit()
                st.session_state.clear()
                st.rerun()














