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
# The search API caps one page at 100; past that the per-repository counts
# undercount and a global link covers the rest.
LIMIT = 100
# Pull requests listed per repository; the rest collapse into a "+N more" link
# that belongs to that repository.
SHOW = 5

# Any rendered star count, used to compare two blocks while ignoring stars.
STARS = re.compile(r"★[\d.]+k?")

# GitHub strips CSS and <font> from Markdown, so inline math is the only way
# to colour text. Named colours, not hex: some renderers (KaTeX, IDE previews)
# reject "#" inside math. One colour has to serve both themes, and these two
# keep roughly 4:1 contrast on light and on dark.
# Both numbers sit in one formula so a narrow screen cannot wrap between them.
DIFF = r"${\color{forestgreen}\textsf{+%s}}\ {\color{indianred}\textsf{−%s}}$"

# Conventional-commit prefix such as "fix(export): ". The type is dropped and
# the scope moves into the metadata after the title.
PREFIX = re.compile(
    r"^(?:feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)"
    r"(?:\((?P<scope>[^)]*)\))?!?:\s*"
)

QUERY = """
query($q: String!, $n: Int!) {
  search(query: $q, type: ISSUE, first: $n) {
    issueCount
    nodes {
      ... on PullRequest {
        number
        title
        url
        mergedAt
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


def split_title(title):
    m = PREFIX.match(title)
    if not m:
        return title, None
    rest = title[m.end():]
    # Capitalise "keep fp16 ..." but leave "iOS ..." alone.
    if rest.split(" ", 1)[0].islower():
        rest = rest[:1].upper() + rest[1:]
    return rest, m["scope"]


def diff(additions, deletions):
    return DIFF % (f"{additions:,}", f"{deletions:,}")


def repo_url(repo):
    q = urllib.parse.quote_plus(f"is:pr is:merged author:{AUTHOR}")
    return f"https://github.com/{repo}/pulls?q={q}"


def all_url():
    q = urllib.parse.quote_plus(SEARCH)
    return f"https://github.com/search?q={q}&type=pullrequests"


def render(prs, total):
    # Newest merge first, so repositories are ordered by their latest merge.
    prs = sorted(prs, key=lambda pr: pr["mergedAt"], reverse=True)
    groups = {}
    for pr in prs:
        groups.setdefault(pr["repository"]["nameWithOwner"], []).append(pr)

    chunks = []
    for repo, items in groups.items():
        star = stars(items[0]["repository"]["stargazerCount"])
        churn = diff(sum(pr["additions"] for pr in items),
                     sum(pr["deletions"] for pr in items))
        lines = [f"**[{repo}]({repo_url(repo)})** · ★{star} · "
                 f"{len(items)} merged · {churn}"]
        for pr in items[:SHOW]:
            title, scope = split_title(pr["title"])
            meta = [scope] if scope else []
            meta += [f'[#{pr["number"]}]({pr["url"]})',
                     diff(pr["additions"], pr["deletions"])]
            lines.append(f'- {title} · {" · ".join(meta)}')
        hidden = len(items) - SHOW
        if hidden > 0:
            lines.append(f"- [+{hidden} more →]({repo_url(repo)})")
        chunks.append("\n".join(lines))

    # Only reachable past LIMIT: those pull requests were never fetched, so
    # they cannot be attributed to a repository.
    unfetched = total - len(prs)
    if unfetched > 0:
        chunks.append(f"[+{unfetched} more merged pull requests]({all_url()})")
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
