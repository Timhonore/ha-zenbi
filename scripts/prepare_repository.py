"""Set real repository metadata before publishing to GitHub/HACS."""
import argparse
import json
from pathlib import Path
import re

parser = argparse.ArgumentParser()
parser.add_argument("--repo", required=True, help="owner/repository")
args = parser.parse_args()
if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repo):
    parser.error("Use owner/repository")
root = Path(__file__).resolve().parents[1]
path = root / "custom_components/zenbi/manifest.json"
manifest = json.loads(path.read_text())
manifest.update(documentation=f"https://github.com/{args.repo}#readme",
                issue_tracker=f"https://github.com/{args.repo}/issues",
                codeowners=[f"@{args.repo.split('/')[0]}"])
path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
print(f"Repository metadata prepared for {args.repo}")
