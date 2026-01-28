import streamlit as st
import pandas as pd

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN DE ESTILOS CSS (Fijo y probado para evitar errores)
# -----------------------------------------------------------------------------
def cargar_estilos_lobby():
    st.markdown("""
    <style>
        /* Tarjeta interactiva con cursor de mano */
        .tournament-card {
            background-color: #1E1E1E;
            border: 1px solid #333;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            position: relative;
        }
        
        .tournament-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
            border-color: #FF4B4B;
        }

        /* Tipografía */
        .card-title {
            color: white;
            font-size: 1.6rem;
            font-weight: 700;
            margin-bottom: 5px;
            display: block;
        }
        
        .status-badge {
            color: #00FF7F;
            font-size: 0.85rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
            display: inline-block;
        }
        
        .card-subtitle {
            color: #ccc;
            font-size: 0.95rem;
            margin-bottom: 15px;
        }

        /* Botón Inscribir (Independiente) */
        .btn-inscribir {
            display: inline-block;
            background-color: #FF4B4B;
            color: white !important;
            padding: 8px 16px;
            border-radius: 5px;
            text-decoration: none;
            font-weight: bold;
            font-size: 0.9rem;
            margin-top: 5px;
            border: none;
            transition: background-color 0.2s;
            position: relative;
            z-index: 10; /* Encima de todo */
        }
        .btn-inscribir:hover {
            background-color: #FF2B2B;
        }
    </style>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. CONEXIÓN Y CONSULTA A BASE DE DATOS (REAL)
# -----------------------------------------------------------------------------
def obtener_datos_copa_demo():
    """
    Conecta a la BD y busca el torneo específico.
    Asegúrate de que tu tabla 'torneos' tenga las columnas:
    id, nombre, formato, cupos_totales, estado
    """
    try:
        # Usamos st.connection para PostgreSQL (requiere 'psycopg2' instalado)
        conn = st.connection("postgresql", type="sql")
        
        # Consulta SQL directa a tu tabla 'torneos'
        # Ajusta el WHERE según cómo identifiques la copa (por ID o por Nombre)
        query = """
        SELECT id, nombre, formato, cupos_totales, estado 
        FROM torneos 
        WHERE nombre = 'Copa Demo' 
        LIMIT 1;
        """
        
        # ttl=600 cachea el resultado por 10 minutos para no saturar la BD
        df = conn.query(query, ttl=0) 
        
        if not df.empty:
            return df.iloc[0] # Retorna la primera fila como Serie
        else:
            return None
            
    except Exception as e:
        st.error(f"Error conectando a la base de datos: {e}")
        return None

# -----------------------------------------------------------------------------
# 3. RENDERIZADO DEL LOBBY
# -----------------------------------------------------------------------------
def render_lobby():
    cargar_estilos_lobby()
    
    st.title("Bienvenido a Gol-Gana")
    st.subheader("Torneos Disponibles")
    
    # Obtener datos reales
    torneo = obtener_datos_copa_demo()
    
    if torneo is not None:
        # Mapeo de variables de la BD a variables locales
        t_id = torneo['id']
        t_nombre = torneo['nombre']
        t_formato = torneo['formato']
        t_cupos = torneo['cupos_totales']
        # Lógica simple para el texto del estado
        t_estado_texto = "Inscripciones Abiertas" if torneo['estado'] == 'abierto' else torneo['estado']

        # Construcción de URLs
        url_torneo = f"/?id={t_id}"
        url_inscripcion = f"/?id={t_id}&action=inscribir"

        # HTML DINÁMICO
        html_code = f"""
        <div class="tournament-card" onclick="window.parent.location.href='{url_torneo}'">
            
            <div class="card-content">
                <span class="card-title">🏆 {t_nombre}</span>
                
                <span class="status-badge">● {t_estado_texto}</span>
                
                <div class="card-subtitle">
                    {t_formato} • {t_cupos} Equipos
                </div>
                
                <a href="{url_inscripcion}" target="_self" class="btn-inscribir" onclick="event.stopPropagation();">
                    Inscribir equipo
                </a>
            </div>
        </div>
        """
        st.markdown(html_code, unsafe_allow_html=True)
    
    else:
        # Fallback por si la BD está vacía o no encuentra la copa
        st.warning("No se encontró la 'Copa Demo' en la base de datos. Verifica la tabla 'torneos'.")

# -----------------------------------------------------------------------------
# EJECUCIÓN
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # Solo para probar este bloque aislado. 
    # En tu app principal, solo llamarías a render_lobby()
    render_lobby()
