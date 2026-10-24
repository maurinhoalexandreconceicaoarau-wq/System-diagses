from expert_system.inference_engine import ForwardChainingEngine


class Consultation:

    def __init__(self):
        self.engine = ForwardChainingEngine()

    def analyze(self, selected_symptoms):
        """
        Menganalisis gejala yang dipilih user
        menggunakan Forward Chaining.
        """

        results = self.engine.run(selected_symptoms)

        if not results:
            return {
                "status": "no_result",
                "message": "Sistema la hetan posibilidade moras ne'ebé klaru bazeia ba sintoma sira ne'ebé hili.",
                "results": []
            }

        return {
            "status": "success",
            "message": "Sistema hetan posibilidade moras bazeia ba sintoma sira ne'ebé hili.",
            "results": results
        }