import re
import json

def extract_json(text):
    # Extract the first valid JSON object from an LLM text response.
    try:
        matches = re.findall(r"```json\s*(\{[\s\S]*?\})\s*```", text)

        for m in matches:
            try:
                return json.loads(m)
            except:
                continue

        matches = re.findall(r"\{[\s\S]*?\}", text)

        for m in matches:
            try:
                return json.loads(m)
            except:
                continue

        return None

    except Exception as e:
        print("JSON parse error:", e)
        return None
