import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

def conectar_sheet():
    # Establece la conexión con Google Sheets usando los secretos
    return st.connection("gsheets", type=GSheetsConnection)

def inicializar_db():
    # En Sheets no hace falta crear la tabla, ya la creaste tú a mano.
    # Dejamos esta función vacía para no romper la compatibilidad con app.py
    pass

def guardar_movimiento(fecha, establecimiento, total, categoria):
    conn = conectar_sheet()
    
    try:
        # 1. Intentamos leer la hoja. Si está vacía o hay error de conexión, saltará al except.
        # ttl=0 asegura que no lea una versión vieja en caché.
        existing_data = conn.read(worksheet="Hoja 1", ttl=0)
    except Exception:
        # 2. Si falla la lectura, asumimos que está vacía y creamos la estructura base.
        # Asegúrate de que estos nombres sean idénticos a la fila 1 de tu Excel.
        existing_data = pd.DataFrame(columns=["fecha", "establecimiento", "total", "categoria", "fecha_registro"])
    
    # 3. Preparamos el nuevo dato asegurando los tipos (str, float)
    nuevo_gasto = pd.DataFrame([{
        "fecha": str(fecha),
        "establecimiento": str(establecimiento),
        "total": float(total),
        "categoria": str(categoria),
        "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }])
    
    # 4. Concatenamos el historial con el nuevo dato
    # dropna(how="all") elimina filas que estén totalmente vacías (común en Sheets)
    updated_df = pd.concat([existing_data, nuevo_gasto], ignore_index=True)
    updated_df = updated_df.dropna(how="all")
    
    # 5. Enviamos los datos de vuelta a Google Sheets
    conn.update(worksheet="Hoja 1", data=updated_df)