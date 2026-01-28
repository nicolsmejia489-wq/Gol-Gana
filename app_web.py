import streamlit as st
import sqlite3
import pandas as pd
import random
import easyocr
import cloudinary
import cloudinary.uploader
import io
import numpy as np
from PIL import Image
import cv2
import re  # Para expresiones regulares (encontrar números difíciles)
from thefuzz import fuzz # Para comparación flexible de nombres
import json
import os
import streamlit as st
from sqlalchemy import create_engine, text
import time
import motor_colores
import motor_grafico
from io import BytesIO
import PIL.Image
import requests
import extcolors
from difflib import SequenceMatcher

# ==============================================================================
# 1. CONFIGURACIÓN E IDENTIDAD
# ==============================================================================
st.set_page_config(page_title="Gol Gana", layout="centered", page_icon="⚽")

# --- ASSETS GRÁFICOS ---
URL_FONDO_BASE = "https://res.cloudinary.com/dlvczeqlp/image/upload/v1769030979/fondo_base_l7i0k6.png"
URL_PORTADA = "https://res.cloudinary.com/dlvczeqlp/image/upload/v1769050565/a906a330-8b8c-4b52-b131-8c75322bfc10_hwxmqb.png"
COLOR_MARCA = "#FFD700"  # Dorado Gol Gana

# --- CONEXIÓN A BASE DE DATOS (SEGURA) ---
@st.cache_resource
def get_db_connection():
    try:
        # Verifica si existen los secretos
        if "connections" not in st.secrets or "postgresql" not in st.secrets["connections"]:
            return None
        db_url = st.secrets["connections"]["postgresql"]["url"]
        return create_engine(db_url, pool_pre_ping=True)
    except:
        return None

conn = get_db_connection()

