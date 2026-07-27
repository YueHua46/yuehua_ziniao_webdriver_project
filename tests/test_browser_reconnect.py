from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from yuehua_ziniao_webdriver.browser import BrowserSession
from yuehua_ziniao_webdriver.exceptions import ZiniaoError


def make_session() -> BrowserSession:
    session = BrowserSession.__new__(BrowserSession)
    session.port = 9222
    session.host = "127.0.0.1"
    session.proxy_host = None
    session.store_id = "store-id"
    session.store_name = "test-store"
    session._browser = Mock(name="stale_browser")
    session._closed = False
    session._get_cdp_browser_id = Mock(return_value="browser-id")
    return session


class DisconnectedPluginTab:
    @property
    def url(self) -> str:
        raise RuntimeError("plugin page websocket disconnected")


class DisconnectedBrowser:
    def get_tabs(self):
        raise RuntimeError("page channel disconnected")


def test_session_initialization_is_lazy() -> None:
    with patch("yuehua_ziniao_webdriver.browser.Chromium") as chromium:
        session = BrowserSession(9222, "store-id", "test-store")

    assert session._browser is None
    chromium.assert_not_called()


def test_reconnect_ignores_disconnected_plugin_tab() -> None:
    session = make_session()
    connected_browser = Mock(name="connected_browser")
    connected_browser.get_tabs.return_value = [
        DisconnectedPluginTab(),
        Mock(url="chrome-extension://example/background.html"),
        Mock(url="https://sellercentral.amazon.co.uk/home"),
    ]

    with patch(
        "yuehua_ziniao_webdriver.browser.Chromium",
        return_value=connected_browser,
    ) as chromium:
        with patch.object(session, "wait_for_web_page_target", return_value=True):
            with patch("yuehua_ziniao_webdriver.browser.time.sleep") as sleep:
                result = session.reconnect(timeout=10, retry_interval=0.5)

    assert result is connected_browser
    assert session.browser is connected_browser
    chromium.assert_called_once_with(9222)
    sleep.assert_not_called()


def test_reconnect_can_validate_browser_before_web_pages_are_opened() -> None:
    session = make_session()
    connected_browser = Mock(name="connected_browser")

    with patch(
        "yuehua_ziniao_webdriver.browser.Chromium",
        return_value=connected_browser,
    ):
        result = session.reconnect(require_web_page=False)

    assert result is connected_browser
    connected_browser.get_tabs.assert_not_called()


def test_reconnect_retries_until_http_page_is_available() -> None:
    session = make_session()
    waiting_browser = Mock(name="waiting_browser")
    waiting_browser.get_tabs.return_value = [Mock(url="chrome://newtab/")]
    connected_browser = Mock(name="connected_browser")
    connected_browser.get_tabs.return_value = [Mock(url="https://example.test/")]

    with patch(
        "yuehua_ziniao_webdriver.browser.Chromium",
        side_effect=[waiting_browser, connected_browser],
    ) as chromium:
        with patch("yuehua_ziniao_webdriver.browser.time.sleep") as sleep:
            with patch.object(session, "wait_for_web_page_target", return_value=True):
                with patch.object(
                    BrowserSession, "_discard_browser_reference"
                ) as discard:
                    result = session.reconnect(timeout=10, retry_interval=0.5)

    assert result is connected_browser
    assert session.browser is connected_browser
    assert chromium.call_count == 2
    discard.assert_called_once_with(waiting_browser)
    sleep.assert_called_once_with(0.5)


def test_reconnect_raises_when_session_is_closed() -> None:
    session = make_session()
    session._closed = True

    with pytest.raises(ZiniaoError, match="浏览器会话已关闭"):
        session.reconnect()


def test_page_property_reuses_current_session_tab() -> None:
    session = make_session()
    tab = Mock(name="business_tab")
    session._browser.get_tabs.return_value = [
        DisconnectedPluginTab(),
        Mock(url="chrome-extension://example/background.html"),
        tab,
    ]
    tab.url = "https://sellercentral.amazon.com/home"

    assert session.page is tab


def test_get_tab_skips_disconnected_latest_plugin_tab() -> None:
    session = make_session()
    business_tab = Mock(url="https://sellercentral.amazon.co.jp/home")
    session._browser.get_tabs.return_value = [
        DisconnectedPluginTab(),
        Mock(url="chrome-extension://example/background.html"),
        business_tab,
    ]

    assert session.get_tab() is business_tab
    session._browser.get_tabs.assert_called_once_with()


def test_only_current_incomplete_drissionpage_browser_is_discarded() -> None:
    incomplete = SimpleNamespace(
        id="browser-id",
        _created=True,
    )
    other = SimpleNamespace(id="other-browser", _created=True)
    fake_chromium = SimpleNamespace(
        _BROWSERS={"browser-id": incomplete, "other-browser": other}
    )

    with patch("yuehua_ziniao_webdriver.browser.Chromium", fake_chromium):
        BrowserSession._discard_incomplete_cached_browser("browser-id")

    assert fake_chromium._BROWSERS == {"other-browser": other}


def test_reconnect_retries_after_interrupted_drissionpage_constructor() -> None:
    session = make_session()
    ready = Mock(name="ready_browser")

    with patch(
        "yuehua_ziniao_webdriver.browser.Chromium",
        side_effect=[RuntimeError("page websocket disconnected"), ready],
    ) as chromium:
        with patch.object(
            BrowserSession,
            "_discard_incomplete_cached_browser",
        ) as discard:
            with patch("yuehua_ziniao_webdriver.browser.time.sleep"):
                result = session.reconnect(
                    timeout=1,
                    retry_interval=0.01,
                    require_web_page=False,
                )

    assert result is ready
    assert session.browser is ready
    assert chromium.call_count == 2
    assert discard.call_count == 2
    discard.assert_called_with("browser-id")


def test_wait_for_web_page_target_requires_stable_http_target() -> None:
    session = make_session()
    session._list_cdp_tabs = Mock(
        side_effect=[
            [{"type": "page", "url": "chrome-extension://plugin", "webSocketDebuggerUrl": "ws://plugin"}],
            [{"type": "page", "url": "https://example.test/", "webSocketDebuggerUrl": "ws://page"}],
            [{"type": "page", "url": "https://example.test/", "webSocketDebuggerUrl": "ws://page"}],
        ]
    )

    with patch("yuehua_ziniao_webdriver.browser.time.sleep"):
        assert session.wait_for_web_page_target(timeout=1, poll_interval=0.01)

    assert session._list_cdp_tabs.call_count == 3


def test_get_tab_lazily_reconnects_a_disconnected_session() -> None:
    session = make_session()
    session._browser = DisconnectedBrowser()
    page = Mock(name="recovered_page")
    page.url = "https://sellercentral.amazon.com/home"
    recovered_browser = Mock()
    recovered_browser.get_tabs.return_value = [page]
    session.reconnect = Mock(return_value=recovered_browser)

    assert session.get_tab() is page
    session.reconnect.assert_called_once_with(
        timeout=10,
        retry_interval=0.5,
        require_web_page=True,
    )
