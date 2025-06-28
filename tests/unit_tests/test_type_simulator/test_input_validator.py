import json
import tempfile
import os
from pathlib import Path
import pytest
from type_simulator.validation import validate_inputs
from type_simulator.type_simulator import Mode

CASES_PATH = os.path.join(os.path.dirname(__file__), "input_validator_cases.json")

with open(CASES_PATH) as f:
    CASES = json.load(f)


def prepare_path(placeholder, temp_resources):
    if placeholder == "TEMPFILE":
        tf = tempfile.NamedTemporaryFile(delete=False)
        temp_resources.append(tf)
        tf.close()
        return tf.name
    elif placeholder == "TEMPDIR":
        td = tempfile.TemporaryDirectory()
        temp_resources.append(td)
        return td.name
    elif placeholder == "NONEXISTENT":
        return "/nonexistent/file.txt"
    else:
        return placeholder


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_input_validator_cases(case):
    temp_resources = []
    file_path = prepare_path(case["file"], temp_resources)
    mode = getattr(Mode, case["mode"])
    is_valid, errors, warnings = validate_inputs(
        mode, file_path, case["editor_cmd"], case["text"]
    )
    assert (
        is_valid == case["is_valid"]
    ), f"Case '{case['name']}' validity mismatch. Errors: {errors}, Warnings: {warnings}"
    for err_sub in case.get("errors", []):
        assert any(
            err_sub in e for e in errors
        ), f"Case '{case['name']}' missing error: {err_sub}"
    for warn_sub in case.get("warnings", []):
        assert any(
            warn_sub in w for w in warnings
        ), f"Case '{case['name']}' missing warning: {warn_sub}"
