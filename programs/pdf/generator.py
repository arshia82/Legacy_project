from weasyprint import HTML
from django.template.loader import render_to_string
from .watermark import apply_watermark
import tempfile

def generate_program_pdf(*, athlete, coach, program_data, order_id):
    html = render_to_string("programs/program_pdf.html", {
        "athlete": athlete,
        "coach": coach,
        "program": program_data,
        "order_id": order_id,
    })

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    HTML(string=html).write_pdf(tmp.name)

    apply_watermark(
        pdf_path=tmp.name,
        athlete=athlete,
        order_id=order_id
    )

    return tmp.name