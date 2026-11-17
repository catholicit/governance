"""Minimal GitHub REST client (stdlib only)."""
import json
import os
import urllib.error
import urllib.request

API = "https://api.github.com"


class GitHubError(Exception):
    def __init__(self, status, body, method, path):
        super().__init__(f"{method} {path} -> {status}: {body[:300]}")
        self.status = status


def _request(method, path, data=None):
    url = path if path.startswith("http") else API + path
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {os.environ['GH_TOKEN']}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else None), resp.headers
    except urllib.error.HTTPError as e:
        raise GitHubError(e.code, e.read().decode(errors="replace"), method, path) from None


def get(path):
    return _request("GET", path)[1]


def paginate(path):
    sep = "&" if "?" in path else "?"
    url = f"{path}{sep}per_page=100"
    out = []
    while url:
        _, data, headers = _request("GET", url)
        out.extend(data)
        url = None
        for part in (headers.get("Link") or "").split(","):
            if 'rel="next"' in part:
                url = part[part.index("<") + 1 : part.index(">")]
    return out


def put(path, data=None):
    return _request("PUT", path, data if data is not None else {})[1]


def post(path, data):
    return _request("POST", path, data)[1]


def patch(path, data):
    return _request("PATCH", path, data)[1]


def delete(path):
    return _request("DELETE", path)[1]
