from utils import extract_json


class LLMComplianceEvaluator:
    def __init__(self):
        # Create the LLM agent used for compliance evaluation.
        from llm_agent import LLMAgent

        self.llm = LLMAgent()

    def evaluate(self, control, evidence):
        # Evaluate evidence with the LLM and normalize the parsed JSON response.
        raw = self.llm.run(control, evidence)
        parsed = extract_json(raw)

        if not parsed:
            return {
                "decision": "UNKNOWN",
                "used_evidence": [],
                "explanation": "Could not parse evaluator output.",
                "remediation": "",
                "confidence": "",
                "raw_output": raw,
            }

        return {
            "decision": parsed.get("decision", "UNKNOWN"),
            "used_evidence": parsed.get("used_evidence", []),
            "explanation": parsed.get("explanation", ""),
            "remediation": parsed.get("remediation", ""),
            "confidence": parsed.get("confidence", ""),
        }
