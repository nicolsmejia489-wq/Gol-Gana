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




##LEER MARCADOR
def limpiar_nombre(nombre):
    """Elimina sufijos comunes para quedarse con la raíz del nombre."""
    palabras_basura = ["FC", "MX", "CLUB", "REAL", "DEPORTIVO", "10", "A", "B"]
    nombre = nombre.upper()
    for palabra in palabras_basura:
        nombre = nombre.replace(palabra, "")
    return nombre.strip().split()

@st.cache_resource
def obtener_lector():
    return easyocr.Reader(['es', 'en'], gpu=False)

def leer_marcador_ia(imagen_bytes, local_real, visitante_real):
    try:
        datos_puros = imagen_bytes.getvalue()  
        reader = obtener_lector()
        file_bytes = np.asarray(bytearray(datos_puros), dtype=np.uint8) 
        # --- PASO 1: MEJORA DE IMAGEN PROFESIONAL ---
        file_bytes = np.asarray(bytearray(imagen_bytes.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        
        # Convertir a escala de grises
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Aumentar contraste y binarizar (hacer que lo gris sea negro y lo blanco brille)
        # Esto es clave para leer pantallas
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        
        # --- PASO 2: OCR ---
        # Leemos sobre la imagen procesada (thresh)
        resultados = reader.readtext(thresh, detail=1) # detail=1 nos da la posición
        
        textos_detectados = [res[1].upper() for res in resultados]
        toda_la_data = " ".join(textos_detectados)
        
        # --- PASO 3: VALIDACIÓN FLEXIBLE DE EQUIPOS ---
        keywords_l = limpiar_nombre(local_real)
        keywords_v = limpiar_nombre(visitante_real)
        
        # Buscamos si AL MENOS UNA palabra clave de cada equipo aparece
        encontrado_l = any(fuzz.partial_ratio(kw, toda_la_data) > 85 for kw in keywords_l)
        encontrado_v = any(fuzz.partial_ratio(kw, toda_la_data) > 85 for kw in keywords_v)

        # Si no encuentra nombres, intentamos una segunda pasada con el texto original
        if not (encontrado_l or encontrado_v):
            # A veces el pre-procesamiento es muy agresivo, probamos con la original
            resultados_raw = reader.readtext(img, detail=0)
            toda_la_data = " ".join(resultados_raw).upper()
            encontrado_l = any(fuzz.partial_ratio(kw, toda_la_data) > 85 for kw in keywords_l)
            encontrado_v = any(fuzz.partial_ratio(kw, toda_la_data) > 85 for kw in keywords_v)

        if not encontrado_l and not encontrado_v:
             return None, f"⚠️ No identifico a {local_real} o {visitante_real}. Asegúrate de que el marcador sea legible."

        # --- PASO 4: EXTRACCIÓN DE GOLES ---
        # Buscamos patrones tipo "2-0", "2 - 0", "2 0"
        patron_marcador = re.findall(r'(\d+)\s*[-|]\s*(\d+)', toda_la_data)
        
        if patron_marcador:
            gl, gv = patron_marcador[0]
            return (int(gl), int(gv)), "OK"
        
        # Si no hay guion, buscamos números sueltos pero filtramos el "90" del tiempo
        numeros = [int(n) for n in re.findall(r'\d+', toda_la_data) if int(n) < 20]
        if len(numeros) >= 2:
            return (numeros[0], numeros[1]), "OK"

        return None, "🚫 No detecto el puntaje (ej: 2-0). Limpia el lente o evita reflejos."

    except Exception as e:
        return None, f"Error en el motor de visión: {str(e)}"

#####FIN IA



def generar_calendario():
    import random # Aseguramos la importación dentro o al inicio del script
    try:
        with conn.connect() as db:
            # 1. Obtener equipos reales aprobados (ignorando 'Sistema')
            res = db.execute(text("SELECT nombre FROM equipos WHERE estado = 'aprobado' AND nombre != 'Sistema'"))
            equipos = [row[0] for row in res.fetchall()]
            n_reales = len(equipos)

            if n_reales < 2:
                st.error("Se necesitan al menos 2 equipos para generar un calendario.")
                return

            # 2. DETERMINAR CUPOS PARA PLAY-OFFS (Tus nuevas reglas)
            if 25 <= n_reales <= 32:
                cupos = 16  # Clasifican a Octavos
            elif 16 <= n_reales <= 24:
                cupos = 8   # Clasifican a Cuartos
            elif 8 <= n_reales < 16:
                cupos = 4   # Clasifican a Semifinales
            else:
                cupos = 2   # Final directa

            # Guardamos los cupos en la tabla 'config' (Sincronizado)
            db.execute(text("""
                INSERT INTO config (clave, valor) 
                VALUES ('cupos_clasificados', :v) 
                ON CONFLICT (clave) DO UPDATE SET valor = :v
            """), {"v": str(cupos)})

            # 3. Mezclar equipos para aleatoriedad total
            random.shuffle(equipos)

            # 4. Generar 3 Jornadas (Sistema Round Robin sin WO)
            # Si es impar, el algoritmo manejará un "descanso" automáticamente
            equipos_sorteo = equipos.copy()
            if len(equipos_sorteo) % 2 != 0:
                equipos_sorteo.append(None) # None = Equipo que descansa

            n_sorteo = len(equipos_sorteo)
            indices = list(range(n_sorteo))

            for jor in range(1, 4): # 3 Jornadas fijas
                for i in range(n_sorteo // 2):
                    loc = equipos_sorteo[indices[i]]
                    vis = equipos_sorteo[indices[n_sorteo - 1 - i]]

                    # Solo insertamos si ninguno es 'None' (el descanso no se escribe en la DB)
                    if loc and vis:
                        db.execute(text("""
                            INSERT INTO partidos (local, visitante, jornada, estado) 
                            VALUES (:l, :v, :j, 'Programado')
                        """), {"l": loc, "v": vis, "j": jor})

                # Rotación de índices (Algoritmo de la Tuerca)
                indices = [indices[0]] + [indices[-1]] + indices[1:-1]

            # 5. ACTUALIZAR FASE DEL TORNEO (Sincronizado con tu tabla 'config')
            db.execute(text("UPDATE config SET valor = 'clasificacion' WHERE clave = 'fase_actual'"))
            
            # Confirmar cambios en Neon
            db.commit()
            
    except Exception as e:
        st.error(f"Error crítico en el calendario: {e}")
        
###FIN GENERAR CALENDARIO


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
        st.subheader("📅 Calendario de Juegos")
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





    
# --- 5. CALENDARIO Y GESTIÓN DE PARTIDOS ---
elif fase_actual == "clasificacion":
    with tabs[1]:
        st.subheader("📅 Calendario Oficial")
        
        try:
            # Usamos el objeto 'conn' directamente para leer los partidos
            df_p = pd.read_sql_query("SELECT * FROM partidos ORDER BY jornada ASC", conn)
            # Traemos los escudos actualizados (por si el admin los cambió)
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
                    
                    for _, p in df_j.iterrows():
                        # Lógica de Marcador
                        res_text = "vs"
                        if p['goles_l'] is not None and p['goles_v'] is not None:
                            try:
                                res_text = f"{int(p['goles_l'])} - {int(p['goles_v'])}"
                            except: res_text = "vs"
                        
                        # Escudos con respaldo (Placeholder si no hay)
                        placeholder = "https://cdn-icons-png.flaticon.com/512/5329/5329945.png"
                        esc_l = escudos_dict.get(p['local']) or placeholder
                        esc_v = escudos_dict.get(p['visitante']) or placeholder

                        # --- DISEÑO DE FILA ELITE (Alineación Forzada) ---
                        with st.container():
                            # Columnas con pesos específicos para evitar saltos de línea en móvil
                            col_izq, col_cnt, col_der = st.columns([1.2, 0.6, 1.2])
                            
                            # Local (Alineado a la derecha del contenedor)
                            with col_izq:
                                st.markdown(f"""
                                    <div style='display: flex; align-items: center; justify-content: flex-end; gap: 8px;'>
                                        <span style='font-size: 13px; font-weight: bold; white-space: nowrap;'>{p['local'][:10]}</span>
                                        <img src='{esc_l}' width='26' height='26' style='object-fit: contain;'>
                                    </div>
                                """, unsafe_allow_html=True)
                            
                            # Marcador (Centro)
                            with col_cnt:
                                # Usamos el color_maestro para el fondo del marcador
                                color_bg = color_maestro if 'color_maestro' in locals() else "#31333F"
                                st.markdown(f"""
                                    <div style='text-align: center; background: {color_bg}; color: #000; 
                                    border-radius: 4px; font-weight: bold; font-size: 13px; padding: 2px 0;'>
                                        {res_text}
                                    </div>
                                """, unsafe_allow_html=True)
                            
                            # Visitante (Alineado a la izquierda del contenedor)
                            with col_der:
                                st.markdown(f"""
                                    <div style='display: flex; align-items: center; justify-content: flex-start; gap: 8px;'>
                                        <img src='{esc_v}' width='26' height='26' style='object-fit: contain;'>
                                        <span style='font-size: 13px; font-weight: bold; white-space: nowrap;'>{p['visitante'][:10]}</span>
                                    </div>
                                """, unsafe_allow_html=True)
                            
                            # Botón de Evidencias (Solo si existen fotos)
                            if p.get('url_foto_l') or p.get('url_foto_v'):
                                if st.button(f"📷 Ver Evidencia", key=f"v_{p['id']}", use_container_width=True):
                                    c1, c2 = st.columns(2)
                                    if p['url_foto_l']: c1.image(p['url_foto_l'], caption="Local")
                                    if p['url_foto_v']: c2.image(p['url_foto_v'], caption="Visitante")
                        
                        st.divider()
        else:
            st.info("El calendario se mostrará cuando inicie el torneo.")



                            ###PARTIDOS

# --- TAB: MIS PARTIDOS (SOLO PARA DT) ---
if rol == "dt":
    with tabs[2]:
        st.subheader(f"🏟️ Mis Partidos: {equipo_usuario}")
        
        # 1. Consultar partidos del usuario (Lectura segura Neon)
        try:
            query_mis = text("SELECT * FROM partidos WHERE (local=:eq OR visitante=:eq) ORDER BY jornada ASC")
            mis = pd.read_sql_query(query_mis, conn, params={"eq": equipo_usuario})
            
            if mis.empty:
                st.info("Aún no tienes partidos asignados.")
            
            for _, p in mis.iterrows():
                es_local = (p['local'] == equipo_usuario)
                rival = p['visitante'] if es_local else p['local']
                
                with st.container():
                    # Caja de información visual
                    st.markdown(f"""
                        <div class='match-box'>
                            <b>Jornada {p['jornada']}</b><br>
                            Rival: {rival}
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # --- CONTACTO WHATSAPP (Consulta puntual sin cursores) ---
                    numero_wa = None
                    try:
                        with conn.connect() as db:
                            q_wa = text("SELECT prefijo, celular FROM equipos WHERE nombre=:n")
                            r = db.execute(q_wa, {"n": rival}).fetchone()
                            if r and r[0] and r[1]:
                                numero_wa = f"{str(r[0]).replace('+', '')}{r[1]}"
                    except:
                        pass # Si falla, solo no muestra el botón

                    if numero_wa:
                        st.markdown(f"""
                            <a href='https://wa.me/{numero_wa}' class='wa-btn' style='text-decoration: none;'>
                                💬 Contactar Rival (WhatsApp)
                            </a>
                        """, unsafe_allow_html=True)
                    else:
                        st.caption("🚫 Sin contacto registrado.")

                    # --- EXPANDER PARA REPORTE ---
                    with st.expander(f"📸 Reportar Marcador J{p['jornada']}", expanded=False):
                        opcion = st.radio(
                            "Selecciona fuente:", 
                            ["Cámara", "Galería"], 
                            key=f"dt_opt_{p['id']}", 
                            horizontal=True
                        )
                        
                        foto = None
                        if opcion == "Cámara":
                            foto = st.camera_input("Capturar pantalla", key=f"dt_cam_{p['id']}")
                        else:
                            foto = st.file_uploader("Subir imagen", type=['png', 'jpg', 'jpeg'], key=f"dt_gal_{p['id']}")
                        
                        if foto:
                            st.image(foto, width=250, caption="Evidencia cargada")
                            
                            if st.button("🔍 Analizar y Enviar Resultado", key=f"dt_btn_ia_{p['id']}"):
                                with st.spinner("La IA está analizando la imagen..."):
                                    # 1. Análisis de IA
                                    # (Asegúrate de que la función leer_marcador_ia esté definida arriba)
                                    res_ia, mensaje_ia = leer_marcador_ia(foto, p['local'], p['visitante'])
                                    
                                    if res_ia is None:
                                        st.error(mensaje_ia)
                                    else:
                                        gl_ia, gv_ia = res_ia
                                        st.info(f"🤖 IA detectó marcador: {gl_ia} - {gv_ia}")

                                        try:
                                            # Rebobinamos el archivo
                                            foto.seek(0)
                                            
                                            # 2. Subida a Cloudinary
                                            res_cloud = cloudinary.uploader.upload(foto, folder="gol_gana_evidencias")
                                            url_nueva = res_cloud['secure_url']
                                            
                                            col_foto = "url_foto_l" if es_local else "url_foto_v"

                                            # 3. Lógica de Consenso / Conflicto (Escritura segura Neon)
                                            with conn.connect() as db:
                                                gl_existente = p['goles_l']
                                                gv_existente = p['goles_v']

                                                # Si ya hay reporte previo (del rival)
                                                # Convertimos a int si existen para poder comparar
                                                if gl_existente is not None:
                                                    # Comparación
                                                    if int(gl_existente) != gl_ia or int(gv_existente) != gv_ia:
                                                        # CONFLICTO
                                                        # Usamos :params para seguridad
                                                        query_conf = text(f"""
                                                            UPDATE partidos SET 
                                                            goles_l=NULL, goles_v=NULL, 
                                                            conflicto=1, {col_foto}=:url, 
                                                            ia_goles_l=:gl, ia_goles_v=:gv 
                                                            WHERE id=:id
                                                        """)
                                                        db.execute(query_conf, {
                                                            "url": url_nueva, "gl": gl_ia, "gv": gv_ia, "id": p['id']
                                                        })
                                                        st.warning("⚠️ Conflicto: Los resultados no coinciden. El Admin decidirá.")
                                                    else:
                                                        # CONSENSO
                                                        query_ok = text(f"""
                                                            UPDATE partidos SET 
                                                            {col_foto}=:url, conflicto=0, estado='Finalizado' 
                                                            WHERE id=:id
                                                        """)
                                                        db.execute(query_ok, {"url": url_nueva, "id": p['id']})
                                                        st.success("✅ ¡Marcador verificado y finalizado!")
                                                else:
                                                    # PRIMER REPORTE
                                                    query_first = text(f"""
                                                        UPDATE partidos SET 
                                                        goles_l=:gl, goles_v=:gv, 
                                                        {col_foto}=:url, ia_goles_l=:gl, 
                                                        ia_goles_v=:gv, estado='Revision' 
                                                        WHERE id=:id
                                                    """)
                                                    db.execute(query_first, {
                                                        "gl": gl_ia, "gv": gv_ia, "url": url_nueva, "id": p['id']
                                                    })
                                                    st.success("⚽ Resultado guardado. Esperando reporte del rival.")
                                                
                                                db.commit() # ¡Importante guardar cambios!
                                            
                                            time.sleep(1.5)
                                            st.rerun()

                                        except Exception as e:
                                            st.error(f"❌ Error al procesar: {e}")
                    
                    st.markdown("<hr style='margin:10px 0; opacity:0.2;'>", unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Error cargando partidos: {e}")
  #########


  
  
# --- TAB: GESTIÓN ADMIN (Completo con Diseño Dinámico) ---
if rol == "admin":
    with tabs[2]:
        st.header("⚙️ Panel de Control Admin")
        
        # --- 1. SECCIÓN DE APROBACIONES (Sin cambios, ya extrae color_principal) ---
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
        
        # --- A. OPCIÓN: DIRECTORIO (Sin cambios) ---
        if opcion_admin == "🛠️ Directorio de Equipos":
            st.subheader("📋 Directorio de Equipos")
            # ... (Toda tu lógica de Directorio se mantiene igual) ...
            st.info("Directorio cargado correctamente.") # Simplificado para el ejemplo

        # --- B. OPCIÓN: DISEÑO WEB (AQUÍ ESTÁ EL ARREGLO) ---
        elif opcion_admin == "🎨 Diseño Web":
            st.subheader("🎨 Personalización Maestro")
            st.info("Cambia la identidad visual de toda la web en un clic.")
            
            with conn.connect() as db:
                # Traemos nombre, escudo y el color ya guardado en la tabla equipos
                equipos_dispo = db.execute(text("SELECT nombre, escudo, color_principal FROM equipos WHERE (estado = 'aprobado' AND escudo IS NOT NULL) OR nombre ='Sistema'")).fetchall()

            if not equipos_dispo:
                st.warning("No hay equipos con ADN completo para diseñar.")
            else:
                # Creamos un diccionario con toda la info del equipo para no repetir consultas
                dict_equipos = {eq[0]: {"escudo": eq[1], "color": eq[2]} for eq in equipos_dispo}
                nombre_sel = st.selectbox("Equipo Inspiración:", list(dict_equipos.keys()))
                
                info_sel = dict_equipos[nombre_sel]
                col_prev, col_action = st.columns([1, 2])
                
                with col_prev:
                    st.image(info_sel['escudo'], width=80, caption=f"Color: {info_sel['color']}")
                
                with col_action:
                    if st.button(f"✨ Vestir Web de {nombre_sel}", type="primary", use_container_width=True):
                        try:
                            # 1. Usar el color que ya tiene el equipo (o detectar si es Sistema)
                            color_a_usar = info_sel['color'] if info_sel['color'] else "#FFD700"
                            
                            # 2. Generar Fondo con Motor Gráfico
                            with st.spinner("🧑‍🎨 Construyendo nueva piel para la web..."):
                                img_pil = motor_grafico.construir_portada(color_a_usar, info_sel['escudo'])
                                buffer = BytesIO()
                                img_pil.save(buffer, format="PNG")
                                buffer.seek(0)
                            
                            # 3. Subir a Cloudinary (Usamos el nombre del equipo en el ID para forzar cambio)
                            with st.spinner("☁️ Sincronizando con la nube..."):
                                res = cloudinary.uploader.upload(
                                    buffer, 
                                    folder="fondos_dinamicos",
                                    public_id=f"fondo_activo_golgana", # ID fijo para el fondo actual
                                    overwrite=True
                                )
                                # Cache buster vital para que el navegador note el cambio
                                url_fondo_nueva = f"{res['secure_url']}?v={int(time.time())}"
                                
                                # 4. Actualizar las 3 llaves maestras en 'configuracion'
                                with conn.connect() as db:
                                    def update_cfg(k, v):
                                        db.execute(text("INSERT INTO configuracion (clave, valor) VALUES (:k, :v) ON CONFLICT (clave) DO UPDATE SET valor = :v"), {"k": k, "v": v})
                                    
                                    update_cfg('fondo_url', url_fondo_nueva)
                                    update_cfg('color_primario', color_a_usar) # Guardamos el HEX exacto
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
                    db.commit()
                st.session_state.clear()
                st.rerun()
                


















