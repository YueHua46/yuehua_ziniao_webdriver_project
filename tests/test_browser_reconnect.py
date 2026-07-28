from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from yuehua_ziniao_webdriver.browser import (
    BrowserDriver,
    BrowserSession,
    Chromium,
    ChromiumTab,
)
from yuehua_ziniao_webdriver.exceptions import ZiniaoError


def web_target(target_id="business", url="https://sellercentral.amazon.com/home"):
    return {
        "id": target_id,
        "type": "page",
        "url": url,
        "webSocketDebuggerUrl": f"ws://page/{target_id}",
    }


def extension_target(target_id="plugin"):
    return {
        "id": target_id,
        "type": "page",
        "url": "chrome-extension://example/background.html",
        "webSocketDebuggerUrl": f"ws://page/{target_id}",
    }


def make_session() -> BrowserSession:
    session = BrowserSession.__new__(BrowserSession)
    session.port = 9222
    session.host = "127.0.0.1"
    session.proxy_host = None
    session.store_id = "store-id"
    session.store_name = "test-store"
    session._browser = Mock(name="stale_browser")
    session._active_tab = None
    session._preferred_target_id = None
    session._closed = False
    session._get_cdp_browser_id = Mock(return_value="browser-id")
    session._list_cdp_tabs = Mock(
        return_value=[extension_target(), web_target()]
    )
    session._clear_drissionpage_caches = Mock()
    return session


def test_session_initialization_is_lazy() -> None:
    with patch("yuehua_ziniao_webdriver.browser.Chromium") as chromium:
        session = BrowserSession(9222, "store-id", "test-store")

    assert session._browser is None
    chromium.assert_not_called()


def test_reconnect_selects_one_json_target_without_get_tabs() -> None:
    session = make_session()
    browser = Mock(name="browser")
    browser.get_tabs.side_effect = AssertionError("get_tabs must not be called")
    tab = Mock(name="business_tab", tab_id="business")

    with patch("yuehua_ziniao_webdriver.browser.Chromium", return_value=browser):
        with patch(
            "yuehua_ziniao_webdriver.browser.ChromiumTab", return_value=tab
        ) as chromium_tab:
            with patch.object(
                session, "wait_for_web_page_target", return_value=True
            ):
                result = session.reconnect()

    assert result is browser
    assert session._active_tab is tab
    chromium_tab.assert_called_once_with(browser, "business")
    browser.get_tabs.assert_not_called()


def test_reconnect_without_web_page_does_not_construct_tab() -> None:
    session = make_session()
    browser = Mock(name="browser")

    with patch("yuehua_ziniao_webdriver.browser.Chromium", return_value=browser):
        with patch("yuehua_ziniao_webdriver.browser.ChromiumTab") as chromium_tab:
            assert session.reconnect(require_web_page=False) is browser

    chromium_tab.assert_not_called()


def test_reconnect_retries_interrupted_chromium_constructor() -> None:
    session = make_session()
    browser = Mock(name="browser")
    tab = Mock(name="tab", tab_id="business")

    with patch(
        "yuehua_ziniao_webdriver.browser.Chromium",
        side_effect=[RuntimeError("websocket disconnected"), browser],
    ) as chromium:
        with patch(
            "yuehua_ziniao_webdriver.browser.ChromiumTab", return_value=tab
        ):
            with patch.object(
                session, "wait_for_web_page_target", return_value=True
            ):
                with patch("yuehua_ziniao_webdriver.browser.time.sleep"):
                    assert session.reconnect(timeout=1, retry_interval=0.01) is browser

    assert chromium.call_count == 2
    assert session._clear_drissionpage_caches.call_count >= 2


def test_reconnect_raises_when_session_is_closed() -> None:
    session = make_session()
    session._closed = True

    with pytest.raises(ZiniaoError, match="浏览器会话已关闭"):
        session.reconnect()


def test_get_tab_filters_json_before_constructing_one_tab() -> None:
    session = make_session()
    tab = Mock(name="business_tab", tab_id="business")

    with patch(
        "yuehua_ziniao_webdriver.browser.ChromiumTab", return_value=tab
    ) as chromium_tab:
        assert session.get_tab() is tab

    chromium_tab.assert_called_once_with(session._browser, "business")


