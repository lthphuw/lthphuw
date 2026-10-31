#!/usr/bin/env python3
"""Refresh the generated parts of README.md.

Two blocks are written: Selected Work, between <!-- feat:start --> and
<!-- feat:end -->, from the hand-picked list in .github/featured.json, and
Contributions, between <!-- os:start --> and <!-- os:end -->. Everything outside
the markers, such as the Abstract, survives.

Both are plain Markdown: no images, so nothing to keep in step with the text.
"""

import json
import pathlib
import re
import subprocess
import sys
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
START = "<!-- os:start -->"
END = "<!-- os:end -->"
FEAT_START = "<!-- feat:start -->"
FEAT_END = "<!-- feat:end -->"
# What to feature is a choice, so it is written by hand; numbers and dates are
# not, and come from the API like everything else.
FEATURED = ROOT / ".github" / "featured.json"
AUTHOR = "lthphuw"
# Merged pull requests the author opened against somebody else's repository.
SEARCH = f"is:pr is:merged author:{AUTHOR} -user:{AUTHOR}"
# The search API caps one page at 100, and the search is ordered by last update,
# not by merge; past that the per-repository counts undercount and a global link
# covers the rest.
LIMIT = 100
# Pull requests listed per repository; the rest collapse into a "+N more" link
# that belongs to that repository.
SHOW = 3

# Between the fields of a line: two spaces either side of a bar. Only the last
# space can break, so a wrapped line ends on a bar instead of starting with one.
SEP = "&nbsp;&nbsp;|&nbsp; "

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


def md_title(text):
    """A pull request title as Markdown: `code` spans kept as code, and the
    rest escaped so that a stray * or _ in it formats nothing. Runs of spaces
    collapse, as some titles carry a few by accident."""
    # The split keeps the code spans at the odd indices.
    parts = re.split(r"(`[^`]+`)", " ".join(text.split()))
    return "".join(
        part if i % 2 else
        re.sub(r"([\\`*_\[\]<>#|~])", r"\\\1", part.replace("&", "&amp;"))
        for i, part in enumerate(parts))


def pr_link(pr):
    return f'[`#{pr["number"]}`]({pr["url"]})'


def featured(items, by_key):
    """The Selected Work block: a bold title linked to the first pull request,
    the repository it went into, a sentence or two on what was built, and a
    line linking every pull request of the item. What to say is a choice, so it
    lives in featured.json; the pull requests are only looked up, to link them
    and to warn about one that is not a fetched merged pull request (not
    merged, or past LIMIT). A missing one is skipped rather than failing the
    refresh, and an item whose first pull request is missing is left out."""
    chunks = []
    for item in items:
        found = []
        for number in item["prs"]:
            pr = by_key.get((item["repo"], number))
            if pr is None:
                print(f"featured: {item['repo']}#{number} is not a fetched "
                      f"merged pull request; skipping it", file=sys.stderr)
            else:
                found.append(pr)
        if found and found[0]["number"] == item["prs"][0]:
            # <br> and the text on one line: a newline after <br> would
            # make a second break.
            repo = item["repo"]
            links = " · ".join(pr_link(pr) for pr in found)
            chunks.append(f'**[{item["title"]}]({found[0]["url"]})**'
                          f'&nbsp;&nbsp;[`{repo}`](https://github.com/{repo})<br>'
                          f'{item["text"]}<br>{links}')
    return "\n\n".join(chunks)


def repo_url(repo):
    q = urllib.parse.quote_plus(f"is:pr is:merged author:{AUTHOR}")
    return f"https://github.com/{repo}/pulls?q={q}"


def all_url():
    q = urllib.parse.quote_plus(SEARCH)
    return f"https://github.com/search?q={q}&type=pullrequests"


def render(prs, total):
    # Newest merge first, which orders the pull requests inside a repository.
    prs = sorted(prs, key=lambda pr: pr["mergedAt"], reverse=True)
    groups = {}
    for pr in prs:
        groups.setdefault(pr["repository"]["nameWithOwner"], []).append(pr)

    # Most merged pull requests first, then most stars. sorted() is stable and
    # the groups were created in order of their latest merge, so that is what
    # breaks a tie in both.
    ranked = sorted(groups.items(),
                    key=lambda g: (-len(g[1]),
                                   -g[1][0]["repository"]["stargazerCount"]))

    chunks = []
    for repo, items in ranked:
        star = stars(items[0]["repository"]["stargazerCount"])
        added = sum(pr["additions"] for pr in items)
        removed = sum(pr["deletions"] for pr in items)
        # One paragraph per repository, its lines joined by <br>: the paragraph
        # margin is the space between repositories, and rows stay one line
        # apart. A list would put its own margin between a title and its rows.
        lines = [f"**[{repo}](https://github.com/{repo})** ★{star}"
                 f" · [{len(items)} merged]({repo_url(repo)})"
                 f" · +{added} −{removed}"]
        lines += [f"{pr_link(pr)}{SEP}{md_title(pr['title'])}"
                  for pr in items[:SHOW]]
        hidden = len(items) - SHOW
        if hidden > 0:
            lines.append(f"[+{hidden} more →]({repo_url(repo)})")
        chunks.append("<br>\n".join(lines))

    # Only reachable past LIMIT: those pull requests were never fetched, so
    # they cannot be attributed to a repository.
    unfetched = total - len(prs)
    if unfetched > 0:
        chunks.append(f"[+{unfetched} more merged pull requests]({all_url()})")
    return "\n\n".join(chunks)


def block_pattern(start, end):
    return re.compile(f"{re.escape(start)}.*?{re.escape(end)}", re.S)


def main():
    prs, total = fetch()
    if not prs:
        print("search returned no pull requests; leaving README.md alone",
              file=sys.stderr)
        return 1

    text = README.read_text(encoding="utf-8")
    os_pattern = block_pattern(START, END)
    feat_pattern = block_pattern(FEAT_START, FEAT_END)
    for pattern, start, end in ((os_pattern, START, END),
                                (feat_pattern, FEAT_START, FEAT_END)):
        if not pattern.search(text):
            print(f"markers {start} / {end} not found in README.md",
                  file=sys.stderr)
            return 1

    by_key = {(pr["repository"]["nameWithOwner"], pr["number"]): pr
              for pr in prs}
    feat_body = featured(json.loads(FEATURED.read_text(encoding="utf-8")),
                         by_key)
    os_block = f"{START}\n{render(prs, total)}\n{END}"
    feat_block = f"{FEAT_START}\n{feat_body}\n{FEAT_END}"

    # lambda replacement: PR titles may contain backslashes, which re.sub would
    # otherwise interpret as escape sequences.
    new = os_pattern.sub(lambda _: os_block, text)
    new = feat_pattern.sub(lambda _: feat_block, new)

    # Star counts drift on their own, with no work from us. Left alone that
    # would commit a new README most days just to move ★9.6k to ★9.7k, so a
    # README that differs only in stars is treated as no change at all; stars
    # ride along the next time a pull request actually changes.
    if STARS.sub("★", new) == STARS.sub("★", text):
        print("no pull request changes (star drift ignored)")
        return 0

    README.write_text(new, encoding="utf-8")
    print(f"rendered {len(prs)} of {total} pull requests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
