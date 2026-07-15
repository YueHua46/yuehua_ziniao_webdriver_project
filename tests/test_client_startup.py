from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from yuehua_ziniao_webdriver.client import ZiniaoClient
from yuehua_ziniao_webdriver.exceptions import BrowserStartError, CommunicationError


def make_client() -> ZiniaoClient:
    client = ZiniaoClient.__new__(ZiniaoClient)
    client.config = SimpleNamespace(
        host="127.0.0.1",
        socket_port=16851,
        startup_timeout=30,
        startup_poll_interval=0.5,
        startup_attempts=2,
        startup_restart_delay=0,
        get_user_info=Mock(return_value={"company": "c"}),
    )
    client.process_manager = Mock()
    client.http_client = Mock()
    client.store_manager = Mock()
    client.store_manager._store_list_cache = None
    client._started = False
    return client


def test_start_waits_for_json_api_before_marking_client_started() -> None:
    client = make_client()
    browser_list = [{"browserName": "test-store"}]
    client.http_client.wait_until_ready.return_value = {
        "statusCode": 0,
        "browserList": browser_list,
    }

    client.start(kill_existing=True, wait_time=5)

    client.process_manager.start_browser.assert_called_once_with(wait_time=5)
    client.http_client.wait_until_ready.assert_called_once_with(
        {"company": "c"},
        timeout=30,
        poll_interval=0.5,
    )
    assert client._started is True
    assert client.store_manager._store_list_cache == browser_list


def test_start_remains_stopped_when_json_api_never_becomes_ready() -> None:
    client = make_client()
    client.http_client.wait_until_ready.side_effect = CommunicationError("not ready")

    with pytest.raises(BrowserStartError, match="HTTP API 启动失败"):
        client.start(kill_existing=True)

    assert client._started is False


def test_start_restarts_client_internally_after_readiness_timeout() -> None:
    client = make_client()
    client.http_client.wait_until_ready.side_effect = [
        CommunicationError("not ready"),
        {"statusCode": 0, "browserList": []},
    ]

    client.start(kill_existing=True)

    assert client._started is True
    assert client.process_manager.start_browser.call_count == 2
    assert client.process_manager.kill_existing_process.call_count == 2