def test_get_tab_lazily_reconnects_after_json_failure() -> None:
    session = make_session()
    browser = Mock(name="recovered_browser")
    tab = Mock(name="recovered_tab", tab_id="business")
    session._select_web_target = Mock(
        side_effect=[RuntimeError("temporary /json failure"), web_target()]
    )
    session.reconnect = Mock(return_value=browser)

    with patch(
        "yuehua_ziniao_webdriver.browser.ChromiumTab", return_value=tab
    ):
        assert session.get_tab() is tab

    session.reconnect.assert_called_once_with(
        timeout=10,
        retry_interval=0.5,
        require_web_page=True,
    )


def test_reconnect_clears_all_three_caches_without_quitting_browser() -> None:
    browser_driver = Mock(name="browser_driver")
    page_driver = Mock(name="page_driver")
    browser = SimpleNamespace(
        id="browser-id",
        _driver=browser_driver,
        _drivers={"business": page_driver},
        _all_drivers={"business": {page_driver}},
        _disconnect_flag=False,
    )
    tab = SimpleNamespace(_browser=browser, _driver=page_driver)
    other_browser = SimpleNamespace(id="other-browser")
    other_tab = SimpleNamespace(_browser=other_browser, _driver=Mock())

    with patch.object(Chromium, "_BROWSERS", {"browser-id": browser}):
        with patch.object(BrowserDriver, "BROWSERS", {"browser-id": browser_driver}):
            with patch.object(
                ChromiumTab,
                "_TABS",
                {"business": tab, "other": other_tab},
            ):
                BrowserSession._clear_drissionpage_caches(
                    "browser-id", ["business"]
                )
                assert Chromium._BROWSERS == {}
                assert BrowserDriver.BROWSERS == {}
                assert ChromiumTab._TABS == {"other": other_tab}

    assert browser._disconnect_flag is True
    browser_driver.stop.assert_called()
    page_driver.stop.assert_called()
    assert not hasattr(browser, "quit")


def test_wait_for_web_target_uses_json_metadata_only() -> None:
    session = make_session()
    session._list_cdp_tabs.side_effect = [
        [extension_target()],
        [extension_target(), web_target()],
        [extension_target(), web_target()],
    ]

    with patch("yuehua_ziniao_webdriver.browser.time.sleep"):
        assert session.wait_for_web_page_target(timeout=1, poll_interval=0.01)

    assert session._list_cdp_tabs.call_count == 3


def test_extension_ip_check_never_attaches_drissionpage() -> None:
    session = make_session()
    session.ip_check_url = "chrome-extension://ziniao/ip-check.html"
    session._open_url_in_new_cdp_tab = Mock(return_value="ip-target")
    session._wait_for_target_state = Mock(return_value="stable")
    session.reconnect = Mock()

    assert session.check_ip()
    session.reconnect.assert_not_called()


def test_http_ip_check_attaches_exact_created_target() -> None:
    session = make_session()
    session.ip_check_url = "https://check.example.test/ip"
    session._open_url_in_new_cdp_tab = Mock(return_value="ip-target")
    session._wait_for_target_state = Mock(return_value="stable")
    tab = Mock(name="ip_tab")
    tab.ele.return_value = Mock(name="success_button")
    browser = Mock(name="browser")

    def reconnect(**kwargs):
        session._active_tab = tab
        return browser

    session.reconnect = Mock(side_effect=reconnect)

    assert session.check_ip()
    session.reconnect.assert_called_once_with(
        timeout=10.0,
        retry_interval=0.5,
        require_web_page=True,
        target_id="ip-target",
    )


def test_auto_closed_ip_target_is_success() -> None:
    session = make_session()
    session.ip_check_url = "https://check.example.test/ip"
    session._open_url_in_new_cdp_tab = Mock(return_value="ip-target")
    session._wait_for_target_state = Mock(return_value="closed")
    session.reconnect = Mock()

    assert session.check_ip()
    session.reconnect.assert_not_called()


def test_loaded_business_page_confirms_network_success() -> None:
    session = make_session()
    tab = Mock(url="https://sellercentral.amazon.com/home")
    session._active_tab = tab

    assert session.verify_business_page(timeout=3)
    tab.wait.doc_loaded.assert_called_once_with(timeout=3)


def test_chrome_error_page_fails_network_verification() -> None:
    session = make_session()
    session._active_tab = Mock(url="chrome-error://chromewebdata/")

    assert not session.verify_business_page(timeout=3)
