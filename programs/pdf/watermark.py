import hashlib

def apply_watermark(*, pdf_path, athlete, order_id):
    fingerprint = hashlib.sha256(
        f"{athlete.id}:{order_id}".encode()
    ).hexdigest()

    # (Invisible watermark placeholder)
    # Stored in DB via pdf_hash + fingerprint
    return fingerprint