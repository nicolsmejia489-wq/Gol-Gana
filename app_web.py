import streamlit as st
import sqlite3
import pandas as pd
import random

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

# --- 2. BASE DE DATOS ROBUSTA ---
def inicializar_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    cursor = conn.cursor()
    # Crear tablas una por una con commits intermedios
    cursor.execute('''CREATE TABLE IF NOT EXISTS equipos (
        nombre TEXT PRIMARY KEY, celular TEXT, prefijo TEXT, pin TEXT, estado TEXT DEFAULT 'pendiente'
    )''')
    conn.commit()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS partidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, local TEXT, visitante TEXT, 
        goles_l INTEGER DEFAULT NULL, goles_v INTEGER DEFAULT NULL, estado TEXT DEFAULT 'programado'
    )''')
    conn.commit()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS config (llave TEXT PRIMARY KEY, valor TEXT)''')
    conn.commit()
    
    # Asegurar valor inicial de fase
    cursor.execute("INSERT OR IGNORE INTO config (llave, valor) VALUES ('fase', 'inscripcion')")
    conn.commit()
    return conn

try:
    conn = inicializar_db()
except Exception as e:
    st.error(f"Error crítico de base de datos. Por favor, reinicia la app. Detalle: {e}")
    st.stop()

# --- 3. LÓGICA DE TORNEO ---
def generar_calendario():
    cur = conn.cursor()
    cur.execute("SELECT nombre FROM equipos WHERE estado = 'aprobado'")
    equipos = [row[0] for row in cur.fetchall()]
    
    while len(equipos) < 32:
        nombre_wo = f"(WO) {len(equipos)+1}"
        conn.execute("INSERT OR IGNORE INTO equipos (nombre, estado) VALUES (?, 'aprobado')", (nombre_wo,))
        equipos.append(nombre_wo)
    
    random.shuffle(equipos)
    n = len(equipos)
    partidos_generados = set()
    
    for i in range(n):
        for offset in [1, 2, 3]:
            rival_idx = (i + offset) % n
            p = tuple(sorted([equipos[i], equipos[rival_idx]]))
            if p not in partidos_generados:
                partidos_generados.add(p)
                conn.execute("INSERT INTO partidos (local, visitante) VALUES (?, ?)", (p[0], p[1]))
    
    conn.execute("UPDATE config SET valor = 'clasificacion' WHERE llave = 'fase'")
    conn.commit()

# --- 4. GESTIÓN DE NAVEGACIÓN ---
if "pin_usuario" not in st.session_state: st.session_state.pin_usuario = ""
if "reg_estado" not in st.session_state: st.session_state.reg_estado = "formulario" # formulario, confirmar, exito

def limpiar_acceso():
    st.session_state.pin_usuario = ""
    st.session_state.reg_estado = "formulario"
    st.rerun()

# --- 5. CABECERA ---
st.title("⚽ Gol-Gana")
col_nav1, col_nav2 = st.columns(2)
with col_nav1:
    if st.button("🔙 Inicio"): limpiar_acceso()
with col_nav2:
    if st.button("🔄 Refrescar"): st.rerun()

pin_input = st.text_input("🔑 PIN de Acceso", value=st.session_state.pin_usuario, type="password")
st.session_state.pin_usuario = pin_input

# Obtener Fase Actual
cur = conn.cursor()
cur.execute("SELECT valor FROM config WHERE llave = 'fase'")
fase_actual = cur.fetchone()[0]

# Roles
rol = "espectador"
equipo_usuario = None
if st.session_state.pin_usuario == ADMIN_PIN:
    rol = "admin"
elif st.session_state.pin_usuario != "":
    cur.execute("SELECT nombre FROM equipos WHERE pin = ? AND estado = 'aprobado'", (st.session_state.pin_usuario,))
    res = cur.fetchone()
    if res:
        rol = "dt"
        equipo_usuario = res[0]

# --- 6. PESTAÑAS ---
if fase_actual == "inscripcion":
    tabs = st.tabs(["📊 Clasificación", "📝 Inscribirse"])
else:
    tabs = st.tabs(["📊 Clasificación", "📅 Calendario", "⚽ Mis Partidos"]) if rol == "dt" else st.tabs(["📊 Clasificación", "📅 Calendario"])

# TAB 1: CLASIFICACIÓN
with tabs[0]:
    cur.execute("SELECT nombre FROM equipos WHERE estado = 'aprobado'")
    todos_eq = [e[0] for e in cur.fetchall()]
    if not todos_eq:
        st.info("Esperando equipos aprobados...")
    else:
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

