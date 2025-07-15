#!/usr/bin/env python3
import os
import requests
import subprocess
import sys
from datetime import datetime

# ─── CONFIG ─────────────────────────────────────────────────────────────────────

# Your GitHub token (with repo scope)
GITHUB_TOKEN = os.getenv("ORG_PAT") or "ghp_your_token_here"

# Org and repo names
ORG            = "Companion-TheCube"
DIRECTORY_REPO = "TheCube-apps-directory"
DEFAULT_BRANCH = "main"

# ─── HELPERS ────────────────────────────────────────────────────────────────────

def run(cmd, **kw):
    print(f"> {' '.join(cmd)}")
    subprocess.run(cmd, check=True, **kw)

def fetch_app_repos():
    """Get all App-* repos from the org via REST."""
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    apps = []
    page = 1
    while True:
        r = requests.get(
            f"https://api.github.com/orgs/{ORG}/repos",
            params={"per_page":100, "page":page},
            headers=headers
        )
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        for repo in batch:
            name = repo["name"]
            if name.startswith("App-") and not name.startswith("AppExample"):
                apps.append({
                    "name": name,
                    "url":  repo["html_url"],
                    "desc": repo.get("description") or ""
                })
        page += 1
    return sorted(apps, key=lambda x: x["name"].lower())

def build_readme(apps):
    """Return a single multiline string with real newlines."""
    header = (
        "# TheCube Apps Directory\n\n"
        "A directory of all official **TheCube** applications, with links to their repos and short descriptions.\n\n"
        "## Apps\n\n"
    )
    # build each bullet line
    bullets = []
    for a in apps:
        if a["desc"]:
            bullets.append(f"- [{a['name']}]({a['url']}) — {a['desc']}")
        else:
            bullets.append(f"- [{a['name']}]({a['url']})")
    body = "\n".join(bullets)
    footer = f"\n_Last updated: {datetime.utcnow().isoformat()} UTC_\n"
    return header + body + footer

# ─── MAIN ───────────────────────────────────────────────────────────────────────

def main():
    if not GITHUB_TOKEN.startswith("ghp_"):
        print("❌ Please set GITHUB_TOKEN (with repo scope).", file=sys.stderr)
        sys.exit(1)

    # 1) clone (or update) the directory repo
    if not os.path.isdir(DIRECTORY_REPO):
        run(["git", "clone", f"https://x-access-token:{GITHUB_TOKEN}@github.com/{ORG}/{DIRECTORY_REPO}.git"])
    else:
        run(["git", "-C", DIRECTORY_REPO, "fetch", "origin"])
        run(["git", "-C", DIRECTORY_REPO, "checkout", DEFAULT_BRANCH])
        run(["git", "-C", DIRECTORY_REPO, "pull", "origin", DEFAULT_BRANCH])

    # 2) fetch your App-* repos
    print("🔍 Fetching App-* repos…")
    apps = fetch_app_repos()
    print(f"✅ Found {len(apps)} apps.\n")

    # 3) build README content
    print("📄 Building README.md…")
    readme_md = build_readme(apps)

    # 4) write it out
    readme_path = os.path.join(DIRECTORY_REPO, "README.md")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_md)

    # 5) commit & push if changed
    run(["git", "-C", DIRECTORY_REPO, "add", "README.md"])
    # check if anything to commit
    status = subprocess.run(
        ["git", "-C", DIRECTORY_REPO, "status", "--porcelain"],
        capture_output=True, text=True
    ).stdout.strip()
    if status:
        run(["git", "-C", DIRECTORY_REPO, "config", "user.name", "github-actions[bot]"])
        run(["git", "-C", DIRECTORY_REPO, "config", "user.email", "github-actions[bot]@users.noreply.github.com"])
        run(["git", "-C", DIRECTORY_REPO, "commit", "-m", "chore: update apps directory"])
        run(["git", "-C", DIRECTORY_REPO, "push", "origin", DEFAULT_BRANCH])
        print("✅ Pushed updated README.md")
    else:
        print("🚫 No changes to commit.")

if __name__ == "__main__":
    main()
