import streamlit as st
import sqlite3
import pandas as pd
import random
from contextlib import contextmanager

# --- 1. CONFIGURACIÓN Y ESTÉTICA (Mantenida) ---
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
    }
    .mobile-table { 
        width: 100%; border-collapse: collapse; font-size: 12px; 
        background-color: white !important; color: black !important;
        border: 1px solid #ddd;
    }
    .mobile-table th { background: #f0f2f6 !important; color: black !important; padding: 8px; border: 1px solid #ddd; }
    .mobile-table td { padding: 8px; text-align: center; border: 1px solid #eee; color: black !important; }
    .team-cell { text-align: left !important; font-weight: bold; color: #1f77b4 !important; }
    .match-box { 
        border: 1px solid #ccc; padding: 15px; border-radius: 10px; 
        margin-bottom: 15px; background: #ffffff !important; color: black !important;
    }
    .wa-btn { 
        display: inline-block; background-color: #25D366; color: white !important; 
        padding: 5px 10px; border-radius: 5px; text-decoration: none; font-weight: bold; font-size: 12px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. GESTIÓN DE BASE DE DATOS ---
@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False, timeout=20)
    try: yield conn
    finally: conn.close()

def inicializar_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS equipos (
            nombre TEXT PRIMARY KEY, celular TEXT, prefijo TEXT, pin TEXT, estado TEXT DEFAULT 'pendiente'
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS partidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, local TEXT, visitante TEXT, 
            goles_l INTEGER DEFAULT NULL, goles_v INTEGER DEFAULT NULL, 
            jornada INTEGER, estado TEXT DEFAULT 'programado'
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS config (llave TEXT PRIMARY KEY, valor TEXT)''')
        cursor.execute("INSERT OR IGNORE INTO config (llave, valor) VALUES ('fase', 'inscripcion')")
        conn.commit()

inicializar_db()

# --- 3. LÓGICA DE JORNADAS ---
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

# --- 4. NAVEGACIÓN Y ROLES ---
if "pin_usuario" not in st.session_state: st.session_state.pin_usuario = ""
if "reg_estado" not in st.session_state: st.session_state.reg_estado = "formulario"

st.title("⚽ Gol-Gana")
pin_input = st.text_input("🔑 PIN de Acceso", value=st.session_state.pin_usuario, type="password")
st.session_state.pin_usuario = pin_input

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

with get_db_connection() as conn:
    cur = conn.cursor()
    cur.execute("SELECT valor FROM config WHERE llave = 'fase'")
    fase_actual = cur.fetchone()[0]

# --- 5. DEFINICIÓN DE PESTAÑAS (DINÁMICAS) ---
if fase_actual == "inscripcion":
    tabs = st.tabs(["📊 Clasificación", "📝 Inscribirse"])
else:
    titulos_tabs = ["📊 Clasificación", "📅 Calendario"]
    if rol == "dt": titulos_tabs.append("⚽ Mis Partidos")
    if rol == "admin": titulos_tabs.append("⚙️ Gestión Admin")
    tabs = st.tabs(titulos_tabs)

# TAB 0: CLASIFICACIÓN (Mantenida)
with tabs[0]:
    with get_db_connection() as conn:
        df_eq = pd.read_sql_query("SELECT nombre FROM equipos WHERE estado = 'aprobado'", conn)
        if not df_eq.empty:
            stats = {e: {'PJ':0, 'PTS':0, 'GF':0, 'GC':0} for e in df_eq['nombre']}
            df_p = pd.read_sql_query("SELECT * FROM partidos WHERE goles_l IS NOT NULL", conn)
            for _, f in df_p.iterrows():
                l, v, gl, gv = f['local'], f['visitante'], f['goles_l'], f['goles_v']
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
            html = '<table class="mobile-table"><thead><tr><th>POS</th><th>EQ</th><th>PTS</th><th>PJ</th><th>GF</th><th>GC</th><th>DG</th></tr></thead><tbody>'
            for _, r in df_f.iterrows():
                html += f"<tr><td>{r['POS']}</td><td class='team-cell'>{r['EQ']}</td><td><b>{r['PTS']}</b></td><td>{r['PJ']}</td><td>{r['GF']}</td><td>{r['GC']}</td><td>{r['DG']}</td></tr>"
            st.markdown(html + "</tbody></table>", unsafe_allow_html=True)

# TAB 1: CALENDARIO / INSCRIPCIÓN
if fase_actual == "inscripcion":
    with tabs[1]:
        # (Lógica de inscripción mantenida de la versión anterior...)
        st.info("Formulario de inscripción activo...")
        # Aquí va tu bloque de st.session_state.reg_estado (formulario/confirmar/exito)
else:
    with tabs[1]:
        with get_db_connection() as conn:
            df_p = pd.read_sql_query("SELECT * FROM partidos ORDER BY jornada ASC", conn)
        j_tabs = st.tabs(["Jornada 1", "Jornada 2", "Jornada 3"])
        for i, jt in enumerate(j_tabs):
            with jt:
                df_j = df_p[df_p['jornada'] == (i + 1)]
                for _, p in df_j.iterrows():
                    res = f"{p['goles_l']} - {p['goles_v']}" if p['goles_l'] is not None else "vs"
                    st.markdown(f"<div class='match-box' style='text-align:center'><b>{p['local']}</b> {res} <b>{p['visitante']}</b></div>", unsafe_allow_html=True)

# TAB ESPECIAL: GESTIÓN ADMIN (Solo para Admin)
if rol == "admin" and fase_actual == "clasificacion":
    with tabs[2]:
        st.subheader("🛠️ Panel de Control de Partidos")
        j_admin = st.radio("Seleccionar Jornada", [1, 2, 3], horizontal=True)
        
        with get_db_connection() as conn:
            partidos_admin = pd.read_sql_query("SELECT * FROM partidos WHERE jornada = ?", conn, params=(j_admin,))
            
            for _, p in partidos_admin.iterrows():
                with st.expander(f"⚽ {p['local']} vs {p['visitante']}"):
                    c1, c2, c3 = st.columns([1, 1, 1])
                    with c1: g_l = st.number_input(f"Goles {p['local']}", value=p['goles_l'] if p['goles_l'] is not None else 0, key=f"l_{p['id']}")
                    with c2: g_v = st.number_input(f"Goles {p['visitante']}", value=p['goles_v'] if p['goles_v'] is not None else 0, key=f"v_{p['id']}")
                    with c3:
                        st.write("Contacto DTs")
                        # Botones de WhatsApp para ambos equipos
                        for equipo in [p['local'], p['visitante']]:
                            cur = conn.cursor()
                            cur.execute("SELECT prefijo, celular FROM equipos WHERE nombre=?", (equipo,))
                            r = cur.fetchone()
                            if r and r[1]:
                                st.markdown(f"<a href='https://wa.me/{str(r[0]).replace('+','')}{r[1]}' class='wa-btn'>💬 WA {equipo}</a>", unsafe_allow_html=True)

                    if st.button(f"Guardar Resultado #{p['id']}", key=f"btn_{p['id']}"):
                        conn.execute("UPDATE partidos SET goles_l=?, goles_v=?, estado='finalizado' WHERE id=?", (g_l, g_v, p['id']))
                        conn.commit()
                        st.success("Resultado actualizado")
                        st.rerun()

# (Mantenemos el botón de Reiniciar al final para el admin)
if rol == "admin":
    st.divider()
    if st.button("🚨 REINICIAR TORNEO"):
        with get_db_connection() as conn:
            conn.execute("DROP TABLE IF EXISTS equipos"); conn.execute("DROP TABLE IF EXISTS partidos")
            conn.execute("UPDATE config SET valor='inscripcion'"); conn.commit()
        st.rerun()
