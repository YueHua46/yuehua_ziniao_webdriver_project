from unittest.mock import Mock, patch

import pytest

from yuehua_ziniao_webdriver.exceptions import StoreOperationError, ZiniaoError
from yuehua_ziniao_webdriver.store import StoreManager


def test_open_store_refreshes_browser_connection_before_returning() -> None:
    http_client = Mock()
    http_client.send_request.return_value = {
        "statusCode": 0,
        "debuggingPort": 9222,
        "browserOauth": "oauth-id",
        "ipDetectionPage": "https://example.test/ip",
        "launcherPage": "https://example.test/home",
    }
    manager = StoreManager(
        http_client, {"company": "c", "username": "u", "password": "p"}
    )
    manager._get_store_name = Mock(return_value="test-store")
    session = Mock()
    session.check_ip.return_value = False
    session.verify_business_page.return_value = True

    with patch("yuehua_ziniao_webdriver.store.BrowserSession", return_value=session):
        result = manager.open_store(
            "oauth-id",
            options={"cdpReconnectTimeout": 6, "cdpReconnectInterval": 0.25},
        )

    assert result is session
    session.open_launcher_page.assert_called_once()
    session.reconnect.assert_called_once_with(
        timeout=6.0,
        retry_interval=0.25,
        require_web_page=True,
    )
    session.verify_business_page.assert_called_once_with(timeout=6.0)


def test_open_store_keeps_session_when_final_page_refresh_is_transient() -> None:
    http_client = Mock()
    http_client.send_request.return_value = {
        "statusCode": 0,
        "debuggingPort": 9222,
        "browserOauth": "oauth-id",
        "ipDetectionPage": None,
        "launcherPage": "https://example.test/home",
    }
    manager = StoreManager(
        http_client, {"company": "c", "username": "u", "password": "p"}
    )
    manager._get_store_name = Mock(return_value="test-store")
    session = Mock()
    session.reconnect.side_effect = ZiniaoError("temporary page disconnect")
    session.verify_business_page.return_value = True

    with patch("yuehua_ziniao_webdriver.store.BrowserSession", return_value=session):
        result = manager.open_store("oauth-id")

    assert result is session
    session.close.assert_not_called()
    session.verify_business_page.assert_called_once_with(timeout=10.0)


def test_network_failure_reopens_store_until_verification_succeeds() -> None:
    http_client = Mock()
    http_client.send_request.return_value = {
        "statusCode": 0,
        "debuggingPort": 9222,
        "browserOauth": "oauth-id",
        "ipDetectionPage": "chrome-extension://ziniao/ip-check.html",
        "launcherPage": "https://example.test/home",
    }
    manager = StoreManager(
        http_client, {"company": "c", "username": "u", "password": "p"}
    )
    manager._get_store_name = Mock(return_value="test-store")
    sessions = [Mock(), Mock(), Mock()]
    for session, verified in zip(sessions, (False, False, True)):
        session.check_ip.return_value = True
        session.verify_business_page.return_value = verified

    with patch(
        "yuehua_ziniao_webdriver.store.BrowserSession",
        side_effect=sessions,
    ):
        result = manager.open_store("oauth-id")

    assert result is sessions[2]
    sessions[0].close.assert_called_once_with()
    sessions[1].close.assert_called_once_with()
    sessions[2].close.assert_not_called()
    start_calls = [
        call
        for call in http_client.send_request.call_args_list
        if call.args[0].get("action") == "startBrowser"
    ]
    assert len(start_calls) == 3


def test_network_failure_raises_only_after_three_full_attempts() -> None:
    http_client = Mock()
    http_client.send_request.return_value = {
        "statusCode": 0,
        "debuggingPort": 9222,
        "browserOauth": "oauth-id",
        "ipDetectionPage": "chrome-extension://ziniao/ip-check.html",
        "launcherPage": "https://example.test/home",
    }
    manager = StoreManager(
        http_client, {"company": "c", "username": "u", "password": "p"}
    )
    manager._get_store_name = Mock(return_value="test-store")
    sessions = [Mock(), Mock(), Mock()]
    for session in sessions:
        session.check_ip.return_value = True
        session.verify_business_page.return_value = False

    with patch(
        "yuehua_ziniao_webdriver.store.BrowserSession",
        side_effect=sessions,
    ):
        with pytest.raises(StoreOperationError, match="连续 3 次"):
            manager.open_store("oauth-id")

    for session in sessions:
        session.close.assert_called_once_with()
