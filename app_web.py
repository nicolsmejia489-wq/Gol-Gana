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

# --- CONFIGURACIÓN DE PÁGINA (GLOBAL) ---
st.set_page_config(page_title="Copa Fácil", layout="centered", page_icon="⚽")

# --- CONEXIÓN DB (Tu string de conexión aquí) ---
# engine = create_engine("postgresql://user:pass@host/dbname")
# conn = engine.connect()

# ==============================================================================
# 1. FUNCIÓN: EL LOBBY (La Nueva Entrada)
# ==============================================================================
def render_lobby():
    st.markdown("<h1 style='text-align: center;'>🏆 Copa Fácil</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; opacity: 0.8;'>La plataforma profesional para gestionar tus torneos de barrio, empresa o amigos.</p>", unsafe_allow_html=True)
    
    st.divider()

    # --- A. LISTA DE TORNEOS VIGENTES ---
    st.subheader("🔥 Torneos en Juego")
    
    try:
        # Consultamos torneos activos (no terminados)
        # Nota: Usamos la nueva tabla 'torneos'
        torneos = pd.read_sql_query(text("SELECT * FROM torneos WHERE fase != 'Terminado' ORDER BY fecha_creacion DESC"), conn)
    except Exception as e:
        st.error("Error conectando a la base de datos.")
        torneos = pd.DataFrame()

    if not torneos.empty:
        # Grid de tarjetas
        for _, t in torneos.iterrows():
            with st.container():
                # Tarjeta visual con el color del torneo
                st.markdown(f"""
                <div style='
                    border-left: 5px solid {t['color_primario']};
                    background-color: rgba(255,255,255,0.05);
                    padding: 15px;
                    border-radius: 8px;
                    margin-bottom: 10px;
                '>
                    <h3 style='margin:0'>{t['nombre']}</h3>
                    <p style='margin:0; font-size: 14px; opacity: 0.7;'>Organiza: {t['organizador']} | Fase: {t['fase'].upper()}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # BOTÓN PARA ENTRAR (MAGIA DE URL)
                # Al hacer click, recargamos la página inyectando el parámetro en la URL
                if st.button(f"➡️ Ir al Torneo", key=f"go_{t['id']}", use_container_width=True):
                    st.query_params["id"] = str(t['id'])
                    st.rerun()
    else:
        st.info("No hay torneos activos en este momento.")

    st.markdown("<br><br>", unsafe_allow_html=True)

    # --- B. CREAR MI TORNEO (EL GANCHO) ---
    with st.expander("✨ ¡Quiero Organizar un Torneo!", expanded=False):
        st.write("Crea tu panel de administración en segundos.")
        with st.form("crear_torneo_form"):
            new_nombre = st.text_input("Nombre del Torneo", placeholder="Ej: Relámpago Viernes")
            c1, c2 = st.columns(2)
            new_org = c1.text_input("Tu Nombre / Organización")
            new_wa = c2.text_input("Tu WhatsApp")
            
            c3, c4 = st.columns(2)
            new_pin = c3.text_input("Crea un PIN de Admin", type="password", max_chars=6, help="Con este PIN entrarás a gestionar.")
            new_color = c4.color_picker("Color del Torneo", "#00FF00")
            
            if st.form_submit_button("🚀 Crear Torneo Ahora", use_container_width=True):
                if new_nombre and new_pin and new_org:
                    try:
                        with conn.connect() as db:
                            # Insertamos y devolvemos el ID generado
                            result = db.execute(text("""
                                INSERT INTO torneos (nombre, organizador, whatsapp_admin, pin_admin, color_primario, fase)
                                VALUES (:n, :o, :w, :p, :c, 'inscripcion') RETURNING id
                            """), {"n": new_nombre, "o": new_org, "w": new_wa, "p": new_pin, "c": new_color})
                            
                            nuevo_id = result.fetchone()[0]
                            db.commit()
                        
                        st.success("¡Torneo Creado!")
                        time.sleep(1)
                        # Redirigir inmediatamente al nuevo torneo
                        st.query_params["id"] = str(nuevo_id)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.warning("Faltan datos obligatorios.")


# ==============================================================================
# 2. FUNCIÓN: RENDERIZAR TORNEO (Tu lógica antigua va aquí dentro)
# ==============================================================================
def render_torneo(torneo_id):
    # A. CARGAR CONFIGURACIÓN DE ESTE TORNEO ESPECÍFICO
    try:
        t_data = pd.read_sql_query(text("SELECT * FROM torneos WHERE id = :id"), conn, params={"id": torneo_id})
    except:
        st.error("Torneo no encontrado.")
        if st.button("Volver al Lobby"):
            st.query_params.clear()
            st.rerun()
        return

    if t_data.empty:
        st.error("El torneo que buscas no existe.")
        time.sleep(2)
        st.query_params.clear()
        st.rerun()
        return

    # DATOS DEL CONTEXTO ACTUAL
    TORNEO = t_data.iloc[0]
    COLOR_WEB = TORNEO['color_primario']
    NOMBRE_TORNEO = TORNEO['nombre']
    FASE_ACTUAL = TORNEO['fase']
    PIN_REAL = TORNEO['pin_admin']

    # --- AQUÍ EMPIEZA TU APP DE SIEMPRE (Login, Tabs, etc.) ---
    # Pero usando las variables de arriba en lugar de 'config' global
    
    # 1. NAVBAR SIMULADO
    c_back, c_tit = st.columns([0.2, 0.8], vertical_alignment="center")
    with c_back:
        if st.button("⬅️ Inicio"):
            st.query_params.clear()
            st.rerun()
    with c_tit:
        st.markdown(f"<h2 style='margin:0; color:{COLOR_WEB}'>{NOMBRE_TORNEO}</h2>", unsafe_allow_html=True)

    # 2. LOGIN (Adaptado para validar contra PIN_REAL del torneo actual)
    if 'rol' not in st.session_state: st.session_state.rol = "visitante"
    
    # ... (Aquí pegaremos toda tu lógica de Login, Tabs, Registro y Admin) ...
    # ... IMPORTANTE: Todas las queries deben añadir "WHERE torneo_id = :tid" ...
    
    st.info(f"Estás viendo el torneo ID: {torneo_id} | Color: {COLOR_WEB}") # Debug temporal


# ==============================================================================
# 3. EL ENRUTADOR PRINCIPAL (Main)
# ==============================================================================
# Leemos los parámetros de la URL
params = st.query_params

if "id" in params:
    # Si hay ID, mostramos el Torneo
    render_torneo(params["id"])
else:
    # Si no hay ID, mostramos el Lobby
    render_lobby()
