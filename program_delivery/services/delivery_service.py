from django.db import transaction
import hashlib

from program_delivery.models import ProgramDelivery
from programs.pdf.generator import generate_program_pdf


@transaction.atomic
def deliver_program(*, athlete, coach, order_id, program_data):
    pdf_path = generate_program_pdf(
        athlete=athlete,
        coach=coach,
        program_data=program_data,
        order_id=order_id,
    )

    with open(pdf_path, "rb") as f:
        pdf_hash = hashlib.sha256(f.read()).hexdigest()

    return ProgramDelivery.objects.create(
        athlete=athlete,
        coach=coach,
        order_id=order_id,
        pdf_file=pdf_path,
        pdf_hash=pdf_hash,
    )