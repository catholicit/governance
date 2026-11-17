#!/usr/bin/env python3
"""Count member votes on open pull requests and merge the ones that pass.

Voters (admins + members in org.yaml) and rules (governance.yml) come from the
base branch (the checked-out copy), never from the pull request itself, so a
proposal cannot add voters for its own benefit.

A vote is an APPROVE review on the pull request's current head commit; pushing
new commits resets the votes. The author counts as a YES if they are a member.
"""
import argparse
import base64
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
import gh  # noqa: E402

MARKER = "<!-- governance-quorum -->"


def parse_time(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def tally(repo, pr, members):
    head = pr["head"]["sha"]
    latest = {}
    for r in gh.paginate(f"/repos/{repo}/pulls/{pr['number']}/reviews"):
        user = (r.get("user") or {}).get("login", "").lower()
        if user not in members or r["state"] not in ("APPROVED", "CHANGES_REQUESTED", "DISMISSED"):
            continue
        latest[user] = r  # reviews come oldest first
    yes, no = set(), set()
    for user, r in latest.items():
        if r.get("commit_id") != head:
            continue
        if r["state"] == "APPROVED":
            yes.add(user)
        elif r["state"] == "CHANGES_REQUESTED":
            no.add(user)
    author = pr["user"]["login"].lower()
    if author in members and author not in no:
        yes.add(author)
    return yes, no


def upsert_comment(repo, number, body):
    body = f"{MARKER}\n{body}"
    for c in gh.paginate(f"/repos/{repo}/issues/{number}/comments"):
        if MARKER in (c.get("body") or "") and c["user"]["type"] == "Bot":
            if c["body"].strip() != body.strip():
                gh.patch(f"/repos/{repo}/issues/comments/{c['id']}", {"body": body})
            return
    gh.post(f"/repos/{repo}/issues/{number}/comments", {"body": body})


def org_plan(pr):
    """Peribolos dry run of the PR's org.yaml (read as data only, never executed)."""
    here = Path(__file__).parent
    try:
        f = gh.get(f"/repos/{pr['head']['repo']['full_name']}/contents/org.yaml?ref={pr['head']['sha']}")
        content = base64.b64decode(f["content"]).decode()
        yaml.safe_load(content)
    except (gh.GitHubError, KeyError, TypeError, yaml.YAMLError) as e:
        return f"org.yaml iz PR-a nije dohvatljiv ili nije ispravan YAML: {e}"
    with tempfile.TemporaryDirectory() as d:
        src, out = Path(d, "org.yaml"), Path(d, "rendered.yaml")
        src.write_text(content)
        r = subprocess.run([sys.executable, str(here / "render.py"), "--org-config", str(src)],
                           capture_output=True, text=True)
        if r.returncode:
            return f"render.py nije uspio:\n{r.stderr.strip()}"
        out.write_text(r.stdout)
        run = subprocess.run([str(here / "peribolos.sh"), str(out)], capture_output=True, text=True)
        plan = subprocess.run([sys.executable, str(here / "peribolos_plan.py")],
                              input=run.stdout + run.stderr, capture_output=True, text=True)
        return plan.stdout.strip()


def process(repo, pr, cfg, members):
    plan_text = org_plan(pr)
    n = len(members)
    needed = n // 2 + 1
    min_hours = (cfg.get("quorum") or {}).get("min_open_hours", 24)
    yes, no = tally(repo, pr, members)
    opened = parse_time(pr["created_at"])
    earliest = opened + timedelta(hours=min_hours)
    now = datetime.now(timezone.utc)
    unanimous = len(yes) == n
    passed = len(yes) >= needed and (unanimous or now >= earliest)

    lines = [
        "### Glasanje",
        "",
        f"Članova: **{n}** · potrebno ZA: **{needed}** · ZA: **{len(yes)}** · PROTIV: **{len(no)}**",
        "",
        f"ZA: {', '.join('@' + u for u in sorted(yes)) or '-'}  ",
        f"PROTIV: {', '.join('@' + u for u in sorted(no)) or '-'}  ",
        f"Najranije spajanje bez jednoglasnosti: {earliest.strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "Glasa se recenzijom (**Approve** = ZA, **Request changes** = PROTIV) na zadnjem commitu; "
        "novi commit poništava glasove. Autor-član se računa kao ZA. Ponovno prebrojavanje: "
        "komentar `/prebroji` ili automatski svakih 15 minuta.",
    ]
    if pr.get("draft"):
        lines += ["", "Draft PR se ne spaja dok nije označen kao spreman."]
        passed = False
    if plan_text:
        lines += ["", "<details><summary>Što će se promijeniti u organizaciji</summary>", "",
                  "```", plan_text.strip(), "```", "</details>"]

    if passed:
        try:
            gh.put(f"/repos/{repo}/pulls/{pr['number']}/merge",
                   {"merge_method": "squash", "sha": pr["head"]["sha"]})
            lines += ["", f"✅ Prijedlog je prihvaćen ({len(yes)}/{n}) i spojen."]
            print(f"#{pr['number']}: merged ({len(yes)}/{n})")
        except gh.GitHubError as e:
            lines += ["", f"⚠️ Prijedlog je prihvaćen, ali spajanje nije uspjelo: `{e.status}`"]
            print(f"#{pr['number']}: merge failed: {e}")
    else:
        print(f"#{pr['number']}: {len(yes)}/{needed} yes, not merged")
    upsert_comment(repo, pr["number"], "\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--org-config", default="org.yaml")
    ap.add_argument("--governance", default="governance.yml")
    ap.add_argument("--pr", type=int)
    args = ap.parse_args()

    repo = os.environ["GITHUB_REPOSITORY"]
    cfg = yaml.safe_load(Path(args.governance).read_text()) or {}
    org_cfg = yaml.safe_load(Path(args.org_config).read_text())
    members = set()
    for org in org_cfg["orgs"].values():
        members |= {u.strip().lower() for u in (org.get("admins") or []) + (org.get("members") or [])}
    if not members:
        raise SystemExit("no voters in base org.yaml")

    if args.pr:
        prs = [gh.get(f"/repos/{repo}/pulls/{args.pr}")]
    else:
        prs = gh.paginate(f"/repos/{repo}/pulls?state=open")
    for pr in prs:
        if pr["state"] != "open" or pr["base"]["ref"] != "main":
            continue
        process(repo, pr, cfg, members)


if __name__ == "__main__":
    main()
