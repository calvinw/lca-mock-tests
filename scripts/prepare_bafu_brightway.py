"""Prepare a cached Brightway BAFU project from the downloaded EcoSpold ZIP.

Stack:
  biosphere3     — standard Brightway elementary flows
  bafu           — 11k processes from BAFU EcoSpold V1 Nexus zip (includes ecoinvent 2.x background)
  LCIA methods   — bw2io default methods (EF 3.1, ReCiPe, etc.)

Parser adapted from romainsacchi/BAFU2BW notebook.

Run once (later calls verify and reuse the cache):
    python scripts/prepare_bafu_brightway.py

Idempotent — skips any step already completed.

File layout:
    source_data/bafu/BAFU-2026 v1_ecoSpold v1.zip  (gitignored)
    resources/elementary_flows_mapping.csv          (checked in)
"""

import ast
import csv
import hashlib
import html
import json
import math
import os
import pathlib
import re
import sys
import tempfile
import zipfile

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if "BRIGHTWAY2_DIR" not in os.environ:
    _bw_dir = ROOT / ".brightway-test-cache"
    _bw_dir.mkdir(parents=True, exist_ok=True)
    os.environ["BRIGHTWAY2_DIR"] = str(_bw_dir)

SOURCE_DIR = ROOT / "source_data" / "bafu"
BAFU_ARCHIVE = SOURCE_DIR / "BAFU-2026 v1_ecoSpold v1.zip"
BAFU_ARCHIVE_SHA256 = "ebaab56717a6227b5eb271fcb4c86fb9db206115eb937fb0ec0b10d7accf26c7"
TEMPLATE_PROJECT = f"bafu-template-{BAFU_ARCHIVE_SHA256[:12]}"
BAFU_DB_NAME = "bafu"

# ── unit normalisation (EcoSpold abbreviations → Brightway names) ─────────────
UNITS_MAP = {
    "kg": "kilogram",
    "tkm": "ton kilometer",
    "p": "unit",
    "kWh": "kilowatt hour",
    "MJ": "megajoule",
    "m2": "square meter",
    "m": "meter",
    "Nm3": "cubic meter",
    "km": "kilometer",
    "personkm": "person-kilometer",
    "my": "meter-year",
    "unit": "unit",
    "m3": "cubic meter",
    "m2a": "square meter-year",
    "kmy": "kilometer-year",
    "a": "year",
    "m3y": "cubic meter-year",
    "kBq": "kilo Becquerel",
    "ha": "hectare",
    "Bq": "Becquerel",
    "hr": "hour",
}

# ── biosphere category mapping → biosphere3 tuples ───────────────────────────
CATS_MAP = {
    ("emissions to air", "unspecified"): ("air",),
    ("emissions to air", "high. pop."): ("air", "urban air close to ground"),
    ("emissions to air", "low. pop."): ("air", "non-urban air or from high stacks"),
    ("emissions to air", "stratosphere + troposphere"): ("air", "lower stratosphere + upper troposphere"),
    ("emissions to air", "low. pop., long-term"): ("air", "low population density, long-term"),
    ("emissions to air", "indoor"): ("air", "urban air close to ground"),
    ("emissions to soil", "unspecified"): ("soil",),
    ("emissions to soil", "forestry"): ("soil", "forestry"),
    ("emissions to soil", "agricultural"): ("soil", "agricultural"),
    ("emissions to soil", "industrial"): ("soil", "industrial"),
    ("emissions to water", "ocean"): ("water", "ocean"),
    ("emissions to water", "river"): ("water", "surface water"),
    ("emissions to water", "unspecified"): ("water",),
    ("emissions to water", "groundwater, long-term"): ("water", "ground-, long-term"),
    ("emissions to water", "groundwater"): ("water", "ground-"),
    ("emissions to water", "lake"): ("water", "surface water"),
    ("emissions to water", "river, long-term"): ("water", "surface water"),
    ("emissions to water", "fossilwater"): ("water", "fossil well"),
    ("economic issues", "unspecified"): ("economic", "primary production factor"),
    ("resources", "in ground"): ("natural resource", "in ground"),
    ("resources", "land"): ("natural resource", "land"),
    ("resources", "in water"): ("natural resource", "in water"),
    ("resources", "in air"): ("natural resource", "in air"),
    ("resources", "biotic"): ("natural resource", "biotic"),
}

