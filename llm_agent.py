from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

class LLMAgent:
    def __init__(self):
        # Load the LLM used for compliance evaluation.
        model_name = "microsoft/Phi-3-mini-4k-instruct"
        print("Loading Phi3...")

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.tokenizer.pad_token = self.tokenizer.eos_token

        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            dtype=torch.float16,
            device_map="cpu"
        )

    def run(self, control, evidence):
        # Evaluate one control/evidence pair and return the raw LLM response.
        if isinstance(control, dict):
            control_id = control.get("id", "")
            control_description = control.get("description", "")
        else:
            control_id = ""
            control_description = str(control)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a cybersecurity compliance analyst. "
                    "Evaluate evidence against the control using your own reasoning. "
                    "Return only valid JSON."
                )
            },
            {
                "role": "user",
                "content": f"""
Decide whether the evidence satisfies the cybersecurity control.

Control ID: {control_id}
Control description: {control_description}

Evidence:
{evidence}

Decision rules:
- PASS: evidence directly supports that the control is implemented.
- FAIL: evidence directly contradicts or shows the control is not implemented.
- UNKNOWN: evidence is missing, incomplete, ambiguous, or not relevant.

Do not assume facts that are not present in the evidence.
Explanation must cite the control and the specific evidence fields used.
Remediation must be practical and specific when decision is FAIL or UNKNOWN.
For PASS, remediation should be an empty string.

Return JSON:
{{
  "decision": "",
  "used_evidence": [],
  "explanation": "",
  "remediation": "",
  "confidence": ""
}}
"""
            }
        ]

        prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        inputs = self.tokenizer(prompt, return_tensors="pt")

        outputs = self.model.generate(
            **inputs,
            max_new_tokens=512,
            do_sample=False,
            eos_token_id=self.tokenizer.eos_token_id
        )

        generated_tokens = outputs[0][inputs["input_ids"].shape[-1]:]
        response = self.tokenizer.decode(
            generated_tokens,
            skip_special_tokens=True
        )

        return response
