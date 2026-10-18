"""PTY walkthrough: add the offline sample feed, fetch, open, mark read, quit."""
import os, pty, re, select, subprocess, sys, tempfile, time

home = tempfile.mkdtemp()
env = dict(os.environ, FEEDFINCH_HOME=home, TERM="xterm-256color",
           LINES="30", COLUMNS="100")
pid, fd = pty.fork()
if pid == 0:
    os.chdir(os.path.dirname(os.path.abspath(__file__)) or ".")
    os.execvpe(sys.executable, [sys.executable, "feedfinch.py"], env)

out = b""
def pump(t):
    global out
    end = time.time() + t
    while time.time() < end:
        r, _, _ = select.select([fd], [], [], 0.2)
        if r:
            try: out += os.read(fd, 65536)
            except OSError: break

fail = []
pump(2.0)
if not re.search(rb"FEEDFINCH v1\.0\.0", out): fail.append("title")
sample = "file://" + os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "sample.xml")
os.write(fd, b"a"); pump(0.6)
os.write(fd, sample.encode() + b"\n"); pump(0.8)
os.write(fd, b"r"); pump(1.5)          # fetch
if not re.search(rb"Finch Test Feed", out): fail.append("feed title")
if not re.search(rb"2 new", out): fail.append("unread count")
os.write(fd, b"\r"); pump(1.0)         # open feed
if not re.search(rb"First perch", out): fail.append("article list")
os.write(fd, b"\r"); pump(1.0)         # open article
if not re.search(rb"Hello from the", out): fail.append("article body")
os.write(fd, b"q"); pump(0.6)          # back to articles
os.write(fd, b"q"); pump(0.6)          # back to feeds
if not re.search(rb"1 new", out): fail.append("read persisted")
os.write(fd, b"q"); pump(0.8)
wp, status = os.waitpid(pid, os.WNOHANG)
if wp == 0:
    try: os.kill(pid, 9); os.waitpid(pid, 0)
    except ProcessLookupError: pass
    fail.append("did not quit")
# store file written
import json
st = json.load(open(os.path.join(home, "feeds.json")))
if st["feeds"][0]["title"] != "Finch Test Feed": fail.append("store")
if fail:
    print("PTY FAIL:", ", ".join(fail)); sys.exit(1)
print("PTY PASS")
