import extcolors
import PIL.Image
import requests
from io import BytesIO

def obtener_color_dominante(url_escudo):
    try:
        # 1. Descargar imagen
        response = requests.get(url_escudo, timeout=5)
        img = PIL.Image.open(BytesIO(response.content)).convert("RGB")
        
        # 2. Extraer colores (tolerancia 12)
        # colores devuelve una lista de tuplas: [((r,g,b), pixeles), ...]
        colores, _ = extcolors.extract_from_image(img, tolerance=12, limit=2)
        
        # 3. Evitar el blanco o negro puro si es posible
        for c in colores:
            r, g, b = c[0]
            # Si el color no es demasiado blanco ni demasiado negro
            if not (r > 240 and g > 240 and b > 240) and not (r < 15 and g < 15 and b < 15):
                return '#{:02x}{:02x}{:02x}'.format(r, g, b)
        
        # Si no encontró uno bueno, toma el primero
        r, g, b = colores[0][0]
        return '#{:02x}{:02x}{:02x}'.format(r, g, b)
        
    except Exception as e:
        print(f"Error en motor_colores: {e}")
        return "#FFD700" # Solo aquí debería haber un dorado
