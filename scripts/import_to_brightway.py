"""
Generic script: extract an olca-schema JSON-LD zip and import it into
a Brightway project using bw2io's native JSONLDImporter / JSONLDLCIAImporter.

Usage:
    python scripts/import_to_brightway.py <path_to_zip> <db_name> <project_name>
"""
import os
import sys
import zipfile
import shutil

def import_jsonld(zip_path, db_name, project_name, bw_dir=None):
    if bw_dir is None:
        bw_dir = os.path.join(os.path.dirname(zip_path), ".bw_project")
    os.makedirs(bw_dir, exist_ok=True)
    os.environ["BRIGHTWAY2_DIR"] = bw_dir

    extract_dir = os.path.join(os.path.dirname(zip_path), "_extracted")
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
    os.makedirs(extract_dir)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(extract_dir)
    # bw2io's extractor requires this key to exist even if empty
    os.makedirs(os.path.join(extract_dir, "locations"), exist_ok=True)

    import bw2data as bd
    bd.projects.set_current(project_name)
    for db in list(bd.databases):
        del bd.databases[db]
    for m in list(bd.methods):
        del bd.methods[m]

    from bw2io.importers.json_ld import JSONLDImporter
    from bw2io.importers.json_ld_lcia import JSONLDLCIAImporter

    imp = JSONLDImporter(extract_dir, db_name)
    imp.apply_strategies(no_warning=True)
    imp.statistics()
    imp.write_separate_biosphere_database()
    imp.write_database()

    lcia_imp = JSONLDLCIAImporter(extract_dir)
    lcia_imp.apply_strategies()
    lcia_imp.match_biosphere_by_id(f"{db_name} biosphere")
    lcia_imp.statistics()
    lcia_imp.write_methods()

    return bw_dir


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    used_bw_dir = import_jsonld(sys.argv[1], sys.argv[2], sys.argv[3])
    print(f"Done. BRIGHTWAY2_DIR used: {used_bw_dir}")
