import os

from transformers import pipeline


class DatasetLLM:

    def __init__(self, model_name=None):
        # Load the Hugging Face text-generation pipeline for dataset generation.

        model_name = (
            model_name
            or os.getenv("DATASET_LLM_MODEL")
            or "Qwen/Qwen2.5-7B-Instruct"
        )

        print(f"Loading Qwen Dataset Model: {model_name}")

        self.pipe = pipeline(
            "text-generation",
            model=model_name,
            device_map="auto"
        )

    def generate(self, prompt: str) -> str:
        # Generate text from the dataset LLM for a given prompt.
        messages = [
            {
                "role": "system",
                "content": (
                    "You generate compact cybersecurity compliance evidence. "
                    "Return only valid JSON. Do not use markdown or prose."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ]

        formatted_prompt = self._format_prompt(messages)

        output = self.pipe(
            formatted_prompt,
            max_new_tokens=256,
            do_sample=False,
            return_full_text=False
        )

        return output[0]["generated_text"].strip()

    def _format_prompt(self, messages):
        # Format messages with the model chat template when available.
        tokenizer = self.pipe.tokenizer
        if getattr(tokenizer, "chat_template", None):
            return tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )

        return "\n\n".join(
            f"{message['role'].upper()}:\n{message['content']}"
            for message in messages
        ) + "\n\nASSISTANT:\n"
