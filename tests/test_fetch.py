import pytest

from ingest.fetch import Fetcher, cache_key


class FakeResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code != 200:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    """Stands in for requests.Session. Records every call."""

    def __init__(self, pages):
        self.pages = pages
        self.calls = []
        self.headers = {}

    def get(self, url, timeout=None, verify=None):
        self.calls.append(url)
        return FakeResponse(self.pages[url])


@pytest.fixture
def sleeps():
    recorded = []
    return recorded, recorded.append


def test_cache_key_is_stable_and_filesystem_safe():
    k = cache_key("https://lawphil.net/statutes/ra_386.html")
    assert k == cache_key("https://lawphil.net/statutes/ra_386.html")
    assert "/" not in k


def test_get_returns_page_text(tmp_path, sleeps):
    recorded, sleep = sleeps
    session = FakeSession({"https://example.com/a": "<html>A</html>"})
    f = Fetcher(tmp_path, session=session, sleep=sleep)
    assert f.get("https://example.com/a") == "<html>A</html>"


def test_second_call_hits_disk_cache_not_network(tmp_path, sleeps):
    recorded, sleep = sleeps
    session = FakeSession({"https://example.com/a": "<html>A</html>"})
    f = Fetcher(tmp_path, session=session, sleep=sleep)
    f.get("https://example.com/a")
    f.get("https://example.com/a")
    assert session.calls == ["https://example.com/a"]


def test_cache_survives_a_new_fetcher_instance(tmp_path, sleeps):
    recorded, sleep = sleeps
    session = FakeSession({"https://example.com/a": "<html>A</html>"})
    Fetcher(tmp_path, session=session, sleep=sleep).get("https://example.com/a")

    empty = FakeSession({})
    assert (
        Fetcher(tmp_path, session=empty, sleep=sleep).get("https://example.com/a")
        == "<html>A</html>"
    )
    assert empty.calls == []


def test_rate_limit_sleeps_between_network_calls(tmp_path, sleeps):
    recorded, sleep = sleeps
    session = FakeSession({"https://example.com/a": "A", "https://example.com/b": "B"})
    f = Fetcher(tmp_path, session=session, sleep=sleep)
    f.get("https://example.com/a")
    f.get("https://example.com/b")
    assert len(recorded) == 2
    assert all(s > 0 for s in recorded)


def test_cached_reads_do_not_sleep(tmp_path, sleeps):
    recorded, sleep = sleeps
    session = FakeSession({"https://example.com/a": "A"})
    f = Fetcher(tmp_path, session=session, sleep=sleep)
    f.get("https://example.com/a")
    recorded.clear()
    f.get("https://example.com/a")
    assert recorded == []


def test_elibrary_urls_use_the_pinned_bundle(tmp_path, sleeps):
    recorded, sleep = sleeps
    captured = {}

    class VerifyRecordingSession(FakeSession):
        def get(self, url, timeout=None, verify=None):
            captured["verify"] = verify
            return super().get(url, timeout=timeout, verify=verify)

    session = VerifyRecordingSession(
        {"https://elibrary.judiciary.gov.ph/x": "<html>X</html>"}
    )
    f = Fetcher(tmp_path, session=session, sleep=sleep)
    f.get("https://elibrary.judiciary.gov.ph/x")
    assert captured["verify"] is not False, "blanket verify=False is forbidden"
    assert str(captured["verify"]).endswith(".pem")
