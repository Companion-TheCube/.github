#!/usr/bin/env python3
import os
import base64
import requests
import sys
from datetime import datetime

# ─── CONFIGURATION ─────────────────────────────────────────────────────────────

# Personal access token with 'repo' scope (set in env or paste here)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

ORG          = "Companion-TheCube"
REPO         = "TheCube-apps-directory"
BRANCH       = "main"
README_PATH  = "README.md"

API_ROOT = "https://api.github.com"
HEADERS   = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept":        "application/vnd.github.v3+json"
}

# ─── HELPERS ────────────────────────────────────────────────────────────────────

def list_app_repos():
    """Return list of {name, url, description} for every App-* repo."""
    apps, page = [], 1
    while True:
        resp = requests.get(
            f"{API_ROOT}/orgs/{ORG}/repos",
            params={"per_page":100, "page":page},
            headers=HEADERS
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        for r in batch:
            if r["name"].startswith("App-"):
                apps.append({
                    "name":        r["name"],
                    "url":         r["html_url"],
                    "description": (r.get("description") or "").strip()
                })
        page += 1
    return sorted(apps, key=lambda a: a["name"].lower())

def get_readme():
    """Fetch and decode the current README.md; return (text, sha)."""
    resp = requests.get(
        f"{API_ROOT}/repos/{ORG}/{REPO}/contents/{README_PATH}?ref={BRANCH}",
        headers=HEADERS
    )
    resp.raise_for_status()
    data   = resp.json()
    sha    = data["sha"]
    b64    = data["content"]
    text   = base64.b64decode(b64).decode("utf-8")
    return text, sha

def split_readme_lines(lines):
    """
    Split into (preamble_lines, community_lines).
    Preamble is everything before '## Apps'.
    Community is from '## Community Apps' onward (including that header).
    """
    apps_idx  = next((i for i, l in enumerate(lines) if l.strip() == "## Apps"), None)
    comm_idx  = next((i for i, l in enumerate(lines) if l.strip() == "## Community Apps"), None)

    if apps_idx is None:
        # no Apps header: treat entire file as preamble
        return lines, []

    # preamble is up to apps_idx
    preamble = lines[:apps_idx]

    # community is from comm_idx onward, if present
    community = lines[comm_idx:] if comm_idx is not None else []

    return preamble, community

def build_apps_lines(apps):
    """Return a list of lines for the '## Apps' section."""
    lines = ["## Apps", ""]
    for a in apps:
        desc = f" — {a['description']}" if a["description"] else ""
        lines.append(f"- [{a['name']}]({a['url']}){desc}")
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    lines += ["", f"_Last updated: {ts}_", ""]
    return lines

def update_readme(new_text, sha):
    """Encode and PUT the updated README.md back to GitHub."""
    b64   = base64.b64encode(new_text.encode("utf-8")).decode("utf-8")
    data  = {
        "message": "chore: update Apps section",
        "content": b64,
        "sha":     sha,
        "branch":  BRANCH
    }
    resp = requests.put(
        f"{API_ROOT}/repos/{ORG}/{REPO}/contents/{README_PATH}",
        headers=HEADERS,
        json=data
    )
    resp.raise_for_status()
    return resp.json()

# ─── MAIN ───────────────────────────────────────────────────────────────────────

def main():
    if not GITHUB_TOKEN or not GITHUB_TOKEN.startswith("ghp_"):
        print("❌ Please set GITHUB_TOKEN (with repo scope).", file=sys.stderr)
        sys.exit(1)

    # 1) Grab existing README and SHA
    text, sha = get_readme()

    # 2) Split into lines, then preamble + community
    lines       = text.splitlines()
    preamble, community = split_readme_lines(lines)

    # 3) Fetch apps & build new Apps section
    apps      = list_app_repos()
    apps_lines = build_apps_lines(apps)

    # 4) Reassemble
    new_lines = preamble + apps_lines + community
    new_text  = "\n".join(new_lines).rstrip() + "\n"

    # 5) Only push if changed
    if new_text == text:
        print("ℹ️  No changes in Apps section; skipping update.")
        return

    print("📤 Pushing updated README.md…")
    result = update_readme(new_text, sha)
    print("✅ README.md updated:", result["commit"]["html_url"])

if __name__ == "__main__":
    main()
