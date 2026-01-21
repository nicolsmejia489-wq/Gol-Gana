import colorgram
import requests
from io import BytesIO

# Configuración: Colores a ignorar (Rango de grises/neutros)
# Si la saturación es muy baja o la luminosidad muy alta/baja, es un neutro.
UMBRAL_SATURACION_MIN = 0.15  # Menos de esto es gris
UMBRAL_LUZ_MIN = 0.15         # Menos de esto es casi negro
UMBRAL_LUZ_MAX = 0.85         # Más de esto es casi blanco

def obtener_color_dominante(url_imagen_escudo, color_defecto="#FFD700"):
    """
    Descarga el escudo, analiza sus píxeles y devuelve el color HEX más vibrante.
    Si falla o el escudo es blanco y negro, devuelve el color_defecto (Dorado).
    """
    if not url_imagen_escudo:
        return color_defecto

    try:
        # 1. Descargar la imagen a la memoria RAM (sin guardarla en disco)
        response = requests.get(url_imagen_escudo)
        response.raise_for_status() # Lanza error si la descarga falla
        img_bytes = BytesIO(response.content)

        # 2. Extraer los 10 colores más comunes
        # colorgram.extract(imagen, cantidad)
        colores_detectados = colorgram.extract(img_bytes, 10)

        # 3. FILTRADO INTELIGENTE
        # Buscamos el primer color que NO sea blanco, negro ni gris.
        for c in colores_detectados:
            rgb = c.rgb
            hsl = c.hsl # Hue, Saturation, Lightness

            h, s, l = hsl.h, hsl.s, hsl.l
            
            # Criterio de exclusión:
            es_muy_oscuro = l < UMBRAL_LUZ_MIN
            es_muy_claro = l > UMBRAL_LUZ_MAX
            es_gris = s < UMBRAL_SATURACION_MIN

            if not es_muy_oscuro and not es_muy_claro and not es_gris:
                # ¡ENCONTRAMOS UN COLOR VIVO!
                # Convertimos RGB a HEX (#RRGGBB)
                color_hex = '#{:02x}{:02x}{:02x}'.format(rgb.r, rgb.g, rgb.b)
                return color_hex

        # 4. PLAN B: Si solo hay blancos y negros en el escudo
        print("Aviso: El escudo es monocromático. Usando defecto.")
        return color_defecto

    except Exception as e:
        print(f"Error detectando color: {e}")
        return color_defecto

# --- BLOQUE DE PRUEBA (Solo para ejecutar localmente y ver si funciona) ---
if __name__ == "__main__":
    # URL de prueba (Escudo de Fifinhos que subiste)
    url_test = "https://res.cloudinary.com/dlvczeqlp/image/upload/v1768943714/escudos_limpios/fjj0lj0sqedubywybsps.png"
    
    print(f"Analizando escudo...")
    color_resultado = obtener_color_dominante(url_test)
    print(f"🎨 ¡Color Detectado!: {color_resultado}")
