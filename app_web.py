import streamlit as st
import sqlite3
import pandas as pd
import random
import easyocr
import cloudinary
import cloudinary.uploader

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

##### ALGORITMO IA
def leer_marcador_ia(imagen_bytes, local_real, visitante_real):
    # Inicializar el lector (solo la primera vez)
    reader = easyocr.Reader(['es', 'en'])
    
    # Convertir imagen para OpenCV
    image = Image.open(imagen_bytes)
    image_np = np.array(image)
    
    # La IA lee todo el texto de la imagen
    resultados = reader.readtext(image_np)
    texto_detectado = " ".join([res[1].upper() for res in resultados])
    numeros = [int(s) for s in texto_detectado.split() if s.isdigit()]
    
    # --- VALIDACIÓN DE EQUIPOS ---
    # Buscamos si el nombre de los equipos aparece en la foto
    found_local = local_real.upper() in texto_detectado
    found_visitante = visitante_real.upper() in texto_detectado

    if not found_local and not found_visitante:
        return None, "⚠️ No detecto los nombres de los clubes. Asegúrate de que se vean en pantalla."

    # --- EXTRACCIÓN DE MARCADOR ---
    # Buscamos los primeros dos números que parezcan un marcador (ej. entre 0 y 20)
    goles = [n for n in numeros if 0 <= n <= 20]
    
    if len(goles) < 2:
        return None, "🚫 No pude identificar el marcador claramente. Toma una mejor foto."
    
    # Asumimos que el primer número es Local y el segundo Visitante (orden estándar)
    gl, gv = goles[0], goles[1]
    return (gl, gv), "OK"
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
                paises = {"Colombia": "+57", "México": "+52", "España": "+34", "Argentina": "+54", "EEUU": "+1", "Chile": "+56", "Ecuador": "+593", "Perú": "+51", "Venezuela": "+58"}
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

    
    # --- TAB: CALENDARIO ---
 # --- TAB: CALENDARIO ---