NAME_LOC_RE = re.compile(r"^(.*)\s+\{([^{}]+)\}\s*$")


def _get_first(elem, xpath):
    res = elem.xpath(xpath)
    return res[0] if res else None


def _get_attr(elem, name, default=None):
    return elem.get(name) if elem is not None and elem.get(name) is not None else default


def _strip_location(name, current_location=None):
    if not name:
        return name, current_location
    m = NAME_LOC_RE.match(name)
    if not m:
        return name, current_location
    base, loc = m.groups()
    return base.strip(), (loc.strip() or current_location)


def _clean_comment(text):
    if not text:
        return ""
    t = html.unescape(text)
    t = re.sub(r"UUID:.*$", "", t, flags=re.S)
    lines = [ln.strip() for ln in t.replace("\r\n", "\n").split("\n") if ln.strip()]
    return "\n".join(lines)


def _uncertainty(exc_xml, data):
    from stats_arrays.distributions import (
        LognormalUncertainty, NormalUncertainty, TriangularUncertainty,
        UniformUncertainty, UndefinedUncertainty,
    )
    def f(x):
        try:
            return float((x or "").strip()) if isinstance(x, str) else float(x)
        except Exception:
            return np.nan

    try:
        utype = int(exc_xml.get("uncertaintyType", 0))
    except ValueError:
        utype = 0

    mean   = f(exc_xml.get("meanValue"))
    min_   = f(exc_xml.get("minValue"))
    max_   = f(exc_xml.get("maxValue"))
    sig95  = f(exc_xml.get("standardDeviation95"))

    if utype == 1 and (sig95 in (0, 1) or np.isnan(sig95)):
        utype = 0

    if utype == 1 and mean != 0 and not np.isnan(mean):
        data.update({"uncertainty type": LognormalUncertainty.id, "amount": float(mean),
                     "loc": math.log(abs(mean)), "scale": math.log(math.sqrt(float(sig95))),
                     "negative": mean < 0})
    elif utype == 2:
        data.update({"uncertainty type": NormalUncertainty.id, "amount": float(mean),
                     "loc": float(mean), "scale": float(sig95) / 2.0})
    elif utype == 3:
        mode = f(exc_xml.get("mostLikelyValue"))
        amt = mode if not np.isnan(mode) else float(mean)
        data.update({"uncertainty type": TriangularUncertainty.id, "amount": amt, "loc": amt,
                     "minimum": float(min_), "maximum": float(max_)})
    elif utype == 4:
        data.update({"uncertainty type": UniformUncertainty.id, "amount": float(mean),
                     "minimum": float(min_), "maximum": float(max_)})
    else:
        data.update({"uncertainty type": UndefinedUncertainty.id,
                     "amount": float(mean) if not np.isnan(mean) else 0.0,
                     "loc": float(mean) if not np.isnan(mean) else 0.0})
    return data


# ── Pass 1: build reference index (flow_id → process info) ───────────────────

