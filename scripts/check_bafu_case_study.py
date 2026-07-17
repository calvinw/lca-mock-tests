"""Build, import, and calculate one BAFU-backed foreground case study."""

import argparse
import atexit
import json
import math
import runpy
import uuid
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("case_dir", type=Path)
    parser.add_argument("--background-database", default="bafu")
    args = parser.parse_args()

    case_dir = args.case_dir.resolve()
    runpy.run_path(str(case_dir / "build.py"), run_name="__main__")

    from prepare_bafu_brightway import prepare

    template_project = prepare()

    import bw2data as bd
    from lca_core import LCAEngine

    from import_bafu_foreground import import_bafu_foreground

    test_project = f"bafu-test-{case_dir.name}-{uuid.uuid4().hex[:8]}"
    bd.projects.set_current(template_project)
    bd.projects.copy_project(test_project, switch=True)

    def cleanup():
        try:
            bd.projects.set_current(template_project)
            if test_project in bd.projects:
                bd.projects.delete_project(test_project, delete_dir=True)
        except Exception as error:
            print(f"WARNING: could not remove disposable project {test_project}: {error}")

    atexit.register(cleanup)
    expected = json.loads((case_dir / "expected.json").read_text())
    foreground_database = expected["foreground_database"]
    linked = import_bafu_foreground(
        case_dir / "olca_ld",
        case_dir / "providers.json",
        foreground_database,
        args.background_database,
    )

    foreground = bd.Database(foreground_database)
    product = next(
        node
        for node in foreground
        if node.get("type") == "product"
        and node.get("name") == expected["functional_unit"]["flow"]
    )
    assembly = next(
        node
        for node in foreground
        if node.get("name") == "Plastic broom assembly"
        and node.get("type") != "product"
    )

    actual_inputs = {
        exchange.input.key: exchange["amount"]
        for exchange in assembly.technosphere()
    }
    manifest = json.loads((case_dir / "providers.json").read_text())
    expected_inputs = {
        (args.background_database, provider["brightway_code"]): provider["amount"]
        for provider in manifest["providers"]
    }
    if actual_inputs != expected_inputs:
        raise AssertionError(
            f"Foreground links differ: expected {expected_inputs}, got {actual_inputs}"
        )

    method_name = expected["method_name"]
    engine = LCAEngine()
    results = {}
    for category, target in expected["scores"].items():
        result = engine.calculate_imported_activity(
            foreground_database,
            method_name,
            category,
            project=test_project,
            code=product["code"],
            amount=expected["functional_unit"]["amount"],
        )
        actual = result["score"]
        wanted = target["score"]
        if not math.isclose(actual, wanted, rel_tol=1e-8, abs_tol=1e-10):
            raise AssertionError(
                f"{category}: expected {wanted}, got {actual}"
            )
        results[category] = {
            "score": actual,
            "unit": result["unit"],
        }

    print(f"Linked {len(linked)} foreground exchanges to '{args.background_database}'")
    for category, result in results.items():
        print(f"{category}: {result['score']} {result['unit']}  OK")
    cleanup()
    atexit.unregister(cleanup)


if __name__ == "__main__":
    main()
