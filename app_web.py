import streamlit as st

# -----------------------------------------------------------------------------
# 1. ESTILOS CSS (Definición global para las tarjetas)
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    /* Estilo del contenedor de la tarjeta */
    .tournament-card {
        background-color: #1E1E1E;
        border: 1px solid #333;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        position: relative; /* Necesario para posicionar el enlace overlay */
        transition: transform 0.2s, box-shadow 0.2s;
    }
    
    .tournament-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        border-color: #FF4B4B;
    }

    /* Enlace "fantasma" que cubre toda la caja */
    .card-link-overlay {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        z-index: 1; /* Nivel 1: Por encima del fondo */
        text-decoration: none;
    }

    /* Contenido visual de la tarjeta */
    .card-content {
        position: relative;
        z-index: 2; /* Nivel 2: Texto visible */
        pointer-events: none; /* Los clicks pasan a través de esto hacia el overlay... */
    }

    /* Excepción: El botón de inscribir debe ser clickeable */
    .card-content .btn-inscribir {
        pointer-events: auto; /* ...excepto aquí, que reactivamos el click */
    }

    /* Tipografía */
    .card-title {
        color: white;
        font-size: 1.6rem;
        font-weight: 700;
        margin-bottom: 5px;
        display: block;
    }
    
    .card-subtitle {
        color: #ccc;
        font-size: 0.95rem;
        margin-bottom: 15px;
    }

    .status-badge {
        color: #00FF7F; /* Verde */
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 10px;
        display: inline-block;
    }

    /* Botón específico de Inscribir */
    .btn-inscribir {
        display: inline-block;
        background-color: #FF4B4B;
        color: white !important;
        padding: 8px 16px;
        border-radius: 5px;
        text-decoration: none;
        font-weight: bold;
        font-size: 0.9rem;
        margin-top: 10px;
        border: none;
        transition: background-color 0.2s;
        z-index: 10; /* Nivel 10: Asegura que esté por encima del overlay */
    }
    .btn-inscribir:hover {
        background-color: #FF2B2B;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. SIMULACIÓN DE DATOS (Aquí conectarías con tu BD Neon/Postgres)
# -----------------------------------------------------------------------------
# Supongamos que esto es lo que te devuelve tu query: SELECT * FROM torneos WHERE id = 'demo'
torneo_db = {
    "id": "demo",
    "nombre": "Copa Demo",          # Variable dinámica solicitada
    "formato": "Liga Clásica",
    "cupos": 8,
    "estado_texto": "Inscripciones Abiertas" # Texto dinámico
}

# -----------------------------------------------------------------------------
# 3. RENDERIZADO DE LA TARJETA
# -----------------------------------------------------------------------------

# Construimos las URLs dinámicamente usando el ID de la base de datos
url_torneo = f"/?id={torneo_db['id']}"
url_inscripcion = f"/?id={torneo_db['id']}&action=inscribir"

# HTML con f-strings inyectando las variables de la BD
html_code = f"""
<div class="tournament-card">
    <a href="{url_torneo}" target="_self" class="card-link-overlay"></a>
    
    <div class="card-content">
        <span class="card-title">🏆 {torneo_db['nombre']}</span>
        
        <span class="status-badge">● {torneo_db['estado_texto']}</span>
        
        <div class="card-subtitle">
            {torneo_db['formato']} • {torneo_db['cupos']} Equipos
        </div>
        
        <a href="{url_inscripcion}" target="_self" class="btn-inscribir">
            Inscribir equipo
        </a>
    </div>
</div>
"""

st.markdown(html_code, unsafe_allow_html=True)
