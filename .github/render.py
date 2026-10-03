#!/usr/bin/env python3
"""Refresh the generated part of the Contributions section in README.md.

Only the text between <!-- os:start --> and <!-- os:end --> is touched, so the
Abstract and anything else written by hand outside the markers survives.
"""

import hashlib
import html
import json
import math
import pathlib
import re
import subprocess
import sys
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
# One small SVG per distinct "+a −d" pair, referenced from README.md and named
# by content (see diff_name()).
DIFF_DIR = "assets/diff"
START = "<!-- os:start -->"
END = "<!-- os:end -->"
AUTHOR = "lthphuw"
# Merged pull requests the author opened against somebody else's repository.
SEARCH = f"is:pr is:merged author:{AUTHOR} -user:{AUTHOR}"
# The search API caps one page at 100, and the search is ordered by last update,
# not by merge; past that the per-repository counts undercount and a global link
# covers the rest.
LIMIT = 100
# Pull requests listed per repository; the rest collapse into a "+N more" link
# that belongs to that repository.
SHOW = 5

# One line of the profile text on GitHub: 14px at a line-height of 1.5. Every
# vertical size below is a multiple or a small offset of it.
LINE_H = 21

# Between the fields of a line: two spaces either side of a bar. Only the last
# space can break, so a wrapped line ends on a bar instead of starting with one.
SEP = "&nbsp;&nbsp;|&nbsp; "

# Any rendered star count, used to compare two blocks while ignoring stars.
STARS = re.compile(r"★[\d.]+k?")

# Stats are drawn as SVG because Markdown on GitHub strips CSS: an image is the
# only way to get a smaller size, another font and colour at once. Monospace
# makes the width computable without measuring text; textLength absorbs the
# small spread between fonts (Consolas 0.55em, most others 0.6em).
MONO = ("ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,"
        "'Liberation Mono',monospace")
SIZE = 12        # px, a notch under the 14px profile text
META_SIZE = 13   # the title's "merged" and the stats beside it
TITLE_SIZE = 15

# The same pair of images serves two layouts, told apart by the width of the
# window (see stats()). At or above WIDE the stats float to the right edge of
# the line; below it they flow after the text and wrap to the start of a line.
WIDE = 601
# 1x1 and transparent: shown in place of the copy that does not belong to the
# current layout. Absolute, because a relative srcset is not known to be
# rewritten the way src is.
BLANK = "assets/blank.svg"
BLANK_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>\n'
BLANK_URL = f"https://raw.githubusercontent.com/{AUTHOR}/{AUTHOR}/main/{BLANK}"
# The space between two groups. A line is never shorter than LINE_H, so an image
# taller than that, sitting at the end of the last line of a group, stretches
# the line and leaves the difference as space below the text. It cannot go above
# the next title instead: the title is two images, and a narrow screen puts the
# second on a line of its own.
GROUP_GAP = 23  # blank space between a group's last line and the next title
GAP = "assets/gap.svg"
GAP_H = LINE_H + GROUP_GAP
GAP_SVG = f'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="{GAP_H}"/>\n'
GAP_IMG = f'<img src="{GAP}" align="top" width="1" height="{GAP_H}" alt="">'

# A row's stats: as tall as a line of text plus a few px, which is the space
# between two rows. Both layouts put the image's top on the
# top of its line (align="top"), so digits on the same baseline as the text
# are level with it whichever layout is shown.
ROW_H = LINE_H + 4
ROW_BASE = 15.5
DIFF_SVG = re.compile(rf"{DIFF_DIR}/(\d+)-(\d+)\.[0-9a-f]{{8}}\.svg")

# Two SVGs per repository for its title line, named by content (see title()).
REPO_DIR = "assets/repo"
# The title is not wrapped in a paragraph (see title()), so what separates it
# from the line above and the first row below is the blank space left in these
# two images, and nothing else. The tallest things in them are the star, which
# reaches 12px above the baseline, and the ascenders. The baseline therefore
# sits 12px down, and the image ends 7px under it, which leaves the title about
# as far from the first row as rows are from each other. The same height is the
# line pitch when a narrow screen puts the right image on a second line.
TITLE_HEIGHT = 19
TITLE_BASE = 12          # shared baseline of every text on the title line
TITLE_GAP = 8            # between the repository name and the star
STAR_R = 6.5             # outer radius of the star
BAR_GAP = 7              # either side of the bar between "merged" and the diff
# Room kept for the star count whatever it is. A width that followed the text
# would change the README whenever 9.9k became 10k, which the star-drift rule
# in main() exists to avoid.
STAR_CHARS = 5

# Colours are GitHub's own. prefers-color-scheme follows the viewer's system
# theme, which is what GitHub's default theme follows too.
COLOURS = """\
.o { fill: #59636e; } .n { fill: #1f2328; } .s { fill: #9a6700; }
.m { fill: #59636e; } .b { fill: #afb8c1; }
.a { fill: #1a7f37; } .d { fill: #d1242f; }
@media (prefers-color-scheme: dark) {
  .o { fill: #9198a1; } .n { fill: #f0f6fc; } .s { fill: #e3b341; }
  .m { fill: #9198a1; } .b { fill: #59636e; }
  .a { fill: #3fb950; } .d { fill: #f85149; }
}"""

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


def stats(src, url, alt):
    """One image, written twice, one copy per layout.

    An image cannot be both at the right edge of a line and at the start of
    the next one, and that is where a line that does not fit has to put it.
    The first copy flows with the text, so when there is no room it wraps to
    the start of a line. The second floats right. Each is swapped for a blank
    image in the window width where it does not belong, so only one shows. The
    link matters: an unlinked image on GitHub opens the image itself."""
    flow = (f'<picture><source media="(min-width: {WIDE}px)" srcset="{BLANK_URL}">'
            f'<img src="{src}" align="top" alt="{alt}"></picture>')
    float_ = (f'<picture><source media="(max-width: {WIDE - 1}px)" '
              f'srcset="{BLANK_URL}"><img src="{src}" align="right" alt="{alt}">'
              f'</picture>')
    return f'<a href="{url}">{flow}</a><a href="{url}">{float_}</a>'


def diff_svg(additions, deletions):
    # No thousands separator: at this size a monospace comma reads as a full
    # stop.
    added, removed = f"+{additions}", f"−{deletions}"
    char = 0.6 * SIZE
    wa, wr = len(added) * char, len(removed) * char
    width = math.ceil(wa + char + wr)
    return f"""\
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{ROW_H}" \
viewBox="0 0 {width} {ROW_H}">
<style>
text {{ font: 500 {SIZE}px {MONO}; }}
{COLOURS}
</style>
<text class="a" x="0" y="{ROW_BASE:g}" textLength="{wa:g}" \
lengthAdjust="spacing">{added}</text>
<text class="d" x="{wa + char:g}" y="{ROW_BASE:g}" textLength="{wr:g}" \
lengthAdjust="spacing">{removed}</text>
</svg>
"""


def short_hash(svg):
    return hashlib.sha1(svg.encode("utf-8")).hexdigest()[:8]


def diff_name(additions, deletions):
    """Named by content, like the title images (see title()). It also matters
    here for a second reason: main() rewrites nothing while the README text is
    unchanged, so a restyled image under an unchanged name would never ship."""
    return f"{additions}-{deletions}.{short_hash(diff_svg(additions, deletions))}.svg"


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
    """Repository name and stars: the group against the left edge."""
    owner, name = repo.split("/")
    base = TITLE_BASE
    char = 0.6 * TITLE_SIZE
    wo, wn = (len(owner) + 1) * char, len(name) * char
    star_cx = wo + wn + TITLE_GAP + STAR_R
    star_cy = base - 0.36 * TITLE_SIZE
    count_x = star_cx + STAR_R + 4
    width = math.ceil(count_x + STAR_CHARS * 0.6 * META_SIZE)
    height = TITLE_HEIGHT
    return f"""\
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">
<style>
text {{ font-family: {MONO}; }}
.o, .n {{ font-size: {TITLE_SIZE}px; }} .n {{ font-weight: 700; }}
.c {{ font-size: {META_SIZE}px; font-weight: 500; }}
{COLOURS}
</style>
<text class="o" x="0" y="{base:g}" textLength="{wo:g}" \
lengthAdjust="spacing">{owner}/</text>
<text class="n" x="{wo:g}" y="{base:g}" textLength="{wn:g}" \
lengthAdjust="spacing">{name}</text>
<polygon class="s" points="{star_points(star_cx, star_cy, STAR_R)}"/>
<text class="c m" x="{count_x:g}" y="{base:g}">{star}</text>
</svg>
""", width, height


def title_right(merged, additions, deletions):
    """Merged count, a bar, and the diff: one group, right edge at the image's."""
    words, added, removed = f"{merged} merged", f"+{additions}", f"−{deletions}"
    char = 0.6 * META_SIZE
    chars = len(words) + 1 + len(added) + 1 + len(removed)
    # Computed widths only size the image; the text is anchored to its right
    # edge, so a font that runs a little wide or narrow cannot move that edge.
    width = math.ceil(chars * char + 2 * BAR_GAP + 2)
    height = TITLE_HEIGHT
    return f"""\
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">
<style>
text {{ font: 500 {META_SIZE}px {MONO}; }}
{COLOURS}
</style>
<text class="m" x="{width}" y="{TITLE_BASE}" text-anchor="end">{words}\
<tspan class="b" dx="{BAR_GAP}">|</tspan>\
<tspan class="a" dx="{BAR_GAP}">{added}</tspan>\
<tspan class="d" dx="{char:g}">{removed}</tspan></text>
</svg>
""", width, height


def title(repo, star, merged, additions, deletions):
    """The title line's HTML, and the SVGs it references by file name."""
    slug = title_slug(repo)
    left, lw, lh = title_left(repo, star)
    right, _, _ = title_right(merged, additions, deletions)
    # Named by content, so an image that changes is a new URL. GitHub serves
    # raw files with max-age=300: under an unchanged name, a cached old copy
    # gets squeezed into the new width and height for minutes. The star count
    # is left out of the hash so that drifting stars stay invisible to the
    # README, which is what main() relies on.
    left_name = f"{slug}.{short_hash(title_left(repo, '')[0])}.svg"
    right_name = f"{slug}.pr.{short_hash(right)}.svg"
    # Two images, two links: an image can only carry one. align="top" stops the
    # left one sitting on the text baseline, which would leave a strip of empty
    # line below it. The clearing break keeps what follows from wrapping around
    # a floated copy. A <div> rather than Markdown: a paragraph gets a 16px
    # bottom margin from GitHub, a div gets none, so the gap to the first row
    # is the one chosen above. Markdown is not parsed inside it, hence anchors.
    line = (
        f'<div><a href="https://github.com/{repo}">'
        f'<img src="{REPO_DIR}/{left_name}" align="top" width="{lw}" '
        f'height="{lh}" alt="{repo}, ★{star}"></a> '
        + stats(f"{REPO_DIR}/{right_name}", repo_url(repo),
                f"{merged} merged | +{additions} −{deletions}")
        + '<br clear="all"></div>'
    )
    return line, {left_name: left, right_name: right}


def inline_code(text):
    """A pull request title as HTML: escaped, with `code` spans kept as code."""
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", html.escape(text, quote=False))


def row(pr, tail=""):
    # Number first, in code font: within a repository the numbers share a
    # width, so they line up into a column like a changelog.
    head = (f'<a href="{pr["url"]}"><code>#{pr["number"]}</code></a>'
            f'{SEP}{inline_code(pr["title"])}')
    src = f'{DIFF_DIR}/{diff_name(pr["additions"], pr["deletions"])}'
    return (f'<div>{head} '
            + stats(src, f'{pr["url"]}/files',
                    f'+{pr["additions"]} −{pr["deletions"]}')
            + tail + '<br clear="all"></div>')


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
    sync_dir(DIFF_DIR, {diff_name(int(a), int(d)): diff_svg(int(a), int(d))
                        for a, d in DIFF_SVG.findall(block)})
    sync_dir(REPO_DIR, titles)
    (ROOT / BLANK).write_text(BLANK_SVG, encoding="utf-8")
    (ROOT / GAP).write_text(GAP_SVG, encoding="utf-8")


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
    for i, (repo, items) in enumerate(ranked):
        star = stars(items[0]["repository"]["stargazerCount"])
        added = sum(pr["additions"] for pr in items)
        removed = sum(pr["deletions"] for pr in items)
        # The gap to the next group is carried by the last line of this one.
        tail = GAP_IMG if i < len(ranked) - 1 else ""
        line, svgs = title(repo, star, len(items), added, removed)
        titles.update(svgs)
        # One HTML block per group, with no blank line in it: a blank line
        # would end the block and hand the rest back to Markdown, which wraps
        # a paragraph's margin around it. Rows are not a list for the same
        # reason: a list brings its own indent, bullets and 16px margins.
        shown = items[:SHOW]
        hidden = len(items) - SHOW
        lines = [line]
        for j, pr in enumerate(shown):
            last = j == len(shown) - 1 and hidden <= 0
            lines.append(row(pr, tail if last else ""))
        if hidden > 0:
            lines.append(f'<div><a href="{repo_url(repo)}">+{hidden} more →</a>'
                         f'{tail}</div>')
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
