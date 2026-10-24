from expert_system.inference_engine import ForwardChainingEngine


engine = ForwardChainingEngine()

selected_symptoms = [
    "S010",
    "S020",
    "S040"
]

results = engine.run(selected_symptoms)

print("================================")
print("FORWARD CHAINING TEST")
print("================================")

print("Selected symptoms:")
for symptom in selected_symptoms:
    print("-", symptom)

print()
print("Results:")

for result in results:
    print(
        result["disease_id"],
        "-",
        result["naran_moras"]
    )