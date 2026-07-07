"""
Zip up a case study's checked-in olca_ld/ directory into an importable
mock_lca.zip release asset. The zip itself is not committed to git --
regenerate it any time from the checked-in JSON-LD folder.

Usage:
    python scripts/make_release.py <case_study_dir>
    python scripts/make_release.py case_studies/mock_widget
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ld_dir import zip_ld_dir

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    case_dir = sys.argv[1]
    ld_dir = os.path.join(case_dir, "olca_ld")
    zpath = os.path.join(case_dir, "mock_lca.zip")
    if not os.path.isdir(ld_dir):
        print(f"No olca_ld/ directory found at {ld_dir} -- run build.py first.")
        sys.exit(1)
    zip_ld_dir(ld_dir, zpath)
    print("Wrote", zpath)
