#!/usr/bin/env python3
"""Feedfinch - a small RSS/Atom reader for the terminal.

Fullscreen curses UI. Pure stdlib: feeds are fetched with urllib and
parsed with xml.etree. Everything lives in one JSON file, so there is
nothing to set up. Supports file:// feeds for offline testing.

MIT license, copyright Greenisus1. Built with AI assistance from my design.
"""
import curses, json, os, re, sys, time, urllib.request, gzip, io
import xml.etree.ElementTree as ET
from html import unescape

VERSION = "1.0.0"
APP_DIR = os.environ.get("FEEDFINCH_HOME", "/root/feedfinch")
STORE = os.path.join(APP_DIR, "feeds.json")
UA = "feedfinch/1.0 (+https://github.com/Greenisus1/feedfinch)"
ATOM = "{http://www.w3.org/2005/Atom}"


def load_store():
    try:
        return json.load(open(STORE))
    except Exception:
        return {"feeds": []}


def save_store(st):
    os.makedirs(APP_DIR, exist_ok=True)
    json.dump(st, open(STORE, "w"), indent=1)


def fetch(url, timeout=10):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            data = gzip.GzipFile(fileobj=io.BytesIO(data)).read()
    return data


def text_of(el, *names):
    for n in names:
        c = el.find(n)
        if c is not None and c.text:
            return c.text.strip()
    return ""


def strip_html(s):
    s = re.sub(r"(?s)<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", unescape(s)).strip()


def parse_feed(data):
    """Parse RSS 2.0 or Atom bytes -> (title, [ {title, link, summary, date} ])."""
    root = ET.fromstring(data)
    if root.tag == "rss" or root.tag == "rdf:RDF":
        ch = root.find("channel")
        if ch is None:
            raise ValueError("no channel")
        title = text_of(ch, "title") or "untitled feed"
        items = []
        for it in ch.findall("item"):
            items.append({
                "title": text_of(it, "title") or "(no title)",
                "link": text_of(it, "link", "guid"),
                "summary": strip_html(text_of(it, "description")),
                "date": text_of(it, "pubDate", "date"),
            })
        return title, items
    if root.tag == ATOM + "feed" or root.tag == "feed":
        title = text_of(root, ATOM + "title", "title") or "untitled feed"
        items = []
        for e in root.findall(ATOM + "entry") + root.findall("entry"):
            link = ""
            for l in e.findall(ATOM + "link") + e.findall("link"):
                if l.get("href") and l.get("rel", "alternate") == "alternate":
                    link = l.get("href")
                    break
            items.append({
                "title": text_of(e, ATOM + "title", "title") or "(no title)",
                "link": link,
                "summary": strip_html(text_of(e, ATOM + "summary",
                                              ATOM + "content", "summary")),
                "date": text_of(e, ATOM + "updated", ATOM + "published",
                                "updated"),
            })
        return title, items
    raise ValueError("not RSS or Atom")


def refresh_feed(f):
    """Fetch + parse one feed dict in place. Returns error string or ''."""
    try:
        title, items = parse_feed(fetch(f["url"]))
    except Exception as e:
        f["error"] = str(e)[:100]
        return f["error"]
    f["title"] = title
    f["error"] = ""
    old = {a["link"] for a in f.get("articles", [])}
    read = {a["link"] for a in f.get("articles", []) if a.get("read")}
    for a in items:
        a["read"] = a["link"] in read
    f["articles"] = items[:100]
    f["fetched_at"] = int(time.time())
    return ""


def unread(f):
    return sum(1 for a in f.get("articles", []) if not a.get("read"))


# ---------- UI ----------

def draw_header(scr, w, subtitle):
    scr.addnstr(0, 0, f" FEEDFINCH v{VERSION} - {subtitle}".ljust(w - 1),
                w - 1, curses.A_REVERSE)


def draw_keys(scr, h, w, keys):
    scr.addnstr(h - 1, 0, keys[:w - 1], w - 1, curses.A_REVERSE)


def prompt(scr, label):
    curses.echo()
    curses.curs_set(1)
    h, w = scr.getmaxyx()
    scr.addnstr(h - 3, 2, label + " ", w - 4, curses.A_BOLD)
    scr.refresh()
    try:
        v = scr.getstr(h - 3, 2 + len(label) + 1, 300).decode().strip()
    except Exception:
        v = ""
    curses.noecho()
    curses.curs_set(0)
    return v


def wrap(text, width):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        if len(cur) + len(wd) + 1 > width:
            lines.append(cur)
            cur = wd
        else:
            cur = (cur + " " + wd).strip()
    if cur:
        lines.append(cur)
    return lines or [""]


