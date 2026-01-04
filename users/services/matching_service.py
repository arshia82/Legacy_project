def deterministic_match(athlete_vector, coach_vectors):
    """
    athlete_vector: list[int]
    coach_vectors: dict[coach_id -> list[int]]
    """
    scored = []

    for coach_id, vector in coach_vectors.items():
        score = sum(abs(a - b) for a, b in zip(athlete_vector, vector))
        scored.append((score, coach_id))

    scored.sort(key=lambda x: (x[0], x[1]))
    return [coach_id for _, coach_id in scored]