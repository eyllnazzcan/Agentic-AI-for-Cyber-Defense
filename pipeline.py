import argparse
import json

from data.extract_controls import (
    extract_controls,
    select_controls_by_ids,
    select_distinct_prefix_controls,
)
from data.parser import load_pdf
from evaluators import LLMComplianceEvaluator, RuleBasedComplianceEvaluator
from evidence_generator import LLMEvidenceGenerator, TemplateEvidenceGenerator


def build_evaluator(mode):
    # Create the compliance evaluator selected from the CLI.
    if mode == "llm":
        return LLMComplianceEvaluator()
    return RuleBasedComplianceEvaluator()


def write_json(path, payload):
    # Write a Python object to a JSON file.
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)


def run_pipeline(args):
    # Run the full PDF -> controls -> evidence -> evaluation pipeline.
    print("1/4 Loading directive PDF...")
    directive_text = load_pdf(args.pdf)

    print("2/4 Extracting controls...")
    controls = extract_controls(directive_text)

    if args.control_ids:
        control_ids = [control_id.strip() for control_id in args.control_ids.split(",")]
        controls = select_controls_by_ids(controls, control_ids)
    elif args.diverse_prefixes:
        controls = select_distinct_prefix_controls(controls, args.diverse_prefixes)
    elif args.max_controls:
        controls = controls[:args.max_controls]

    write_json(args.controls_out, controls)
    print(f"Extracted {len(controls)} controls -> {args.controls_out}")

    print("3/4 Generating evidence...")
    if args.evidence_mode == "llm":
        evidence_generator = LLMEvidenceGenerator(model_name=args.dataset_model)
    else:
        evidence_generator = TemplateEvidenceGenerator()
    cases = []
    for index, control in enumerate(controls, start=1):
        print(f"  evidence {index}/{len(controls)} {control['id']}")
        cases.extend(evidence_generator.generate(control))
    write_json(args.evidence_out, cases)
    print(f"Generated {len(cases)} evidence cases -> {args.evidence_out}")

    print("4/4 Evaluating compliance...")
    evaluator = build_evaluator(args.evaluation_mode)
    results = []
    for index, case in enumerate(cases, start=1):
        control = case["control"]
        print(f"  evaluation {index}/{len(cases)} {control['id']}")
        evaluation = evaluator.evaluate(control, case["evidence"])
        results.append({
            "control": control,
            "evidence": case["evidence"],
            "expected": case.get("expected"),
            "evaluation": evaluation,
            "match": evaluation.get("decision") == case.get("expected"),
        })
    write_json(args.results_out, results)
    print(f"Wrote {len(results)} evaluation results -> {args.results_out}")


def main():
    # Parse CLI arguments and start the pipeline.
    parser = argparse.ArgumentParser(
        description="Directive PDF -> Control Extraction -> Evidence Generation -> Compliance Evaluation"
    )
    parser.add_argument("--pdf", default="data/D48.pdf")
    parser.add_argument("--controls-out", default="data/controls.json")
    parser.add_argument("--evidence-out", default="data/generated_dataset.json")
    parser.add_argument("--results-out", default="data/evaluation_results.json")
    parser.add_argument("--max-controls", type=int, default=None)
    parser.add_argument("--diverse-prefixes", type=int, default=None)
    parser.add_argument("--control-ids", default=None)
    parser.add_argument("--evidence-mode", choices=["template", "llm"], default="template")
    parser.add_argument("--dataset-model", default=None)
    parser.add_argument("--evaluation-mode", choices=["baseline", "rule", "llm"], default="baseline")
    args = parser.parse_args()

    run_pipeline(args)


if __name__ == "__main__":
    main()
