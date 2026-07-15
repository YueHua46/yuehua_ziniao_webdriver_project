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


def test_reconnect_discards_stale_browser_and_retries_page_connection() -> None:
    session = make_session()
    connected_browser = Mock(name="connected_browser")

    with patch(
        "yuehua_ziniao_webdriver.browser.Chromium",
        side_effect=[RuntimeError("page websocket disconnected"), connected_browser],
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
