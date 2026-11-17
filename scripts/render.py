#!/usr/bin/env python3
"""Render the final Peribolos config.

Takes org.yaml and adds every organization repository to the `all_repos` team
from governance.yml, unless org.yaml already names that repository for the
team. Peribolos itself has no wildcard, and with --fix-team-repos it would
otherwise strip the team from repositories created later.

Usage: render.py [--org-config org.yaml] [--governance governance.yml] > out.yaml
"""
import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
import gh  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--org-config", default="org.yaml")
    ap.add_argument("--governance", default="governance.yml")
    args = ap.parse_args()

    cfg = yaml.safe_load(Path(args.org_config).read_text())
    gov = yaml.safe_load(Path(args.governance).read_text()) or {}
    rule = gov.get("all_repos")
    if rule:
        for org_name, org in cfg["orgs"].items():
            team = org.setdefault("teams", {}).setdefault(rule["team"], {})
            repos = team.get("repos") or {}
            for repo in gh.paginate(f"/orgs/{org_name}/repos?type=all"):
                if not repo.get("archived") and repo["name"] not in repos:
                    repos[repo["name"]] = rule["permission"]
            team["repos"] = dict(sorted(repos.items()))
    yaml.safe_dump(cfg, sys.stdout, sort_keys=False, allow_unicode=True)


if __name__ == "__main__":
    main()