# TAB 2: REGISTRO (Corregido)
if fase_actual == "inscripcion":
    with tabs[1]:
        if st.session_state.reg_estado == "exito":
            st.success("✅ ¡Inscripción enviada!")
            if st.button("Inscribir otro"):
                st.session_state.reg_estado = "formulario"
                st.rerun()
        
        elif st.session_state.reg_estado == "confirmar":
            d = st.session_state.datos_temp
            st.warning("⚠️ **Confirma tus datos:**")
            st.write(f"**Equipo:** {d['n']}\n\n**WhatsApp:** {d['pref']} {d['wa']}\n\n**PIN:** {d['pin']}")
            c1, c2 = st.columns(2)
            if c1.button("✅ Confirmar"):
                try:
                    conn.execute("INSERT INTO equipos (nombre, celular, prefijo, pin) VALUES (?,?,?,?)", (d['n'], d['wa'], d['pref'], d['pin']))
                    conn.commit()
                    st.session_state.reg_estado = "exito"
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("❌ El nombre de equipo ya existe.")
                    st.session_state.reg_estado = "formulario"
            if c2.button("✏️ Editar"):
                st.session_state.reg_estado = "formulario"
                st.rerun()
        
        else:
            with st.form("form_reg"):
                nom = st.text_input("Nombre del Equipo")
                paises = {"Colombia": "+57", "México": "+52", "España": "+34", "Argentina": "+54", "EEUU": "+1", "Chile": "+56", "Ecuador": "+593", "Perú": "+51", "Venezuela": "+58"}
                pais_sel = st.selectbox("País", [f"{p} ({pref})" for p, pref in paises.items()])
                tel = st.text_input("WhatsApp (Sin prefijo)")
                pin_n = st.text_input("PIN (4 dígitos)", max_chars=4, type="password")
                if st.form_submit_button("Revisar"):
                    # Validar PIN duplicado
                    cur.execute("SELECT nombre FROM equipos WHERE pin = ?", (pin_n,))
                    if cur.fetchone(): st.error("❌ PIN ya en uso.")
                    elif nom and tel and len(pin_n) == 4:
                        st.session_state.datos_temp = {"n": nom, "wa": tel, "pin": pin_n, "pref": pais_sel.split('(')[-1].replace(')', '')}
                        st.session_state.reg_estado = "confirmar"
                        st.rerun()
                    else: st.error("Completa todo correctamente.")

# TABS POST-INSCRIPCIÓN
elif fase_actual == "clasificacion":
    with tabs[1]:
        st.subheader("📅 Calendario")
        partidos = pd.read_sql_query("SELECT * FROM partidos", conn)
        for _, p in partidos.iterrows():
            res = f"{p['goles_l']} - {p['goles_v']}" if p['goles_l'] is not None else "vs"
            st.write(f"**{p['local']}** {res} **{p['visitante']}**")

    if rol == "dt":
        with tabs[2]:
            st.subheader(f"🏟️ Mis Partidos: {equipo_usuario}")
            mis = pd.read_sql_query("SELECT * FROM partidos WHERE local=? OR visitante=?", conn, params=(equipo_usuario, equipo_usuario))
            for _, p in mis.iterrows():
                rival = p['visitante'] if p['local'] == equipo_usuario else p['local']
                with st.container():
                    st.markdown(f"<div class='match-box'><b>Rival: {rival}</b>", unsafe_allow_html=True)
                    cur.execute("SELECT prefijo, celular FROM equipos WHERE nombre=?", (rival,))
                    rd = cur.fetchone()
                    if rd and rd[1]:
                        st.markdown(f"<a href='https://wa.me/{rd[0].replace('+','')}{rd[1]}' class='wa-btn'>💬 WhatsApp Rival</a>", unsafe_allow_html=True)
                    if p['goles_l'] is None: st.button("📸 Subir Resultado", key=f"r_{p['id']}")
                    else: st.success(f"Final: {p['goles_l']} - {p['goles_v']}")
                    st.markdown("</div>", unsafe_allow_html=True)

# --- 7. PANEL ADMIN ---
if rol == "admin":
    st.divider()
    if fase_actual == "inscripcion":
        pend = pd.read_sql_query("SELECT nombre, prefijo, celular FROM equipos WHERE estado='pendiente'", conn)
        aprob = pd.read_sql_query("SELECT * FROM equipos WHERE estado='aprobado'", conn)
        st.write(f"**Aprobados:** {len(aprob)}/32")
        for _, r in pend.iterrows():
            if st.button(f"✅ Aprobar {r['nombre']}"):
                conn.execute("UPDATE equipos SET estado='aprobado' WHERE nombre=?", (r['nombre'],))
                conn.commit(); st.rerun()
        if st.button("🚀 INICIAR TORNEO"): generar_calendario(); st.rerun()
    else:
        if st.button("🚨 RESET TOTAL"):
            conn.execute("DROP TABLE IF EXISTS partidos"); conn.execute("DROP TABLE IF EXISTS equipos")
            conn.execute("UPDATE config SET valor='inscripcion'"); conn.commit(); limpiar_acceso()
