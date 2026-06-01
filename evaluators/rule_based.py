class RuleBasedComplianceEvaluator:
    def evaluate(self, control, evidence):
        # Evaluate evidence with a simple deterministic baseline rule.
        evidence = {
            key: value for key, value in evidence.items()
            if key != "source"
        }
        used_evidence = list(evidence.keys())

        if not evidence:
            decision = "UNKNOWN"
        elif any(value is False for value in evidence.values()):
            decision = "FAIL"
        elif any(value is True for value in evidence.values()):
            decision = "PASS"
        else:
            decision = "UNKNOWN"

        return {
            "decision": decision,
            "used_evidence": used_evidence,
            "rule_applied": "empty evidence -> UNKNOWN; any false -> FAIL; any true -> PASS",
            "explanation": self._explanation(control, evidence, decision),
            "remediation": self._remediation(decision),
        }

    def _explanation(self, control, evidence, decision):
        # Create a short explanation for the baseline decision.
        if decision == "UNKNOWN":
            return (
                f"No decisive evidence was provided for control {control['id']}. "
                "The baseline rule cannot determine compliance."
            )

        return (
            f"Baseline rule evaluated control {control['id']} using evidence fields "
            f"{list(evidence.keys())}. The resulting decision is {decision}."
        )

    def _remediation(self, decision):
        # Create a simple remediation message for the baseline decision.
        if decision == "PASS":
            return ""
        if decision == "UNKNOWN":
            return "Provide relevant machine-readable evidence before reassessment."
        return "Review the failing evidence fields and remediate the control implementation."