def _build_ref_index(xml_dir: pathlib.Path) -> dict:
    from lxml import etree
    ref_index = {}
    for xml in xml_dir.rglob("*.xml"):
        try:
            root = etree.parse(str(xml)).getroot()
        except Exception:
            continue
        dataset = _get_first(root, '//*[local-name()="dataset"]')
        if dataset is None:
            continue
        PI  = _get_first(dataset, './/*[local-name()="processInformation"]')
        RF  = _get_first(PI,      './/*[local-name()="referenceFunction"]') if PI is not None else None
        geo = _get_first(PI,      './/*[local-name()="geography"]')          if PI is not None else None
        if RF is None:
            continue
        raw_name     = _get_attr(RF,  "name", "") or ""
        unit         = UNITS_MAP.get(_get_attr(RF, "unit", ""), _get_attr(RF, "unit", ""))
        xml_location = _get_attr(geo, "location", None) or "GLO"
        dataset_num  = _get_attr(dataset, "number", "")
        name, location = _strip_location(raw_name, xml_location)

        flow_data = _get_first(dataset, './/*[local-name()="flowData"]')
        prod_flow_id = None
        if flow_data is not None:
            for exc in flow_data.xpath('./*[local-name()="exchange"]'):
                og = _get_first(exc, './*[local-name()="outputGroup"]')
                if og is not None and (og.text or "").strip() == "0":
                    prod_flow_id = _get_attr(exc, "number", None)
                    if prod_flow_id:
                        break
        flow_id = prod_flow_id or dataset_num
        if not flow_id:
            continue
        ref_index[flow_id] = {
            "activity_code": dataset_num,
            "name": name,
            "reference product": name,
            "location": location,
            "unit": unit,
        }
    return ref_index


# ── Pass 2: parse each file ────────────────────────────────────────────────────

def _parse_file(xml_path: pathlib.Path, db_name: str, ref_index: dict):
    from lxml import etree
    try:
        root = etree.parse(str(xml_path)).getroot()
    except Exception:
        return None

    dataset = _get_first(root, '//*[local-name()="dataset"]')
    if dataset is None:
        return None
    PI  = _get_first(dataset, './/*[local-name()="processInformation"]')
    RF  = _get_first(PI,      './/*[local-name()="referenceFunction"]') if PI is not None else None
    geo = _get_first(PI,      './/*[local-name()="geography"]')          if PI is not None else None
    if RF is None:
        return None

    raw_name     = _get_attr(RF,  "name", "") or ""
    unit         = UNITS_MAP.get(_get_attr(RF, "unit", ""), _get_attr(RF, "unit", ""))
    xml_location = _get_attr(geo, "location", None) or "GLO"
    dataset_num  = _get_attr(dataset, "number", "")
    name, location = _strip_location(raw_name, xml_location)

    category    = _get_attr(RF, "category", None)
    subcategory = _get_attr(RF, "subCategory", None)
    comment     = _clean_comment(_get_attr(RF, "generalComment", ""))

    flow_data = _get_first(dataset, './/*[local-name()="flowData"]')
    exchanges = []
    if flow_data is not None:
        for exc in flow_data.xpath('./*[local-name()="exchange"]'):
            mean_val = _get_attr(exc, "meanValue", None)
            if mean_val is None:
                continue

            raw_ex_name = _get_attr(exc, "name", "") or ""
            ex_unit     = UNITS_MAP.get(_get_attr(exc, "unit", ""), _get_attr(exc, "unit", ""))
            ex_cat      = (_get_attr(exc, "category", "") or "").lower()
            ex_subcat   = (_get_attr(exc, "subCategory", "") or "").lower()
            ex_loc_xml  = _get_attr(exc, "location", None)
            ex_name, ex_loc = _strip_location(raw_ex_name, ex_loc_xml)

            og = _get_first(exc, './*[local-name()="outputGroup"]')
            ig = _get_first(exc, './*[local-name()="inputGroup"]')
            og_val = (og.text or "").strip() if og is not None else None
            ig_val = (ig.text or "").strip() if ig is not None else None

            is_bio_cat = (
                ex_cat.startswith("emissions to ")
                or ex_cat.startswith("emission to ")
                or ex_cat in {"emissions", "emission"}
                or "resource" in ex_cat
                or (ex_cat, ex_subcat) in CATS_MAP
            )

            if og_val == "0":
                ex_type = "production"
            elif is_bio_cat:
                ex_type = "biosphere"
            elif ig_val is not None:
                ex_type = "technosphere"
            else:
                ex_type = "biosphere"

            cat_tuple = CATS_MAP.get((ex_cat, ex_subcat), (ex_cat, ex_subcat))

            exc_dict = {
                "name": ex_name,
                "unit": ex_unit,
                "type": ex_type,
                "categories": cat_tuple,
            }
            if ex_loc:
                exc_dict["location"] = ex_loc

            ex_number = _get_attr(exc, "number", None)
            if ex_number:
                exc_dict["flow"] = ex_number
                if ex_type in ("technosphere", "production"):
                    ref_info = ref_index.get(ex_number)
                    if ref_info is not None:
                        exc_dict["reference product"] = ref_info["reference product"]
                        if not exc_dict.get("location"):
                            exc_dict["location"] = ref_info["location"]

            _uncertainty(exc, exc_dict)
            exchanges.append(exc_dict)

    return {
        "database": db_name,
        "code": dataset_num,
        "name": name,
        "reference product": name,
        "location": location,
        "unit": unit,
        "comment": comment,
        "classifications": [("EcoSpold01Categories", f"{category or ''}/{subcategory or ''}")],
        "exchanges": exchanges,
        "filename": xml_path.name,
        "type": "process",
    }


