import streamlit as st
import os
import pandas as pd
from datetime import datetime

# --- 1. IMPORTACIONES ---
from motores.ia_motor import extraer_datos_foto
from motores.xml_motor import leer_xml_facturae
from motores.correo_motor import enviar_resumen
from motores.lector_motor import conectar_y_descargar
from database import inicializar_db, guardar_movimiento, conectar_sheet

# --- 2. INICIALIZACIÓN ---
inicializar_db()

# --- 3. ESTILO UI (Adaptable) ---
st.set_page_config(page_title="Buskaia Finance", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: transparent; }
    .stButton>button { 
        width: 100%; background-color: #1e293b; color: #f8fafc; 
        border-radius: 8px; border: 1px solid #334155;
        font-weight: 600; padding: 0.6rem; transition: 0.3s;
    }
    .stButton>button:hover { background-color: #334155; color: white; border: 1px solid #475569; }
    .caption-text { color: #64748b; font-size: 0.9rem; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. CABECERA Y USUARIO ---
st.title("Gastos 💰")
st.markdown("<p class='caption-text'>Gestiona tus finanzas automáticamente</p>", unsafe_allow_html=True)

# El selector de usuario es lo primero que vemos
usuario_activo = st.radio("👤 ¿Quién registra el gasto?", ["Chao", "Kath","Casa"], horizontal=True)

# --- 5. AUTOMATIZACIÓN DE GMAIL ---
st.subheader("🤖 Automatización")
if st.button("🔍 Buscar facturas en mi Gmail"):
    with st.spinner("Revisando correos..."):
        try:
            tickets_encontrados = conectar_y_descargar()
            if not tickets_encontrados:
                st.info("No se encontraron tickets nuevos.")
            else:
                for ticket_path in tickets_encontrados:
                    datos = extraer_datos_foto(ticket_path)
                    # Aquí asignamos el gasto a "Sistema" o al usuario activo
                    guardar_movimiento(datos['fecha'], datos['establecimiento'], datos['total'], "Correo", usuario_activo)
                    if os.path.exists(ticket_path):
                        os.remove(ticket_path)
                st.success(f"¡Procesados {len(tickets_encontrados)} tickets!")
                st.rerun()
        except Exception as e:
            st.error(f"Error Gmail: {e}")

st.markdown("---")

# --- 6. CARGA MANUAL ---
st.subheader("📁 Subida Manual")
archivo = st.file_uploader("Sube ticket o captura de Eroski/Lupa", type=['png', 'jpg', 'jpeg', 'xml', 'pdf'])

if archivo is not None:
    temp_path = f"temp_{archivo.name}"
    with open(temp_path, "wb") as f:
        f.write(archivo.getbuffer())
    
    with st.spinner("Analizando documento..."):
        try:
            if temp_path.lower().endswith('.xml'):
                resultado = leer_xml_facturae(temp_path)
            else:
                resultado = extraer_datos_foto(temp_path)
            
            st.markdown("---")
            st.subheader("📋 Validar Gasto")
            
            col1, col2 = st.columns(2)
            with col1:
                comercio = st.text_input("Comercio", value=resultado['establecimiento'])
                fecha = st.text_input("Fecha", value=resultado['fecha'])
            with col2:
                total = st.number_input("Total (€)", value=float(resultado['total']), step=0.01)
                categoria = st.selectbox("Categoría", ["Comida", "Ocio", "Transporte", "Hogar", "Otros"])

            # EL BOTÓN DE GUARDAR DEBE ESTAR AQUÍ DENTRO
            if st.button("Confirmar y Guardar"):
                guardar_movimiento(fecha, comercio, total, categoria, usuario_activo)
                st.toast(f"✅ Guardado por {usuario_activo}")
                st.rerun()

        except Exception as e:
            st.error(f"Error: {e}")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

# --- 7. HISTORIAL ---
st.markdown("---")
st.subheader("📊 Historial (Google Sheets)")
try:
    conn = conectar_sheet()
    df = conn.read(worksheet="Hoja 1", ttl=0)
    if not df.empty:
        st.dataframe(df.tail(10), use_container_width=True, hide_index=True)
        
        # Métricas
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric("Último total", f"{float(df['total'].iloc[-1]):.2f} €")
        with col_m2:
            st.metric("Registrado por", df['usuario'].iloc[-1])
except:
    st.info("Esperando conexión con la nube...")