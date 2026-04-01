from decimal import Decimal
from io import BytesIO

from django.core.files.base import ContentFile
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def build_invoice_number(run_id, stop_position):
    date_part = timezone.localtime().strftime("%Y%m%d")
    run_part = str(run_id).split("-")[0].upper()
    return f"INV-{date_part}-{run_part}-{stop_position:02d}"


def create_invoice_pdf_file(*, invoice_number, company_name, shop_name, driver_name, route_name, items):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 50
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, y, "ROUTEMASTER INVOICE")
    y -= 24

    pdf.setFont("Helvetica", 10)
    pdf.drawString(40, y, f"Invoice: {invoice_number}")
    y -= 16
    pdf.drawString(40, y, f"Date: {timezone.localtime().strftime('%Y-%m-%d %H:%M')}")
    y -= 16
    pdf.drawString(40, y, f"Company: {company_name}")
    y -= 16
    pdf.drawString(40, y, f"Shop: {shop_name}")
    y -= 16
    pdf.drawString(40, y, f"Driver: {driver_name}")
    y -= 16
    pdf.drawString(40, y, f"Route: {route_name}")
    y -= 28

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(40, y, "Product")
    pdf.drawString(260, y, "Qty")
    pdf.drawString(320, y, "Rate")
    pdf.drawString(400, y, "Line Total")
    y -= 14

    pdf.setFont("Helvetica", 10)
    total = Decimal("0.00")
    for item in items:
        name = str(item["name"])[:34]
        qty = int(item["quantity"])
        rate = Decimal(str(item["rate"]))
        line_total = Decimal(str(item["line_total"]))
        total += line_total

        if y < 80:
            pdf.showPage()
            y = height - 50
            pdf.setFont("Helvetica", 10)
        pdf.drawString(40, y, name)
        pdf.drawString(260, y, str(qty))
        pdf.drawString(320, y, f"{rate:.2f}")
        pdf.drawString(400, y, f"{line_total:.2f}")
        y -= 14

    y -= 10
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(320, y, "Grand Total")
    pdf.drawString(400, y, f"{total:.2f}")
    pdf.showPage()
    pdf.save()

    buffer.seek(0)
    filename = f"{invoice_number}.pdf"
    return filename, ContentFile(buffer.read())