# ── Crosswalk ─────────────────────────────────────────────────────────────────

def _load_crosswalk() -> dict:
    csv_path = ROOT / "resources" / "elementary_flows_mapping.csv"
    if not csv_path.exists():
        return {}
    mapping = {}
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            bafu_name = row["BAFU name"].strip()
            try:
                bafu_cat = tuple(ast.literal_eval((row["BAFU category"] or "").strip()))
            except Exception:
                continue
            mapping[(bafu_name, bafu_cat)] = {
                "ecoinvent_name": (row.get("Ecoinvent name") or "").strip() or None,
                "ecoinvent_category": (
                    tuple(ast.literal_eval(row["Ecoinvent category"].strip()))
                    if (row.get("Ecoinvent category") or "").strip()
                    else None
                ),
            }
    return mapping


# ── Import steps ──────────────────────────────────────────────────────────────

def import_biosphere(bd, bi):
    if "biosphere3" in bd.databases:
        print(f"  biosphere3 already present ({len(bd.Database('biosphere3'))} flows) — skipping.")
        return
    print("  Installing default biosphere3...")
    bi.create_default_biosphere3()
    print(f"  Done — {len(bd.Database('biosphere3'))} flows.")


def import_bafu(bd, bi, bafu_zip: pathlib.Path):
    if BAFU_DB_NAME in bd.databases:
        n = len(bd.Database(BAFU_DB_NAME))
        print(f"  '{BAFU_DB_NAME}' already present ({n} processes) — skipping.")
        return

    from bw2io.importers.base_lci import LCIImporter

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = pathlib.Path(tmp)
        print(f"  Extracting {bafu_zip.name}...")
        with zipfile.ZipFile(bafu_zip) as zf:
            zf.extractall(tmp_path)

        xml_dir = next(tmp_path.rglob("*.xml")).parent
        xml_files = list(xml_dir.rglob("*.xml"))
        print(f"  Found {len(xml_files)} XML files.")

        print("  Pass 1: building reference index...")
        ref_index = _build_ref_index(xml_dir)
        print(f"  Reference index: {len(ref_index)} entries.")

        print("  Pass 2: parsing all datasets...")
        all_data = []
        for i, xml in enumerate(xml_files):
            if i % 2000 == 0 and i > 0:
                print(f"    {i}/{len(xml_files)}...")
            d = _parse_file(xml, BAFU_DB_NAME, ref_index)
            if d is not None:
                all_data.append(d)
        print(f"  Parsed {len(all_data)} datasets.")

        print("  Applying crosswalk...")
        mapping = _load_crosswalk()
        substituted = 0
        for ds in all_data:
            for exc in ds["exchanges"]:
                if exc["type"] != "biosphere":
                    continue
                k = (exc["name"], exc.get("categories", ()))
                m = mapping.get(k)
                if m:
                    if m["ecoinvent_name"]:
                        exc["name"] = m["ecoinvent_name"]
                        substituted += 1
                    if m["ecoinvent_category"]:
                        exc["categories"] = m["ecoinvent_category"]
        print(f"  Crosswalk substitutions: {substituted}")

        print("  Importing into Brightway...")
        imp = LCIImporter(db_name=BAFU_DB_NAME)
        imp.data = all_data
        imp.apply_strategies()

        # Link technosphere within bafu by name + reference product + location
        imp.match_database(fields=["name", "reference product", "location"])
        # Link biosphere to biosphere3 by name + categories
        imp.match_database("biosphere3", fields=["name", "categories"])

        stats = imp.statistics()
        print(f"  After matching: {stats}")

        from collections import Counter
        unlinked = list(imp.unlinked)
        print(f"  Unlinked: {len(unlinked)}")
        types = Counter(u.get("type") for u in unlinked)
        print(f"    by type: {dict(types)}")
        for u in [x for x in unlinked if x.get("type") == "biosphere"][:5]:
            print(f"    bio: {u.get('name')!r} | {u.get('categories')}")

        imp.drop_unlinked(i_am_reckless=True)
        print(f"  Writing '{BAFU_DB_NAME}'...")
        imp.write_database()
        print(f"  Done — {len(bd.Database(BAFU_DB_NAME))} processes.")


