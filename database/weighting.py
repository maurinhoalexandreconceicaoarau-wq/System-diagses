import math


def derive_symptom_weights(symptom_ids, rules):
    """Assign decimal 0.25–1.00 weights using inverse disease-rule frequency.

    Symptoms mentioned by fewer distinct diseases receive higher weights.
    Less common symptoms receive more weight. This is a ranking heuristic,
    not a clinically calibrated weight.
    """
    disease_ids = {str(rule["conclusion"]) for rule in rules}
    total_diseases = max(1, len(disease_ids))
    frequencies = {str(symptom_id): set() for symptom_id in symptom_ids}
    for rule in rules:
        disease_id = str(rule["conclusion"])
        for symptom_id in str(rule["conditions"]).split("AND"):
            symptom_id = symptom_id.strip()
            if symptom_id in frequencies:
                frequencies[symptom_id].add(disease_id)

    scores = {
        symptom_id: math.log((total_diseases + 1) / (len(diseases) + 1))
        for symptom_id, diseases in frequencies.items()
    }
    if not scores:
        return {}
    low, high = min(scores.values()), max(scores.values())
    if high == low:
        return {symptom_id: 1.0 for symptom_id in scores}
    return {
        symptom_id: round(0.25 + 0.75 * (score - low) / (high - low), 2)
        for symptom_id, score in scores.items()
    }
