from unittest.mock import Mock, patch

import pytest

from yuehua_ziniao_webdriver.browser import BrowserSession
from yuehua_ziniao_webdriver.exceptions import ZiniaoError


def make_session() -> BrowserSession:
    session = BrowserSession.__new__(BrowserSession)
    session.port = 9222
    session.host = "127.0.0.1"
    session.store_id = "store-id"
    session.store_name = "test-store"
    session._browser = Mock(name="stale_browser")
    session._closed = False
    return session


class DisconnectedPluginTab:
    @property
    def url(self) -> str:
        raise RuntimeError("plugin page websocket disconnected")


def test_session_initialization_does_not_require_web_page() -> None:
    connected_browser = Mock(name="connected_browser")

    with patch(
        "yuehua_ziniao_webdriver.browser.Chromium",
        return_value=connected_browser,
    ):
        session = BrowserSession(9222, "store-id", "test-store")

    assert session.browser is connected_browser
    connected_browser.get_tabs.assert_not_called()


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
            result = session.reconnect(timeout=10, retry_interval=0.5)

    assert result is connected_browser
    assert session.browser is connected_browser
    assert chromium.call_count == 2
    sleep.assert_called_once_with(0.5)


def test_reconnect_raises_when_session_is_closed() -> None:
    session = make_session()
    session._closed = True

    with pytest.raises(ZiniaoError, match="浏览器会话已关闭"):
        session.reconnect()