def import_lcia_methods(bd, bi):
    if len(list(bd.methods)) > 100:
        print(f"  LCIA methods already present ({len(list(bd.methods))}) — skipping.")
        return
    print("  Installing default LCIA methods...")
    # bw2io 0.9's shortcut package stores flow keys as JSON lists. Current
    # bw2data correctly requires hashable (database, code) tuples, so normalize
    # the bundled package before writing it.
    from bw2io.importers.base_lcia import LCIAImporter

    package = pathlib.Path(bi.__file__).parent / "data" / "lcia" / "lcia_39_ecoinvent.zip"
    with zipfile.ZipFile(package) as archive:
        data = json.load(archive.open("data.json"))
    for method in data:
        method["name"] = tuple(method["name"])
        for exchange in method.get("exchanges", []):
            if isinstance(exchange.get("input"), list):
                exchange["input"] = tuple(exchange["input"])
    importer = LCIAImporter(package.name)
    importer.data = data
    importer.write_methods(overwrite=True)
    print(f"  Done — {len(list(bd.methods))} methods.")


# ── Main ──────────────────────────────────────────────────────────────────────

def _sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepare() -> str:
    import bw2data as bd
    import bw2io as bi

    if not BAFU_ARCHIVE.is_file():
        raise FileNotFoundError(
            "BAFU EcoSpold source archive is missing. Download it from openLCA "
            f"Nexus and place it at: {BAFU_ARCHIVE}"
        )
    digest = _sha256(BAFU_ARCHIVE)
    if digest != BAFU_ARCHIVE_SHA256:
        raise RuntimeError(
            f"Unexpected checksum for {BAFU_ARCHIVE.name}: expected "
            f"{BAFU_ARCHIVE_SHA256}, got {digest}"
        )

    project = os.environ.get("BRIGHTWAY_TEMPLATE_PROJECT", TEMPLATE_PROJECT)
    bd.projects.set_current(project)
    print(f"Brightway project : {project}")
    print(f"Found BAFU zip: {BAFU_ARCHIVE.name} (checksum OK)")

    print(f"\n── Step 1: biosphere3 ──")
    import_biosphere(bd, bi)

    print(f"\n── Step 2: {BAFU_DB_NAME} ──")
    import_bafu(bd, bi, BAFU_ARCHIVE)

    print(f"\n── Step 3: LCIA methods ──")
    import_lcia_methods(bd, bi)

    print(f"\n── Summary ──")
    for name in bd.databases:
        print(f"  DB  {name}: {len(bd.Database(name))} entries")
    print(f"  Methods: {len(list(bd.methods))}")

    (pathlib.Path(bd.projects.dir) / ".bafu-source-sha256").write_text(digest + "\n")
    print("\nDone.")
    return project


def main():
    prepare()


if __name__ == "__main__":
    main()
