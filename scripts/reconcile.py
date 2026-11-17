#!/usr/bin/env python3
"""Make the GitHub organization match members.yml.

Dry run by default; pass --apply to change anything.
Needs GH_TOKEN with org members/administration write (the governance App token).
"""
import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
import gh  # noqa: E402

PERMISSION_ALIASES = {"read": "pull", "write": "push"}


def load_config(path):
    cfg = yaml.safe_load(Path(path).read_text())
    members = [m["github"].strip() for m in cfg.get("members") or [] if m.get("github")]
    if not members:
        raise SystemExit("members.yml has no members; refusing to empty the organization")
    lower = [m.lower() for m in members]
    dupes = {m for m in lower if lower.count(m) > 1}
    if dupes:
        raise SystemExit(f"duplicate members: {', '.join(sorted(dupes))}")
    owners = [o.strip() for o in cfg.get("owners") or []]
    if not owners:
        raise SystemExit("owners list is empty; the organization needs at least one owner")
    return cfg, members, owners


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="members.yml")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    cfg, members, owners = load_config(args.config)
    org = cfg["org"]
    team = cfg.get("team", "core")
    perm = PERMISSION_ALIASES.get(cfg.get("repo_permission", "admin"), cfg.get("repo_permission", "admin"))
    restricted = {k: PERMISSION_ALIASES.get(v, v) for k, v in (cfg.get("restricted_repos") or {}).items()}

    wanted = {m.lower(): m for m in members}
    owners_l = {o.lower() for o in owners}
    actions = []  # (description, callable)

    def plan(desc, fn):
        actions.append((desc, fn))

    # --- current state -------------------------------------------------------
    org_members = {u["login"].lower(): u["login"] for u in gh.paginate(f"/orgs/{org}/members?role=all")}
    org_owners = {u["login"].lower() for u in gh.paginate(f"/orgs/{org}/members?role=admin")}
    invitations = gh.paginate(f"/orgs/{org}/invitations")
    invited = {i["login"].lower(): i for i in invitations if i.get("login")}

    try:
        gh.get(f"/orgs/{org}/teams/{team}")
        team_exists = True
        team_members = {u["login"].lower() for u in gh.paginate(f"/orgs/{org}/teams/{team}/members")}
        team_repos = {r["name"]: r.get("role_name") for r in gh.paginate(f"/orgs/{org}/teams/{team}/repos")}
    except gh.GitHubError as e:
        if e.status != 404:
            raise
        team_exists, team_members, team_repos = False, set(), {}

    # --- team ----------------------------------------------------------------
    if not team_exists:
        plan(f"create team '{team}'", lambda: gh.post(f"/orgs/{org}/teams", {"name": team, "privacy": "closed"}))

    # --- members -------------------------------------------------------------
    for key, login in sorted(wanted.items()):
        if key in org_members:
            if key not in team_members:
                plan(f"add {login} to team '{team}'",
                     lambda l=login: gh.put(f"/orgs/{org}/teams/{team}/memberships/{l}", {"role": "member"}))
        elif key in invited:
            pass  # invitation already pending
        else:
            plan(f"invite {login} to the organization (via team '{team}')",
                 lambda l=login: gh.put(f"/orgs/{org}/teams/{team}/memberships/{l}", {"role": "member"}))

    for key in sorted(team_members - set(wanted)):
        plan(f"remove {key} from team '{team}'",
             lambda k=key: gh.delete(f"/orgs/{org}/teams/{team}/memberships/{k}"))

    # --- owners --------------------------------------------------------------
    listed_owners_present = org_owners & owners_l
    for key in sorted(org_owners - owners_l):
        if not listed_owners_present:
            print(f"WARNING: {key} is an owner but not listed in owners:, and no listed owner holds "
                  f"the role yet; not demoting so the organization keeps an owner.")
            continue
        if key in wanted:
            plan(f"demote owner {key} to member",
                 lambda k=key: gh.put(f"/orgs/{org}/memberships/{k}", {"role": "member"}))
    for key in sorted(owners_l - org_owners):
        print(f"NOTE: {key} is listed in owners: but is not an owner. Promotion is manual "
              f"(an existing owner must do it); the bot never creates owners.")

    # --- removals ------------------------------------------------------------
    for key, login in sorted(org_members.items()):
        if key in wanted or key in owners_l:
            continue
        if key in org_owners and not listed_owners_present:
            continue  # warned above
        plan(f"remove {login} from the organization",
             lambda l=login: gh.delete(f"/orgs/{org}/memberships/{l}"))
    for key, inv in sorted(invited.items()):
        if key not in wanted:
            plan(f"cancel invitation for {inv['login']}",
                 lambda i=inv: gh.delete(f"/orgs/{org}/invitations/{i['id']}"))

    # --- repositories --------------------------------------------------------
    for repo in gh.paginate(f"/orgs/{org}/repos?type=all"):
        if repo.get("archived"):
            continue
        name = repo["name"]
        want = restricted.get(name, perm)
        have = team_repos.get(name)
        # role_name uses read/write for pull/push
        have_norm = PERMISSION_ALIASES.get(have, have)
        if have_norm != want:
            plan(f"set team '{team}' permission on {name}: {have or 'none'} -> {want}",
                 lambda n=name, w=want: gh.put(f"/orgs/{org}/teams/{team}/repos/{org}/{n}", {"permission": w}))

    # --- org settings --------------------------------------------------------
    settings = cfg.get("org_settings") or {}
    if settings:
        current = gh.get(f"/orgs/{org}")
        diff = {k: v for k, v in settings.items() if current.get(k) != v}
        if diff:
            plan(f"update org settings: {diff}", lambda d=diff: gh.patch(f"/orgs/{org}", d))

    # --- execute -------------------------------------------------------------
    if not actions:
        print("No changes: the organization matches members.yml.")
        return
    print(f"{'Applying' if args.apply else 'Plan'} ({len(actions)} change(s)):")
    failed = 0
    for desc, fn in actions:
        print(f"  - {desc}")
        if args.apply:
            try:
                fn()
            except gh.GitHubError as e:
                failed += 1
                print(f"    FAILED: {e}")
    if failed:
        raise SystemExit(f"{failed} change(s) failed")


if __name__ == "__main__":
    main()
