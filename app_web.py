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

import re  # Para expresiones regulares (encontrar números difíciles)
from thefuzz import fuzz # Para comparación flexible de nombres

# Configura tus credenciales (Búscalas en tu Dashboard de Cloudinary)
cloudinary.config( 
  cloud_name = "dlvczeqlp", 
  api_key = "276694391654197", 
  api_secret = "j-_6AaUam_Acwng0GGr8tmb8Zyk",
  secure = True
)


from contextlib import contextmanager

# --- 1. CONFIGURACIÓN Y TEMA FIJO CLARO ---
DB_NAME = "gol_gana.db"
ADMIN_PIN = "2025" 

st.set_page_config(page_title="Gol-Gana Pro", layout="centered")
st.markdown("""
    <style>
    .stApp { background-color: white !important; }
    .stApp, .stMarkdown, p, h1, h2, h3, label { color: black !important; }

    div.stButton > button {
        background-color: #f0f2f6 !important;
        color: #31333f !important;
        border: 1px solid #dcdfe4 !important;
        border-radius: 8px !important;
        transition: 0.3s;
    }
    
    .mobile-table { 
        width: 100%; border-collapse: collapse; font-size: 12px; 
        background-color: white !important; color: black !important;
        border: 1px solid #ddd;
    }
    .mobile-table th { 
        background: #f0f2f6 !important; color: black !important; 
        padding: 8px; border: 1px solid #ddd;
    }
    .mobile-table td { padding: 8px; text-align: center; border: 1px solid #eee; color: black !important; }
    .team-cell { text-align: left !important; font-weight: bold; color: #1f77b4 !important; }

    .match-box { 
        border: 1px solid #ccc; padding: 15px; border-radius: 10px; 
        margin-bottom: 15px; background: #ffffff !important; 
        color: black !important;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }

    .wa-btn { 
        display: inline-block; background-color: #25D366; color: white !important; 
        padding: 8px 15px; border-radius: 5px; text-decoration: none; 
        font-weight: bold; font-size: 14px; margin-top: 5px;
    }

    div[data-testid="stCameraInput"] button {
    background-color: #ffffff !important;
    color: #000000 !important;
    border: 2px solid #dcdfe4 !important;
    font-weight: bold !important;
}

/* Estilo para el botón de 'Eliminar foto' que aparece después */
div[data-testid="stCameraInput"] button:disabled {
    background-color: #f0f2f6 !important;
    color: #31333f !important;
}
/* 1. Botón de Galería (Browse Files) */
    section[data-testid="stFileUploadDropzone"] button {
        background-color: #f0f2f6 !important;
        color: #31333f !important;
    }

    /* 2. Títulos de los Expander y etiquetas */
    .st-emotion-cache-p4m0d4, .st-ae, label, .stMarkdown p {
        background-color: #f0f2f6 !important;
        color: #31333f !important;;
    }

    /* 3. Fondo del Expander cuando se abre */
    .st-emotion-cache-1h9usn1, .st-emotion-cache-6q9sum {
        background-color: #f0f2f6 !important;
        color: #31333f !important;
    }

    /* 4. Texto dentro del Expander */
    .st-emotion-cache-1h9usn1 p, .st-emotion-cache-1h9usn1 span {
        color: black !important;
    }

    /* Ajuste para el radio button (Cámara/Galería) */
    div[data-testid="stWidgetLabel"] p {
        color: black !important;
        font-weight: bold !important;
    }
    
    </style>
    """, unsafe_allow_html=True)




@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False, timeout=15)
    try: yield conn
    finally: conn.close()