with tabs[1]:
    st.subheader("📅 Calendario Oficial")
    with get_db_connection() as conn:
        df_p = pd.read_sql_query("SELECT * FROM partidos ORDER BY jornada ASC", conn)
    
    j_tabs = st.tabs(["Jornada 1", "Jornada 2", "Jornada 3"])
    for i, jt in enumerate(j_tabs):
        with jt:
            df_j = df_p[df_p['jornada'] == (i + 1)]
            for _, p in df_j.iterrows():
                # BLOQUE CORREGIDO: Manejo robusto de marcadores
                # Verificamos que los goles no sean None antes de convertirlos
                if p['goles_l'] is not None and p['goles_v'] is not None:
                    try:
                        res_text = f"{int(p['goles_l'])} - {int(p['goles_v'])}"
                    except (ValueError, TypeError):
                        res_text = "vs"
                else:
                    res_text = "vs"
                
                # Diseño de la fila del partido
                c1, c2 = st.columns([0.8, 0.2])
                c1.write(f"**{p['local']}** {res_text} **{p['visitante']}**")
                
                # Si hay fotos subidas, mostrar el icono para visualizarlas
                if p['url_foto_l'] or p['url_foto_v']:
                    if c2.button("👁️", key=f"view_{p['id']}"):
                        if p['url_foto_l']: 
                            st.image(p['url_foto_l'], caption=f"Evidencia {p['local']}")
                        if p['url_foto_v']: 
                            st.image(p['url_foto_v'], caption=f"Evidencia {p['visitante']}")
    # --- TAB: MIS PARTIDOS (SOLO PARA DT) ---

 # --- TAB: MIS PARTIDOS (SOLO PARA DT) ---
    if rol == "dt":
        with tabs[2]:
            st.subheader(f"🏟️ Mis Partidos: {equipo_usuario}")
            with get_db_connection() as conn:
                mis = pd.read_sql_query("SELECT * FROM partidos WHERE (local=? OR visitante=?) ORDER BY jornada ASC", 
                                       conn, params=(equipo_usuario, equipo_usuario))
                
                for _, p in mis.iterrows():
                    rival = p['visitante'] if p['local'] == equipo_usuario else p['local']
                    
                    with st.container():
                        st.markdown(f"<div class='match-box'><b>Jornada {p['jornada']}</b><br>Rival: {rival}</div>", unsafe_allow_html=True)
                        
                        # Botón WhatsApp
                        cur = conn.cursor()
                        cur.execute("SELECT prefijo, celular FROM equipos WHERE nombre=?", (rival,))
                        r = cur.fetchone()
                        if r and r[0] and r[1]:
                            st.markdown(f"<a href='https://wa.me/{str(r[0]).replace('+','')}{r[1]}' class='wa-btn'>💬 WhatsApp Rival</a>", unsafe_allow_html=True)
                        
                        # Sistema de Carga de Resultado
                        with st.expander("📸 Reportar Marcador"):
                            opcion = st.radio("Fuente:", ["Cámara", "Galería"], key=f"opt_{p['id']}", horizontal=True)
                            
                            if opcion == "Cámara":
                                foto = st.camera_input("Capturar", key=f"cam_{p['id']}")
                            else:
                                foto = st.file_uploader("Archivo", type=['png', 'jpg', 'jpeg'], key=f"gal_{p['id']}")
                            
                            if foto:
                                st.image(foto, width=150)
                                if st.button("🔍 Analizar y Enviar", key=f"btn_ia_{p['id']}"):
                                    with st.spinner("La IA está analizando la evidencia..."):
                                        # 1. Ejecutar el Cerebro IA
                                        res_ia, mensaje_ia = leer_marcador_ia(foto, p['local'], p['visitante'])
                                        
                                        if res_ia is None:
                                            st.error(mensaje_ia)
                                        else:
                                            gl_ia, gv_ia = res_ia
                                            es_local = (p['local'] == equipo_usuario)
                                            
                                            # 2. Feedback de Victoria/Derrota/Empate
                                            mis_goles = gl_ia if es_local else gv_ia
                                            sus_goles = gv_ia if es_local else gl_ia
                                            if mis_goles > sus_goles: 
                                                st.success(f"✅ ¡Resultado {gl_ia}-{gv_ia} a tu favor!")
                                            elif mis_goles < sus_goles: 
                                                st.warning(f"📉 Resultado {gl_ia}-{gv_ia} en contra.")
                                            else: 
                                                st.info(f"🤝 Empate {gl_ia}-{gv_ia}.")

                                            try:
                                                # 3. Subir a la Nube
                                                res_cloud = cloudinary.uploader.upload(foto, folder="gol_gana_evidencias")
                                                url_nueva = res_cloud['secure_url']
                                                col_foto = "url_foto_l" if es_local else "url_foto_v"

                                                with get_db_connection() as conn_up:
                                                    # 4. Lógica de Consenso / Conflicto
                                                    gl_existente = p['goles_l']
                                                    gv_existente = p['goles_v']

                                                    if gl_existente is not None:
                                                        # Si ya había un resultado y no coincide con la nueva foto
                                                        if int(gl_existente) != gl_ia or int(gv_existente) != gv_ia:
                                                            conn_up.execute(f"""UPDATE partidos SET 
                                                                             goles_l=NULL, goles_v=NULL, 
                                                                             conflicto=1, {col_foto}=?, 
                                                                             ia_goles_l=?, ia_goles_v=? 
                                                                             WHERE id=?""", (url_nueva, gl_ia, gv_ia, p['id']))
                                                            st.warning("⚠️ Conflicto detectado. El Admin resolverá.")
                                                        else:
                                                            # Si coincide, quitamos conflicto y guardamos la foto
                                                            conn_up.execute(f"UPDATE partidos SET {col_foto}=?, conflicto=0 WHERE id=?", (url_nueva, p['id']))
                                                            st.success("¡Confirmado por ambos equipos!")
                                                    else:
                                                        # Primer reporte del partido
                                                        conn_up.execute(f"""UPDATE partidos SET 
                                                                         goles_l=?, goles_v=?, 
                                                                         {col_foto}=?, ia_goles_l=?, 
                                                                         ia_goles_v=?, estado='Revision' 
                                                                         WHERE id=?""", (gl_ia, gv_ia, url_nueva, gl_ia, gv_ia, p['id']))
                                                        st.info("Resultado guardado. Esperando reporte del rival.")
                                                    
                                                    conn_up.commit()
                                                st.rerun()
                                            except Exception as e:
                                                st.error(f"Error técnico: {e}")

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















