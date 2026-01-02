import uuid
from io import BytesIO


def generate_watermarked_pdf(program, athlete):
    fingerprint = uuid.uuid4().hex

    content = f"""
    Program: {program.title}
    Athlete: {athlete.id}
    Fingerprint: {fingerprint}
    """

    pdf_bytes = content.encode("utf-8")  # placeholder PDF generator

    return pdf_bytes, fingerprint