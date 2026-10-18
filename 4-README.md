# Feedfinch

A small RSS/Atom reader for the terminal. Fullscreen curses UI, pure
Python standard library - no dependencies, nothing to set up. Your feeds
and read-state live in one JSON file.

## What it does

- **Add feeds** (`a`) by URL. Fetches over http(s) with a proper
  user-agent and gzip support; `file://` works too for offline use.
- **Headlines view** with unread counts per feed; bold = unread.
- **Article view** with the title, date, link and cleaned summary text.
- **Mark read/unread** (`space`), mark a whole feed read (`x`), refresh
  one feed (`r`) or all of them (`A`).
- Parses RSS 2.0 and Atom, keeps the 100 newest articles per feed, and
  read-state survives refreshes.

## Install (Pi App Store)

Install through the Pi App Store, or:

```sh
sudo bash app-store.sh install   # checks Python/curses, compiles sources
sudo python3 feedfinch.py        # or: bash app-store.sh run
```

Data is stored in `/root/feedfinch/feeds.json` (override with the
`FEEDFINCH_HOME` environment variable).

## Tests

```sh
python3 test_feedfinch.py   # unit tests (RSS + Atom parsing, store, refresh)
python3 test_pty.py         # fullscreen walkthrough against an offline feed
```

MIT license, copyright Greenisus1. Built with AI assistance from my design.
