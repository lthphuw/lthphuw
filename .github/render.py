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

ROOT = pathlib.Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
# One small SVG per distinct "+a −d" pair, referenced from README.md.
DIFF_DIR = "assets/diff"
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

# Between the fields of a line: two spaces either side of a bar. Only the last
# space can break, so a wrapped line ends on a bar instead of starting with one.
SEP = "&nbsp;&nbsp;|&nbsp; "

# Any rendered star count, used to compare two blocks while ignoring stars.
STARS = re.compile(r"★[\d.]+k?")

# Diff stats are drawn as SVG because Markdown on GitHub strips CSS: an image
# is the only way to get a smaller size, another font and colour at once.
# Monospace makes the width computable without measuring text; textLength
# absorbs the small spread between fonts (Consolas 0.55em, most others 0.6em).
MONO = ("ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,"
        "'Liberation Mono',monospace")
SIZE = 12      # px, a notch under the 14px profile text
HEIGHT = 12
# An inline image sits with its bottom edge on the text baseline. Lifting the
# digits' own baseline slightly off that edge centres them on the 14px digits
# around them instead of bottom-aligning them.
BASELINE = HEIGHT - 0.8
DIFF_SVG = re.compile(rf"{DIFF_DIR}/(\d+)-(\d+)\.svg")

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


def diff(additions, deletions, url):
    src = f"{DIFF_DIR}/{additions}-{deletions}.svg"
    alt = f"+{additions} −{deletions}"
    # The link matters: an unlinked image on GitHub opens the image itself.
    return f'[<img src="{src}" alt="{alt}">]({url})'


def diff_svg(additions, deletions):
    # No thousands separator: at 12px a monospace comma reads as a full stop.
    added, removed = f"+{additions}", f"−{deletions}"
    char = 0.6 * SIZE
    wa, wr = len(added) * char, len(removed) * char
    width = wa + char + wr
    # Colours are GitHub's diff green and red. prefers-color-scheme follows the
    # viewer's system theme, which is what GitHub's default theme follows too.
    return f"""\
<svg xmlns="http://www.w3.org/2000/svg" width="{width:g}" height="{HEIGHT}" \
viewBox="0 0 {width:g} {HEIGHT}">
<style>
text {{ font: 500 {SIZE}px {MONO}; }}
.a {{ fill: #1a7f37; }} .d {{ fill: #d1242f; }}
@media (prefers-color-scheme: dark) {{ .a {{ fill: #3fb950; }} .d {{ fill: #f85149; }} }}
</style>
<text class="a" x="0" y="{BASELINE:g}" textLength="{wa:g}" \
lengthAdjust="spacing">{added}</text>
<text class="d" x="{wa + char:g}" y="{BASELINE:g}" textLength="{wr:g}" \
lengthAdjust="spacing">{removed}</text>
</svg>
"""


def sync_svgs(block):
    """Write the SVGs the block references and delete the ones it no longer does."""
    out = ROOT / DIFF_DIR
    out.mkdir(parents=True, exist_ok=True)
    wanted = {f"{a}-{d}.svg": diff_svg(int(a), int(d))
              for a, d in DIFF_SVG.findall(block)}
    for path in out.glob("*.svg"):
        if path.name not in wanted:
            path.unlink()
    for name, svg in wanted.items():
        (out / name).write_text(svg, encoding="utf-8")


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
                     sum(pr["deletions"] for pr in items), repo_url(repo))
        lines = [SEP.join([f"**[{repo}]({repo_url(repo)})**", f"★{star}",
                           f"{len(items)} merged", churn])]
        for pr in items[:SHOW]:
            # Number first, in code font: within a repository the numbers share
            # a width, so they line up into a column like a changelog.
            fields = [f'[`#{pr["number"]}`]({pr["url"]})', pr["title"],
                      diff(pr["additions"], pr["deletions"], f'{pr["url"]}/files')]
            lines.append(f"- {SEP.join(fields)}")
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
    sync_svgs(block)
    print(f"rendered {len(prs)} of {total} pull requests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
