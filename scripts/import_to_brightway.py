"""
Generic script: extract an olca-schema JSON-LD zip and import it into
a Brightway project using bw2io's native JSONLDImporter / JSONLDLCIAImporter.

Usage:
    python scripts/import_to_brightway.py <path_to_zip> <db_name> <project_name>
"""
import os
import sys

def import_jsonld(zip_path, db_name, project_name, bw_dir=None):
    if bw_dir is None:
        bw_dir = os.path.join(os.path.dirname(zip_path), ".bw_project")
    os.makedirs(bw_dir, exist_ok=True)
    os.environ["BRIGHTWAY2_DIR"] = bw_dir

    from lca_core import LCAEngine

    LCAEngine().import_jsonld(
        zip_path,
        db_name,
        project=project_name,
        replace_project_data=True,
    )

    return bw_dir


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    used_bw_dir = import_jsonld(sys.argv[1], sys.argv[2], sys.argv[3])
    print(f"Done. BRIGHTWAY2_DIR used: {used_bw_dir}")
