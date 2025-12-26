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

st.title("⚽ Gol-Gana")

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
    tab1, tab2 = st.tabs(["📊 Tabla", "📝 Inscripción"])

    with tab1:
        cur = conn.cursor()
        cur.execute("SELECT nombre, prefijo, celular FROM equipos WHERE estado='aprobado'")
        oficiales = cur.fetchall()
        if oficiales:
            for nom, pref, cel in oficiales:
                st.info(f"⚽ {nom} | [WhatsApp](https://wa.me/{pref.replace('+','')}{cel})")
        else:
            st.write("No hay equipos aprobados.")

    with tab2:
        paises = {"Colombia": "+57", "México": "+52", "Ecuador": "+593", "Venezuela": "+58", "Argentina": "+54", "EEUU": "+1", "España": "+34"}
        
        if not st.session_state.confirmado:
            # FASE 1: DATOS
            with st.form("reg_form"):
                st.subheader("Registra tu equipo")
                n = st.text_input("Nombre del Equipo")
                p = st.selectbox("País", list(paises.keys()))
                w = st.text_input("WhatsApp (sin prefijo)")
                pin_n = st.text_input("PIN (4 números)", max_chars=4, type="password")
                
                if st.form_submit_button("Revisar"):
                    cur.execute("SELECT nombre FROM equipos WHERE pin=?", (pin_n,))
                    if pin_n == "2025" or cur.fetchone():
                        st.error("PIN ocupado.")
                    elif n and w and len(pin_n)==4:
                        st.session_state.datos_temp = {"nombre":n, "pref":paises[p], "wa":w, "pin":pin_n, "pais_nom":p}
                        st.session_state.confirmado = True
                        st.rerun()
                    else:
                        st.error("Llena todos los campos.")
        else:
            # FASE 2: CONFIRMACIÓN (FUERA DEL FORM PARA EVITAR ERRORES)
            d = st.session_state.datos_temp
            st.warning("⚠️ ¿Son correctos estos datos?")
            st.write(f"**Equipo:** {d['nombre']}")
            st.write(f"**WhatsApp:** {d['pref']} {d['wa']}")
            st.write(f"**PIN:** {d['pin']}")
            
            c1, c2 = st.columns(2)
            if c1.button("🚀 CONFIRMAR E INSCRIBIR"):
                conn.execute("INSERT INTO equipos (nombre, celular, prefijo, pin) VALUES (?,?,?,?)",
                             (d['nombre'], d['wa'], d['pref'], d['pin']))
                conn.commit()
                st.session_state.confirmado = False
                st.session_state.datos_temp = None
                st.success("¡Enviado al Admin!")
                st.rerun()
            if c2.button("✏️ EDITAR"):
                st.session_state.confirmado = False
                st.rerun()

# --- VISTA ADMIN ---
elif st.session_state.rol == "admin":
    st.header("🛠️ Panel Admin")
    cur = conn.cursor()
    cur.execute("SELECT nombre, prefijo, celular FROM equipos WHERE estado='pendiente'")
    pendientes = cur.fetchall()
    
    if not pendientes:
        st.info("No hay solicitudes.")
    else:
        for nom, pref, cel in pendientes:
            with st.container(border=True):
                col1, col2 = st.columns([3,1])
                col1.write(f"**{nom}** ({pref} {cel})")
                if col2.button("✅ Aceptar", key=f"ok_{nom}"):
                    conn.execute("UPDATE equipos SET estado='aprobado' WHERE nombre=?", (nom,))
                    conn.commit()
                    st.rerun()

    st.divider()
    if st.button("🚨 RESET TORNEO"):
        conn.execute("DELETE FROM equipos"); conn.commit()
        st.rerun()

# --- VISTA DT ---
elif st.session_state.rol == "dt":
    st.header(f"🎮 Panel DT: {st.session_state.equipo_usuario}")
    st.write("Aquí podrás subir tus fotos de resultados próximamente.")
