import json
import re


FORBIDDEN_EVIDENCE_KEYS = {
    "actual",
    "compliant",
    "control",
    "decision",
    "description",
    "expected",
    "field_name",
    "field_value",
    "pass",
    "reason",
    "remediation",
    "result",
    "status",
}


class TemplateEvidenceGenerator:
    def generate(self, control):
        # Create simple deterministic evidence cases for quick smoke tests.
        return [
            {
                "control": control,
                "evidence": {
                    "control_implemented": True
                },
                "expected": "PASS",
            },
            {
                "control": control,
                "evidence": {
                    "control_implemented": False
                },
                "expected": "FAIL",
            },
            {
                "control": control,
                "evidence": {},
                "expected": "UNKNOWN",
            },
        ]


class LLMEvidenceGenerator:
    def __init__(self, model_name=None):
        # Load the dataset LLM used for evidence generation.
        from llm_dataset import DatasetLLM

        self.llm = DatasetLLM(model_name=model_name)

    def generate(self, control):
        # Generate PASS, FAIL, and UNKNOWN evidence cases for one control.
        pass_evidence = self._generate_evidence_object(control, "supporting")
        fail_evidence = self._generate_evidence_object(control, "contradicting")

        return [
            {
                "control": control,
                "evidence": pass_evidence,
                "expected": "PASS",
            },
            {
                "control": control,
                "evidence": fail_evidence,
                "expected": "FAIL",
            },
            {
                "control": control,
                "evidence": {},
                "expected": "UNKNOWN",
            },
        ]

    def _generate_evidence_object(self, control, scenario):
        # Ask the LLM for one evidence object for a supporting or contradicting case.
        prompt = f"""
Return one JSON object only. Do not use markdown. Do not write prose.

Control:
{control.get("id", "")}
{control["description"]}

Scenario: create raw evidence facts that are {scenario} this control.

Write only observed facts, not an evaluation result.
Use 2 to 4 concise snake_case keys with short scalar values.
Do not include the control id or control description.
Use evidence facts from an audit record, repository record, inventory, or review log.
Do not include long text, file contents, code blocks, examples, or explanations.

The JSON object must be non-empty.
The first character of your response must be {{.
The last character of your response must be }}.
"""
        raw = self.llm.generate(prompt)
        evidence = _parse_json_object(raw)

        if not evidence:
            raise ValueError(
                f"{scenario} evidence generator returned an empty object. "
                f"Raw output preview: {_preview(raw)}"
            )

        _validate_evidence_object(evidence, raw)

        return evidence


def _parse_json_object(raw):
    # Parse an LLM response into a JSON object.
    if not raw or not raw.strip():
        raise ValueError("Evidence generator returned empty output.")

    raw = raw.strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", raw)
        if fenced:
            parsed = _load_jsonish_object(fenced.group(1))
        else:
            parsed = _decode_first_json_object(raw)

    if not isinstance(parsed, dict):
        raise ValueError(
            "Evidence generator did not return a JSON object. "
            f"Raw output preview: {_preview(raw)}"
        )

    return parsed


def _decode_first_json_object(raw):
    # Find and decode the first JSON object inside a larger text response.
    decoder = json.JSONDecoder()

    for index, char in enumerate(raw):
        if char != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(raw[index:])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            try:
                parsed, _ = decoder.raw_decode(_normalize_jsonish(raw[index:]))
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                continue

    raise ValueError(
        "Evidence generator did not return a JSON object. "
        f"Raw output preview: {_preview(raw)}"
    )


def _load_jsonish_object(text):
    # Parse strict JSON or a JSON-like object with minor formatting issues.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return json.loads(_normalize_jsonish(text))


def _normalize_jsonish(text):
    # Convert simple JSON-like syntax into valid JSON syntax.
    text = re.sub(
        r"([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)(\s*:)",
        r'\1"\2"\3',
        text,
    )
    text = re.sub(r":\s*'([^']*)'", r': "\1"', text)
    text = re.sub(r"\bTrue\b", "true", text)
    text = re.sub(r"\bFalse\b", "false", text)
    text = re.sub(r"\bNone\b", "null", text)
    return text


def _validate_evidence_object(evidence, raw):
    # Reject evidence objects that contain metadata or evaluation fields.
    bad_keys = sorted(_find_forbidden_keys(evidence))
    if bad_keys:
        raise ValueError(
            "Evidence generator returned evaluation/metadata fields instead of raw evidence. "
            f"Forbidden keys: {bad_keys}. Raw output preview: {_preview(raw)}"
        )


def _find_forbidden_keys(value):
    # Recursively collect forbidden keys from nested evidence data.
    found = set()

    if isinstance(value, dict):
        for key, nested_value in value.items():
            if key in FORBIDDEN_EVIDENCE_KEYS:
                found.add(key)
            found.update(_find_forbidden_keys(nested_value))
    elif isinstance(value, list):
        for item in value:
            found.update(_find_forbidden_keys(item))

    return found


def _preview(text, limit=500):
    # Return a short single-line preview of long text for error messages.
    text = (text or "").replace("\n", "\\n")
    if len(text) <= limit:
        return text
    return text[:limit] + "..."
