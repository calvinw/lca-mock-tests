"""
Shared helper: write olca_schema entities to an expanded, human-readable
JSON-LD directory (the same folder layout olca-schema zips use internally),
and zip that directory up for import into Brightway/openLCA.

The expanded directory is the checked-in source of truth for each case
study's database structure; the zip is a derived, regenerate-on-demand
build artifact.
"""
import os
import shutil
import zipfile

import olca_schema as o

_FOLDER_BY_TYPE = {
    o.Flow: "flows",
    o.Process: "processes",
    o.ImpactCategory: "lcia_categories",
    o.ImpactMethod: "lcia_methods",
    o.UnitGroup: "unit_groups",
}


def write_ld_dir(outdir, entities):
    if os.path.exists(outdir):
        shutil.rmtree(outdir)
    os.makedirs(outdir)
    with open(os.path.join(outdir, "olca-schema.json"), "w") as fh:
        fh.write('{"version": 2}')
    for entity in entities:
        folder = _FOLDER_BY_TYPE[type(entity)]
        folder_path = os.path.join(outdir, folder)
        os.makedirs(folder_path, exist_ok=True)
        with open(os.path.join(folder_path, f"{entity.id}.json"), "w") as fh:
            fh.write(entity.to_json())
    return outdir


def zip_ld_dir(ld_dir, zpath):
    if os.path.exists(zpath):
        os.remove(zpath)
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(ld_dir):
            for name in files:
                full_path = os.path.join(root, name)
                arcname = os.path.relpath(full_path, ld_dir)
                zf.write(full_path, arcname)
    return zpath
