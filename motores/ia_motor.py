import streamlit as st
from groq import Groq
import base64
from io import BytesIO
import PIL.Image
import json
import re

# --- FUNCIÓN 1: EXTRACCIÓN DESDE IMAGEN (VISIÓN) ---
def extraer_datos_foto(ruta_imagen):
    try:
        client = Groq(api_key=st.secrets["GROQ_KEY"])

        # 1. Procesar imagen
        img = PIL.Image.open(ruta_imagen)
        img.thumbnail((1200, 1200)) 
        buffered = BytesIO()
        img.save(buffered, format="JPEG", quality=95)
        img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # 2. Petición al modelo Llama 4 Scout (Visión)
        completion = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text", 
                            "text": "Return ONLY a JSON object with: 'establecimiento' (string), 'fecha' (YYYY-MM-DD), and 'total' (float). Focus on the grand total amount."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img_base64}"
                            }
                        }
                    ]
                }
            ],
            temperature=0, 
            response_format={"type": "json_object"} 
        )

        res_texto = completion.choices[0].message.content
        datos = json.loads(res_texto)

        # 3. Normalización del total
        total_final = 0.0
        t_raw = datos.get("total") or datos.get("amount")
        
        if t_raw:
            if isinstance(t_raw, str):
                limpio = re.sub(r'[^\d.,]', '', t_raw).replace(',', '.')
                if limpio.count('.') > 1:
                    partes = limpio.split('.')
                    limpio = "".join(partes[:-1]) + "." + partes[-1]
                total_final = float(limpio)
            else:
                total_final = float(t_raw)

        return {
            "establecimiento": datos.get("establecimiento") or "No detectado",
            "fecha": datos.get("fecha") or "2026-02-15",
            "total": total_final
        }

    except Exception as e:
        st.error(f"Error con Llama 4 Scout (Visión): {e}")
        return {"establecimiento": "Error", "fecha": "2026-02-15", "total": 0.0}

# --- FUNCIÓN 2: ASESOR FINANCIERO (TEXTO) ---
def analizar_gastos_ia(resumen_texto):
    """
    Analiza el resumen de texto enviado desde el DataFrame de Streamlit.
    """
    try:
        client = Groq(api_key=st.secrets["GROQ_KEY"])
        
        prompt = f"""
        Eres un asesor financiero para Chao, Kath y su Casa. 
        Analiza estos totales del mes y sé muy breve (máx 80 palabras):
        {resumen_texto}
        
        Dime: 1. Quién lleva el mando del gasto. 2. Alerta de categoría alta. 3.hazme un resumen general de nuestros habitos de compras. 
        Usa emojis.
        """
        
        completion = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return completion.choices[0].message.content
        
    except Exception as e:
        return f"La IA se ha ido de rebajas... (Error: {e})"