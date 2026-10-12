import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"backend"))
from app.evaluation.metrics import binary_metrics
from app.guardrails.safety import detect_prompt_injection
data=json.loads((ROOT/"data/evaluation/sample.json").read_text())
labels=[x["label"] for x in data["injection_examples"]];predicted=[bool(detect_prompt_injection(x["text"])) for x in data["injection_examples"]]
result={"dataset_version":data["version"],"label":"synthetic pipeline check — not a benchmark","prompt_injection":binary_metrics(predicted,labels),"retrieval":None,"claim_verification":None,"latency":None,"token_usage":None,"estimated_cost":None}
out=ROOT/"data/evaluation/results.json";out.write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

