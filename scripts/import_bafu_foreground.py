"""Import a foreground JSON-LD package and link it to an existing BAFU database.

The stock bw2io JSON-LD importer only links within its current import batch.
This module preserves that importer pipeline, then resolves external exchanges
using the process/flow UUID to Brightway-code bridge in providers.json.
"""

import json
from pathlib import Path


NORMALIZED_UNITS = {
    "kg": "kilogram",
    "tkm": "ton kilometer",
    "unit": "unit",
}


def import_bafu_foreground(ld_dir, manifest_path, foreground_database, background_database=None):
    import bw2data as bd
    from bw2io.importers.json_ld import JSONLDImporter

    ld_dir = Path(ld_dir)
    manifest = json.loads(Path(manifest_path).read_text())
    background_database = background_database or manifest["background"]["brightway_database"]
    if background_database not in bd.databases:
        raise RuntimeError(
            f"Required background database '{background_database}' is not installed"
        )

    by_process = {item["process_uuid"]: item for item in manifest["providers"]}
    by_flow = {item["flow_uuid"]: item for item in manifest["providers"]}

    importer = JSONLDImporter(ld_dir, foreground_database)
    importer.apply_strategies(no_warning=True)

    linked = []
    for dataset in importer.data:
        for exchange in dataset.get("exchanges", []):
            if exchange.get("type") != "technosphere" or exchange.get("input"):
                continue
            provider_ref = exchange.get("defaultProvider") or {}
            provider = by_process.get(provider_ref.get("@id")) or by_flow.get(exchange.get("code"))
            if provider is None:
                raise RuntimeError(
                    f"No BAFU provider mapping for technosphere exchange "
                    f"'{exchange.get('name')}' ({exchange.get('code')})"
                )

            activity = bd.get_node(
                database=background_database,
                code=provider["brightway_code"],
            )
            expected_unit = NORMALIZED_UNITS[provider["unit"]]
            actual = {
                "name": activity.get("name"),
                "location": activity.get("location"),
                "unit": activity.get("unit"),
            }
            expected = {
                "name": provider["process_name"],
                "location": provider["location"],
                "unit": expected_unit,
            }
            if actual != expected:
                raise RuntimeError(
                    f"BAFU provider {provider['brightway_code']} does not match manifest: "
                    f"expected {expected}, got {actual}"
                )
            filename = activity.get("filename", "")
            if provider["process_uuid"] not in filename:
                raise RuntimeError(
                    f"BAFU provider {provider['brightway_code']} has unexpected source "
                    f"filename '{filename}'"
                )

            exchange["input"] = activity.key
            exchange.pop("defaultProvider", None)
            linked.append(
                {
                    "exchange": exchange["name"],
                    "input": list(activity.key),
                    "process_uuid": provider["process_uuid"],
                    "flow_uuid": provider["flow_uuid"],
                }
            )

    expected_count = len(manifest["providers"])
    if len(linked) != expected_count:
        raise RuntimeError(
            f"Expected to link {expected_count} BAFU exchanges, linked {len(linked)}"
        )

    unlinked = [
        (dataset.get("name"), exchange.get("name"), exchange.get("type"))
        for dataset in importer.data
        for exchange in dataset.get("exchanges", [])
        if exchange.get("type") in {"production", "technosphere"}
        and not exchange.get("input")
    ]
    if unlinked:
        raise RuntimeError(f"Unlinked foreground exchanges remain: {unlinked}")

    if foreground_database in bd.databases:
        del bd.databases[foreground_database]
    importer.write_database()
    return linked
