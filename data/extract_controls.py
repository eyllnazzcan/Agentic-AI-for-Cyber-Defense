import re


CONTROL_ID_PATTERN = re.compile(
    r"""
    \b
    (?P<id>
        (?:[A-Z]{2,5}\s*\d+\s*-\s*\d+)
        |
        (?:(?:SM|SC)\s*-\s*[A-Z0-9]{2,}(?:\s*-\s*[A-Z0-9]{2,})+)
    )
    """,
    re.VERBOSE,
)

LEGACY_CONTROL_PREFIXES = {
    "AC",
    "AM",
    "AU",
    "CA",
    "CM",
    "CP",
    "DA",
    "DCS",
    "IAM",
    "IA",
    "IR",
    "LMA",
    "MA",
    "MP",
    "PE",
    "PHM",
    "PL",
    "PM",
    "POS",
    "PS",
    "PSW",
    "RA",
    "SA",
    "SC",
    "SI",
    "SMT",
}


def normalize_control_id(control_id):
    # Normalize spacing around a control ID.
    control_id = re.sub(r"\s+", "", control_id)
    control_id = re.sub(r"\s*-\s*", "-", control_id)
    return control_id


def clean_control_description(description):
    # Remove PDF noise and formatting artifacts from a control description.
    description = description.replace("\ufffd", " ")

    noisy_lines = {
        "NATO UNCLASSIFIED",
        "Releasable to North Macedonia",
        "ANNEX 1",
        "APPENDIX C",
        "ID",
        "Security Measure",
        "Security Control",
        "Remarks",
    }

    cleaned_lines = []
    for line in description.splitlines():
        line = " ".join(line.split())
        if not line:
            continue
        if line in noisy_lines:
            continue
        if line.startswith("Section "):
            continue
        if re.fullmatch(r"(?:\d+-\d+|\d+|AC/\d+.*|NC/NS/CTS.*|NU/NR.*)", line):
            continue
        cleaned_lines.append(line)

    description = " ".join(cleaned_lines)
    description = re.sub(r"\s+Section\s+[A-Z0-9].*$", "", description)
    description = re.sub(r"\s+\d+-\d+\s+\d+(?:\.\d+)+\s+.*$", "", description)
    description = re.sub(r"\s+NATO\s+UNCLASSIFIED.*$", "", description)
    description = re.sub(r"\s+ANNEX\s+.*$", "", description)
    description = re.sub(r"\s+APPENDIX\s+.*$", "", description)
    description = re.sub(r"\s+(?:M|R|N/A)(?:\s+(?:M|R|N/A)){1,}.*$", "", description)
    description = re.sub(r"\s+[,.;:]", lambda match: match.group(0).strip(), description)
    description = fix_pdf_spacing(description)
    description = re.sub(r"\s+", " ", description).strip()
    return description.rstrip(" .;:")


def fix_pdf_spacing(text):
    # Fix common word spacing issues introduced by PDF text extraction.
    replacements = {
        "p rovide": "provide",
        "a nd": "and",
        "spee d": "speed",
        "organisation al": "organisational",
        "organis ation": "organisation",
        "secur ity": "security",
        "passwo rds": "passwords",
        "requir ements": "requirements",
        "Securi ty": "Security",
        "r eference": "reference",
    }

    for broken, fixed in replacements.items():
        text = text.replace(broken, fixed)

    return text


def extract_controls(text, min_description_length=20):
    # Extract unique control IDs and descriptions from directive text.
    matches = list(CONTROL_ID_PATTERN.finditer(text))
    allowed_legacy_prefixes = {
        match.group(1)
        for match in re.finditer(r"\bSection\s+([A-Z]{2,5})\s*\d+\s*:", text)
    }
    controls = []
    seen = set()

    for index, match in enumerate(matches):
        control_id = normalize_control_id(match.group("id"))
        if not control_id.startswith(("SM-", "SC-")):
            legacy_prefix = re.match(r"([A-Z]+)", control_id).group(1)
            if legacy_prefix not in LEGACY_CONTROL_PREFIXES:
                continue
            if allowed_legacy_prefixes and legacy_prefix not in allowed_legacy_prefixes:
                continue

        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        description = clean_control_description(text[start:end])

        if len(description) < min_description_length:
            continue

        if description[0] in ",.;:":
            continue

        if is_table_of_contents_entry(description):
            continue

        if control_id in seen:
            continue

        seen.add(control_id)
        controls.append({
            "id": control_id,
            "description": description,
        })

    return controls


def control_prefix(control_id):
    # Return the family prefix of a control ID, such as PHM, IAM, or CP.
    if control_id.startswith(("SM-", "SC-")):
        return control_id.split("-", 1)[0]

    match = re.match(r"([A-Z]+)", control_id)
    if match:
        return match.group(1)

    return control_id


def select_distinct_prefix_controls(controls, count):
    # Select the first controls that belong to different control prefixes.
    selected = []
    seen_prefixes = set()

    for control in controls:
        prefix = control_prefix(control["id"])
        if prefix in seen_prefixes:
            continue

        seen_prefixes.add(prefix)
        selected.append(control)

        if len(selected) == count:
            break

    return selected


def select_controls_by_ids(controls, control_ids):
    # Select controls by exact ID while preserving the requested order.
    controls_by_id = {
        control["id"]: control
        for control in controls
    }
    selected = []
    missing_ids = []

    for control_id in control_ids:
        control = controls_by_id.get(control_id)
        if control:
            selected.append(control)
        else:
            missing_ids.append(control_id)

    if missing_ids:
        raise ValueError(f"Control IDs not found: {', '.join(missing_ids)}")

    return selected


def is_table_of_contents_entry(description):
    # Detect descriptions that look like table-of-contents entries.
    toc_terms = [
        "C3B Taxonomy",
        "CIS Security Capability Breakdown",
        "CIS Security Measures Organisation",
        "CIS Protection:",
    ]

    return any(term in description for term in toc_terms)
