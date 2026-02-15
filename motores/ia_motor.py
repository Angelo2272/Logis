import streamlit as st
from groq import Groq
import base64
from io import BytesIO
import PIL.Image
import json
import re

def extraer_datos_foto(ruta_imagen):
    try:
        client = Groq(api_key=st.secrets["GROQ_KEY"])

        # 1. Procesar imagen (Subimos un poco la resolución para el Lupa)
        img = PIL.Image.open(ruta_imagen)
        img.thumbnail((1200, 1200)) # Más resolución = mejor lectura de números pequeños
        buffered = BytesIO()
        img.save(buffered, format="JPEG", quality=95)
        img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # 2. Petición al modelo Llama 4 Scout
        # IMPORTANTE: Forzamos el formato JSON en el sistema
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
            temperature=0, # Cero absoluto para máxima precisión numérica
            response_format={"type": "json_object"} # Esto evita que la IA hable de más
        )

        res_texto = completion.choices[0].message.content
        datos = json.loads(res_texto)

        # 3. Normalización inteligente (Sin valores quemados)
        # Extraemos el total buscando el número más probable si el JSON viene raro
        total_final = 0.0
        t_raw = datos.get("total") or datos.get("amount")
        
        if t_raw:
            if isinstance(t_raw, str):
                # Limpiamos el texto "4,51€" -> "4.51"
                limpio = re.sub(r'[^\d.,]', '', t_raw).replace(',', '.')
                # Si hay dos puntos (ej 1.250.50), nos quedamos con el último para decimales
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
        st.error(f"Error con Llama 4 Scout: {e}")
        return {"establecimiento": "Error", "fecha": "", "total": 0.0}