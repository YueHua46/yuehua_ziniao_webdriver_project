"""Amazon Seller Central sign-in and MFA handling."""

import logging
import time
from typing import Any, Tuple

from .exceptions import AmazonLoginRequired

logger = logging.getLogger(__name__)


class AmazonAuthMixin:
    """Login behavior used by :class:`AmazonSellerCentral`."""

    page: Any
    selectors: Any

    def ensure_logged_in(self, context: str = "Amazon", max_rounds: int = 5) -> str:
        if not self._login_pending():
            return "成功"

        logger.info("【亚马逊登录开始】上下文=%s | URL=%s", context, self._login_url_for_log())
        time.sleep(3)
        self._close_login_blocker()

        for round_no in range(1, max_rounds + 1):
            if not self._solve_regular_login_step(context):
                break
            logger.info(
                "【亚马逊登录步骤完成】上下文=%s | 轮次=%d/%d | URL=%s",
                context,
                round_no,
                max_rounds,
                self._login_url_for_log(),
            )
            self._wait_login_page_ready()
            time.sleep(3)

        if self._safe_ele(self.selectors.send_code_announce[0], timeout=2):
            self._select_otp_method_and_send(context)
            for _ in range(max_rounds):
                if not self._solve_regular_login_step(context):
                    break
                self._wait_login_page_ready()
                time.sleep(3)

        if self._login_pending():
            error = self._text_of(self.selectors.auth_error, timeout=1).strip()
            detail = "，页面错误：%s" % error if error else ""
            raise AmazonLoginRequired(
                "【%s】登录未完成%s，URL=%s" % (context, detail, self._login_url_for_log())
            )
        logger.info("【亚马逊登录成功】上下文=%s | URL=%s", context, self._login_url_for_log())
        return "成功"

    def handle_login(
        self,
        project_name: str = "",
        shop_name: str = "",
        max_rounds: int = 5,
    ) -> str:
        """Backward-compatible alias; ``shop_name`` is intentionally not logged."""
        del shop_name
        return self.ensure_logged_in(project_name or "Amazon", max_rounds=max_rounds)

    def is_login_required(self) -> bool:
        return self._login_pending()

    def _solve_regular_login_step(self, context: str) -> bool:
        if self._first_element(self.selectors.sign_in_submit):
            self._click_login_control(self.selectors.sign_in_submit, "密码登录")
            return True

        mfa = self._first_element(self.selectors.mfa_input)
        if mfa:
            time.sleep(3)
            code = self._input_value(mfa)
            if not code:
                self.page.refresh()
                self._wait_login_page_ready()
                time.sleep(3)
                mfa = self._first_element(self.selectors.mfa_input)
                code = self._input_value(mfa)
            if not code:
                raise AmazonLoginRequired("【%s】两次获取自动验证码均为空" % context)
            self._click_login_control(self.selectors.mfa_submit, "提交两步验证码")
            return True

        if self._first_element(self.selectors.continue_submit):
            self._click_login_control(self.selectors.continue_submit, "继续")
            return True
        return False

    def _click_login_submit(self) -> bool:
        if not self._first_element(self.selectors.sign_in_submit):
            return False
        self._click_login_control(self.selectors.sign_in_submit, "密码登录")
        return True

    def _click_login_control(self, locators: Tuple[str, ...], step: str) -> None:
        button = self._first_element(locators)
        if not button:
            raise AmazonLoginRequired("亚马逊登录步骤“%s”未找到对应元素" % step)
        before = self._login_fingerprint()
        actions = (
            lambda: button.click(timeout=3),
            lambda: button.click(by_js=True),
            lambda: button.run_js(
                "this.form && this.form.requestSubmit ? "
                "this.form.requestSubmit(this) : this.click();"
            ),
        )
        errors = []
        for attempt, action in enumerate(actions, 1):
            try:
                action()
            except Exception as exc:
                errors.append("第%d次点击异常=%s" % (attempt, exc))
            if self._wait_login_transition(before, timeout=4):
                return
            logger.warning("【亚马逊登录点击未生效】步骤=%s | 尝试=%d/3", step, attempt)
        error = self._text_of(self.selectors.auth_error, timeout=1).strip()
        detail = " | 页面错误=%s" % error if error else ""
        raise AmazonLoginRequired(
            "亚马逊登录步骤“%s”连续3种点击均未触发页面变化 | URL=%s%s | %s"
            % (step, self._login_url_for_log(), detail, "; ".join(errors))
        )

    def _wait_login_transition(self, before: Tuple[Any, ...], timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            time.sleep(0.4)
            if self._login_fingerprint() != before:
                return True
        return False

    def _login_fingerprint(self) -> Tuple[Any, ...]:
        return (
            self.url,
            bool(self._first_element(self.selectors.sign_in_submit, timeout=0.2)),
            bool(self._first_element(self.selectors.mfa_input, timeout=0.2)),
            bool(self._first_element(self.selectors.continue_submit, timeout=0.2)),
            bool(self._safe_ele(self.selectors.send_code_announce[0], timeout=0.2)),
            self._text_of(self.selectors.auth_error, timeout=0.2).strip(),
        )

    def _login_pending(self) -> bool:
        url = self.url.lower()
        return (
            "signin" in url
            or "/ap/mfa" in url
            or bool(self._first_element(self.selectors.sign_in_submit, timeout=0.5))
            or bool(self._first_element(self.selectors.mfa_input, timeout=0.5))
            or bool(self._first_element(self.selectors.continue_submit, timeout=0.5))
        )

    def _wait_login_page_ready(self, timeout: float = 15) -> None:
        try:
            self.page.wait.doc_loaded(timeout=timeout)
        except Exception:
            time.sleep(1)

    def _login_url_for_log(self) -> str:
        return self.url.split("?", 1)[0]

    @staticmethod
    def _input_value(element: Any) -> str:
        if not element:
            return ""
        try:
            return str(element.attr("value") or element.property("value") or "").strip()
        except Exception:
            return ""

    def _close_login_blocker(self) -> None:
        locators = (
            "xpath://div[@id='seller-sprite-extension-app']//div[@id='main-sellersprite-extension']//button[@aria-label='Close this dialog']",
            "xpath://div[@id='main-sellersprite-extension']//button[@aria-label='Close this dialog']",
        )
        close = self._first_element(locators, timeout=1)
        if close:
            try:
                close.click(by_js=True)
            except Exception:
                pass

    def _select_otp_method_and_send(self, context: str) -> None:
        form = self._first_element(self.selectors.auth_device_form)
        if not form:
            raise AmazonLoginRequired("【%s】出现发送验证码页面，但未找到验证方式表单" % context)
        options = form.eles("tag:label")
        if len(options) < 3:
            raise AmazonLoginRequired("【%s】验证方式不足3项" % context)
        options[2].click()
        self._click_login_control(self.selectors.send_code_button, "发送一次性密码")
        self._wait_login_page_ready()
        time.sleep(2)


def is_login(page: Any) -> bool:
    from .client import AmazonSellerCentral

    return AmazonSellerCentral(page).is_login_required()


def handle_login(page: Any) -> str:
    from .client import AmazonSellerCentral

    return AmazonSellerCentral(page).ensure_logged_in()
