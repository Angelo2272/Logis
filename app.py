import streamlit as st
import os
import pandas as pd
from datetime import datetime

# --- 1. IMPORTACIONES DE TUS MOTORES Y LÓGICA ---
from motores.ia_motor import extraer_datos_foto, analizar_gastos_ia # <--- Agregada la nueva función
from motores.xml_motor import leer_xml_facturae
from motores.correo_motor import enviar_resumen
from motores.lector_motor import conectar_y_descargar
from database import inicializar_db, guardar_movimiento, conectar_sheet

# --- 2. INICIALIZACIÓN ---
inicializar_db()

# --- 3. ESTILO UI ---
st.set_page_config(page_title="Logis Finance", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: transparent; }
    .stButton>button { 
        width: 100%; 
        background-color: #1e293b; 
        color: #f8fafc; 
        border-radius: 8px; 
        border: 1px solid #334155;
        font-weight: 600;
        padding: 0.6rem; 
        transition: 0.3s;
    }
    .stButton>button:hover { 
        background-color: #334155; 
        color: white;
    }
    .caption-text {
        color: #64748b;
        font-size: 0.9rem;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 4. CABECERA ---
st.title("Gastos 💰")
st.markdown("<p class='caption-text'>Gestiona tus finanzas automáticamente</p>", unsafe_allow_html=True)

usuario_activo = st.radio("👤 ¿Quién registra el gasto?", ["Chao", "Kath", "Casa"], horizontal=True)

# --- 5. AUTOMATIZACIÓN DE GMAIL ---
st.subheader("🤖 Automatización")
if st.button("🔍 Buscar facturas en mi Gmail"):
    with st.spinner("Revisando correos y procesando con IA..."):
        try:
            tickets_encontrados = conectar_y_descargar()
            if not tickets_encontrados:
                st.info("No se encontraron tickets nuevos.")
            else:
                for ticket_path in tickets_encontrados:
                    datos = extraer_datos_foto(ticket_path)
                    guardar_movimiento(datos['fecha'], datos['establecimiento'], datos['total'], "Correo", usuario_activo)
                    if os.path.exists(ticket_path):
                        os.remove(ticket_path)
                st.success(f"¡Magia! Se han procesado {len(tickets_encontrados)} tickets.")
                st.rerun()
        except Exception as e:
            st.error(f"Error al conectar con Gmail: {e}")

st.markdown("---")

# --- 6. CARGA MANUAL ---
st.subheader("📁 Subida Manual")
archivo = st.file_uploader("Sube ticket, PDF o captura de App", type=['png', 'jpg', 'jpeg', 'xml', 'pdf'])

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
            
            with st.container():
                col1, col2 = st.columns(2)
                with col1:
                    comercio = st.text_input("Comercio", value=resultado['establecimiento'])
                    fecha = st.text_input("Fecha", value=resultado['fecha'])
                with col2:
                    total = st.number_input("Total (€)", value=float(resultado['total']), step=0.01)
                    categoria = st.selectbox("Categoría", ["Comida", "Ocio", "Transporte", "Hogar", "Otros"])

                if st.button("Confirmar y Guardar"):
                    guardar_movimiento(fecha, comercio, total, categoria, usuario_activo)
                    st.toast(f"Guardado: {comercio} por {usuario_activo}", icon="✅")
                    st.rerun()
        except Exception as e:
            st.error(f"Error al procesar: {e}")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

# --- 7. HISTORIAL Y FILTRO DINÁMICO ---
st.markdown("---")
st.subheader("📊 Análisis Histórico")

try:
    conn = conectar_sheet()
    df = conn.read(worksheet="Hoja 1", ttl=0)
    
    if not df.empty:
        df['total'] = df['total'].astype(str).str.replace('€', '').str.replace(',', '.').str.strip()
        df['total'] = pd.to_numeric(df['total'], errors='coerce').fillna(0)
        df['fecha'] = df['fecha'].astype(str).str.strip()
        df['fecha_limpia'] = pd.to_datetime(df['fecha'], errors='coerce')
        df = df.dropna(subset=['fecha_limpia'])

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            lista_anios = sorted(df['fecha_limpia'].dt.year.unique(), reverse=True)
            anio_sel = st.selectbox("📅 Selecciona Año", lista_anios)
        with col_f2:
            meses_nombres = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
            mes_sel_num = st.selectbox("📆 Selecciona Mes", options=list(meses_nombres.keys()), format_func=lambda x: meses_nombres[x], index=datetime.now().month - 1)

        df_filtrado = df[(df['fecha_limpia'].dt.month == mes_sel_num) & (df['fecha_limpia'].dt.year == anio_sel)]
        total_filtro = df_filtrado['total'].sum()

        st.markdown(f"#### Resumen de {meses_nombres[mes_sel_num]} {anio_sel}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Gasto Total", f"{total_filtro:.2f} €")
        c2.metric("Nº Tickets", len(df_filtrado))
        c3.metric("Total Histórico", f"{df['total'].sum():.2f} €")

        if total_filtro > 0:
            col_g1, col_g2 = st.columns([1, 1])
            with col_g1:
                st.write("💰 Por Usuario")
                g_user = df_filtrado.groupby("usuario")["total"].sum().reset_index()
                st.bar_chart(g_user, x="usuario", y="total", color="#1e293b")
            with col_g2:
                st.write("📂 Por Categoría")
                g_cat = df_filtrado.groupby("categoria")["total"].sum().reset_index()
                st.bar_chart(g_cat, x="categoria", y="total", color="#475569")

            # --- MÓDULO NUEVO: ASESOR IA ---
            st.markdown("### 💡 El Asesor de Logis")
            if st.button("🧠 Analizar hábitos de este mes"):
                with st.spinner("La IA está estudiando vuestros gastos..."):
                    resumen_para_ia = df_filtrado.groupby(['usuario', 'categoria'])['total'].sum().to_string()
                    consejo = analizar_gastos_ia(resumen_para_ia)
                    st.info(consejo)
            # -------------------------------

            with st.expander(f"Ver tickets de {meses_nombres[mes_sel_num]}"):
                st.dataframe(df_filtrado[['fecha', 'establecimiento', 'total', 'categoria', 'usuario']].sort_values(by='fecha', ascending=False), use_container_width=True, hide_index=True)
        else:
            st.warning(f"No hay gastos registrados en {meses_nombres[mes_sel_num]} del {anio_sel}")

    else:
        st.info("El Excel está vacío.")

except Exception as e:
    st.error(f"Error en el filtro: {e}")