import imaplib
import email
from email.header import decode_header
import streamlit as st
import os
from datetime import datetime

def conectar_y_descargar():
    user = st.secrets["EMAIL_EMISOR"]
    password = st.secrets["EMAIL_PASSWORD"]
    imap_url = 'imap.gmail.com'

    # Conexión al servidor
    mail = imaplib.IMAP4_SSL(imap_url)
    mail.login(user, password)
    mail.select("inbox")

    # --- CONFIGURACIÓN DE FILTROS ---
    # Fecha de hoy en formato IMAP (ejemplo: 15-Feb-2026)
    fecha_hoy = datetime.now().strftime("%d-%b-%Y")
    
    # Lista de dominios o nombres de los supermercados
    supermercados = ['carrefour.es', 'lupa.com', 'eroski.es', 'alcampo.es', 'mercadona.es']
    
    # Construimos la consulta de búsqueda: 
    # Queremos: (Desde hoy) Y (No leídos) Y (Venga de alguno de estos)
    # Nota: IMAP usa una sintaxis un poco compleja para OR múltiples
    search_query = f'(SINCE "{fecha_hoy}" UNSEEN'
    
    # Añadimos los emisores (buscamos en el cuerpo o remitente)
    # Para simplificar, buscamos si el remitente contiene el nombre
    emisores_query = ""
    for super_nombre in supermercados:
        emisores_query += f' FROM "{super_nombre}"'
    
    # Combinamos (Nota: Si son muchos, a veces es mejor buscar todos y filtrar en Python)
    # Usaremos una búsqueda amplia por fecha y filtramos los remitentes en el bucle
    status, messages = mail.search(None, f'(SINCE "{fecha_hoy}" UNSEEN)')
    
    archivos_descargados = []

    if status == 'OK':
        for num in messages[0].split():
            res, msg = mail.fetch(num, '(RFC822)')
            for response in msg:
                if isinstance(response, tuple):
                    msg_obj = email.message_from_bytes(response[1])
                    remitente = msg_obj.get("From", "").lower()
                    
                    # COMPROBACIÓN: ¿El remitente es uno de nuestros supermercados?
                    if any(s in remitente for s in supermercados):
                        # Si coincide, buscamos los adjuntos
                        for part in msg_obj.walk():
                            if part.get_content_maintype() == 'multipart': continue
                            if part.get('Content-Disposition') is None: continue
                            
                            filename = part.get_filename()
                            if filename:
                                # Filtramos por extensiones válidas
                                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.xml', '.pdf')):
                                    if not os.path.exists("temp"): os.makedirs("temp")
                                    filepath = os.path.join("temp", filename)
                                    with open(filepath, "wb") as f:
                                        f.write(part.get_payload(decode=True))
                                    archivos_descargados.append(filepath)
    
    mail.logout()
    return archivos_descargados