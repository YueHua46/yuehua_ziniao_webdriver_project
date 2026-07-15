from unittest.mock import Mock, patch

from yuehua_ziniao_webdriver.http_client import HttpClient


def test_wait_until_ready_retries_empty_response_until_valid_json() -> None:
    client = HttpClient(16851)
    empty_response = Mock(content=b"", status_code=200)
    ready_response = Mock(content=b"{}", status_code=200)
    ready_response.json.return_value = {
        "statusCode": 0,
        "browserList": [{"browserName": "test-store"}],
    }

    with patch(
        "yuehua_ziniao_webdriver.http_client.requests.post",
        side_effect=[empty_response, ready_response],
    ) as post:
        with patch("yuehua_ziniao_webdriver.http_client.time.sleep") as sleep:
            result = client.wait_until_ready(
                {"company": "c", "username": "u", "password": "p"},
                timeout=10,
                poll_interval=0.5,
            )

    assert result["statusCode"] == 0
    assert post.call_count == 2
    sleep.assert_called_once_with(0.5)
    empty_response.close.assert_called_once()
    ready_response.close.assert_called_once()
