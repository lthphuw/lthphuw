#!/usr/bin/env python3
"""Refresh the auto-generated part of the Open source section in README.md.

Only the text between <!-- os:start --> and <!-- os:end --> is touched, so any
pinned lines written by hand above the marker survive untouched.
"""

import hashlib
import json
import math
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

# Two SVGs per repository for its title line, named by content (see title()).
REPO_DIR = "assets/repo"
TITLE_SIZE = 15
META_SIZE = 13
# The title is not wrapped in a paragraph (see title()), so nothing but this
# height separates it from the first pull request below: the strip under
# the text and its descenders is the whole gap.
TITLE_HEIGHT = 24
TITLE_BASE = 16          # shared baseline of every text on the title line
TITLE_GAP = 8            # between the repository name and the star
STAR_R = 6.5             # outer radius of the star
# Room kept for the star count whatever it is. A width that followed the text
# would change the README whenever 9.9k became 10k, which the star-drift rule
# in main() exists to avoid.
STAR_CHARS = 5

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


def star_points(cx, cy, r):
    inner = r * 0.382
    pts = []
    for i in range(10):
        radius = r if i % 2 == 0 else inner
        angle = math.pi * i / 5 - math.pi / 2
        pts.append(f"{cx + radius * math.cos(angle):.2f},"
                   f"{cy + radius * math.sin(angle):.2f}")
    return " ".join(pts)


def title_slug(repo):
    return repo.replace("/", "--")


def title_left(repo, star):
    """Repository name and stars: the group that sits against the left edge."""
    owner, name = repo.split("/")
    char = 0.6 * TITLE_SIZE
    wo, wn = (len(owner) + 1) * char, len(name) * char
    star_cx = wo + wn + TITLE_GAP + STAR_R
    star_cy = TITLE_BASE - 0.36 * TITLE_SIZE
    count_x = star_cx + STAR_R + 4
    width = math.ceil(count_x + STAR_CHARS * 0.6 * META_SIZE)
    return f"""\
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{TITLE_HEIGHT}">
<style>
text {{ font-family: {MONO}; }}
.o {{ font-size: {TITLE_SIZE}px; fill: #59636e; }}
.n {{ font-size: {TITLE_SIZE}px; font-weight: 700; fill: #1f2328; }}
.s {{ fill: #9a6700; }}
.c {{ font-size: {META_SIZE}px; font-weight: 500; fill: #59636e; }}
@media (prefers-color-scheme: dark) {{
  .o {{ fill: #9198a1; }} .n {{ fill: #f0f6fc; }} .s {{ fill: #e3b341; }}
  .c {{ fill: #9198a1; }}
}}
</style>
<text class="o" x="0" y="{TITLE_BASE}" textLength="{wo:g}" \
lengthAdjust="spacing">{owner}/</text>
<text class="n" x="{wo:g}" y="{TITLE_BASE}" textLength="{wn:g}" \
lengthAdjust="spacing">{name}</text>
<polygon class="s" points="{star_points(star_cx, star_cy, STAR_R)}"/>
<text class="c" x="{count_x:g}" y="{TITLE_BASE}">{star}</text>
</svg>
""", width


def title_right(merged, additions, deletions):
    """Merged count and diff: one group, anchored at its own right edge."""
    char = 0.6 * META_SIZE
    chars = len(f"{merged} merged") + len(f"+{additions}") + len(f"−{deletions}")
    # 12 and 6 are the gaps drawn below; the slack absorbs font width spread.
    width = math.ceil(chars * char + 12 + 6 + 4)
    return f"""\
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{TITLE_HEIGHT}">
<style>
text {{ font: 500 {META_SIZE}px {MONO}; fill: #59636e; }}
.a {{ fill: #1a7f37; }} .d {{ fill: #d1242f; }}
@media (prefers-color-scheme: dark) {{
  text {{ fill: #9198a1; }} .a {{ fill: #3fb950; }} .d {{ fill: #f85149; }}
}}
</style>
<text x="{width}" y="{TITLE_BASE}" text-anchor="end">{merged} merged\
<tspan class="a" dx="12">+{additions}</tspan>\
<tspan class="d" dx="6">−{deletions}</tspan></text>
</svg>
""", width


def short_hash(svg):
    return hashlib.sha1(svg.encode("utf-8")).hexdigest()[:8]


def title(repo, star, merged, additions, deletions):
    """The title line's Markdown, and the SVGs it references by file name."""
    slug = title_slug(repo)
    left, lw = title_left(repo, star)
    right, rw = title_right(merged, additions, deletions)
    # Named by content, so an image that changes is a new URL. GitHub serves
    # raw files with max-age=300: under an unchanged name, a cached old copy
    # gets squeezed into the new width and height for minutes. The star count
    # is left out of the hash so that drifting stars stay invisible to the
    # README, which is what main() relies on.
    left_name = f"{slug}.{short_hash(title_left(repo, '')[0])}.svg"
    right_name = f"{slug}.pr.{short_hash(right)}.svg"
    # Two images, two links: an image can only carry one. The right one floats
    # and comes second, so on a screen too narrow for both it drops under the
    # left one instead of pushing it out of the way. The clearing break keeps
    # the pull request list from wrapping around it when it does. align="top"
    # stops the left image sitting on the text baseline, which would leave a
    # strip of empty line below it. A <div> rather than Markdown: a paragraph
    # gets a 16px bottom margin from GitHub, a div gets none, and the gap to
    # the list is then the one chosen above. Markdown is not parsed inside it,
    # hence the anchors.
    line = (
        f'<div><a href="https://github.com/{repo}">'
        f'<img src="{REPO_DIR}/{left_name}" align="top" width="{lw}" '
        f'height="{TITLE_HEIGHT}" alt="{repo}, ★{star}"></a>'
        f'<a href="{repo_url(repo)}">'
        f'<img src="{REPO_DIR}/{right_name}" align="right" width="{rw}" '
        f'height="{TITLE_HEIGHT}" alt="{merged} merged, +{additions} −{deletions}">'
        f'</a><br clear="all"></div>'
    )
    return line, {left_name: left, right_name: right}


def sync_dir(subdir, wanted):
    """Write the SVGs wanted in subdir and delete the ones it no longer wants."""
    out = ROOT / subdir
    out.mkdir(parents=True, exist_ok=True)
    for path in out.glob("*.svg"):
        if path.name not in wanted:
            path.unlink()
    for name, svg in wanted.items():
        (out / name).write_text(svg, encoding="utf-8")


def sync_svgs(block, titles):
    """Write the SVGs the block references; drop the ones it no longer does."""
    sync_dir(DIFF_DIR, {f"{a}-{d}.svg": diff_svg(int(a), int(d))
                        for a, d in DIFF_SVG.findall(block)})
    sync_dir(REPO_DIR, titles)


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
    titles = {}
    for repo, items in ranked:
        star = stars(items[0]["repository"]["stargazerCount"])
        added = sum(pr["additions"] for pr in items)
        removed = sum(pr["deletions"] for pr in items)
        line, svgs = title(repo, star, len(items), added, removed)
        titles.update(svgs)
        # The blank line ends the HTML block; without it the list is swallowed.
        lines = [line, ""]
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
    return "\n\n".join(chunks), titles


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

    body, titles = render(prs, total)
    block = f"{START}\n{body}\n{END}"

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
    sync_svgs(block, titles)
    print(f"rendered {len(prs)} of {total} pull requests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
