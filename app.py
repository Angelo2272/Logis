import streamlit as st
import os
import sqlite3
import pandas as pd

# --- 1. IMPORTACIONES DE TUS MOTORES Y LÓGICA ---
from motores.ia_motor import extraer_datos_foto
from motores.xml_motor import leer_xml_facturae
from motores.correo_motor import enviar_resumen
from motores.lector_motor import conectar_y_descargar  # <-- NUEVA IMPORTACIÓN
from database import inicializar_db, guardar_movimiento

# --- 2. INICIALIZACIÓN ---
# Aseguramos que la tabla exista en gastos.db al arrancar
inicializar_db()

# --- 3. ESTILO UI (Shadcn Style) ---
st.set_page_config(page_title="Buskaia Finance", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    .stButton>button { 
        width: 100%; background-color: #0f172a; color: white; 
        border-radius: 6px; border: none; font-weight: 500;
        padding: 0.6rem; transition: 0.2s;
    }
    .stButton>button:hover { background-color: #1e293b; color: white; border: none; }
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div {
        border-radius: 6px !important;
        border: 1px solid #e2e8f0 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 4. CABECERA ---
st.title("Buskaia Gastos 💰")
st.markdown("<p style='color: #64748b;'>Gestiona tus finanzas automáticamente</p>", unsafe_allow_html=True)

# --- 5. AUTOMATIZACIÓN DE GMAIL (AUTO-SCAN) ---
st.subheader("🤖 Automatización")
if st.button("🔍 Buscar facturas nuevas en mi Gmail"):
    with st.spinner("Revisando correos no leídos y procesando con IA..."):
        try:
            tickets_encontrados = conectar_y_descargar()
            
            if not tickets_encontrados:
                st.info("No se encontraron tickets nuevos (sin leer) en el correo.")
            else:
                for ticket_path in tickets_encontrados:
                    # La IA analiza el archivo descargado del correo
                    datos = extraer_datos_foto(ticket_path)
                    # Guardar directamente en la base de datos
                    guardar_movimiento(
                        datos['fecha'], 
                        datos['establecimiento'], 
                        datos['total'], 
                        "Correo"
                    )
                    # Eliminar archivo temporal
                    if os.path.exists(ticket_path):
                        os.remove(ticket_path)
                
                st.success(f"¡Magia! Se han procesado {len(tickets_encontrados)} tickets automáticamente.")
                st.rerun()
        except Exception as e:
            st.error(f"Error al conectar con Gmail: {e}. Revisa si habilitaste IMAP.")

st.markdown("---")

# --- 6. CARGA MANUAL DE ARCHIVOS ---
st.subheader("📁 Subida Manual")
archivo = st.file_uploader("O sube un ticket tú mismo", type=['png', 'jpg', 'jpeg', 'xml'])

if archivo is not None:
    temp_path = archivo.name
    with open(temp_path, "wb") as f:
        f.write(archivo.getbuffer())
    
    with st.spinner("Analizando documento..."):
        try:
            if temp_path.lower().endswith('.xml'):
                resultado = leer_xml_facturae(temp_path)
            else:
                resultado = extraer_datos_foto(temp_path)
            
            # Formulario de validación manual
            st.markdown("---")
            st.subheader("📋 Validar Gasto Detectado")
            
            with st.container():
                col1, col2 = st.columns(2)
                with col1:
                    comercio = st.text_input("Comercio", value=resultado['establecimiento'])
                    fecha = st.text_input("Fecha", value=resultado['fecha'])
                with col2:
                    total = st.number_input("Total (€)", value=float(resultado['total']), step=0.01)
                    categoria = st.selectbox("Categoría", ["Comida", "Ocio", "Transporte", "Hogar", "Otros"])

                if st.button("Confirmar y Guardar"):
                    guardar_movimiento(fecha, comercio, total, categoria)
                    st.toast(f"Guardado: {comercio} por {total}€", icon="✅")
                    st.rerun()

        except Exception as e:
            st.error(f"Error al procesar: {e}")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

# --- 7. HISTORIAL Y ENVÍO DE REPORTES ---
st.markdown("---")
st.subheader("📊 Historial de Gastos")

try:
    conn = sqlite3.connect("gastos.db")
    df = pd.read_sql_query("""
        SELECT fecha as 'Fecha', establecimiento as 'Comercio', 
        total as 'Total (€)', categoria as 'Categoría' 
        FROM movimientos 
        ORDER BY id DESC LIMIT 10
    """, conn)
    conn.close()

    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric("Último gasto", f"{df['Total (€)'].iloc[0]:.2f} €")
        with col_m2:
            total_vista = df['Total (€)'].sum()
            st.metric("Total (últimos 10)", f"{total_vista:.2f} €")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("📧 Enviar informe por correo"):
            destinatarios = [st.secrets["EMAIL_EMISOR"], st.secrets["EMAIL_NOVIA"]]
            resumen_texto = (
                f"¡Hola! Resumen de los últimos gastos en Buskaia Finance:\n\n"
                f"{df.to_string(index=False)}\n\n"
                f"Total: {total_vista:.2f} €"
            )
            
            with st.spinner("Enviando..."):
                if enviar_resumen(destinatarios, "Resumen de Gastos 💰", resumen_texto):
                    st.success("¡Informe enviado!")
                else:
                    st.error("Error al enviar. Revisa la configuración.")
    else:
        st.info("No hay gastos registrados todavía.")

except Exception as e:
    st.info("La base de datos está lista.")