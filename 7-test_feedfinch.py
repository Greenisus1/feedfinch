import importlib.util, json, os, tempfile, unittest

os.environ["FEEDFINCH_HOME"] = tempfile.mkdtemp()
spec = importlib.util.spec_from_file_location(
    "feedfinch", os.path.join(os.path.dirname(__file__), "feedfinch.py"))
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)

RSS = open(os.path.join(os.path.dirname(__file__), "sample.xml"), "rb").read()
ATOM = b'''<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<title>Atom Nest</title>
<entry><title>Bird one</title><link rel="alternate" href="https://a.example/1"/>
<summary>Summary &lt;b&gt;one&lt;/b&gt;</summary><updated>2026-10-18T08:00:00Z</updated></entry>
<entry><title>Bird two</title><link href="https://a.example/2"/>
<content>Body two</content><published>2026-10-18T09:00:00Z</published></entry>
</feed>'''


class TestParse(unittest.TestCase):
    def test_rss(self):
        title, items = f.parse_feed(RSS)
        self.assertEqual(title, "Finch Test Feed")
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["title"], "First perch")
        self.assertEqual(items[0]["summary"], "Hello from the test feed.")
        self.assertEqual(items[1]["link"], "https://example.com/2")

    def test_atom(self):
        title, items = f.parse_feed(ATOM)
        self.assertEqual(title, "Atom Nest")
        self.assertEqual(items[0]["link"], "https://a.example/1")
        self.assertEqual(items[1]["summary"], "Body two")
        self.assertEqual(items[1]["date"], "2026-10-18T09:00:00Z")

    def test_garbage(self):
        self.assertRaises(Exception, f.parse_feed, b"<html>nope</html>")


class TestStore(unittest.TestCase):
    def test_roundtrip(self):
        st = {"feeds": [{"url": "file:///x", "title": "t", "articles": []}]}
        f.save_store(st)
        self.assertEqual(f.load_store(), st)

    def test_refresh_offline_and_read_state(self):
        feed = {"url": "file://" + os.path.join(os.path.dirname(__file__),
                                                 "sample.xml"),
                "title": "", "articles": []}
        self.assertEqual(f.refresh_feed(feed), "")
        self.assertEqual(feed["title"], "Finch Test Feed")
        self.assertEqual(f.unread(feed), 2)
        feed["articles"][0]["read"] = True
        self.assertEqual(f.refresh_feed(feed), "")
        self.assertTrue(feed["articles"][0]["read"])   # survives refresh
        self.assertEqual(f.unread(feed), 1)

    def test_refresh_bad_url(self):
        feed = {"url": "file:///nonexistent.xml", "articles": []}
        self.assertTrue(f.refresh_feed(feed))
        self.assertIn("error", feed)


class TestWrap(unittest.TestCase):
    def test_wrap(self):
        lines = f.wrap("one two three four five six", 12)
        self.assertTrue(all(len(l) <= 12 for l in lines))
        self.assertEqual(" ".join(lines), "one two three four five six")


if __name__ == "__main__":
    unittest.main()