def inicializar_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS equipos (
            nombre TEXT PRIMARY KEY, celular TEXT, prefijo TEXT, pin TEXT, estado TEXT DEFAULT 'pendiente'
        )''')
        # Agregamos las columnas nuevas aquí también para que si la base de datos es nueva, nazca completa
        cursor.execute('''CREATE TABLE IF NOT EXISTS partidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            local TEXT, visitante TEXT, 
            goles_l INTEGER DEFAULT NULL, goles_v INTEGER DEFAULT NULL, 
            jornada INTEGER, estado TEXT DEFAULT 'programado',
            url_foto_l TEXT, url_foto_v TEXT, 
            ia_goles_l INTEGER, ia_goles_v INTEGER, 
            conflicto INTEGER DEFAULT 0
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS config (llave TEXT PRIMARY KEY, valor TEXT)''')
        cursor.execute("INSERT OR IGNORE INTO config (llave, valor) VALUES ('fase', 'inscripcion')")
        conn.commit()

def migrar_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Estas son las columnas que añadimos por si la base de datos ya existía de antes
        columnas = [
            ("url_foto_l", "TEXT"),
            ("url_foto_v", "TEXT"),
            ("ia_goles_l", "INTEGER"),
            ("ia_goles_v", "INTEGER"),
            ("conflicto", "INTEGER DEFAULT 0")
        ]
        for nombre_col, tipo in columnas:
            try:
                cursor.execute(f"ALTER TABLE partidos ADD COLUMN {nombre_col} {tipo}")
            except sqlite3.OperationalError:
                pass # Si la columna ya existe, no hace nada
        conn.commit()

# --- EJECUCIÓN ---
inicializar_db() # 1. Crea lo básico
migrar_db()      # 2. Asegura que lo nuevo esté ahí


##### ALGORITMO IA #####

@st.cache_resource
def obtener_lector():
    # Inicializamos EasyOCR solo una vez para ahorrar memoria
    return easyocr.Reader(['es', 'en'], gpu=False)

def leer_marcador_ia(imagen_bytes, local_real, visitante_real):
    try:
        reader = obtener_lector()
        
        # 1. Procesar imagen (igual que antes)
        image = Image.open(io.BytesIO(imagen_bytes.getvalue()))
        image_np = np.array(image.convert('RGB'))
        
        # Leer todo el texto
        resultados = reader.readtext(image_np, detail=0, paragraph=True)
        texto_detectado = " ".join(resultados).upper()
        
        # --- MEJORA 1: BÚSQUEDA FLEXIBLE DE NOMBRES (Fuzzy Matching) ---
        # Usamos 'partial_ratio' para buscar si el nombre real está "contenido" en el texto detectado.
        # Un puntaje > 80 suele ser una coincidencia muy sólida.
        score_local = fuzz.partial_ratio(local_real.upper(), texto_detectado)
        score_visitante = fuzz.partial_ratio(visitante_real.upper(), texto_detectado)
        
        umbrla_coincidencia = 80 # Exigimos un 80% de similitud mínima

        # Validamos: ¿Encontré al menos uno de los dos equipos con certeza?
        # (A veces el OCR falla en un nombre raro, pero si el otro y el marcador están bien, es válido)
        found_local = score_local >= umbrla_coincidencia
        found_visitante = score_visitante >= umbrla_coincidencia

        if not found_local and not found_visitante:
            # Si no encuentro a ninguno, es muy arriesgado aceptar la foto.
            # Debug: Descomenta esto si quieres ver qué leyó la IA realmente
            # print(f"Texto leído: {texto_detectado} | Scores: L={score_local}, V={score_visitante}")
            return None, f"⚠️ No reconozco los nombres de los equipos en la imagen (Similitud baja). Intenta enfocar mejor los nombres."

        # --- MEJORA 2: EXTRACCIÓN ROBUSTA DE NÚMEROS (Regex) ---
        # En lugar de buscar dígitos aislados, usamos regex para encontrar cualquier secuencia de números.
        # Esto encuentra el "2" y el "0" incluso en cadenas como "2-0" o "2v0".
        numeros_encontrados = re.findall(r'\d+', texto_detectado)
        
        # Convertimos a enteros y filtramos resultados locos (ej. un año "2023" o un número de camiseta "99")
        goles_posibles = []
        for num in numeros_encontrados:
            n = int(num)
            if 0 <= n <= 15: # Asumimos que es raro un marcador mayor a 15 en fútbol
                goles_posibles.append(n)
        
        # Necesitamos encontrar al menos dos números válidos
        if len(goles_posibles) < 2:
            return None, "🚫 No pude identificar claramente dos números para el marcador. Toma una mejor foto."
        
        # ASUNCIÓN IMPORTANTE: En los marcadores horizontales, el primer número que se lee 
        # de izquierda a derecha suele ser el del equipo local (izquierda) y el segundo el visitante (derecha).
        # Tomamos los dos primeros números válidos que encontramos.
        gl = goles_posibles[0]
        gv = goles_posibles[1]
        
        return (gl, gv), "OK"

    except Exception as e:
        return None, f"Error técnico en el análisis de imagen: {e}"

#####FIN IA
# --- 2. LÓGICA DE JORNADAS ---
def generar_calendario():
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT nombre FROM equipos WHERE estado = 'aprobado'")
        equipos = [row[0] for row in cur.fetchall()]
        while len(equipos) < 32:
            nombre_wo = f"(WO) {len(equipos)+1}"
            conn.execute("INSERT OR IGNORE INTO equipos (nombre, estado) VALUES (?, 'aprobado')", (nombre_wo,))
            equipos.append(nombre_wo)
        random.shuffle(equipos)
        n = len(equipos)
        indices = list(range(n))
        for jor in range(1, 4):
            for i in range(n // 2):
                loc = equipos[indices[i]]
                vis = equipos[indices[n - 1 - i]]
                conn.execute("INSERT INTO partidos (local, visitante, jornada) VALUES (?, ?, ?)", (loc, vis, jor))
            indices = [indices[0]] + [indices[-1]] + indices[1:-1]
        conn.execute("UPDATE config SET valor = 'clasificacion' WHERE llave = 'fase'")
        conn.commit()

# --- 3. NAVEGACIÓN ---
if "reg_estado" not in st.session_state: st.session_state.reg_estado = "formulario"
if "pin_usuario" not in st.session_state: st.session_state.pin_usuario = ""

st.title("⚽ Gol Gana")
c_nav1, c_nav2 = st.columns(2)
with c_nav1:
    if st.button("🔙 Inicio"):
        st.session_state.reg_estado = "formulario"
        st.session_state.pin_usuario = ""
        st.rerun()
with c_nav2:
    if st.button("🔄 Refrescar"): st.rerun()

pin_input = st.text_input("🔑 PIN de Acceso", value=st.session_state.pin_usuario, type="password")
st.session_state.pin_usuario = pin_input

with get_db_connection() as conn:
    cur = conn.cursor()
    cur.execute("SELECT valor FROM config WHERE llave = 'fase'")
    fase_actual = cur.fetchone()[0]

rol = "espectador"
equipo_usuario = None
if st.session_state.pin_usuario == ADMIN_PIN:
    rol = "admin"
elif st.session_state.pin_usuario:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT nombre FROM equipos WHERE pin = ? AND estado = 'aprobado'", (st.session_state.pin_usuario,))
        res = cur.fetchone()
        if res: rol = "dt"; equipo_usuario = res[0]

# --- 4. TABS ---
if fase_actual == "inscripcion":
    tabs = st.tabs(["📊 Clasificación", "📝 Inscribirse"])
else:
    # Agregamos la pestaña de Gestión solo si es Admin
    if rol == "admin":
        tabs = st.tabs(["📊 Clasificación", "📅 Calendario", "⚙️ Gestión Admin"])
    elif rol == "dt": 
        tabs = st.tabs(["📊 Clasificación", "📅 Calendario", "⚽ Mis Partidos"])
    else: 
        tabs = st.tabs(["📊 Clasificación", "📅 Calendario"])

# TAB: CLASIFICACIÓN
with tabs[0]:
    with get_db_connection() as conn:
        df_eq = pd.read_sql_query("SELECT nombre FROM equipos WHERE estado = 'aprobado'", conn)
        if df_eq.empty: st.info("No hay equipos todavía.")
        else:
            stats = {e: {'PJ':0, 'PTS':0, 'GF':0, 'GC':0} for e in df_eq['nombre']}
            df_p = pd.read_sql_query("SELECT * FROM partidos WHERE goles_l IS NOT NULL", conn)
            for _, f in df_p.iterrows():
                l, v, gl, gv = f['local'], f['visitante'], int(f['goles_l']), int(f['goles_v'])
                if l in stats and v in stats:
                    stats[l]['PJ']+=1; stats[v]['PJ']+=1
                    stats[l]['GF']+=gl; stats[l]['GC']+=gv
                    stats[v]['GF']+=gv; stats[v]['GC']+=gl
                    if gl > gv: stats[l]['PTS']+=3
                    elif gv > gl: stats[v]['PTS']+=3
                    else: stats[l]['PTS']+=1; stats[v]['PTS']+=1
            df_f = pd.DataFrame.from_dict(stats, orient='index').reset_index()
            df_f.columns = ['EQ', 'PJ', 'PTS', 'GF', 'GC']
            df_f['DG'] = df_f['GF'] - df_f['GC']
            df_f = df_f.sort_values(by=['PTS', 'DG', 'GF'], ascending=False).reset_index(drop=True)
            df_f.insert(0, 'POS', range(1, len(df_f) + 1))
            html = '<table class="mobile-table"><thead><tr><th>POS</th><th style="text-align:left">EQ</th><th>PTS</th><th>PJ</th><th>GF</th><th>GC</th><th>DG</th></tr></thead><tbody>'
            for _, r in df_f.iterrows():
                html += f"<tr><td>{r['POS']}</td><td class='team-cell'>{r['EQ']}</td><td><b>{r['PTS']}</b></td><td>{r['PJ']}</td><td>{r['GF']}</td><td>{r['GC']}</td><td>{r['DG']}</td></tr>"
            st.markdown(html + "</tbody></table>", unsafe_allow_html=True)

# TAB: REGISTRO (CON FIX DEFINITIVO)
if fase_actual == "inscripcion":
    with tabs[1]:
        if st.session_state.reg_estado == "exito":
            st.success("✅ ¡Inscripción recibida!")
            if st.button("Nuevo Registro"): st.session_state.reg_estado = "formulario"; st.rerun()
        
        elif st.session_state.reg_estado == "confirmar":
            d = st.session_state.datos_temp
            st.warning("⚠️ **Confirma tus datos:**")
            st.write(f"**Equipo:** {d['n']}\n\n**WA:** {d['pref']} {d['wa']}\n\n**PIN:** {d['pin']}")
            c1, c2 = st.columns(2)
            
            if c1.button("✅ Confirmar"):
                registro_ok = False
                with get_db_connection() as conn:
                    try:
                        conn.execute("INSERT INTO equipos (nombre, celular, prefijo, pin) VALUES (?,?,?,?)", (d['n'], d['wa'], d['pref'], d['pin']))
                        conn.commit()
                        registro_ok = True
                    except sqlite3.Error as e:
                        st.error(f"Error real de base de datos: {e}")
                
                if registro_ok: # Rerun FUERA del try-except
                    st.session_state.reg_estado = "exito"
                    st.rerun()

            if c2.button("✏️ Editar"): st.session_state.reg_estado = "formulario"; st.rerun()
        
        else:
            with st.form("reg_preventivo"):
                nom = st.text_input("Nombre Equipo").strip()
                paises = {"Colombia": "+57",    "EEUU": "+1",    "México": "+52",    "Canadá": "+1",    "Costa Rica": "+506",    "Ecuador": "+593",    "Panamá": "+507",    "Perú": "+51",    "Uruguay": "+598",    "Argentina": "+54",    "Bolivia": "+591", "Brasil": "+55",    "Chile": "+56",    "Venezuela": "+58",    "Belice": "+501",    "Guatemala": "+502",    "El Salvador": "+503",    "Honduras": "+504",    "Nicaragua": "+505"}
                pais_sel = st.selectbox("País", [f"{p} ({pref})" for p, pref in paises.items()])
                tel = st.text_input("WhatsApp").strip()
                pin_r = st.text_input("PIN (4 dígitos)", max_chars=4, type="password").strip()
                if st.form_submit_button("Siguiente"):
                    if not nom or not tel or len(pin_r) < 4: st.error("Datos incompletos.")
                    else:
                        with get_db_connection() as conn:
                            cur = conn.cursor()
                            cur.execute("SELECT 1 FROM equipos WHERE nombre=? OR pin=? OR celular=?", (nom, pin_r, tel))
                            if cur.fetchone(): st.error("❌ Nombre, PIN o Teléfono ya registrados.")
                            else:
                                st.session_state.datos_temp = {"n": nom, "wa": tel, "pin": pin_r, "pref": pais_sel.split('(')[-1].replace(')', '')}
                                st.session_state.reg_estado = "confirmar"; st.rerun()


    
# --- 5. CALENDARIO Y GESTIÓN DE PARTIDOS ---
elif fase_actual == "clasificacion":
    # 1. Pestaña de Calendario (tabs[1])
    with tabs[1]:
        st.subheader("📅 Calendario Oficial")
        with get_db_connection() as conn:
            df_p = pd.read_sql_query("SELECT * FROM partidos ORDER BY jornada ASC", conn)
        
        j_tabs = st.tabs(["Jornada 1", "Jornada 2", "Jornada 3"])
        for i, jt in enumerate(j_tabs):
            with jt:
                df_j = df_p[df_p['jornada'] == (i + 1)]
                for _, p in df_j.iterrows():
                    # Manejo de marcadores
                    if p['goles_l'] is not None and p['goles_v'] is not None:
                        try:
                            res_text = f"{int(p['goles_l'])} - {int(p['goles_v'])}"
                        except:
                            res_text = "vs"
                    else:
                        res_text = "vs"
                    
                    c1, c2 = st.columns([0.8, 0.2])
                    c1.write(f"**{p['local']}** {res_text} **{p['visitante']}**")
                    
                    if p['url_foto_l'] or p['url_foto_v']:
                        if c2.button("👁️", key=f"view_{p['id']}"):
                            if p['url_foto_l']: st.image(p['url_foto_l'], caption=f"Evidencia {p['local']}")
                            if p['url_foto_v']: st.image(p['url_foto_v'], caption=f"Evidencia {p['visitante']}")


# --- TAB: MIS PARTIDOS (SOLO PARA DT) ---
    if rol == "dt":
        with tabs[2]:
            st.subheader(f"🏟️ Mis Partidos: {equipo_usuario}")
            with get_db_connection() as conn:
                # Obtenemos los partidos donde participa el usuario
                mis = pd.read_sql_query(
                    "SELECT * FROM partidos WHERE (local=? OR visitante=?) ORDER BY jornada ASC", 
                    conn, params=(equipo_usuario, equipo_usuario)
                )
                
                for _, p in mis.iterrows():
                    rival = p['visitante'] if p['local'] == equipo_usuario else p['local']
                    
                    with st.container():
                        # Caja de información del partido
                        st.markdown(f"""
                            <div class='match-box'>
                                <b>Jornada {p['jornada']}</b><br>
                                Rival: {rival}
                            </div>
                        """, unsafe_allow_html=True)
                        
                        # --- SECCIÓN DE CONTACTO WHATSAPP ---
                        cur = conn.cursor()
                        cur.execute("SELECT prefijo, celular FROM equipos WHERE nombre=?", (rival,))
                        r = cur.fetchone()
                        
                        if r and r[0] and r[1] and str(r[1]).isdigit():
                            numero_wa = f"{str(r[0]).replace('+', '')}{r[1]}"
                            st.markdown(f"""
                                <a href='https://wa.me/{numero_wa}' class='wa-btn' style='text-decoration: none;'>
                                    💬 Contactar Rival (WhatsApp)
                                </a>
                            """, unsafe_allow_html=True)
                        else:
                            st.caption("🚫 Sin contacto registrado para este rival.")

                        # --- EXPANDER PARA REPORTAR RESULTADO ---
                        with st.expander(f"📸 Reportar Marcador J{p['jornada']}", expanded=False):
                            # Llave única con prefijo 'dt_' para evitar DuplicateElementKey
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
                                st.image(foto, width=200, caption="Evidencia seleccionada")
                                
                                # Botón con llave única
                                if st.button("🔍 Analizar y Enviar Resultado", key=f"dt_btn_ia_{p['id']}"):
                                    with st.spinner("La IA está analizando la evidencia..."):
                                        # 1. Llamada a la función del "Cerebro IA"
                                        res_ia, mensaje_ia = leer_marcador_ia(foto, p['local'], p['visitante'])
                                        
                                        if res_ia is None:
                                            st.error(mensaje_ia)
                                        else:
                                            gl_ia, gv_ia = res_ia
                                            es_local = (p['local'] == equipo_usuario)
                                            
                                            # 2. Feedback emocional/informativo al DT
                                            mis_goles = gl_ia if es_local else gv_ia
                                            sus_goles = gv_ia if es_local else gl_ia
                                            
                                            if mis_goles > sus_goles:
                                                st.success(f"✅ ¡Resultado {gl_ia}-{gv_ia} a tu favor! ¡Excelente victoria!")
                                            elif mis_goles < sus_goles:
                                                st.warning(f"📉 Resultado {gl_ia}-{gv_ia} en contra. ¡A mejorar en la siguiente!")
                                            else:
                                                st.info(f"🤝 Marcador {gl_ia}-{gv_ia}. ¡Empate!")

                                            try:
                                                # 3. Subida de la imagen a Cloudinary
                                                res_cloud = cloudinary.uploader.upload(foto, folder="gol_gana_evidencias")
                                                url_nueva = res_cloud['secure_url']
                                                col_foto = "url_foto_l" if es_local else "url_foto_v"

                                                with get_db_connection() as conn_up:
                                                    # 4. Lógica de Consenso y Detección de Conflictos
                                                    gl_existente = p['goles_l']
                                                    gv_existente = p['goles_v']

                                                    # Si ya había un resultado cargado (por el rival)
                                                    if gl_existente is not None:
                                                        if int(gl_existente) != gl_ia or int(gv_existente) != gv_ia:
                                                            # CONFLICTO: Los datos no coinciden
                                                            conn_up.execute(f"""
                                                                UPDATE partidos SET 
                                                                goles_l=NULL, goles_v=NULL, 
                                                                conflicto=1, {col_foto}=?, 
                                                                ia_goles_l=?, ia_goles_v=? 
                                                                WHERE id=?""", (url_nueva, gl_ia, gv_ia, p['id']))
                                                            st.warning("⚠️ Conflicto: Tu reporte no coincide con el del rival. El Admin revisará las fotos.")
                                                        else:
                                                            # CONSENSO: Ambos reportaron lo mismo
                                                            conn_up.execute(f"""
                                                                UPDATE partidos SET 
                                                                {col_foto}=?, conflicto=0 
                                                                WHERE id=?""", (url_nueva, p['id']))
                                                            st.success("¡Marcador verificado y confirmado por ambos equipos!")
                                                    else:
                                                        # PRIMER REPORTE: Nadie había subido evidencia aún
                                                        conn_up.execute(f"""
                                                            UPDATE partidos SET 
                                                            goles_l=?, goles_v=?, 
                                                            {col_foto}=?, ia_goles_l=?, 
                                                            ia_goles_v=?, estado='Revision' 
                                                            WHERE id=?""", (gl_ia, gv_ia, url_nueva, gl_ia, gv_ia, p['id']))
                                                        st.info("Resultado guardado con éxito. Esperando a que el rival reporte.")
                                                    
                                                    conn_up.commit()
                                                
                                                # Refrescar la página para actualizar estados
                                                st.rerun()
                                                
                                            except Exception as e:
                                                st.error(f"Error técnico durante el guardado: {e}")
                        
                        st.markdown("<hr>", unsafe_allow_html=True)

  #########


  
  
    # --- NUEVA PESTAÑA: GESTIÓN ADMIN ---
    if rol == "admin":
        with tabs[2]:
            st.subheader("⚙️ Gestión de Resultados")
            with get_db_connection() as conn:
                df_adm = pd.read_sql_query("SELECT * FROM partidos ORDER BY jornada ASC, id ASC", conn)
            
            for _, p in df_adm.iterrows():
                with st.expander(f"J{p['jornada']}: {p['local']} vs {p['visitante']}"):
                    c1, c2 = st.columns(2)
                    # Precarga de goles evitando decimales
                    gl_val = int(p['goles_l']) if pd.notna(p['goles_l']) else 0
                    gv_val = int(p['goles_v']) if pd.notna(p['goles_v']) else 0
                    
                    with c1: gl = st.number_input(f"Goles {p['local']}", value=gl_val, step=1, key=f"al_{p['id']}")
                    with c2: gv = st.number_input(f"Goles {p['visitante']}", value=gv_val, step=1, key=f"av_{p['id']}")
                    
                    # Botones de WhatsApp para el Admin
                    with get_db_connection() as conn:
                        cur = conn.cursor()
                        cur.execute("SELECT nombre, prefijo, celular FROM equipos WHERE nombre IN (?,?)", (p['local'], p['visitante']))
                        dts = {row[0]: (row[1], row[2]) for row in cur.fetchall()}
                    
                    wa_cols = st.columns(2)
                    for idx, equipo in enumerate([p['local'], p['visitante']]):
                        if equipo in dts and dts[equipo][1]:
                            pref, cel = dts[equipo]
                            wa_cols[idx].markdown(f"<a href='https://wa.me/{str(pref).replace('+','')}{cel}' class='wa-btn' style='font-size:10px'>💬 WA {equipo}</a>", unsafe_allow_html=True)
                    
                    if st.button("Guardar Marcador", key=f"btn_s_{p['id']}"):
                        with get_db_connection() as conn:
                            conn.execute("UPDATE partidos SET goles_l=?, goles_v=?, estado='finalizado' WHERE id=?", (gl, gv, p['id']))
                            conn.commit()
                        st.success("Resultado guardado")
                        st.rerun()

# SECCIÓN ADMIN (INFERIOR)
if rol == "admin":
    st.divider()
    if fase_actual == "inscripcion":
        with get_db_connection() as conn:
            pend = pd.read_sql_query("SELECT * FROM equipos WHERE estado='pendiente'", conn)
            st.write(f"Aprobados: {len(pd.read_sql_query('SELECT 1 FROM equipos WHERE estado=\'aprobado\'', conn))}/32")
            for _, r in pend.iterrows():
                if st.button(f"Aprobar {r['nombre']}"):
                    conn.execute("UPDATE equipos SET estado='aprobado' WHERE nombre=?", (r['nombre'],))
                    conn.commit(); st.rerun()
        if st.button("🚀 INICIAR TORNEO"): generar_calendario(); st.rerun()
    if st.button("🚨 REINICIAR TODO"):
        with get_db_connection() as conn:
            conn.execute("DROP TABLE IF EXISTS equipos"); conn.execute("DROP TABLE IF EXISTS partidos")
            conn.execute("UPDATE config SET valor='inscripcion'"); conn.commit()
        st.rerun()


























