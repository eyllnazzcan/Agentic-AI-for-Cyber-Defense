from data.parser import load_pdf

from data.extract_controls import (
    extract_controls,
    select_controls_by_ids,
    select_distinct_prefix_controls,
)
from evidence_generator import LLMEvidenceGenerator, TemplateEvidenceGenerator

import argparse
import json


MAX_CONTROLS = 5


def deduplicate_controls(controls):
    # Remove duplicate controls by keeping the first item for each control ID.
    deduplicated = []
    seen = set()

    for control in controls:
        control_id = control["id"]
        if control_id in seen:
            continue
        seen.add(control_id)
        deduplicated.append(control)

    return deduplicated


def main():
    # Generate evidence dataset cases from controls extracted from a PDF.
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", default="data/D48.pdf")
    parser.add_argument("--dataset-out", default="data/generated_dataset.json")
    parser.add_argument("--evidence-mode", choices=["template", "llm"], default="template")
    parser.add_argument("--max-controls", type=int, default=MAX_CONTROLS)
    parser.add_argument("--diverse-prefixes", type=int, default=None)
    parser.add_argument("--control-ids", default=None)
    parser.add_argument("--dataset-model", default=None)
    args = parser.parse_args()

    print("Loading PDF...")

    pdf_text = load_pdf(args.pdf)

    print("Extracting controls from full PDF text...")
    controls = deduplicate_controls(extract_controls(pdf_text))
    print(f"Extracted controls: {len(controls)}")

    if args.control_ids:
        control_ids = [control_id.strip() for control_id in args.control_ids.split(",")]
        controls = select_controls_by_ids(controls, control_ids)
    elif args.diverse_prefixes:
        controls = select_distinct_prefix_controls(controls, args.diverse_prefixes)
    else:
        controls = controls[:args.max_controls]

    print(f"Testing controls: {len(controls)}")

    if args.evidence_mode == "llm":
        evidence_generator = LLMEvidenceGenerator(model_name=args.dataset_model)
    else:
        evidence_generator = TemplateEvidenceGenerator()

    dataset = []

    for control in controls:
        cases = evidence_generator.generate(control)
        dataset.extend(cases)
        print(f"Generated cases: {len(dataset)}")

    with open(args.dataset_out, "w") as f:
        json.dump(dataset, f, indent=2)

    print(f"Final dataset size: {len(dataset)}")


if __name__ == "__main__":
    main()
