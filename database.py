import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

def conectar_sheet():
    # Establece la conexión con Google Sheets usando los secretos
    return st.connection("gsheets", type=GSheetsConnection)

def inicializar_db():
    # Sigue vacía para no romper el flujo
    pass

def guardar_movimiento(fecha, establecimiento, total, categoria, usuario): # <--- 1. AÑADIDO 'usuario'
    conn = conectar_sheet()
    
    try:
        # ttl=0 asegura que no lea una versión vieja en caché.
        existing_data = conn.read(worksheet="Hoja 1", ttl=0)
    except Exception:
        # Si falla, creamos la estructura base incluyendo la nueva columna 'usuario'
        existing_data = pd.DataFrame(columns=["fecha", "establecimiento", "total", "categoria", "usuario", "fecha_registro"])
    
    # 2. Preparamos el nuevo dato incluyendo quién hizo el gasto
    nuevo_gasto = pd.DataFrame([{
        "fecha": str(fecha),
        "establecimiento": str(establecimiento),
        "total": float(total),
        "categoria": str(categoria),
        "usuario": str(usuario), # <--- 3. GUARDAMOS EL USUARIO AQUÍ
        "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }])
    
    # 4. Concatenamos y limpiamos
    updated_df = pd.concat([existing_data, nuevo_gasto], ignore_index=True)
    updated_df = updated_df.dropna(how="all")
    
    # 5. Enviamos los datos de vuelta a Google Sheets
    conn.update(worksheet="Hoja 1", data=updated_df)    