from unittest.mock import Mock, call, patch

import pytest

from yuehua_ziniao_webdriver.platforms.amazon import (
    AmazonLocaleError,
    AmazonSellerCentral,
)


def test_login_submit_falls_back_to_js_click() -> None:
    page = Mock()
    page.url = "https://sellercentral.amazon.com/ap/signin?token=SECRET"
    button = Mock()
    amazon = AmazonSellerCentral(page)
    amazon._first_element = Mock(return_value=button)
    amazon._login_fingerprint = Mock(return_value=("same",))
    amazon._wait_login_transition = Mock(side_effect=[False, True])

    amazon._click_login_control(amazon.selectors.sign_in_submit, "密码登录")

    assert button.click.call_args_list == [call(timeout=3), call(by_js=True)]
    button.run_js.assert_not_called()
    assert amazon._login_url_for_log() == "https://sellercentral.amazon.com/ap/signin"


@patch("yuehua_ziniao_webdriver.platforms.amazon.auth.time.sleep")
def test_empty_mfa_refreshes_once_for_automatic_fill(_sleep: Mock) -> None:
    page = Mock()
    page.url = "https://sellercentral.amazon.com/ap/mfa"
    first, second = Mock(), Mock()
    first.attr.return_value = ""
    first.property.return_value = ""
    second.attr.return_value = "123456"
    amazon = AmazonSellerCentral(page)

    def find(locators, timeout=2):
        if locators == amazon.selectors.sign_in_submit:
            return None
        if locators == amazon.selectors.mfa_input:
            return find.mfa.pop(0)
        return None

    find.mfa = [first, second]
    amazon._first_element = Mock(side_effect=find)
    amazon._click_login_control = Mock()

    assert amazon._solve_regular_login_step("TEST") is True
    page.refresh.assert_called_once_with()
    amazon._click_login_control.assert_called_once_with(
        amazon.selectors.mfa_submit, "提交两步验证码"
    )


def test_login_step_prefers_password_before_continue() -> None:
    page, password = Mock(), Mock()
    page.url = "https://sellercentral.amazon.com/ap/signin"
    amazon = AmazonSellerCentral(page)

    def find(locators, timeout=2):
        if locators == amazon.selectors.sign_in_submit:
            return password
        if locators == amazon.selectors.continue_submit:
            return Mock()
        return None

    amazon._first_element = Mock(side_effect=find)
    amazon._click_login_control = Mock()

    assert amazon._solve_regular_login_step("TEST") is True
    amazon._click_login_control.assert_called_once_with(
        amazon.selectors.sign_in_submit, "密码登录"
    )


@patch("yuehua_ziniao_webdriver.platforms.amazon.marketplace.time.sleep")
def test_marketplace_switch_retries_with_fresh_page(_sleep: Mock) -> None:
    page = Mock()
    page.url = "https://sellercentral.amazon.co.uk/account-switcher/default/merchantMarketplace"
    amazon = AmazonSellerCentral(page)
    amazon._switch_marketplace_once = Mock(side_effect=[RuntimeError("stale"), None])

    amazon.switch_marketplace("FR")

    assert amazon._switch_marketplace_once.call_args_list == [call("法国"), call("法国")]
    page.get.assert_called_once_with(
        "https://sellercentral.amazon.co.uk/account-switcher/default/merchantMarketplace"
    )


@patch("yuehua_ziniao_webdriver.platforms.amazon.marketplace.time.sleep")
def test_marketplace_waits_for_async_country_rows(_sleep: Mock) -> None:
    page = Mock()
    page.url = "https://sellercentral.amazon.co.uk/home"
    account = Mock()
    account.text = "STORE_NAME（当前）"
    target = Mock()
    target.text = "英国"
    page.eles.side_effect = [[account], [account, target]]
    amazon = AmazonSellerCentral(page)
    amazon.dismiss_known_popups = Mock()
    amazon._text_of = Mock(side_effect=["德国", "英国"])
    amazon._safe_ele = Mock(side_effect=[account, Mock()])

    def confirm(_locators, timeout=0):
        page.url = "https://sellercentral.amazon.co.uk/home"
        return True

    amazon._click_if_exists = Mock(side_effect=confirm)
    amazon.ensure_logged_in = Mock()

    amazon.switch_marketplace("UK")

    assert page.eles.call_count == 2
    account.click.assert_not_called()
    target.click.assert_called_once_with()


def test_marketplace_error_reports_only_observed_page_labels() -> None:
    page = Mock()
    page.url = "https://sellercentral.amazon.co.uk/account-switcher/default/merchantMarketplace"
    account, germany = Mock(), Mock()
    account.text = "STORE_NAME（当前）"
    germany.text = "德国（当前）"
    page.eles.return_value = [account, germany]
    amazon = AmazonSellerCentral(page)
    amazon.dismiss_known_popups = Mock()
    amazon._safe_ele = Mock(side_effect=[account, Mock()])

    with patch(
        "yuehua_ziniao_webdriver.platforms.amazon.marketplace.time.monotonic",
        side_effect=[0, 31],
    ):
        with pytest.raises(
            RuntimeError,
            match="页面实际识别=STORE_NAME（当前）；德国（当前）",
        ):
            amazon._switch_marketplace_once("英国")


def test_dismiss_known_popups_uses_bounded_selector_checks() -> None:
    page = Mock()
    page.url = "https://sellercentral.amazon.com/home"
    amazon = AmazonSellerCentral(page)
    amazon._click_if_exists = Mock(return_value=False)

    amazon.dismiss_known_popups()

    assert amazon._click_if_exists.call_count == len(amazon.selectors.popup_close)
    for called in amazon._click_if_exists.call_args_list:
        assert called.kwargs["timeout"] == 0.5


@patch("yuehua_ziniao_webdriver.platforms.amazon.locale.time.sleep")
def test_language_switch_waits_for_verified_locale(_sleep: Mock) -> None:
    page = Mock()
    page.url = "https://sellercentral.amazon.com/home"
    trigger_before, option, trigger_after = Mock(), Mock(), Mock()
    trigger_before.text = "EN"
    trigger_after.text = "ZH"
    amazon = AmazonSellerCentral(page)
    amazon._first_element = Mock(side_effect=[trigger_before, option, trigger_after])

    amazon.switch_language("zh_CN")

    trigger_before.hover.assert_called_once_with()
    option.click.assert_called_once_with()


def test_unknown_language_is_rejected_before_touching_page() -> None:
    page = Mock()
    page.url = "https://sellercentral.amazon.com/home"

    with pytest.raises(AmazonLocaleError, match="不支持"):
        AmazonSellerCentral(page).switch_language("INVALID")
