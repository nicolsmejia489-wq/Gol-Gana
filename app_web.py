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
        cursor.execute('''CREATE TABLE IF NOT EXISTS partidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, local TEXT, visitante TEXT, 
            goles_l INTEGER DEFAULT NULL, goles_v INTEGER DEFAULT NULL, 
            jornada INTEGER, estado TEXT DEFAULT 'programado'
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS config (llave TEXT PRIMARY KEY, valor TEXT)''')
        cursor.execute("INSERT OR IGNORE INTO config (llave, valor) VALUES ('fase', 'inscripcion')")
        conn.commit()

inicializar_db()

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

st.title("⚽ Gol-Gana")
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
    if rol == "dt": tabs = st.tabs(["📊 Clasificación", "📅 Calendario", "⚽ Mis Partidos"])
    else: tabs = st.tabs(["📊 Clasificación", "📅 Calendario"])

# TAB: CLASIFICACIÓN
with tabs[0]:
    with get_db_connection() as conn:
        df_eq = pd.read_sql_query("SELECT nombre FROM equipos WHERE estado = 'aprobado'", conn)
        if df_eq.empty: st.info("No hay equipos todavía.")
        else:
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
                paises = {"Colombia": "+57", "México": "+52", "España": "+34"}
                pais_sel = st.selectbox("País", [f"{k} ({v})" for k,v in paises.items()])
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

# CALENDARIO Y MIS PARTIDOS (Mantenidos igual)
if fase_actual == "clasificacion":
    with tabs[1]:
        st.subheader("📅 Calendario Oficial")
        with get_db_connection() as conn:
            df_p = pd.read_sql_query("SELECT * FROM partidos ORDER BY jornada ASC", conn)
        j_tabs = st.tabs(["Jornada 1", "Jornada 2", "Jornada 3"])
        for i, jt in enumerate(j_tabs):
            with jt:
                df_j = df_p[df_p['jornada'] == (i + 1)]
                for _, p in df_j.iterrows():
                    res = f"{p['goles_l']} - {p['goles_v']}" if p['goles_l'] is not None else "vs"
                    st.write(f"**{p['local']}** {res} **{p['visitante']}**")

    if rol == "dt":
        with tabs[2]:
            st.subheader(f"🏟️ Mis Partidos: {equipo_usuario}")
            with get_db_connection() as conn:
                mis = pd.read_sql_query("SELECT * FROM partidos WHERE (local=? OR visitante=?) ORDER BY jornada ASC", conn, params=(equipo_usuario, equipo_usuario))
                for _, p in mis.iterrows():
                    rival = p['visitante'] if p['local'] == equipo_usuario else p['local']
                    with st.container():
                        st.markdown(f"<div class='match-box'><b>Jornada {p['jornada']}</b><br>Rival: {rival}", unsafe_allow_html=True)
                        cur = conn.cursor()
                        cur.execute("SELECT prefijo, celular FROM equipos WHERE nombre=?", (rival,))
                        r = cur.fetchone()
                        if r and r[0] and r[1] and str(r[1]).isdigit():
                            st.markdown(f"<a href='https://wa.me/{str(r[0]).replace('+','')}{r[1]}' class='wa-btn'>💬 WhatsApp</a>", unsafe_allow_html=True)
                        else: st.caption("🚫 Sin contacto (WO)")
                        st.button("📸 Subir Resultado", key=f"cam_{p['id']}")
                        st.markdown("</div>", unsafe_allow_html=True)

# ADMIN
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
