"""Run mock case studies end-to-end in a disposable openLCA IPC server.

Examples:
    uv run python scripts/check_openlca.py foreground
    uv run python scripts/check_openlca.py foreground --case cotton_fiber
    uv run python scripts/check_openlca.py bafu --case plastic_broom
    uv run python scripts/check_openlca.py all
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
import zipfile
from pathlib import Path
from typing import Iterable

import olca_schema as o
from olca_ipc.rest import RestClient

sys.path.insert(0, str(Path(__file__).resolve().parent))
from openlca_server import OpenLcaServer, ROOT, prepare_bafu_template


ENTITY_ORDER = (
    ("unit_groups", o.UnitGroup),
    ("flow_properties", o.FlowProperty),
    ("currencies", o.Currency),
    ("actors", o.Actor),
    ("sources", o.Source),
    ("locations", o.Location),
    ("flows", o.Flow),
    ("parameters", o.Parameter),
    ("processes", o.Process),
    ("lcia_categories", o.ImpactCategory),
    ("lcia_methods", o.ImpactMethod),
)
METHODS_ARCHIVE_SHA256 = "b564e49cfaeb4014645c784b229099462c9bf70fecf27e1a8bd375c03cd2973e"


def _entities(folder: Path, type_: type):
    if not folder.is_dir():
        return
    for path in sorted(folder.glob("*.json")):
        yield type_.from_json(path.read_bytes())


def import_ld(client: RestClient, ld_dir: Path, include: Iterable[str] | None = None):
    started = time.perf_counter()
    selected = set(include) if include is not None else None
    counts = {}
    for folder, type_ in ENTITY_ORDER:
        if selected is not None and folder not in selected:
            continue
        models = list(_entities(ld_dir / folder, type_))
        for model in models:
            if client.put(model) is None:
                raise RuntimeError(f"openLCA rejected {folder}/{model.id}")
        if models:
            counts[folder] = len(models)
    print(
        "Imported:",
        ", ".join(f"{count} {folder}" for folder, count in counts.items()),
        f"({time.perf_counter() - started:.2f}s)",
        flush=True,
    )


def _descriptor(client: RestClient, type_: type, name: str):
    matches = [item for item in client.get_descriptors(type_) if item.name == name]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one {type_.__name__} named {name!r}, found {len(matches)}")
    return matches[0]


def _reference_process(
    client: RestClient,
    reference_product: str,
    process_name: str | None = None,
):
    if process_name is not None:
        descriptor = client.find(o.Process, process_name)
        if descriptor is None:
            raise RuntimeError(f"Process named {process_name!r} was not found")
        process = client.get(o.Process, descriptor.id)
        if process is None:
            raise RuntimeError(f"Process named {process_name!r} could not be read")
        references = [
            exchange
            for exchange in process.exchanges or []
            if exchange.is_quantitative_reference
            and exchange.flow.name == reference_product
        ]
        if len(references) != 1:
            raise RuntimeError(
                f"Process {process_name!r} does not have exactly one quantitative "
                f"reference exchange for {reference_product!r}"
            )
        return process

    matches = []
    for descriptor in client.get_descriptors(o.Process):
        process = client.get(o.Process, descriptor.id)
        if process is None:
            continue
        for exchange in process.exchanges or []:
            if exchange.is_quantitative_reference and exchange.flow.name == reference_product:
                matches.append(process)
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected one process producing {reference_product!r}, found {len(matches)}"
        )
    return matches[0]


def _calculate(client: RestClient, process: o.Process, method_name: str, amount: float = 1.0):
    config = o.LinkingConfig(
        prefer_unit_processes=True,
        provider_linking=o.ProviderLinking.PREFER_DEFAULTS,
    )
    started = time.perf_counter()
    system = client.create_product_system(process, config)
    if system is None:
        raise RuntimeError("openLCA did not create a product system")
    product_system = client.get(o.ProductSystem, system.id)
    if product_system is None:
        raise RuntimeError("Created product system could not be read back")
    print(
        f"Created product system: {len(product_system.processes or [])} processes, "
        f"{len(product_system.process_links or [])} links "
        f"({time.perf_counter() - started:.2f}s)",
        flush=True,
    )

    method = _descriptor(client, o.ImpactMethod, method_name)
    started = time.perf_counter()
    result = client.calculate(
        o.CalculationSetup(target=system, amount=amount, impact_method=method.to_ref())
    )
    state = result.wait_until_ready()
    print(f"Calculation completed ({time.perf_counter() - started:.2f}s)", flush=True)
    if not state.is_ready or state.error:
        raise RuntimeError(f"Calculation did not complete successfully: {state}")
    try:
        impacts = {
            value.impact_category.name: (value.amount, value.impact_category.ref_unit or "")
            for value in result.get_total_impacts()
        }
        scaling = {
            value.tech_flow.provider.name: value.amount
            for value in result.get_scaling_factors()
        }
        return product_system, impacts, scaling
    finally:
        result.dispose()


def _close(actual: float, expected: float, rel_tol: float = 1e-7, abs_tol: float = 1e-10):
    return math.isclose(actual, expected, rel_tol=rel_tol, abs_tol=abs_tol)


def check_foreground_case(case_dir: Path) -> None:
    expected = json.loads((case_dir / "expected.json").read_text())
    with OpenLcaServer(database=f"test-{case_dir.name}") as server:
        client = RestClient(server.endpoint)
        import_ld(client, case_dir / "olca_ld")
        process = _reference_process(client, expected["reference_product"])
        system, impacts, scaling = _calculate(client, process, expected["method_name"])

        expected_processes = len(list((case_dir / "olca_ld" / "processes").glob("*.json")))
        if len(system.processes or []) != expected_processes:
            raise AssertionError(
                f"Product system has {len(system.processes or [])} processes; "
                f"expected {expected_processes}"
            )
        for name, score in expected["impact_scores"].items():
            actual = impacts.get(name, (None, ""))[0]
            if actual is None or not _close(actual, score):
                raise AssertionError(f"{name}: expected {score}, got {actual}")
            print(f"Impact {name}: {actual}  OK")
        for name, amount in expected["scaling_vector"].items():
            actual = scaling.get(name)
            if actual is None or not _close(actual, amount):
                raise AssertionError(f"Scaling {name}: expected {amount}, got {actual}")
            print(f"Scaling {name}: {actual}  OK")
    print(f"PASS foreground/{case_dir.name}")


def _import_ef31(client: RestClient, archive: Path) -> str:
    started = time.perf_counter()
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != METHODS_ARCHIVE_SHA256:
        raise RuntimeError(
            f"Unexpected checksum for {archive.name}: expected "
            f"{METHODS_ARCHIVE_SHA256}, got {digest}"
        )
    target_name = "EF 3.1 Method (adapted)"
    with zipfile.ZipFile(archive) as package:
        method_data = None
        for name in package.namelist():
            if not name.startswith("lcia_methods/") or not name.endswith(".json"):
                continue
            candidate = json.loads(package.read(name))
            if candidate.get("name") == target_name:
                method_data = candidate
                break
        if method_data is None:
            raise RuntimeError(f"{target_name} not found in {archive}")
        method = o.ImpactMethod.from_json(json.dumps(method_data))
        for ref in method.impact_categories or []:
            category_name = f"lcia_categories/{ref.id}.json"
            category = o.ImpactCategory.from_json(package.read(category_name))
            if client.put(category) is None:
                raise RuntimeError(f"openLCA rejected impact category {ref.name}")
        if client.put(method) is None:
            raise RuntimeError(f"openLCA rejected impact method {target_name}")
    print(
        f"Imported {target_name} ({len(method.impact_categories or [])} categories) "
        f"({time.perf_counter() - started:.2f}s)",
        flush=True,
    )
    return target_name


def check_bafu_case(case_dir: Path, bafu_archive: Path, methods_archive: Path) -> None:
    expected = json.loads((case_dir / "expected.json").read_text())
    manifest = json.loads((case_dir / "providers.json").read_text())
    cache = Path(os.environ.get("OPENLCA_TEST_CACHE", ROOT / ".openlca-test-cache"))
    template = prepare_bafu_template(
        bafu_archive,
        cache,
        manifest["background"]["openlca_archive_sha256"],
    )
    with OpenLcaServer(database="bafu", template=template) as server:
        client = RestClient(server.endpoint)
        method_name = _import_ef31(client, methods_archive)
        import_ld(client, case_dir / "olca_ld", include=("flows", "processes"))
        process_files = list((case_dir / "olca_ld" / "processes").glob("*.json"))
        if len(process_files) != 1:
            raise RuntimeError(
                f"Expected one foreground process for {case_dir.name}, "
                f"found {len(process_files)}"
            )
        process_name = json.loads(process_files[0].read_text())["name"]
        process = _reference_process(
            client,
            expected["functional_unit"]["flow"],
            process_name=process_name,
        )
        system, impacts, _ = _calculate(
            client, process, method_name, expected["functional_unit"]["amount"]
        )
        if len(system.processes or []) <= 4:
            raise AssertionError(
                "BAFU product system did not recursively include background processes"
            )
        rel_tol = expected.get("openlca_relative_tolerance", 5e-6)
        for name, item in expected["scores"].items():
            openlca_name = item.get("openlca_category", name)
            actual = impacts.get(openlca_name, (None, ""))[0]
            if actual is None or not _close(actual, item["score"], rel_tol=rel_tol):
                raise AssertionError(
                    f"{name} ({openlca_name}): expected {item['score']}, got {actual}"
                )
            print(f"Impact {name}: {actual}  OK")
    print(f"PASS bafu/{case_dir.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite", choices=("foreground", "bafu", "all"))
    parser.add_argument("--case", help="run one case instead of the complete suite")
    parser.add_argument(
        "--bafu-archive",
        type=Path,
        default=ROOT / "source_data" / "bafu" / "BAFU-2026 v1_openLCA.zip",
    )
    parser.add_argument(
        "--methods-archive",
        type=Path,
        default=(
            ROOT
            / "source_data"
            / "methods"
            / "openLCA LCIA Methods 2.8.0 2025-12-15.zip"
        ),
    )
    args = parser.parse_args()

    if args.suite in ("foreground", "all"):
        cases = [ROOT / "case_studies" / args.case] if args.case else sorted(
            path for path in (ROOT / "case_studies").iterdir() if path.is_dir()
        )
        for case in cases:
            check_foreground_case(case)

    if args.suite in ("bafu", "all"):
        name = args.case or "plastic_broom"
        check_bafu_case(
            ROOT / "bafu_case_studies" / name,
            args.bafu_archive,
            args.methods_archive,
        )


if __name__ == "__main__":
    main()
