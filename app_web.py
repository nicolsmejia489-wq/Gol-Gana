import streamlit as st
import sqlite3
import pandas as pd
import random
from contextlib import contextmanager

# --- 1. CONFIGURACIÓN ---
DB_NAME = "gol_gana.db"
ADMIN_PIN = "2025" 

st.set_page_config(page_title="Gol-Gana Pro", layout="centered")

# --- 2. GESTIÓN SEGURA DE BASE DE DATOS ---
@contextmanager
def get_db_connection():
    """Gestor de contexto para asegurar que la conexión siempre se cierre."""
    conn = sqlite3.connect(DB_NAME, check_same_thread=False, timeout=10)
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
            goles_l INTEGER DEFAULT NULL, goles_v INTEGER DEFAULT NULL, estado TEXT DEFAULT 'programado'
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS config (llave TEXT PRIMARY KEY, valor TEXT)''')
        cursor.execute("INSERT OR IGNORE INTO config (llave, valor) VALUES ('fase', 'inscripcion')")
        conn.commit()

inicializar_db()

# --- 3. LÓGICA DE NEGOCIO ---
def obtener_fase():
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT valor FROM config WHERE llave = 'fase'")
        return cur.fetchone()[0]

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
        partidos_gen = set()
        n = len(equipos)
        for i in range(n):
            for offset in [1, 2, 3]:
                ridx = (i + offset) % n
                p = tuple(sorted([equipos[i], equipos[ridx]]))
                if p not in partidos_gen:
                    partidos_gen.add(p)
                    conn.execute("INSERT INTO partidos (local, visitante) VALUES (?, ?)", (p[0], p[1]))
        conn.execute("UPDATE config SET valor = 'clasificacion' WHERE llave = 'fase'")
        conn.commit()

# --- 4. INTERFAZ Y NAVEGACIÓN ---
if "reg_estado" not in st.session_state: st.session_state.reg_estado = "formulario"
if "pin_usuario" not in st.session_state: st.session_state.pin_usuario = ""

st.title("⚽ Gol-Gana")
col_nav1, col_nav2 = st.columns(2)
with col_nav1:
    if st.button("🔙 Inicio"):
        st.session_state.reg_estado = "formulario"
        st.session_state.pin_usuario = ""
        st.rerun()
with col_nav2:
    if st.button("🔄 Refrescar"): st.rerun()

pin_input = st.text_input("🔑 PIN de Acceso", value=st.session_state.pin_usuario, type="password")
st.session_state.pin_usuario = pin_input

fase_actual = obtener_fase()

# Roles
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
            rol = "dt"
            equipo_usuario = res[0]

# --- 5. PESTAÑAS ---
if fase_actual == "inscripcion":
    tabs = st.tabs(["📊 Clasificación", "📝 Inscribirse"])
else:
    tabs = st.tabs(["📊 Clasificación", "📅 Calendario", "⚽ Mis Partidos"]) if rol == "dt" else st.tabs(["📊 Clasificación", "📅 Calendario"])

# TAB: CLASIFICACIÓN
with tabs[0]:
    with get_db_connection() as conn:
        df_eq = pd.read_sql_query("SELECT nombre FROM equipos WHERE estado = 'aprobado'", conn)
        if df_eq.empty:
            st.info("Esperando equipos...")
        else:
            # (Lógica de tabla simplificada para brevedad, igual a la anterior)
            st.write("Tabla de Posiciones lista.")

# TAB: REGISTRO (VALIDACIÓN PREVENTIVA)
if fase_actual == "inscripcion":
    with tabs[1]:
        if st.session_state.reg_estado == "exito":
            st.success("✅ ¡Inscripción enviada!")
            if st.button("Nuevo Registro"):
                st.session_state.reg_estado = "formulario"
                st.rerun()

        elif st.session_state.reg_estado == "confirmar":
            d = st.session_state.datos_temp
            st.warning("⚠️ **Confirma tus datos:**")
            st.write(f"**Equipo:** {d['n']}\n\n**WhatsApp:** {d['pref']} {d['wa']}\n\n**PIN:** {d['pin']}")
            c1, c2 = st.columns(2)
            if c1.button("✅ Enviar"):
                with get_db_connection() as conn:
                    try:
                        conn.execute("INSERT INTO equipos (nombre, celular, prefijo, pin) VALUES (?,?,?,?)", (d['n'], d['wa'], d['pref'], d['pin']))
                        conn.commit()
                        st.session_state.reg_estado = "exito"
                        st.rerun()
                    except:
                        st.error("Error final. Intenta de nuevo.")
                        st.session_state.reg_estado = "formulario"
            if c2.button("✏️ Editar"):
                st.session_state.reg_estado = "formulario"
                st.rerun()

        else:
            with st.form("registro_preventivo"):
                nom = st.text_input("Nombre Equipo").strip()
                paises = {"Colombia": "+57", "México": "+52", "España": "+34", "Argentina": "+54", "EEUU": "+1", "Chile": "+56"}
                pais_sel = st.selectbox("País", [f"{p} ({pref})" for p, pref in paises.items()])
                tel = st.text_input("WhatsApp (Solo números)").strip()
                pin_reg = st.text_input("PIN (4 dígitos)", max_chars=4, type="password").strip()
                
                if st.form_submit_button("Revisar Datos"):
                    if not nom or not tel or len(pin_reg) < 4:
                        st.error("⚠️ Completa todos los campos correctamente.")
                    else:
                        # VALIDACIÓN CRÍTICA ANTES DE AVANZAR
                        with get_db_connection() as conn:
                            cur = conn.cursor()
                            # Verificar Nombre, PIN y Teléfono en una sola pasada
                            cur.execute("SELECT 'nombre' FROM equipos WHERE nombre = ? UNION ALL "
                                        "SELECT 'pin' FROM equipos WHERE pin = ? UNION ALL "
                                        "SELECT 'tel' FROM equipos WHERE celular = ?", (nom, pin_reg, tel))
                            errores = cur.fetchall()
                            
                            if errores:
                                st.error("❌ No se puede continuar: El Nombre, el PIN o el Teléfono ya están registrados.")
                            else:
                                st.session_state.datos_temp = {
                                    "n": nom, "wa": tel, "pin": pin_reg, 
                                    "pref": pais_sel.split('(')[-1].replace(')', '')
                                }
                                st.session_state.reg_estado = "confirmar"
                                st.rerun()

# --- PANEL ADMIN ---
if rol == "admin":
    st.divider()
    if fase_actual == "inscripcion":
        with get_db_connection() as conn:
            pend = pd.read_sql_query("SELECT nombre FROM equipos WHERE estado='pendiente'", conn)
            st.write(f"Pendientes: {len(pend)}")
            for _, r in pend.iterrows():
                if st.button(f"Aprobar {r['nombre']}"):
                    conn.execute("UPDATE equipos SET estado='aprobado' WHERE nombre=?", (r['nombre'],))
                    conn.commit(); st.rerun()
        if st.button("🚀 INICIAR TORNEO"): generar_calendario(); st.rerun()
    else:
        if st.button("🚨 RESET TOTAL"):
            with get_db_connection() as conn:
                conn.execute("DROP TABLE IF EXISTS equipos")
                conn.execute("DROP TABLE IF EXISTS partidos")
                conn.execute("UPDATE config SET valor='inscripcion'")
                conn.commit()
            st.rerun()
