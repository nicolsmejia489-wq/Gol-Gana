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
    .team-cell { text-align: left !important; font-weight: bold; color: #1f77b4; max-width: 90px; overflow: hidden; text-overflow: ellipsis; }
    .match-box { border: 1px solid #ddd; padding: 12px; border-radius: 10px; margin-bottom: 10px; background: #fff; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .wa-btn { display: inline-block; background-color: #25D366; color: white !important; padding: 5px 10px; border-radius: 5px; text-decoration: none; font-weight: bold; font-size: 12px; margin-top: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BASE DE DATOS ---
def inicializar_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS equipos (
        nombre TEXT PRIMARY KEY, celular TEXT, prefijo TEXT, pin TEXT, estado TEXT DEFAULT 'pendiente'
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS partidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, local TEXT, visitante TEXT, 
        goles_l INTEGER DEFAULT NULL, goles_v INTEGER DEFAULT NULL, estado TEXT DEFAULT 'programado'
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS config (llave TEXT PRIMARY KEY, valor TEXT)''')
    cursor.execute("INSERT OR IGNORE INTO config VALUES ('fase', 'inscripcion')")
    conn.commit()
    return conn

conn = inicializar_db()

# --- 3. LÓGICA DE CALENDARIO ---
def generar_calendario():
    cur = conn.cursor()
    cur.execute("SELECT nombre FROM equipos WHERE estado = 'aprobado'")
    equipos = [row[0] for row in cur.fetchall()]
    
    while len(equipos) < 32:
        nombre_wo = f"(WO) {len(equipos)+1}"
        conn.execute("INSERT OR IGNORE INTO equipos (nombre, estado) VALUES (?, 'aprobado')", (nombre_wo,))
        equipos.append(nombre_wo)
    
    random.shuffle(equipos)
    partidos_generados = []
    n = len(equipos)
    for i in range(n):
        for offset in [1, 2, 3]:
            rival_idx = (i + offset) % n
            p = sorted([equipos[i], equipos[rival_idx]])
            if p not in partidos_generados:
                partidos_generados.append(p)
                conn.execute("INSERT INTO partidos (local, visitante) VALUES (?, ?)", (p[0], p[1]))
    
    conn.execute("UPDATE config SET valor = 'clasificacion' WHERE llave = 'fase'")
    conn.commit()

# --- 4. GESTIÓN DE ESTADOS ---
if "pin_usuario" not in st.session_state: st.session_state.pin_usuario = ""
if "reg_confirmar" not in st.session_state: st.session_state.reg_confirmar = False
if "reg_exito" not in st.session_state: st.session_state.reg_exito = False

def limpiar_acceso():
    st.session_state.pin_usuario = ""
    st.session_state.reg_confirmar = False
    st.session_state.reg_exito = False
    st.rerun()

# --- 5. NAVEGACIÓN ---
st.title("⚽ Gol-Gana")
col_nav1, col_nav2 = st.columns(2)
with col_nav1:
    if st.button("🔙 Inicio"): limpiar_acceso()
with col_nav2:
    if st.button("🔄 Refrescar"): st.rerun()

pin_input = st.text_input("🔑 PIN de Acceso", value=st.session_state.pin_usuario, type="password")
st.session_state.pin_usuario = pin_input

# Definir Roles
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

# --- 6. VISTAS POR PESTAÑAS ---
if fase_actual == "inscripcion":
    tabs = st.tabs(["📊 Clasificación", "📝 Inscribirse"])
else:
    tabs = st.tabs(["📊 Clasificación", "📅 Calendario", "⚽ Mis Partidos"]) if rol == "dt" else st.tabs(["📊 Clasificación", "📅 Calendario"])

# TAB: CLASIFICACIÓN (Siempre visible)
with tabs[0]:
    cur.execute("SELECT nombre FROM equipos WHERE estado = 'aprobado'")
    todos_eq = [e[0] for e in cur.fetchall()]
    
    if not todos_eq:
        st.info("Esperando que el Admin apruebe los primeros equipos...")
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

        html = '<table class="mobile-table"><thead><tr><th>POS</th><th style="text-align:left">EQ</th><th>PTS</th><th>PJ</th><th>GF</th><th>GC</th><th>DG</th></tr></thead><tbody>'
        for _, r in df_final.iterrows():
            html += f"<tr><td>{r['POS']}</td><td class='team-cell'>{r['EQ']}</td><td><b>{r['PTS']}</b></td><td>{r['PJ']}</td><td>{r['GF']}</td><td>{r['GC']}</td><td>{r['DG']}</td></tr>"
        st.markdown(html + "</tbody></table>", unsafe_allow_html=True)

# TAB: REGISTRO (Solo en fase de inscripción)
if fase_actual == "inscripcion":
    with tabs[1]:
        if st.session_state.reg_exito:
            st.success("✅ ¡Inscripción recibida! El Admin verificará tus datos pronto.")
            if st.button("Inscribir otro equipo"):
                st.session_state.reg_exito = False
                st.rerun()
        
        elif st.session_state.reg_confirmar:
            d = st.session_state.datos_temp
            st.warning("⚠️ **Confirma tus datos antes de enviar:**")
            st.write(f"**Equipo:** {d['n']}")
            st.write(f"**WhatsApp:** {d['pref']} {d['wa']}")
            st.write(f"**PIN:** `{d['pin']}`")
            
            c1, c2 = st.columns(2)
            if c1.button("✅ Confirmar Envío"):
                try:
                    conn.execute("INSERT INTO equipos (nombre, celular, prefijo, pin) VALUES (?,?,?,?)", (d['n'], d['wa'], d['pref'], d['pin']))
                    conn.commit()
                    st.session_state.reg_exito = True
                    st.session_state.reg_confirmar = False
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("❌ Error: El nombre de equipo ya existe.")
                    st.session_state.reg_confirmar = False
            if c2.button("✏️ Editar"):
                st.session_state.reg_confirmar = False
                st.rerun()
        
        else:
            st.subheader("📩 Registro de Equipo")
            with st.form("form_registro"):
                nom = st.text_input("Nombre del Equipo")
                paises = {"Colombia": "+57", "México": "+52", "España": "+34", "Argentina": "+54", "EEUU": "+1", "Chile": "+56", "Ecuador": "+593", "Perú": "+51", "Venezuela": "+58", "Panamá": "+507"}
                pais_sel = st.selectbox("País (WhatsApp)", [f"{p} ({pref})" for p, pref in paises.items()])
                tel = st.text_input("Número de WhatsApp (Sin prefijo)")
                pin_n = st.text_input("PIN de 4 dígitos", max_chars=4, type="password")
                
                if st.form_submit_button("Revisar Registro"):
                    # Validación de PIN duplicado antes de pasar a confirmación
                    cur.execute("SELECT nombre FROM equipos WHERE pin = ?", (pin_n,))
                    if cur.fetchone():
                        st.error("❌ Este PIN ya está siendo usado por otro equipo.")
                    elif nom and tel and len(pin_n) == 4:
                        st.session_state.datos_temp = {"n": nom, "wa": tel, "pin": pin_n, "pref": pais_sel.split('(')[-1].replace(')', '')}
                        st.session_state.reg_confirmar = True
                        st.rerun()
                    else:
                        st.error("Completa todos los campos (PIN debe ser de 4 dígitos).")

# TABS DE TORNEO (Calendario y Mis Partidos)
elif fase_actual == "clasificacion":
    with tabs[1]:
        st.subheader("📅 Calendario Clasificatorio")
        df_all = pd.read_sql_query("SELECT * FROM partidos", conn)
        for _, p in df_all.iterrows():
            res = f"{p['goles_l']} - {p['goles_v']}" if p['goles_l'] is not None else "vs"
            st.write(f"**{p['local']}** {res} **{p['visitante']}**")

    if rol == "dt":
        with tabs[2]:
            st.subheader(f"🏟️ Mis Partidos: {equipo_usuario}")
            mis_p = pd.read_sql_query("SELECT * FROM partidos WHERE local = ? OR visitante = ?", conn, params=(equipo_usuario, equipo_usuario))
            for _, p in mis_p.iterrows():
                rival = p['visitante'] if p['local'] == equipo_usuario else p['local']
                with st.container():
                    st.markdown(f"<div class='match-box'>", unsafe_allow_html=True)
                    st.write(f"🆚 **Contra:** {rival}")
                    
                    # WhatsApp del Rival
                    cur.execute("SELECT prefijo, celular FROM equipos WHERE nombre = ?", (rival,))
                    r_data = cur.fetchone()
                    if r_data and r_data[1]:
                        link = f"https://wa.me/{r_data[0].replace('+','')}{r_data[1]}"
                        st.markdown(f"<a href='{link}' class='wa-btn'>💬 WhatsApp del Rival</a>", unsafe_allow_html=True)
                    
                    if p['goles_l'] is None:
                        st.button(f"📸 Subir Resultado", key=f"btn_{p['id']}")
                    else:
                        st.success(f"Marcador Final: {p['goles_l']} - {p['goles_v']}")
                    st.markdown("</div>", unsafe_allow_html=True)

# --- 7. PANEL ADMIN ---
if rol == "admin":
    st.divider()
    st.header("👑 Administración")
    
    if fase_actual == "inscripcion":
        pendientes = pd.read_sql_query("SELECT nombre, prefijo, celular FROM equipos WHERE estado = 'pendiente'", conn)
        aprobados = pd.read_sql_query("SELECT * FROM equipos WHERE estado = 'aprobado'", conn)
        
        st.write(f"**Estado:** {len(aprobados)}/32 equipos listos.")
        
        if not pendientes.empty:
            st.subheader("Solicitudes:")
            for _, r in pendientes.iterrows():
                c1, c2, c3 = st.columns([1,1,1])
                c1.write(r['nombre'])
                c2.write(f"{r['prefijo']}{r['celular']}")
                if c3.button("✅ Ok", key=f"adm_{r['nombre']}"):
                    conn.execute("UPDATE equipos SET estado = 'aprobado' WHERE nombre = ?", (r['nombre'],))
                    conn.commit(); st.rerun()
        
        if st.button("🚀 CERRAR INSCRIPCIONES E INICIAR"):
            generar_calendario()
            st.rerun()
    else:
        st.info("Torneo en Fase de Clasificación")
        if st.button("🚨 RESET TOTAL (Borra todo)"):
            conn.execute("DELETE FROM partidos"); conn.execute("DELETE FROM equipos"); conn.execute("UPDATE config SET valor = 'inscripcion'")
            conn.commit(); limpiar_acceso()
