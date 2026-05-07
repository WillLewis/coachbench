from html.parser import HTMLParser
from pathlib import Path


class TabParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_tab = False
        self.current = None
        self.tabs = []
        self.tablist_count = 0
        self.tabpanel_count = 0

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        role = data.get("role")
        if role == "tablist":
            self.tablist_count += 1
        if role == "tabpanel":
            self.tabpanel_count += 1
        if role == "tab":
            self.in_tab = True
            self.current = {"text": "", "attrs": data}

    def handle_data(self, data):
        if self.in_tab and self.current is not None:
            self.current["text"] += data

    def handle_endtag(self, tag):
        if self.in_tab and tag == "button":
            self.current["text"] = " ".join(self.current["text"].split())
            self.tabs.append(self.current)
            self.current = None
            self.in_tab = False


def test_play_inspector_has_four_accessible_tabs():
    parser = TabParser()
    parser.feed(Path("ui/index.html").read_text())

    assert parser.tablist_count == 1
    assert parser.tabpanel_count == 1
    assert [tab["text"] for tab in parser.tabs] == [
        "Outcome",
        "Resources",
        "Beliefs",
        "Graph Evidence",
    ]
    assert len(parser.tabs) == 4

    first = parser.tabs[0]["attrs"]
    assert first["aria-selected"] == "true"
    assert first["data-inspector-tab"] == "outcome"
    assert first["aria-controls"] == "inspectorPanel"
