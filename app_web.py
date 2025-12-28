import streamlit as st
import sqlite3
import pandas as pd

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Gol-Gana", layout="centered", page_icon="⚽")

def get_connection():
    return sqlite3.connect("gol_gana.db", check_same_thread=False)

# --- INICIALIZACIÓN DE DB ---
conn = get_connection()
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS equipos (
    nombre TEXT PRIMARY KEY, celular TEXT, prefijo TEXT, pin TEXT, estado TEXT DEFAULT 'pendiente'
)''')
conn.commit()

# --- ESTADOS DE SESIÓN ---
if 'rol' not in st.session_state: st.session_state.rol = "espectador"
if 'confirmado' not in st.session_state: st.session_state.confirmado = False
if 'datos_temp' not in st.session_state: st.session_state.datos_temp = None

# --- BOTÓN ATRÁS UNIVERSAL ---
if st.session_state.rol != "espectador" or st.session_state.confirmado:
    if st.button("⬅️ Volver / Cancelar"):
        st.session_state.confirmado = False
        st.session_state.rol = "espectador"
        st.session_state.datos_temp = None
        st.rerun()

st.title("⚽ Gol Gana")

# --- BLOQUE DE LOGIN ---
if st.session_state.rol == "espectador" and not st.session_state.confirmado:
    with st.expander("🔑 Acceso DT / Admin"):
        with st.form("login"):
            pin_in = st.text_input("PIN", type="password")
            if st.form_submit_button("Entrar"):
                if pin_in == "2025":
                    st.session_state.rol = "admin"
                    st.rerun()
                else:
                    cur = conn.cursor()
                    cur.execute("SELECT nombre FROM equipos WHERE pin=? AND estado='aprobado'", (pin_in,))
                    res = cur.fetchone()
                    if res:
                        st.session_state.rol = "dt"; st.session_state.equipo_usuario = res[0]
                        st.rerun()
                    else:
                        st.error("PIN no válido o equipo pendiente.")

# --- VISTA ESPECTADOR ---
if st.session_state.rol == "espectador":
    tab1, tab2 = st.tabs(["📊 Tabla de Posiciones", "📝 Inscripción"])

    with tab1:
        st.subheader("🏆 Posiciones")
        
        cur = conn.cursor()
        cur.execute("SELECT nombre FROM equipos WHERE estado='aprobado'")
        equipos_db = cur.fetchall()
        
        if not equipos_db:
            st.info("Aún no hay equipos oficiales.")
        else:
            # 1. Preparar datos
            stats = []
            for (nom,) in equipos_db:
                stats.append({"EQ": nom, "J": 0, "Pts": 0, "GF": 0, "GC": 0, "DG": 0})
            
            df = pd.DataFrame(stats)
            
            # 2. Crear la tabla en formato HTML (Compacto para móvil)
            tabla_html = """
            <style>
                .tabla-movil { width: 100%; border-collapse: collapse; font-size: 13px; font-family: sans-serif; }
                .tabla-movil th { background-color: #f0f2f6; border-bottom: 2px solid #ccc; padding: 8px 4px; text-align: left; }
                .tabla-movil td { border-bottom: 1px solid #eee; padding: 10px 4px; }
                .pos { font-weight: bold; color: #1f77b4; width: 20px; }
                .equipo { font-weight: bold; }
                .pts { background-color: #e1f5fe; font-weight: bold; text-align: center; }
                .num { text-align: center; }
            </style>
            <table class="tabla-movil">
                <tr>
                    <th class="pos">#</th>
                    <th>EQ</th>
                    <th class="num">J</th>
                    <th class="pts">Pts</th>
                    <th class="num">GF</th>
                    <th class="num">GC</th>
                    <th class="num">DG</th>
                </tr>
            """
            for i, fila in enumerate(df.values):
                tabla_html += f"<tr><td class='pos'>{i+1}</td><td class='equipo'>{fila[0]}</td><td class='num'>{fila[1]}</td><td class='pts'>{fila[2]}</td><td class='num'>{fila[3]}</td><td class='num'>{fila[4]}</td><td class='num'>{fila[5]}</td></tr>"
            tabla_html += "</table>"
            
            st.markdown(tabla_html, unsafe_allow_html=True)
            st.caption("J: Jugados | Pts: Puntos | DG: Diferencia Goles")

    with tab2:
        # Aquí recuperamos tu lógica de inscripción intacta
        paises = {"Colombia": "+57", "México": "+52", "Ecuador": "+593", "Venezuela": "+58", "Argentina": "+54", "EEUU": "+1", "España": "+34"}
        
        if not st.session_state.confirmado:
            with st.form("reg_form"):
                st.subheader("Registra tu equipo")
                n = st.text_input("Nombre del Equipo")
                p = st.selectbox("País", list(paises.keys()))
                w = st.text_input("WhatsApp (sin prefijo)")
                pin_n = st.text_input("PIN (4 caracteres para acceder como DT)", max_chars=4, type="password")
                
                if st.form_submit_button("Inscribir mi equipo"):
                    cur.execute("SELECT nombre FROM equipos WHERE pin=?", (pin_n,))
                    if pin_n == "2025" or cur.fetchone():
                        st.error("PIN ocupado.")
                    elif n and w and len(pin_n)==4:
                        st.session_state.datos_temp = {"nombre":n, "pref":paises[p], "wa":w, "pin":pin_n, "pais_nom":p}
                        st.session_state.confirmado = True
                        st.rerun()
                    else:
                        st.error("Llena todos los campos correctamente.")
        else:
            d = st.session_state.datos_temp
            st.warning("⚠️ ¿Son correctos estos datos?")
            st.write(f"**Equipo:** {d['nombre']} | **WA:** {d['pref']} {d['wa']}")
            
            c1, c2 = st.columns(2)
            if c1.button("🚀 CONFIRMAR"):
                conn.execute("INSERT INTO equipos (nombre, celular, prefijo, pin) VALUES (?,?,?,?)", (d['nombre'], d['wa'], d['pref'], d['pin']))
                conn.commit()
                st.session_state.confirmado = False
                st.session_state.datos_temp = None
                st.success("¡Enviado!")
                st.rerun()
            if c2.button("✏️ EDITAR"):
                st.session_state.confirmado = False
                st.rerun()
# --- VISTA ADMIN ---
# --- VISTA ADMIN ---
elif rol == "admin":
    st.header("👑 Panel Admin")
    
    # 1. Consultar equipos pendientes
    pendientes = pd.read_sql_query("SELECT nombre, celular, prefijo FROM equipos WHERE estado = 'pendiente'", conn)
    
    if not pendientes.empty:
        st.subheader("Solicitudes nuevas")
        st.write("Toca el número para contactar al DT antes de aprobar:")
        
        # 2. Crear filas interactivas para cada solicitud
        for _, r in pendientes.iterrows():
            with st.container():
                col_info, col_wa, col_accion = st.columns([2, 1, 1])
                
                # Nombre del equipo
                col_info.write(f"**{r['nombre']}**")
                
                # Link de WhatsApp con el número y prefijo
                link_wa = f"https://wa.me/{r['prefijo'].replace('+', '')}{r['celular']}"
                col_wa.markdown(f"[💬 Chatear]({link_wa})", unsafe_allow_html=True)
                
                # Botón rápido para aprobar en la misma fila
                if col_accion.button("✅ Aprobar", key=f"btn_{r['nombre']}"):
                    conn.execute("UPDATE equipos SET estado = 'aprobado' WHERE nombre = ?", (r['nombre'],))
                    conn.commit()
                    st.success(f"¡{r['nombre']} aprobado!")
                    st.rerun()
                st.divider()
    else:
        st.info("No hay equipos pendientes de aprobación.")

    # Sección de Reset (opcional mantenerla aquí o en sidebar)
    with st.expander("Danger Zone"):
        if st.button("🚨 RESET TOTAL DEL TORNEO"):
            conn.execute("DELETE FROM historial")
            conn.execute("DELETE FROM equipos")
            conn.commit()
            st.rerun()

# --- VISTA DT ---
elif st.session_state.rol == "dt":
    st.header(f"🎮 Panel DT: {st.session_state.equipo_usuario}")
    st.write("Aquí podrás subir tus fotos de resultados próximamente.")




