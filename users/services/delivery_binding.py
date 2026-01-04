import hashlib

def generate_delivery_proof(order_id, athlete_id, coach_id):
    raw = f"{order_id}:{athlete_id}:{coach_id}"
    return hashlib.sha256(raw.encode()).hexdigest()


def verify_delivery_proof(order_id, athlete_id, coach_id, proof):
    expected = generate_delivery_proof(order_id, athlete_id, coach_id)
    return expected == proof