from expert_system.knowledge_base import (
    get_all_rules,
    get_all_symptoms,
    get_disease_by_id
)


class ForwardChainingEngine:

    def __init__(self):
        self.rules = get_all_rules()
        self.symptom_weights = {
            symptom["symptom_id"]: max(0.01, float(symptom.get("bobot", 0.25)))
            for symptom in get_all_symptoms()
        }

    def score_rule(self, rule, selected_symptoms):
        required = [part.strip() for part in rule["conditions"].split("AND") if part.strip()]
        if not required:
            return None
        weights = [self.symptom_weights.get(symptom, 0.25) for symptom in required]
        matched = [symptom for symptom in required if symptom in selected_symptoms]
        matched_weight = sum(self.symptom_weights.get(symptom, 0.25) for symptom in matched)
        total_weight = sum(weights)
        if matched_weight == 0:
            return None
        return {
            "coverage": matched_weight / total_weight,
            "matched_weight": matched_weight,
            "total_weight": total_weight,
            "matched": matched,
            "missing": [symptom for symptom in required if symptom not in selected_symptoms],
        }

    def run(self, selected_symptoms):
        selected_symptoms = set(selected_symptoms)
        best_by_disease = {}

        for rule in self.rules:
            match = self.score_rule(rule, selected_symptoms)
            if match is None:
                continue
            disease_id = rule["conclusion"]
            candidate = {
                **match,
                "rule_id": rule["rule_id"],
                "disease_id": disease_id,
                "priority": rule["priority"],
            }
            previous = best_by_disease.get(disease_id)
            if previous is None or (
                candidate["coverage"], candidate["matched_weight"], len(candidate["matched"]), -candidate["priority"]
            ) > (
                previous["coverage"], previous["matched_weight"], len(previous["matched"]), -previous["priority"]
            ):
                best_by_disease[disease_id] = candidate

        results = []
        for disease_id, match in best_by_disease.items():
            disease = get_disease_by_id(disease_id)
            if not disease:
                continue
            results.append({
                "rule_id": match["rule_id"],
                "disease_id": disease["disease_id"],
                "naran_moras": disease["naran_moras"],
                "solusi": disease["solusi"],
                "priority": match["priority"],
                "score": round(match["coverage"] * 100),
                "matched_symptoms": match["matched"],
                "missing_symptoms": match["missing"],
            })
        results.sort(key=lambda item: (-item["score"], item["priority"], item["disease_id"]))
        return results[:1]
