import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch

def generate_certificate_pdf(recipient_name: str, event_name: str, date: str, certificate_id: int) -> str:
    """
    Generates a simple certificate PDF.
    Returns the file path to the generated PDF.
    """
    filename = f"cert_{certificate_id}.pdf"
    file_path = os.path.join("generated_certificates", filename)
    
    # Ensure directory exists
    os.makedirs("generated_certificates", exist_ok=True)
    
    c = canvas.Canvas(file_path, pagesize=letter)
    width, height = letter
    
    # Title
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(width / 2, height - 2 * inch, "Certificate of Participation")
    
    # Body
    c.setFont("Helvetica", 14)
    c.drawCentredString(width / 2, height - 3.5 * inch, "This is to certify that")
    
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2, height - 4.5 * inch, recipient_name)
    
    c.setFont("Helvetica", 14)
    c.drawCentredString(width / 2, height - 5.5 * inch, "has successfully participated in")
    
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - 6.5 * inch, event_name)
    
    c.setFont("Helvetica", 12)
    c.drawCentredString(width / 2, height - 7.5 * inch, f"Date: {date}")
    
    # Footer
    c.setFont("Helvetica", 10)
    c.drawString(1 * inch, 1 * inch, f"Certificate ID: {certificate_id}")
    
    c.save()
    
    return file_path