def view_feeds(scr, st):
    sel, top, msg = 0, 0, ""
    while True:
        scr.erase()
        h, w = scr.getmaxyx()
        draw_header(scr, w, "your feeds")
        feeds = st["feeds"]
        if not feeds:
            scr.addnstr(3, 4, "No feeds yet - press a to add one.", w - 8)
        body = h - 4
        top = max(0, min(top, sel - body + 1)) if sel >= top + body else min(top, sel)
        for row, f in enumerate(feeds[top:top + body]):
            i = top + row
            n = unread(f)
            mark = "*" if n else " "
            name = f.get("title") or f["url"]
            if f.get("error"):
                name += f"  [error: {f['error']}]"
            line = f"{mark} {name} ({n} new)"
            attr = curses.A_REVERSE if i == sel else 0
            scr.addnstr(2 + row, 2, line.ljust(w - 4), w - 4, attr)
        if msg:
            scr.addnstr(h - 2, 2, msg, w - 4, curses.A_BOLD)
        draw_keys(scr, h, w,
                  "[enter] read  [a]dd  [d]elete  [r]efresh  refresh [A]ll  [q]uit")
        scr.refresh()
        ch = scr.getch()
        msg = ""
        if ch in (curses.KEY_UP, ord("k")):
            sel = max(0, sel - 1)
        elif ch in (curses.KEY_DOWN, ord("j")):
            sel = min(max(0, len(feeds) - 1), sel + 1)
        elif ch in (10, 13) and feeds:
            view_articles(scr, st, feeds[sel])
        elif ch == ord("a"):
            url = prompt(scr, "Feed URL (http(s):// or file://):")
            if url:
                feeds.append({"url": url, "title": "", "articles": []})
                msg = "Added - press r to fetch it."
                save_store(st)
        elif ch == ord("d") and feeds:
            gone = feeds.pop(sel)
            sel = max(0, sel - 1)
            save_store(st)
            msg = f"Removed {gone.get('title') or gone['url']}."
        elif ch == ord("r") and feeds:
            scr.addnstr(h - 2, 2, "fetching...", w - 4, curses.A_BOLD)
            scr.refresh()
            err = refresh_feed(feeds[sel])
            save_store(st)
            msg = err and ("Error: " + err) or f"{len(feeds[sel]['articles'])} articles."
        elif ch == ord("A"):
            for i, f in enumerate(feeds):
                scr.addnstr(h - 2, 2, f"fetching {i + 1}/{len(feeds)}...",
                            w - 4, curses.A_BOLD)
                scr.refresh()
                refresh_feed(f)
            save_store(st)
            msg = "All feeds refreshed."
        elif ch in (ord("q"), 27):
            return


def view_articles(scr, st, f):
    sel, top, msg = 0, 0, ""
    arts = f.get("articles", [])
    while True:
        scr.erase()
        h, w = scr.getmaxyx()
        draw_header(scr, w, (f.get("title") or f["url"])[:w - 22])
        if not arts:
            scr.addnstr(3, 4, "No articles - go back and press r to fetch.",
                        w - 8)
        body = h - 4
        top = max(0, min(top, sel - body + 1)) if sel >= top + body else min(top, sel)
        for row, a in enumerate(arts[top:top + body]):
            i = top + row
            mark = " " if a.get("read") else "*"
            line = f"{mark} {a['title']}"
            attr = curses.A_REVERSE if i == sel else 0
            if not a.get("read"):
                attr |= curses.A_BOLD
            scr.addnstr(2 + row, 2, line.ljust(w - 4), w - 4, attr)
        if msg:
            scr.addnstr(h - 2, 2, msg, w - 4, curses.A_BOLD)
        draw_keys(scr, h, w, "[enter] open  [space] read/unread  "
                             "mark all [x]  [r]efresh  [q] back")
        scr.refresh()
        ch = scr.getch()
        msg = ""
        if ch in (curses.KEY_UP, ord("k")):
            sel = max(0, sel - 1)
        elif ch in (curses.KEY_DOWN, ord("j")):
            sel = min(max(0, len(arts) - 1), sel + 1)
        elif ch in (10, 13) and arts:
            arts[sel]["read"] = True
            save_store(st)
            view_article(scr, arts[sel])
        elif ch == ord(" ") and arts:
            arts[sel]["read"] = not arts[sel].get("read")
            save_store(st)
        elif ch == ord("x"):
            for a in arts:
                a["read"] = True
            save_store(st)
            msg = "All marked read."
        elif ch == ord("r"):
            scr.addnstr(h - 2, 2, "fetching...", w - 4, curses.A_BOLD)
            scr.refresh()
            err = refresh_feed(f)
            save_store(st)
            arts = f.get("articles", [])
            sel = min(sel, max(0, len(arts) - 1))
            msg = err and ("Error: " + err) or f"{len(arts)} articles."
        elif ch in (ord("q"), 27):
            return


def view_article(scr, a):
    top = 0
    while True:
        scr.erase()
        h, w = scr.getmaxyx()
        draw_header(scr, w, "article")
        lines = [a["title"], a.get("date", ""), a.get("link", ""), ""]
        lines += wrap(a.get("summary") or "(no summary stored)", w - 6)
        body = h - 4
        for row, line in enumerate(lines[top:top + body]):
            attr = curses.A_BOLD if top + row == 0 else 0
            scr.addnstr(2 + row, 2, line, w - 4, attr)
        draw_keys(scr, h, w, "[j/k] scroll  [q] back")
        scr.refresh()
        ch = scr.getch()
        if ch in (curses.KEY_UP, ord("k")):
            top = max(0, top - 1)
        elif ch in (curses.KEY_DOWN, ord("j")):
            top = min(max(0, len(lines) - body), top + 1)
        elif ch in (ord("q"), 27, 10, 13):
            return


def main(scr):
    curses.curs_set(0)
    st = load_store()
    view_feeds(scr, st)
    save_store(st)


if __name__ == "__main__":
    if "--parse" in sys.argv:
        t, items = parse_feed(open(sys.argv[2], "rb").read())
        print(t)
        for a in items:
            print("-", a["title"], "|", a["link"])
        sys.exit(0)
    curses.wrapper(main)
