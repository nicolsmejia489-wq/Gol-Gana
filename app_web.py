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
        font-size: 11px; /* Letra pequeña para móvil */
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
        max-width: 80px;
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

# --- 3. GESTIÓN DE NAVEGACIÓN ---
if "pin_usuario" not in st.session_state:
    st.session_state.pin_usuario = ""
if "registro_exitoso" not in st.session_state:
    st.session_state.registro_exitoso = False

def limpiar_acceso():
    st.session_state.pin_usuario = ""
    st.session_state.registro_exitoso = False
    st.rerun()

# --- 4. CABECERA Y NAVEGACIÓN ---
st.title("⚽ Gol-Gana")

col_nav1, col_nav2 = st.columns(2)
with col_nav1:
    if st.button("🔙 Inicio"):
        limpiar_acceso()
with col_nav2:
    if st.button("🔄 Refrescar"):
        st.rerun()

pin_input = st.text_input("🔑 PIN", value=st.session_state.pin_usuario, type="password", placeholder="Acceso DT/Admin")
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

            # --- CONSTRUCCIÓN DE TABLA HTML COMPACTA ---
            html_tabla = """
            <table class="mobile-table">
                <thead>
                    <tr>
                        <th>POS</th>
                        <th style="text-align:left">EQ</th>
                        <th>PTS</th>
                        <th>PJ</th>
                        <th>GF</th>
                        <th>GC</th>
                        <th>DG</th>
                    </tr>
                </thead>
                <tbody>
            """
            for _, row in df_final.iterrows():
                html_tabla += f"""
                <tr>
                    <td>{row['POS']}</td>
                    <td class="team-cell">{row['EQ']}</td>
                    <td class="pts-cell">{row['PTS']}</td>
                    <td>{row['PJ']}</td>
                    <td>{row['GF']}</td>
                    <td>{row['GC']}</td>
                    <td>{row['DG']}</td>
                </tr>
                """
            html_tabla += "</tbody></table>"
            st.markdown(html_tabla, unsafe_allow_html=True)

    with tab2:
        if st.session_state.registro_exitoso:
            st.success("✅ ¡Enviado! Espera aprobación.")
            if st.button("Inscribir otro"):
                st.session_state.registro_exitoso = False
                st.rerun()
        else:
            with st.form("reg_equipo"):
                nom = st.text_input("Nombre Equipo")
                paises = {"Colombia": "+57", "México": "+52", "EEUU": "+1", "España": "+34", "Argentina": "+54", "Venezuela": "+58", "Chile": "+56", "Ecuador": "+593", "Perú": "+51"}
                pais_sel = st.selectbox("País", [f"{p} ({pref})" for p, pref in paises.items()])
                tel = st.text_input("WhatsApp")
                pin_n = st.text_input("PIN (4 dígitos)", max_chars=4, type="password")
                
                if st.form_submit_button("Siguiente"):
                    if nom and tel and len(pin_n) == 4:
                        st.session_state.datos_temp = {"n": nom, "wa": tel, "pin": pin_n, "pref": pais_sel.split('(')[-1].replace(')', '')}
                        st.session_state.confirmado = True
                    else: st.error("Completa todo.")

            if st.get("confirmado", False): # Lógica simple de confirmación
                d = st.session_state.datos_temp
                st.warning(f"¿Confirmas: {d['n']} ({d['pref']} {d['wa']})?")
                if st.button("✅ SÍ, REGISTRAR"):
                    try:
                        conn.execute("INSERT INTO equipos (nombre, celular, prefijo, pin) VALUES (?,?,?,?)", (d['n'], d['wa'], d['pref'], d['pin']))
                        conn.commit()
                        st.session_state.registro_exitoso = True
                        st.rerun()
                    except: st.error("Error: Nombre o PIN duplicado.")

# --- 6. VISTA: ADMIN ---
elif rol == "admin":
    st.header("👑 Admin")
    pendientes = pd.read_sql_query("SELECT nombre, celular, prefijo FROM equipos WHERE estado = 'pendiente'", conn)
    if not pendientes.empty:
        for _, r in pendientes.iterrows():
            with st.container():
                c1, c2, c3 = st.columns([1.5, 1.5, 1])
                c1.write(f"**{r['nombre']}**")
                link_wa = f"https://wa.me/{r['prefijo'].replace('+','')}{r['celular']}"
                c2.markdown(f"[💬 {r['prefijo']}{r['celular']}]({link_wa})")
                if c3.button("✅", key=f"ok_{r['nombre']}"):
                    conn.execute("UPDATE equipos SET estado = 'aprobado' WHERE nombre = ?", (r['nombre'],))
                    conn.commit(); st.rerun()
                st.divider()
    else: st.info("Sin pendientes.")
    if st.button("🚨 RESET TOTAL"):
        conn.execute("DELETE FROM historial"); conn.execute("DELETE FROM equipos"); conn.commit(); limpiar_acceso()

# --- 7. VISTA: DT ---
elif rol == "dt":
    st.header(f"🎮 DT: {equipo_usuario}")
    archivo = st.file_uploader("Captura de pantalla", type=['jpg', 'png'])
    if archivo:
        st.image(archivo)
        if st.button("Procesar con IA"):
            st.info("Lógica de IA lista para conectar.")
