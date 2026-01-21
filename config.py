# 

# --- 1. INGREDIENTES FIJOS (Tus Plantillas en Cloudinary) ---
ASSETS = {
    # El fondo oscuro del estadio (Full HD)
    "fondo_base": "https://res.cloudinary.com/dlvczeqlp/image/upload/v1769030979/fondo_base_l7i0k6.png",

    # El jugador con ropa en escala de grises (blanco/negro) y fondo transparente
    "plantilla_jugador": "https://res.cloudinary.com/dlvczeqlp/image/upload/v1769035337/Gemini_Generated_Image_l02ahnl02ahnl02a_f8owdu.png",

    # El logo de GOL GANA en BLANCO PURO transparente
    "plantilla_logo": "https://res.cloudinary.com/dlvczeqlp/image/upload/v1769030972/plantilla_logo_ka9bnn.png"
}

# --- 2. VALORES POR DEFECTO (Plan de Contingencia) ---
# Si el script falla al detectar colores o cargar el escudo del campeón, usará esto:
DEFAULTS = {
    "color_principal": "#FFD700",  # DORADO (El color oficial de la marca)
    
    # En vez del escudo del equipo, usamos el Logo de Gol Gana como "Marca de Agua" central
    "escudo_backup": ASSETS["plantilla_logo"] 
}
