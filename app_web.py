import streamlit as st
import sqlite3
import pandas as pd

# --- 1. CONFIGURACIÓN Y ESTILOS ---
DB_NAME = "gol_gana.db"
ADMIN_PIN = "2025" 

st.set_page_config(page_title="Gol-Gana", layout="centered")

# CSS para optimización móvil y tablas limpias
st.markdown("""
    <style>
    .stApp { max-width: 600px; margin: 0 auto; }
    .stButton > button { width: 100%; border-radius: 10px; }
    /* Estilo para cabecera de tabla manual */
    .header-tabla { font-weight: bold; background-color: #f0f2f6; padding: 5px; border-radius: 5px; font-size: 0.8rem; text-align: center; }
    .fila-tabla { padding: 8px 0; border-bottom: 1px solid #eee; text-align: center; font-size: 0.85rem; }
    .eq-name { text-align: left; font-weight: bold; color: #1f77b4; }
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

# --- 4. CABECERA Y NAVEGACIÓN SIEMPRE VISIBLE ---
st.title("⚽ Gol Gana")

col_nav1, col_nav2 = st.columns(2)
with col_nav1:
    if st.button("🔙 Volver al Inicio"):
        limpiar_acceso()
with col_nav2:
    if st.button("🔄 Refrescar"):
        st.rerun()

pin_input = st.text_input("🔑 PIN de Acceso", value=st.session_state.pin_usuario, type="password")
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
    tab1, tab2 = st.tabs(["📊 Clasificación", "📝 Inscribirse"])

    with tab1:
        cur = conn.cursor()
        cur.execute("SELECT nombre FROM equipos WHERE estado = 'aprobado'")
        equipos_db = cur.fetchall()
        
        if not equipos_db:
            st.info("Aún no hay equipos aprobados.")
        else:
            # Diccionario de estadísticas completo
            stats = {e[0]: {'PJ':0, 'Pts':0, 'GF':0, 'GC':0, 'DG':0} for e in equipos_db}
            
            # Cargar partidos
            df_p = pd.read_sql_query("SELECT * FROM historial", conn)
            for _, fila in df_p.iterrows():
                l, gl, gv, v = fila['local'], fila['goles_l'], fila['goles_v'], fila['visitante']
                if l in stats and v in stats:
                    stats[l]['PJ'] += 1; stats[v]['PJ'] += 1
                    stats[l]['GF'] += gl; stats[l]['GC'] += gv
                    stats[v]['GF'] += gv; stats[v]['GC'] += gl
                    if gl > gv: stats[l]['Pts'] += 3
                    elif gv > gl: stats[v]['Pts'] += 3
                    else: stats[l]['Pts'] += 1; stats[v]['Pts'] += 1

            # Procesar DataFrame
            df_final = pd.DataFrame.from_dict(stats, orient='index').reset_index()
            df_final.columns = ['EQ', 'PJ', 'PTS', 'GF', 'GC', 'DG']
            df_final['DG'] = df_final['GF'] - df_final['GC']
            df_final = df_final.sort_values(by=['PTS', 'DG', 'GF'], ascending=False)
            df_final.insert(0, 'POS', range(1, len(df_final) + 1))

            # --- RENDERIZADO DE TABLA PARA MÓVIL ---
            # Cabecera
            c_pos, c_eq, c_pts, c_pj, c_gf, c_gc, c_dg = st.columns([0.8, 2.5, 1, 1, 0.8, 0.8, 0.8])
            c_pos.markdown('<div class="header-tabla">POS</div>', unsafe_allow_html=True)
            c_eq.markdown('<div class="header-tabla">EQ</div>', unsafe_allow_html=True)
            c_pts.markdown('<div class="header-tabla">PTS</div>', unsafe_allow_html=True)
            c_pj.markdown('<div class="header-tabla">PJ</div>', unsafe_allow_html=True)
            c_gf.markdown('<div class="header-tabla">GF</div>', unsafe_allow_html=True)
            c_gc.markdown('<div class="header-tabla">GC</div>', unsafe_allow_html=True)
            c_dg.markdown('<div class="header-tabla">DG</div>', unsafe_allow_html=True)

            # Filas de datos (Sin enlaces de contacto para el espectador)
            for _, row in df_final.iterrows():
                r_pos, r_eq, r_pts, r_pj, r_gf, r_gc, r_dg = st.columns([0.8, 2.5, 1, 1, 0.8, 0.8, 0.8])
                r_pos.markdown(f'<div class="fila-tabla">{row["POS"]}</div>', unsafe_allow_html=True)
                r_eq.markdown(f'<div class="fila-tabla eq-name">{row["EQ"]}</div>', unsafe_allow_html=True)
                r_pts.markdown(f'<div class="fila-tabla"><b>{row["PTS"]}</b></div>', unsafe_allow_html=True)
                r_pj.markdown(f'<div class="fila-tabla">{row["PJ"]}</div>', unsafe_allow_html=True)
                r_gf.markdown(f'<div class="fila-tabla">{row["GF"]}</div>', unsafe_allow_html=True)
                r_gc.markdown(f'<div class="fila-tabla">{row["GC"]}</div>', unsafe_allow_html=True)
                r_dg.markdown(f'<div class="fila-tabla">{row["DG"]}</div>', unsafe_allow_html=True)

    with tab2:
        if st.session_state.registro_exitoso:
            st.success("✅ ¡Inscripción enviada! El Admin te aprobará pronto.")
            if st.button("Inscribir otro equipo"):
                st.session_state.registro_exitoso = False
                st.rerun()
        else:
            st.subheader("📩 Registro de Equipo")
            paises_data = {
                "Argentina": "+54", "Bolivia": "+591", "Brasil": "+55", "Canadá": "+1",
                "Chile": "+56", "Colombia": "+57", "Costa Rica": "+506", "Ecuador": "+593",
                "España": "+34", "Estados Unidos": "+1", "México": "+52", "Panamá": "+507",
                "Perú": "+51", "Uruguay": "+598", "Venezuela": "+58"
            }
            opciones_paises = [f"{p} ({pref})" for p, pref in paises_data.items()]

            if 'confirmado' not in st.session_state: st.session_state.confirmado = False

            if not st.session_state.confirmado:
                with st.form("registro_equipo"):
                    nom = st.text_input("Nombre del Equipo")
                    pais_sel = st.selectbox("País", opciones_paises)
                    tel = st.text_input("WhatsApp (Solo números)")
                    pin_nuevo = st.text_input("PIN (4 dígitos)", max_chars=4, type="password")
                    if st.form_submit_button("Revisar Registro"):
                        if nom and tel and len(pin_nuevo) == 4:
                            st.session_state.datos_temp = {"n": nom, "wa": tel, "pin": pin_nuevo, "pref": pais_sel.split('(')[-1].replace(')', '')}
                            st.session_state.confirmado = True
                            st.rerun()
                        else: st.error("Llene todos los campos correctamente.")
            else:
                d = st.session_state.datos_temp
                st.info(f"**¿Confirmas los datos?**\n\nEquipo: {d['n']}\n\nWhatsApp: {d['pref']} {d['wa']}\n\nPIN: `{d['pin']}`")
                col1, col2 = st.columns(2)
                if col1.button("✅ Confirmar"):
                    try:
                        cur = conn.cursor()
                        cur.execute("INSERT INTO equipos (nombre, celular, prefijo, pin) VALUES (?,?,?,?)", (d['n'], d['wa'], d['pref'], d['pin']))
                        conn.commit()
                        st.session_state.registro_exitoso = True
                        st.session_state.confirmado = False
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("❌ El nombre de equipo o el PIN ya están en uso.")
                if col2.button("✏️ Editar"):
                    st.session_state.confirmado = False
                    st.rerun()

# --- 6. VISTA: ADMIN ---
elif rol == "admin":
    st.header("👑 Panel de Administración")
    pendientes = pd.read_sql_query("SELECT nombre, celular, prefijo FROM equipos WHERE estado = 'pendiente'", conn)
    
    if not pendientes.empty:
        st.subheader("Solicitudes Pendientes")
        for _, r in pendientes.iterrows():
            with st.container():
                c1, c2, c3 = st.columns([1.5, 1.5, 1])
                c1.write(f"**{r['nombre']}**")
                numero_completo = f"{r['prefijo']} {r['celular']}"
                link_wa = f"https://wa.me/{r['prefijo'].replace('+','')}{r['celular']}"
                c2.markdown(f"[💬 {numero_completo}]({link_wa})", unsafe_allow_html=True)
                if c3.button("✅ Ok", key=f"ok_{r['nombre']}"):
                    conn.execute("UPDATE equipos SET estado = 'aprobado' WHERE nombre = ?", (r['nombre'],))
                    conn.commit()
                    st.rerun()
                st.divider()
    else:
        st.info("No hay equipos por aprobar.")

    with st.expander("Zona de Peligro"):
        if st.button("🚨 REINICIAR TODO EL TORNEO"):
            conn.execute("DELETE FROM historial"); conn.execute("DELETE FROM equipos")
            conn.commit()
            limpiar_acceso()

# --- 7. VISTA: DT ---
elif rol == "dt":
    st.header(f"🎮 Panel DT: {equipo_usuario}")
    st.write("Sube la foto del resultado de tu partido.")
    archivo = st.file_uploader("Captura de pantalla", type=['jpg', 'png'])
    if archivo:
        st.image(archivo, caption="Imagen cargada")
        if st.button("Procesar Resultado"):
            st.info("IA de lectura de marcadores lista para ser configurada.")
