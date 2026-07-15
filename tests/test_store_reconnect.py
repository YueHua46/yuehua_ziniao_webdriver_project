from unittest.mock import Mock, patch

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
