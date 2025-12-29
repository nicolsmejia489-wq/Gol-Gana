import streamlit as st
import sqlite3
import pandas as pd
import random

# --- 1. CONFIGURACIÓN ---
DB_NAME = "gol_gana.db"
ADMIN_PIN = "2025" 

st.set_page_config(page_title="Gol-Gana Pro", layout="centered")

# CSS para móvil y tablas
st.markdown("""
    <style>
    .stApp { max-width: 600px; margin: 0 auto; }
    .mobile-table { width: 100%; border-collapse: collapse; font-size: 11px; }
    .mobile-table th { background: #f0f2f6; padding: 5px; border-bottom: 2px solid #ddd; }
    .mobile-table td { padding: 8px 2px; text-align: center; border-bottom: 1px solid #eee; }
    .team-cell { text-align: left !important; font-weight: bold; color: #1f77b4; }
    .match-box { border: 1px solid #ddd; padding: 10px; border-radius: 10px; margin-bottom: 10px; background: #f9f9f9; }
    .wa-btn { color: #25D366; text-decoration: none; font-weight: bold; font-size: 14px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BASE DE DATOS ---
def inicializar_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Tabla Equipos
    cursor.execute('''CREATE TABLE IF NOT EXISTS equipos (
        nombre TEXT PRIMARY KEY, celular TEXT, prefijo TEXT, pin TEXT, estado TEXT DEFAULT 'pendiente'
    )''')
    # Tabla Partidos
    cursor.execute('''CREATE TABLE IF NOT EXISTS partidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, local TEXT, visitante TEXT, 
        goles_l INTEGER DEFAULT NULL, goles_v INTEGER DEFAULT NULL, estado TEXT DEFAULT 'programado'
    )''')
    # Tabla Configuración (Estado del torneo)
    cursor.execute('''CREATE TABLE IF NOT EXISTS config (llave TEXT PRIMARY KEY, valor TEXT)''')
    cursor.execute("INSERT OR IGNORE INTO config VALUES ('fase', 'inscripcion')")
    conn.commit()
    return conn

conn = inicializar_db()

# --- 3. LÓGICA DE TORNEO ---
def generar_calendario():
    # 1. Obtener equipos aprobados
    cur = conn.cursor()
    cur.execute("SELECT nombre FROM equipos WHERE estado = 'aprobado'")
    equipos = [row[0] for row in cur.fetchall()]
    
    # 2. Completar con (WO) hasta 32
    while len(equipos) < 32:
        nombre_wo = f"(WO) {len(equipos)+1}"
        conn.execute("INSERT OR IGNORE INTO equipos (nombre, estado) VALUES (?, 'aprobado')", (nombre_wo,))
        equipos.append(nombre_wo)
    
    random.shuffle(equipos)
    
    # 3. Algoritmo de 3 partidos sin repetir
    # Cada equipo i juega contra (i+1), (i+2) y (i+3) en la lista circular
    partidos_generados = []
    n = len(equipos)
    for i in range(n):
        for offset in [1, 2, 3]:
            rival_idx = (i + offset) % n
            # Ordenar nombres alfabéticamente para evitar duplicados A vs B y B vs A
            p = sorted([equipos[i], equipos[rival_idx]])
            if p not in partidos_generados:
                partidos_generados.append(p)
                conn.execute("INSERT INTO partidos (local, visitante) VALUES (?, ?)", (p[0], p[1]))
    
    conn.execute("UPDATE config SET valor = 'clasificacion' WHERE llave = 'fase'")
    conn.commit()

# --- 4. GESTIÓN DE SESIÓN ---
if "pin_usuario" not in st.session_state: st.session_state.pin_usuario = ""

def limpiar_acceso():
    st.session_state.pin_usuario = ""
    st.rerun()

# --- 5. INTERFAZ ---
st.title("⚽ Gol-Gana")

col_nav1, col_nav2 = st.columns(2)
with col_nav1:
    if st.button("🔙 Inicio"): limpiar_acceso()
with col_nav2:
    if st.button("🔄 Refrescar"): st.rerun()

pin_input = st.text_input("🔑 PIN de Acceso", value=st.session_state.pin_usuario, type="password")
st.session_state.pin_usuario = pin_input

# Definir Rol y Fase
cur = conn.cursor()
cur.execute("SELECT valor FROM config WHERE llave = 'fase'")
fase_actual = cur.fetchone()[0]

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

# --- 6. TABS SEGÚN EL ROL ---
if fase_actual == "inscripcion":
    tabs = st.tabs(["📊 Clasificación", "📝 Inscribirse"])
else:
    if rol == "dt":
        tabs = st.tabs(["📊 Clasificación", "📅 Calendario", "⚽ Mis Partidos"])
    else:
        tabs = st.tabs(["📊 Clasificación", "📅 Calendario"])

# TAB 1: CLASIFICACIÓN (Visible para todos siempre)
with tabs[0]:
    cur.execute("SELECT nombre FROM equipos WHERE estado = 'aprobado'")
    todos_eq = [e[0] for e in cur.fetchall()]
    
    if not todos_eq:
        st.info("Esperando equipos...")
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

        df_final = pd.DataFrame.from_dict(stats, orient='index').reset_index()
        df_final.columns = ['EQ', 'PJ', 'PTS', 'GF', 'GC', 'DG']
        df_final['DG'] = df_final['GF'] - df_final['GC']
        df_final = df_final.sort_values(by=['PTS', 'DG', 'GF'], ascending=False)
        df_final.insert(0, 'POS', range(1, len(df_final) + 1))

        # Renderizar Tabla Slim
        html = '<table class="mobile-table"><thead><tr><th>POS</th><th style="text-align:left">EQ</th><th>PTS</th><th>PJ</th><th>GF</th><th>GC</th><th>DG</th></tr></thead><tbody>'
        for _, r in df_final.iterrows():
            html += f"<tr><td>{r['POS']}</td><td class='team-cell'>{r['EQ']}</td><td><b>{r['PTS']}</b></td><td>{r['PJ']}</td><td>{r['GF']}</td><td>{r['GC']}</td><td>{r['DG']}</td></tr>"
        st.markdown(html + "</tbody></table>", unsafe_allow_html=True)

# LOGICA DE PESTAÑAS ADICIONALES
if fase_actual == "inscripcion":
    with tabs[1]:
        # (Aquí va el código de registro que ya teníamos, simplificado por espacio)
        st.subheader("📩 Registro de Equipo")
        if st.checkbox("Entiendo que al registrarme acepto las reglas"):
            with st.form("reg"):
                n = st.text_input("Nombre Equipo")
                p = st.text_input("WhatsApp (Sin +)")
                pin = st.text_input("PIN 4 dígitos", type="password", max_chars=4)
                if st.form_submit_button("Registrar"):
                    try:
                        conn.execute("INSERT INTO equipos (nombre, celular, prefijo, pin) VALUES (?,?,'+',?)", (n, p, pin))
                        conn.commit(); st.success("¡Registrado!")
                    except: st.error("Duplicado.")
else:
    with tabs[1]:
        st.subheader("📅 Calendario Completo")
        partidos_all = pd.read_sql_query("SELECT * FROM partidos", conn)
        for _, p in partidos_all.iterrows():
            res = f"{p['goles_l']} - {p['goles_v']}" if p['goles_l'] is not None else "vs"
            st.markdown(f"**{p['local']}** {res} **{p['visitante']}**")

    if rol == "dt":
        with tabs[2]:
            st.subheader(f"🏟️ Partidos de {equipo_usuario}")
            mis_p = pd.read_sql_query("SELECT * FROM partidos WHERE local = ? OR visitante = ?", conn, params=(equipo_usuario, equipo_usuario))
            
            for _, p in mis_p.iterrows():
                rival = p['visitante'] if p['local'] == equipo_usuario else p['local']
                with st.container():
                    st.markdown(f"<div class='match-box'>", unsafe_allow_html=True)
                    st.write(f"🆚 **Rival:** {rival}")
                    
                    # Link WhatsApp Rival
                    cur.execute("SELECT prefijo, celular FROM equipos WHERE nombre = ?", (rival,))
                    r_data = cur.fetchone()
                    if r_data and r_data[1]:
                        link = f"https://wa.me/{r_data[0].replace('+','')}{r_data[1]}"
                        st.markdown(f"<a href='{link}' class='wa-btn'>💬 Contactar Rival</a>", unsafe_allow_html=True)
                    
                    if p['goles_l'] is None:
                        st.button("📸 Subir Resultado", key=f"btn_{p['id']}")
                    else:
                        st.success(f"Resultado: {p['goles_l']} - {p['goles_v']}")
                    st.markdown("</div>", unsafe_allow_html=True)

# --- 7. PANEL ADMIN ---
if rol == "admin":
    st.divider()
    st.header("👑 Panel Master")
    
    if fase_actual == "inscripcion":
        pendientes = pd.read_sql_query("SELECT nombre FROM equipos WHERE estado = 'pendiente'", conn)
        st.write(f"Equipos inscritos: {len(pd.read_sql_query('SELECT * FROM equipos WHERE estado= \'aprobado\'', conn))}/32")
        
        for _, r in pendientes.iterrows():
            if st.button(f"Aprobar {r['nombre']}"):
                conn.execute("UPDATE equipos SET estado = 'aprobado' WHERE nombre = ?", (r['nombre'],))
                conn.commit(); st.rerun()
        
        if st.button("🚀 INICIAR TORNEO (Cerrar inscripciones)"):
            generar_calendario()
            st.rerun()
    else:
        st.warning("Torneo en curso: Fase Clasificación")
        if st.button("🚨 Reset Total"):
            conn.execute("DELETE FROM partidos"); conn.execute("DELETE FROM equipos")
            conn.execute("UPDATE config SET valor = 'inscripcion'")
            conn.commit(); st.rerun()
