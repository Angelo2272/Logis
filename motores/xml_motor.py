import xml.etree.ElementTree as ET

def leer_xml_facturae(ruta_xml):
    tree = ET.parse(ruta_xml)
    root = tree.getroot()
    # Buscamos etiquetas estándar de FacturaE
    total = root.find('.//TotalAmount')
    nombre = root.find('.//RegistrationName')
    fecha = root.find('.//InvoiceIssueDate')
    
    return {
        "establecimiento": nombre.text if nombre is not None else "Factura XML",
        "fecha": fecha.text if fecha is not None else "2026-01-01",
        "total": float(total.text) if total is not None else 0.0
    }