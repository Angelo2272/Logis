import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit as st

def enviar_resumen(destinatarios, asunto, cuerpo):
    emisor = st.secrets["EMAIL_EMISOR"]
    password = st.secrets["EMAIL_PASSWORD"]
    
    msg = MIMEMultipart()
    msg['From'] = emisor
    msg['To'] = ", ".join(destinatarios)
    msg['Subject'] = asunto
    
    msg.attach(MIMEText(cuerpo, 'plain'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(emisor, password)
        server.sendmail(emisor, destinatarios, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Error enviando correo: {e}")
        return False