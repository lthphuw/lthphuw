#!/usr/bin/env python3
"""Refresh the auto-generated part of the Open source section in README.md.

Only the text between <!-- os:start --> and <!-- os:end --> is touched, so any
pinned lines written by hand above the marker survive untouched.
"""

import json
import pathlib
import re
import subprocess
import sys
import urllib.parse

README = pathlib.Path(__file__).resolve().parent.parent / "README.md"
START = "<!-- os:start -->"
END = "<!-- os:end -->"
AUTHOR = "lthphuw"
# Merged pull requests the author opened against somebody else's repository.
SEARCH = f"is:pr is:merged author:{AUTHOR} -user:{AUTHOR}"
LIMIT = 8

# Any rendered star count, used to compare two blocks while ignoring stars.
STARS = re.compile(r"★[\d.]+k?")

QUERY = """
query($q: String!, $n: Int!) {
  search(query: $q, type: ISSUE, first: $n) {
    issueCount
    nodes {
      ... on PullRequest {
        number
        title
        url
        additions
        deletions
        repository { nameWithOwner stargazerCount }
      }
    }
  }
}
"""


def fetch():
    out = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={QUERY}",
         "-f", f"q={SEARCH} sort:updated-desc", "-F", f"n={LIMIT}"],
        check=True, capture_output=True, text=True,
    ).stdout
    search = json.loads(out)["data"]["search"]
    return [n for n in search["nodes"] if n], search["issueCount"]


def stars(n):
    if n < 1000:
        return str(n)
    return f"{n / 1000:.1f}".removesuffix(".0") + "k"


def repo_url(repo):
    q = urllib.parse.quote_plus(f"is:pr is:merged author:{AUTHOR}")
    return f"https://github.com/{repo}/pulls?q={q}"


def all_url():
    q = urllib.parse.quote_plus(SEARCH)
    return f"https://github.com/search?q={q}&type=pullrequests"


def render(prs, total):
    groups = {}
    for pr in prs:
        groups.setdefault(pr["repository"]["nameWithOwner"], []).append(pr)

    chunks = []
    for repo, items in groups.items():
        star = stars(items[0]["repository"]["stargazerCount"])
        lines = [f"**[{repo}]({repo_url(repo)})** ★{star}"]
        lines += [
            f'- [#{pr["number"]}]({pr["url"]}) — {pr["title"]} '
            f'`+{pr["additions"]} −{pr["deletions"]}`'
            for pr in items
        ]
        chunks.append("\n".join(lines))

    # Without this the pull requests past LIMIT would just vanish, and the
    # section would read as the complete list of contributions.
    hidden = total - len(prs)
    if hidden > 0:
        chunks.append(f"[+{hidden} more merged pull requests]({all_url()})")
    return "\n\n".join(chunks)


def main():
    prs, total = fetch()
    if not prs:
        print("search returned no pull requests; leaving README.md alone",
              file=sys.stderr)
        return 1

    text = README.read_text(encoding="utf-8")
    pattern = re.compile(f"{re.escape(START)}.*?{re.escape(END)}", re.S)
    current = pattern.search(text)
    if not current:
        print(f"markers {START} / {END} not found in README.md", file=sys.stderr)
        return 1

    block = f"{START}\n{render(prs, total)}\n{END}"

    # Star counts drift on their own, with no work from us. Left alone that
    # would commit a new README most days just to move ★9.6k to ★9.7k, so a
    # block that differs only in stars is treated as no change at all; stars
    # ride along the next time a pull request actually changes.
    if STARS.sub("★", current.group()) == STARS.sub("★", block):
        print("no pull request changes (star drift ignored)")
        return 0

    # lambda replacement: PR titles may contain backslashes, which re.sub would
    # otherwise interpret as escape sequences.
    README.write_text(pattern.sub(lambda _: block, text), encoding="utf-8")
    print(f"rendered {len(prs)} of {total} pull requests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