# ==============================================================================
# 2. ESTILOS CSS (BLINDAJE VISUAL + BOT DISCRETO)
# ==============================================================================
st.markdown(f"""
    <style>
        /* A. FONDO GENERAL */
        .stApp {{
            background: linear-gradient(rgba(14, 17, 23, 0.92), rgba(14, 17, 23, 0.96)), 
                        url("{URL_FONDO_BASE}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
            color: white;
        }}
        
        /* B. INPUTS Y SELECTORES */
        div[data-testid="stTextInput"] input, div[data-testid="stSelectbox"] > div > div {{
            background-color: #262730 !important;
            border: 1px solid #444 !important;
            color: white !important;
            height: 48px !important;
            font-size: 16px !important;
            border-radius: 8px !important;
        }}
        
        /* C. BOTONES */
        button[kind="secondary"], div[data-testid="stLinkButton"] a {{
            background-color: #262730 !important;
            border: 1px solid #555 !important;
            color: white !important;
            height: 45px !important;
            border-radius: 8px !important;
            transition: all 0.3s ease;
        }}
        button[kind="secondary"]:hover, div[data-testid="stLinkButton"] a:hover {{
            border-color: {COLOR_MARCA} !important;
            color: {COLOR_MARCA} !important;
            transform: translateY(-2px);
        }}
        button[kind="primary"] {{
            background-color: {COLOR_MARCA} !important;
            color: black !important;
            font-weight: 800 !important;
            border: none !important;
            height: 48px !important;
            border-radius: 8px !important;
            font-size: 16px !important;
        }}
        
        /* D. TARJETAS DEL LOBBY */
        .lobby-card {{
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 15px 20px;
            margin-bottom: 15px;
            border: 1px solid rgba(255,255,255,0.1);
            transition: transform 0.2s;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }}
        .lobby-card:hover {{
            transform: scale(1.01);
            border-color: {COLOR_MARCA};
        }}

        /* E. ANIMACIÓN FLOTANTE PARA EL ROBOT */
        @keyframes float {{
            0% {{ transform: translateY(0px); }}
            50% {{ transform: translateY(-3px); }}
            100% {{ transform: translateY(0px); }}
        }}
        .bot-icon {{
            animation: float 3s ease-in-out infinite;
            font-size: 22px;
        }}
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 3. COMPONENTE: BOT GANA (VERSIÓN DISCRETA)
# ==============================================================================
def mostrar_bot_mini(mensaje, key_unica):
    """
    Asistente virtual discreto en una sola línea.
    """
    session_key = f"bot_closed_{key_unica}"
    
    # Inicializar estado
    if session_key not in st.session_state:
        st.session_state[session_key] = False

    # Si está cerrado, no renderizar nada
    if st.session_state[session_key]:
        return

    # Contenedor visual limpio
    # Usamos columnas para alinear: [Icono] [Texto] [Like] [Cerrar]
    c_bot = st.container()
    with c_bot:
        cols = st.columns([0.1, 0.75, 0.075, 0.075], vertical_alignment="center")
        
        with cols[0]:
            st.markdown('<div class="bot-icon">🤖</div>', unsafe_allow_html=True)
        
        with cols[1]:
            st.markdown(f"<span style='color:#ddd; font-size:14px; font-style:italic;'>{mensaje}</span>", unsafe_allow_html=True)
            
        with cols[2]:
            if st.button("👍", key=f"lk_{key_unica}", help="Útil"):
                st.session_state[session_key] = True
                st.toast("¡Anotado! 😎")
                time.sleep(0.3)
                st.rerun()
                
        with cols[3]:
            if st.button("✖️", key=f"cl_{key_unica}", help="Cerrar"):
                st.session_state[session_key] = True
                st.rerun()
        
        # Separador invisible para dar aire
        st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)

# ==============================================================================
# 4. LÓGICA DEL LOBBY
# ==============================================================================

def render_lobby():
    # --- A. PORTADA ---
    st.image(URL_PORTADA, use_container_width=True)
    
    st.markdown("""
        <div style="text-align: center; margin-bottom: 25px;">
            <p style="font-size: 16px; opacity: 0.7;">
                Plataforma profesional para torneos relámpago y ligas.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # BOT: Bienvenida Discreta
    mostrar_bot_mini(
        "¡Hola! Abajo están los torneos activos. Si eres organizador, crea el tuyo al final.", 
        "bot_lobby_intro"
    )

    st.markdown("---")

    # --- B. TORNEOS VIGENTES ---
    st.subheader("🔥 Torneos en Curso")

    try:
        if conn:
            query = text("""
                SELECT id, nombre, organizador, color_primario, fase, formato, fecha_creacion 
                FROM torneos 
                WHERE fase != 'Terminado' 
                ORDER BY fecha_creacion DESC
            """)
            df_torneos = pd.read_sql_query(query, conn)
        else:
            df_torneos = pd.DataFrame()
    except Exception as e:
        st.error("Conectando con el servidor...") # Mensaje suave de error
        df_torneos = pd.DataFrame()

    if not df_torneos.empty:
        for _, t in df_torneos.iterrows():
            with st.container():
                # Tarjeta HTML
                st.markdown(f"""
                <div class="lobby-card" style="border-left: 5px solid {t['color_primario']};">
                    <div style="display:flex; justify-content:space-between; align-items:start;">
                        <div>
                            <h3 style="margin:0; font-weight:700; font-size: 20px; color:white;">{t['nombre']}</h3>
                            <p style="margin:5px 0 0 0; font-size:13px; opacity:0.7; color:#ccc;">
                                👮 {t['organizador']} | 🎮 {t['formato']}
                            </p>
                        </div>
                        <div style="text-align:right;">
                             <span style="border: 1px solid {t['color_primario']}; color: {t['color_primario']}; padding:2px 8px; border-radius:12px; font-size:11px; text-transform:uppercase;">
                                {t['fase']}
                            </span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Botón Entrar
                col_b = st.columns([1, 2, 1])[1]
                if st.button(f"⚽ Ver Torneo", key=f"btn_go_{t['id']}", use_container_width=True):
                    st.query_params["id"] = str(t['id'])
                    st.rerun()
    else:
        st.info("No hay torneos activos. ¡Crea el primero!")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- C. CREAR TORNEO ---
    with st.expander("✨ ¿Eres Organizador? Crea tu Torneo", expanded=False):
        
        # BOT: Consejo sobre el color
        mostrar_bot_mini(
            "Elige un color único. ¡Ese color definirá la identidad de toda la web para tus jugadores!", 
            "bot_crear_color"
        )
        
        with st.form("form_crear_torneo"):
            st.markdown("##### 1. El Torneo")
            new_nombre = st.text_input("Nombre del Torneo", placeholder="Ej: Relámpago Jueves")
            
            c1, c2 = st.columns(2)
            new_formato = c1.selectbox("Formato", ["Grupos + Eliminatoria", "Todos contra Todos", "Eliminación Directa"])
            new_color = c2.color_picker("Color de Marca", "#00FF00")
            
            st.markdown("##### 2. El Admin")
            c3, c4 = st.columns(2)
            new_org = c3.text_input("Tu Nombre / Cancha")
            new_wa = c4.text_input("WhatsApp (Sin +)")
            
            st.markdown("##### 3. Seguridad")
            # BOT: Consejo sobre el PIN
            st.caption("🤖 Bot: El PIN es tu llave maestra. ¡No lo olvides!")
            new_pin = st.text_input("PIN de Admin (4 dígitos)", type="password", max_chars=4)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.form_submit_button("🚀 Crear y Gestionar", use_container_width=True, type="primary"):
                if new_nombre and new_pin and new_org and conn:
                    try:
                        with conn.connect() as db:
                            res = db.execute(text("""
                                INSERT INTO torneos (nombre, organizador, whatsapp_admin, pin_admin, color_primario, fase, formato)
                                VALUES (:n, :o, :w, :p, :c, 'inscripcion', :f) RETURNING id
                            """), {
                                "n": new_nombre, "o": new_org, "w": new_wa, 
                                "p": new_pin, "c": new_color, "f": new_formato
                            })
                            nuevo_id = res.fetchone()[0]
                            db.commit()
                        
                        st.balloons()
                        time.sleep(1)
                        st.query_params["id"] = str(nuevo_id)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creando: {e}")
                else:
                    st.warning("⚠️ Faltan datos obligatorios.")

