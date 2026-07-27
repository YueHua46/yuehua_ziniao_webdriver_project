"""Stable selectors shared by Amazon Seller Central operations."""

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class AmazonSelectors:
    sign_in_submit: Tuple[str, ...] = (
        "#signInSubmit",
        "xpath://input[@id='signInSubmit']",
        "xpath://input[contains(@aria-labelledby,'signInSubmit')]",
    )
    continue_submit: Tuple[str, ...] = (
        "xpath://form[@name='signIn']//input[@id='continue' and @type='submit']",
        "xpath://input[@id='continue' and @type='submit']",
    )
    mfa_input: Tuple[str, ...] = (
        "#auth-mfa-otpcode",
        "xpath://input[@id='auth-mfa-otpcode']",
    )
    mfa_submit: Tuple[str, ...] = (
        "xpath://form[@id='auth-mfa-form']//input[@id='auth-signin-button' and @name='mfaSubmit']",
        "xpath://form[@id='auth-mfa-form']//input[@type='submit']",
    )
    send_code_announce: Tuple[str, ...] = (
        "#auth-send-code-announce",
        "xpath://span[@id='auth-send-code-announce']",
    )
    send_code_button: Tuple[str, ...] = (
        "xpath://span[@id='auth-send-code']//input[@type='submit']",
        "xpath://input[@type='submit']",
        "xpath://span[@id='auth-send-code-announce']/ancestor::form//input[@type='submit']",
    )
    auth_device_form: Tuple[str, ...] = (
        "#auth-select-device-form",
        "xpath://form[@id='auth-select-device-form']",
    )
    auth_error: Tuple[str, ...] = (
        "#auth-error-message-box",
        "xpath://div[@id='auth-error-message-box']",
    )
    country_label: Tuple[str, ...] = (
        "css:.dropdown-account-switcher-header-label-regional-child",
        "css:.dropdown-account-switcher-header-label",
        "xpath://span[contains(@class,'merchant-marketplace')]",
    )
    marketplace_option_buttons: Tuple[str, ...] = (
        "css:div.full-page-account-switcher-accounts-wrapper button.full-page-account-switcher-account-details",
        "css:button.full-page-account-switcher-account-details",
    )
    marketplace_confirm: Tuple[str, ...] = (
        "css:kat-button[data-test='confirm-selection']",
        "xpath://kat-button[@data-test='confirm-selection']",
        "xpath://span[normalize-space()='选择账户' or normalize-space()='選擇帳戶' or normalize-space()='選取帳戶']/ancestor::button[1]",
        "xpath://button[contains(.,'Select account') or contains(.,'Choose account')]",
    )
    locale_trigger: Tuple[str, ...] = (
        "css:.locale-icon-wrapper",
        "xpath://div[contains(@class,'locale-icon-wrapper')]",
    )
    popup_close: Tuple[str, ...] = (
        "css:casino-simple-button[data-testid='tour-popover-dismiss-button']",
        "#vibes-close-button",
        "css:#modal button.modal-close",
        "xpath://button[contains(@aria-label,'Close') or contains(@aria-label,'关闭') or contains(@aria-label,'關閉')]",
        "xpath://kat-popover//casino-simple-button",
    )
