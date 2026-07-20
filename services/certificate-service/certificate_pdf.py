from datetime import date, datetime
from io import BytesIO


def _format_issued_at(value):
    if isinstance(value, (date, datetime)):
        return value.strftime("%d/%m/%Y")
    if value:
        return str(value)[:10]
    return "Non renseignee"


def generate_certificate_pdf(certificate, verification_url):
    """Generate a certificate PDF in memory and return its byte buffer."""
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    page_width, page_height = landscape(A4)
    pdf = canvas.Canvas(buffer, pagesize=(page_width, page_height))
    pdf.setTitle(f"Certificat {certificate['certificate_code']}")
    pdf.setAuthor("TrainingHub")

    navy = HexColor("#16213E")
    blue = HexColor("#2563EB")
    gray = HexColor("#4B5563")

    pdf.setStrokeColor(blue)
    pdf.setLineWidth(4)
    pdf.rect(24, 24, page_width - 48, page_height - 48)

    pdf.setFillColor(navy)
    pdf.setFont("Helvetica-Bold", 34)
    pdf.drawCentredString(page_width / 2, page_height - 110, "CERTIFICAT DE REUSSITE")

    pdf.setFillColor(gray)
    pdf.setFont("Helvetica", 15)
    pdf.drawCentredString(page_width / 2, page_height - 155, "TrainingHub certifie que")

    pdf.setFillColor(blue)
    pdf.setFont("Helvetica-Bold", 25)
    pdf.drawCentredString(
        page_width / 2,
        page_height - 205,
        str(certificate.get("learner_name", "Apprenant")),
    )

    pdf.setFillColor(gray)
    pdf.setFont("Helvetica", 15)
    pdf.drawCentredString(page_width / 2, page_height - 250, "a termine avec succes la formation")

    pdf.setFillColor(navy)
    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawCentredString(
        page_width / 2,
        page_height - 295,
        str(certificate.get("course_title", "Formation")),
    )

    details = "Categorie : {}    |    Niveau : {}".format(
        certificate.get("category") or "Non renseignee",
        certificate.get("level") or "Non renseigne",
    )
    pdf.setFillColor(gray)
    pdf.setFont("Helvetica", 12)
    pdf.drawCentredString(page_width / 2, page_height - 335, details)

    issued_at = _format_issued_at(certificate.get("issued_at"))
    pdf.drawCentredString(page_width / 2, 150, f"Date d'emission : {issued_at}")

    certificate_code = str(certificate["certificate_code"])
    pdf.setFillColor(navy)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawCentredString(page_width / 2, 115, f"Code : {certificate_code}")

    pdf.setFillColor(gray)
    pdf.setFont("Helvetica", 9)
    pdf.drawCentredString(page_width / 2, 82, f"Verification : {verification_url}")

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer
