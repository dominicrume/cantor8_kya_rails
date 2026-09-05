#!/usr/bin/env python3
"""Fold receipts.js into verifier.html and emit ONE file.

verifier.html loads receipts.js with a <script src>, which a browser will
refuse to fetch over file:// in some configurations. This build inlines it, so
the result is a single document that opens by double-click, on any machine,
with no server, no install and no network. That is the file you hand a judge.

    python3 step-3-verify/build-standalone.py
    open step-3-verify/kya-rails-standalone.html

--fragment emits the same page without the <!DOCTYPE>/<html>/<head>/<body>
wrapper, for hosts that supply their own. It is generated rather than hand
edited so a hosted copy cannot quietly drift from the file people are handed:
both come from verifier.html and the current receipts.js, or neither does.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def build():
    html = open(os.path.join(HERE, "verifier.html")).read()
    receipts = open(os.path.join(HERE, "receipts.js")).read()
    out = html.replace('<script src="receipts.js"></script>',
                       "<script>\n" + receipts + "\n</script>")
    if out == html:
        raise SystemExit("could not find the receipts.js script tag in verifier.html")
    return out


def as_fragment(page):
    """Everything inside <body>, plus the <title> and <style> from the head.

    Not a regex over the whole document: the <style> and <title> are lifted
    deliberately, because dropping them would leave an unstyled page that
    still passed every test about content.
    """
    head = page[page.index("<head>"):page.index("</head>")]
    keep = "".join(re.findall(r"<title>.*?</title>|<style>.*?</style>", head, re.S))
    body = page[page.index("<body>") + len("<body>"):page.rindex("</body>")]
    return keep + "\n" + body


def main():
    page = build()
    if "--pages" in sys.argv:
        return write(hosted(page), os.path.join(HERE, "..", "docs", "index.html"))
    fragment = "--fragment" in sys.argv
    name = "kya-rails-fragment.html" if fragment else "kya-rails-standalone.html"
    return write(as_fragment(page) if fragment else page, os.path.join(HERE, name))


def hosted(page):
    """The same page, titled for someone arriving from a link rather than
    being handed a file. Generated, never hand-edited: a hosted copy that
    drifted from the handed-out one would show two different chains under one
    name, which is worse than having no hosted copy."""
    return page.replace(
        "<title>KYA Rails. Pay out abroad, prove it at home.</title>",
        "<title>Check a payment record | KYA Rails</title>\n"
        "<meta name=\"description\" content=\"Drop a receipts file and see "
        "whether it was edited. Runs entirely in your browser: nothing is "
        "uploaded, nothing is stored, works offline.\">")


def write(out, path):
    open(path, "w").write(out)
    print("wrote %s (%s bytes, no external files)"
          % (os.path.relpath(path), format(len(out), ",")))


if __name__ == "__main__":
    main()
