import streamlit as st
import sqlite3
import pandas as pd
import random
from contextlib import contextmanager

# --- 1. CONFIGURACIÓN Y ESTILOS ---
DB_NAME = "gol_gana.db"
ADMIN_PIN = "2025" 

st.set_page_config(page_title="Gol-Gana Pro", layout="centered")

st.markdown("""
    <style>
    .stApp { max-width: 600px; margin: 0 auto; }
    .mobile-table { width: 100%; border-collapse: collapse; font-size: 11px; }
    .mobile-table th { background: #f0f2f6; padding: 5px; border-bottom: 2px solid #ddd; }
    .mobile-table td { padding: 8px 2px; text-align: center; border-bottom: 1px solid #eee; }
    .team-cell { text-align: left !important; font-weight: bold; color: #1f77b4; }
    .match-box { border: 1px solid #ddd; padding: 12px; border-radius: 10px; margin-bottom: 10px; background: #fff; }
    .wa-btn { display: inline-block; background-color: #25D366; color: white !important; padding: 5px 10px; border-radius: 5px; text-decoration: none; font-weight: bold; font-size: 12px; }
    .jornada-header { background: #1f77b4; color: white; padding: 5px 10px; border-radius: 5px; margin-top: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. GESTIÓN DE BASE DE DATOS ---
@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False, timeout=15)
    try:
        yield conn
    finally:
        conn.close()

def inicializar_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS equipos (
            nombre TEXT PRIMARY KEY, celular TEXT, prefijo TEXT, pin TEXT, estado TEXT DEFAULT 'pendiente'
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS partidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, local TEXT, visitante TEXT, 
            goles_l INTEGER DEFAULT NULL, goles_v INTEGER DEFAULT NULL, 
            estado TEXT DEFAULT 'programado', jornada INTEGER
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS config (llave TEXT PRIMARY KEY, valor TEXT)''')
        cursor.execute("INSERT OR IGNORE INTO config (llave, valor) VALUES ('fase', 'inscripcion')")
        conn.commit()

inicializar_db()

# --- 3. LÓGICA DE TORNEO (3 JORNADAS EXACTAS) ---
def generar_calendario():
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT nombre FROM equipos WHERE estado = 'aprobado'")
        equipos = [row[0] for row in cur.fetchall()]
        
        # Rellenar con WO hasta 32 para asegurar pares
        while len(equipos) < 32:
            nombre_wo = f"(WO) {len(equipos)+1}"
            conn.execute("INSERT OR IGNORE INTO equipos (nombre, estado) VALUES (?, 'aprobado')", (nombre_wo,))
            equipos.append(nombre_wo)
        
        random.shuffle(equipos)
        n = len(equipos)
        
        # Algoritmo de círculo para 3 jornadas (Cada equipo juega 1 vez por jornada)
        for j in range(1, 4):
            for i in range(n // 2):
                loc = equipos[i]
                vis = equipos[n - 1 - i]
                conn.execute("INSERT INTO partidos (local, visitante, jornada) VALUES (?, ?, ?)", (loc, vis, j))
            # Rotar equipos excepto el primero
            equipos = [equipos[0]] + [equipos[-1]] + equipos[1:-1]
        
        conn.execute("UPDATE config SET valor = 'clasificacion' WHERE llave = 'fase'")
        conn.commit()

# --- 4. NAVEGACIÓN Y ROLES ---
if "reg_estado" not in st.session_state: st.session_state.reg_estado = "formulario"
if "pin_usuario" not in st.session_state: st.session_state.pin_usuario = ""

st.title("⚽ Gol-Gana")
col_nav1, col_nav2 = st.columns(2)
with col_nav1:
    if st.button("🔙 Inicio"):
        st.session_state.reg_estado = "formulario"; st.session_state.pin_usuario = ""; st.rerun()
with col_nav2:
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
        if res:
            rol = "dt"; equipo_usuario = res[0]

# --- 5. VISTAS POR PESTAÑAS ---
if fase_actual == "inscripcion":
    tabs = st.tabs(["📊 Clasificación", "📝 Inscribirse"])
else:
    # Calendario ahora es visible para TODOS
    titulos_tabs = ["📊 Clasificación", "📅 Calendario"]
    if rol == "dt": titulos_tabs.append("⚽ Mis Partidos")
    tabs = st.tabs(titulos_tabs)

# TAB: CLASIFICACIÓN
with tabs[0]:
    with get_db_connection() as conn:
        df_eq = pd.read_sql_query("SELECT nombre FROM equipos WHERE estado = 'aprobado'", conn)
        if df_eq.empty:
            st.info("No hay equipos aprobados.")
        else:
            todos_eq = df_eq['nombre'].tolist()
            stats = {e: {'PJ':0, 'PTS':0, 'GF':0, 'GC':0, 'DG':0} for e in todos_eq}
            df_p = pd.read_sql_query("SELECT * FROM partidos WHERE goles_l IS NOT NULL", conn)
            for _, f in df_p.iterrows():
                l, v, gl, gv = f['local'], f['visitante'], f['goles_l'], f['goles_v']
                if l in stats and v in stats:
                    stats[l]['PJ'] += 1; stats[v]['PJ'] += 1
                    stats[l]['GF'] += gl; stats[l]['GC'] += gv
                    stats[v]['GF'] += gv; stats[v]['GC'] += gl
                    if gl > gv: stats[l]['PTS'] += 3
                    elif gv > gl: stats[v]['PTS'] += 3
                    else: stats[l]['PTS'] += 1; stats[v]['PTS'] += 1
            df_f = pd.DataFrame.from_dict(stats, orient='index').reset_index()
            df_f.columns = ['EQ', 'PJ', 'PTS', 'GF', 'GC', 'DG']
            df_f['DG'] = df_f['GF'] - df_f['GC']
            df_f = df_f.sort_values(by=['PTS', 'DG', 'GF'], ascending=False).reset_index(drop=True)
            df_f.insert(0, 'POS', range(1, len(df_f) + 1))
            html = '<table class="mobile-table"><thead><tr><th>POS</th><th style="text-align:left">EQ</th><th>PTS</th><th>PJ</th><th>GF</th><th>GC</th><th>DG</th></tr></thead><tbody>'
            for _, r in df_f.iterrows():
                html += f"<tr><td>{r['POS']}</td><td class='team-cell'>{r['EQ']}</td><td><b>{r['PTS']}</b></td><td>{r['PJ']}</td><td>{r['GF']}</td><td>{r['GC']}</td><td>{r['DG']}</td></tr>"
            st.markdown(html + "</tbody></table>", unsafe_allow_html=True)

# TAB: REGISTRO (Solo en inscripcion)
if fase_actual == "inscripcion":
    with tabs[1]:
        if st.session_state.reg_estado == "exito":
            st.success("✅ ¡Inscripción recibida!")
            if st.button("Nuevo Registro"): st.session_state.reg_estado = "formulario"; st.rerun()
        elif st.session_state.reg_estado == "confirmar":
            d = st.session_state.datos_temp
            st.warning("⚠️ **Confirma los datos:**")
            st.write(f"**Equipo:** {d['n']}\n**WhatsApp:** {d['pref']} {d['wa']}\n**PIN:** {d['pin']}")
            if st.button("✅ Confirmar"):
                with get_db_connection() as conn:
                    try:
                        conn.execute("INSERT INTO equipos (nombre, celular, prefijo, pin) VALUES (?,?,?,?)", (d['n'], d['wa'], d['pref'], d['pin']))
                        conn.commit(); st.session_state.reg_estado = "exito"; st.rerun()
                    except: st.error("Error al guardar.")
            if st.button("✏️ Editar"): st.session_state.reg_estado = "formulario"; st.rerun()
        else:
            with st.form("reg_form"):
                nom = st.text_input("Nombre Equipo").strip()
                paises = {"Colombia": "+57", "México": "+52", "España": "+34", "Argentina": "+54"}
                pais_sel = st.selectbox("País", [f"{p} ({pref})" for p, pref in paises.items()])
                tel = st.text_input("WhatsApp").strip()
                pin_r = st.text_input("PIN (4 dígitos)", max_chars=4, type="password").strip()
                if st.form_submit_button("Siguiente"):
                    if not nom or not tel or len(pin_r) < 4: st.error("Faltan datos.")
                    else:
                        with get_db_connection() as conn:
                            cur = conn.cursor()
                            cur.execute("SELECT 'x' FROM equipos WHERE nombre=? OR pin=? OR celular=?", (nom, pin_r, tel))
                            if cur.fetchone(): st.error("Nombre, PIN o Teléfono ya registrados.")
                            else:
                                st.session_state.datos_temp = {"n": nom, "wa": tel, "pin": pin_r, "pref": pais_sel.split('(')[-1].replace(')', '')}
                                st.session_state.reg_estado = "confirmar"; st.rerun()

# TAB: CALENDARIO (Visible para todos por jornadas)
elif fase_actual == "clasificacion":
    with tabs[1]:
        st.header("📅 Calendario de Clasificación")
        with get_db_connection() as conn:
            for j in range(1, 4):
                st.markdown(f"<div class='jornada-header'>Jornada {j}</div>", unsafe_allow_html=True)
                df_j = pd.read_sql_query("SELECT * FROM partidos WHERE jornada=?", conn, params=(j,))
                for _, p in df_j.iterrows():
                    res = f"{p['goles_l']} - {p['goles_v']}" if p['goles_l'] is not None else "vs"
                    st.write(f" {p['local']} **{res}** {p['visitante']}")

    if rol == "dt":
        with tabs[2]:
            st.subheader(f"🏟️ Mis Partidos: {equipo_usuario}")
            with get_db_connection() as conn:
                mis = pd.read_sql_query("SELECT * FROM partidos WHERE local=? OR visitante=?", conn, params=(equipo_usuario, equipo_usuario))
                for _, p in mis.iterrows():
                    rival = p['visitante'] if p['local'] == equipo_usuario else p['local']
                    st.markdown(f"<div class='match-box'><b>Jornada {p['jornada']}</b><br>Rival: {rival}", unsafe_allow_html=True)
                    cur = conn.cursor()
                    cur.execute("SELECT prefijo, celular FROM equipos WHERE nombre=?", (rival,))
                    r_info = cur.fetchone()
                    if r_info and r_info[0] and r_info[1]:
                        st.markdown(f"<a href='https://wa.me/{str(r_info[0]).replace('+','')}{r_info[1]}' class='wa-btn'>💬 WhatsApp</a>", unsafe_allow_html=True)
                    st.button("📸 Subir Resultado", key=f"cam_{p['id']}")
                    st.markdown("</div>", unsafe_allow_html=True)

# PANEL ADMIN
if rol == "admin":
    st.divider()
    if fase_actual == "inscripcion":
        with get_db_connection() as conn:
            pendientes = pd.read_sql_query("SELECT * FROM equipos WHERE estado='pendiente'", conn)
            st.write(f"Pendientes: {len(pendientes)}")
            for _, r in pendientes.iterrows():
                if st.button(f"Aprobar {r['nombre']}"):
                    conn.execute("UPDATE equipos SET estado='aprobado' WHERE nombre=?", (r['nombre'],))
                    conn.commit(); st.rerun()
            if st.button("🚀 INICIAR TORNEO (3 Jornadas)"): generar_calendario(); st.rerun()
    
    if st.button("🚨 REINICIAR TODO"):
        with get_db_connection() as conn:
            conn.execute("DROP TABLE IF EXISTS equipos")
            conn.execute("DROP TABLE IF EXISTS partidos")
            conn.execute("UPDATE config SET valor='inscripcion'")
            conn.commit(); st.rerun()
