from PIL import Image, ImageOps
import requests
from io import BytesIO
import config

# --- DIMENSIONES MÓVILES (Vertical HD) ---
ANCHO_CANVAS = 1080
ALTO_CANVAS = 1920

def descargar_imagen(url):
    """Descarga imagen y la convierte a RGBA para manejar transparencias."""
    try:
        if not url: return Image.new("RGBA", (100, 100), (0, 0, 0, 0))
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content)).convert("RGBA")
        return img
    except Exception as e:
        print(f"⚠️ Error descargando {url}: {e}")
        # Retorna una imagen vacía transparente para no romper el script
        return Image.new("RGBA", (100, 100), (0, 0, 0, 0))

def procesar_escudo_fantasma(img_escudo):
    """
    Convierte el escudo en una marca de agua gigante, 
    en escala de grises y con transparencia sutil.
    """
    if not img_escudo: return None

    # 1. Convertir a Escala de Grises manteniendo canal Alfa
    # convert("L") lo vuelve gris, pero perdemos transparencia, así que recuperamos el canal alpha original
    r, g, b, alpha = img_escudo.split()
    img_gris = img_escudo.convert("L") # Imagen en grises
    
    # Fusionamos: Canal L (Gris) repetido 3 veces para RGB + Canal Alpha Original
    escudo_final = Image.merge("RGBA", (img_gris, img_gris, img_gris, alpha))
    
    # 2. Redimensionar (Hacerlo GIGANTE para llenar el fondo)
    # Ocupará el 85% del ancho de la pantalla
    ancho_objetivo = int(ANCHO_CANVAS * 0.85)
    factor = ancho_objetivo / escudo_final.width
    nuevo_alto = int(escudo_final.height * factor)
    escudo_final = escudo_final.resize((ancho_objetivo, nuevo_alto), Image.Resampling.LANCZOS)
    
    # 3. Aplicar Transparencia (Efecto Fantasma)
    # Bajamos la opacidad drásticamente para que sea sutil
    datos = escudo_final.getdata()
    nuevos_datos = []
    
    # OPACIDAD: Ajusta este 0.10 (10%) si lo quieres más o menos visible
    NIVEL_OPACIDAD = 0.10 
    
    for item in datos:
        # item es (R, G, B, Alpha)
        # Multiplicamos el Alpha actual por el nivel de opacidad
        nuevo_alpha = int(item[3] * NIVEL_OPACIDAD)
        nuevos_datos.append((item[0], item[1], item[2], nuevo_alpha))
    
    escudo_final.putdata(nuevos_datos)
    return escudo_final

def construir_portada(color_campeon, url_escudo_campeon):
    """
    Genera el fondo vertical simple: Estadio Oscuro + Escudo Fantasma.
    Nota: 'color_campeon' no se usa en el gráfico, pero lo recibimos por compatibilidad.
    """
    print(f"📱 Generando Fondo Atmosférico...")

    # --- 1. CARGA DE FONDO ---
    # Usamos el fondo base definido en config.py
    fondo = descargar_imagen(config.ASSETS["fondo_base"])
    
    # Ajuste Vertical (Crop inteligente al centro)
    # Esto asegura que el estadio cubra toda la pantalla del celular (1080x1920)
    lienzo = ImageOps.fit(fondo, (ANCHO_CANVAS, ALTO_CANVAS), centering=(0.5, 0.5))

    # --- 2. PROCESAR Y PEGAR ESCUDO ---
    if url_escudo_campeon:
        escudo_original = descargar_imagen(url_escudo_campeon)
        escudo_fantasma = procesar_escudo_fantasma(escudo_original)
        
        if escudo_fantasma:
            # Calcular posición central absoluta
            x = (ANCHO_CANVAS - escudo_fantasma.width) // 2
            y = (ALTO_CANVAS - escudo_fantasma.height) // 2
            
            # Pegar sobre el fondo (alpha_composite respeta transparencias)
            lienzo.alpha_composite(escudo_fantasma, (x, y))

    return lienzo

# --- PRUEBA LOCAL ---
if __name__ == "__main__":
    # URL de prueba (Tu escudo Fifinhos)
    url_test = "https://res.cloudinary.com/dlvczeqlp/image/upload/v1768951368/escudos_limpios/h0brcsuihwiznexlcaz0.png"
    
    img = construir_portada("#000000", url_test)
    img.show()
    # img.save("fondo_prueba.png")
