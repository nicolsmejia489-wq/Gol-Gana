import streamlit as st
import sqlite3
import pandas as pd

# --- 1. CONFIGURACIÓN Y ESTILOS ---
DB_NAME = "gol_gana.db"
ADMIN_PIN = "2025" 

st.set_page_config(page_title="Gol-Gana", layout="centered")

# CSS para forzar una tabla compacta y estética en móviles
st.markdown("""
    <style>
    .stApp { max-width: 600px; margin: 0 auto; }
    .stButton > button { width: 100%; border-radius: 10px; height: 35px; font-size: 14px; }
    
    /* Estilos para la Tabla Compacta */
    .mobile-table {
        width: 100%;
        border-collapse: collapse;
        font-family: sans-serif;
        font-size: 11px;
    }
    .mobile-table th {
        background-color: #f0f2f6;
        color: #31333F;
        text-align: center;
        padding: 5px 2px;
        border-bottom: 2px solid #ddd;
    }
    .mobile-table td {
        padding: 8px 2px;
        text-align: center;
        border-bottom: 1px solid #eee;
    }
    .team-cell {
        text-align: left !important;
        font-weight: bold;
        color: #1f77b4;
        max-width: 85px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .pts-cell { font-weight: bold; color: #000; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BASE DE DATOS ---
def inicializar_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS equipos (
        nombre TEXT PRIMARY KEY, celular TEXT, prefijo TEXT, pin TEXT, estado TEXT DEFAULT 'pendiente'
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS historial (
        id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, local TEXT, goles_l INTEGER, goles_v INTEGER, visitante TEXT
    )''')
    conn.commit()
    return conn

conn = inicializar_db()

# --- 3. GESTIÓN DE NAVEGACIÓN Y ESTADOS ---
if "pin_usuario" not in st.session_state:
    st.session_state.pin_usuario = ""
if "registro_exitoso" not in st.session_state:
    st.session_state.registro_exitoso = False
if "confirmado" not in st.session_state:
    st.session_state.confirmado = False

def limpiar_acceso():
    st.session_state.pin_usuario = ""
    st.session_state.registro_exitoso = False
    st.session_state.confirmado = False
    st.rerun()

# --- 4. CABECERA Y BOTONES FIJOS ---
st.title("⚽ Gol-Gana")

col_nav1, col_nav2 = st.columns(2)
with col_nav1:
    if st.button("🔙 Inicio"):
        limpiar_acceso()
with col_nav2:
    if st.button("🔄 Refrescar"):
        st.rerun()

pin_input = st.text_input("🔑 PIN de Acceso", value=st.session_state.pin_usuario, type="password", placeholder="DTs o Admin")
st.session_state.pin_usuario = pin_input

# Lógica de Roles
rol = "espectador"
equipo_usuario = None

if st.session_state.pin_usuario == ADMIN_PIN:
    rol = "admin"
elif st.session_state.pin_usuario != "":
    cur = conn.cursor()
    cur.execute("SELECT nombre FROM equipos WHERE pin = ? AND estado = 'aprobado'", (st.session_state.pin_usuario,))
    res = cur.fetchone()
    if res:
        rol = "dt"
        equipo_usuario = res[0]

# --- 5. VISTA: ESPECTADOR ---
if rol == "espectador":
    tab1, tab2 = st.tabs(["📊 Tabla", "📝 Registro"])

    with tab1:
        cur = conn.cursor()
        cur.execute("SELECT nombre FROM equipos WHERE estado = 'aprobado'")
        equipos_db = cur.fetchall()
        
        if not equipos_db:
            st.info("Esperando equipos aprobados...")
        else:
            stats = {e[0]: {'PJ':0, 'PTS':0, 'GF':0, 'GC':0, 'DG':0} for e in equipos_db}
            df_p = pd.read_sql_query("SELECT * FROM historial", conn)
            for _, fila in df_p.iterrows():
                l, gl, gv, v = fila['local'], fila['goles_l'], fila['goles_v'], fila['visitante']
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

            html_tabla = """
            <table class="mobile-table">
                <thead><tr><th>POS</th><th style="text-align:left">EQ</th><th>PTS</th><th>PJ</th><th>GF</th><th>GC</th><th>DG</th></tr></thead>
                <tbody>
            """
            for _, row in df_final.iterrows():
                html_tabla += f"<tr><td>{row['POS']}</td><td class='team-cell'>{row['EQ']}</td><td class='pts-cell'>{row['PTS']}</td><td>{row['PJ']}</td><td>{row['GF']}</td><td>{row['GC']}</td><td>{row['DG']}</td></tr>"
            html_tabla += "</tbody></table>"
            st.markdown(html_tabla, unsafe_allow_html=True)

    with tab2:
        if st.session_state.registro_exitoso:
            st.success("✅ ¡Inscripción enviada! El Admin te aprobará pronto.")
            if st.button("Inscribir otro equipo"):
                st.session_state.registro_exitoso = False
                st.rerun()
        elif st.session_state.confirmado:
            # PANTALLA DE CONFIRMACIÓN
            d = st.session_state.datos_temp
            st.warning("⚠️ **Verifica tus datos antes de enviar:**")
            st.write(f"**Equipo:** {d['n']}")
            st.write(f"**WhatsApp:** {d['pref']} {d['wa']}")
            st.write(f"**PIN:** `{d['pin']}`")
            
            c1, c2 = st.columns(2)
            if c1.button("✅ Confirmar"):
                try:
                    conn.execute("INSERT INTO equipos (nombre, celular, prefijo, pin) VALUES (?,?,?,?)", (d['n'], d['wa'], d['pref'], d['pin']))
                    conn.commit()
                    st.session_state.registro_exitoso = True
                    st.session_state.confirmado = False
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("❌ El nombre o el PIN ya están en uso.")
                    st.session_state.confirmado = False
            if c2.button("✏️ Editar"):
                st.session_state.confirmado = False
                st.rerun()
        else:
            # FORMULARIO INICIAL
            with st.form("registro_equipo"):
                nom = st.text_input("Nombre del Equipo")
                paises = {"Argentina": "+54", "Bolivia": "+591", "Brasil": "+55", "Canadá": "+1", "Chile": "+56", "Colombia": "+57", "Costa Rica": "+506", "Ecuador": "+593", "EEUU": "+1", "España": "+34", "México": "+52", "Panamá": "+507", "Perú": "+51", "Uruguay": "+598", "Venezuela": "+58"}
                pais_sel = st.selectbox("País", [f"{p} ({pref})" for p, pref in paises.items()])
                tel = st.text_input("WhatsApp (Solo números)")
                pin_n = st.text_input("PIN (4 dígitos)", max_chars=4, type="password")
                
                if st.form_submit_button("Revisar Datos"):
                    if nom and tel and len(pin_n) == 4:
                        st.session_state.datos_temp = {"n": nom, "wa": tel, "pin": pin_n, "pref": pais_sel.split('(')[-1].replace(')', '')}
                        st.session_state.confirmado = True
                        st.rerun()
                    else:
                        st.error("Por favor, completa todos los campos correctamente.")

# --- 6. VISTA: ADMIN ---
elif rol == "admin":
    st.header("👑 Panel Admin")
    pendientes = pd.read_sql_query("SELECT nombre, celular, prefijo FROM equipos WHERE estado = 'pendiente'", conn)
    
    if not pendientes.empty:
        for _, r in pendientes.iterrows():
            with st.container():
                c1, c2, c3 = st.columns([1.5, 1.5, 1])
                c1.write(f"**{r['nombre']}**")
                num_full = f"{r['prefijo']} {r['celular']}"
                link_wa = f"https://wa.me/{r['prefijo'].replace('+','')}{r['celular']}"
                c2.markdown(f"[💬 {num_full}]({link_wa})")
                if c3.button("✅", key=f"ok_{r['nombre']}"):
                    conn.execute("UPDATE equipos SET estado = 'aprobado' WHERE nombre = ?", (r['nombre'],))
                    conn.commit(); st.rerun()
                st.divider()
    else:
        st.info("No hay solicitudes pendientes.")

    with st.expander("Configuración Avanzada"):
        if st.button("🚨 REINICIAR TORNEO"):
            conn.execute("DELETE FROM historial"); conn.execute("DELETE FROM equipos"); conn.commit()
            limpiar_acceso()

# --- 7. VISTA: DT ---
elif rol == "dt":
    st.header(f"🎮 DT: {equipo_usuario}")
    archivo = st.file_uploader("Sube el resultado del partido", type=['jpg', 'png'])
    if archivo:
        st.image(archivo)
        if st.button("Procesar con IA"):
            st.info("Estamos listos para configurar el lector automático de resultados.")
