"""Public Amazon Seller Central automation facade."""

import time
from typing import Any, Iterable, Optional
from urllib.parse import urlsplit

from .auth import AmazonAuthMixin
from .locale import AmazonLocaleMixin
from .marketplace import AmazonMarketplaceMixin
from .selectors import AmazonSelectors


class AmazonSellerCentral(AmazonAuthMixin, AmazonMarketplaceMixin, AmazonLocaleMixin):
    """Reusable Seller Central operations over an existing DrissionPage tab."""

    def __init__(self, page: Any, selectors: Optional[AmazonSelectors] = None) -> None:
        self.page = page
        self.selectors = selectors or AmazonSelectors()
        self._seller_base_url = self._base_url_from(self.url)

    @property
    def url(self) -> str:
        return str(getattr(self.page, "url", "") or "")

    @property
    def base_url(self) -> str:
        current = self._base_url_from(self.url)
        if "sellercentral" in current and "amazon." in current:
            self._seller_base_url = current
        if not self._seller_base_url:
            raise RuntimeError("无法确定 Amazon Seller Central 基本地址")
        return self._seller_base_url

    @staticmethod
    def _base_url_from(url: str) -> str:
        parsed = urlsplit(str(url or ""))
        return "%s://%s" % (parsed.scheme, parsed.netloc) if parsed.scheme and parsed.netloc else ""

    def go_home(self) -> None:
        self.page.get("%s/home" % self.base_url)
        try:
            self.page.wait.doc_loaded(timeout=15)
        except Exception:
            pass
        self.ensure_logged_in(context="Amazon 首页")
        self.dismiss_known_popups()

    def prepare(self, marketplace: str, locale: Optional[str] = None) -> None:
        self.ensure_logged_in()
        self.dismiss_known_popups()
        self.switch_marketplace(marketplace)
        if locale:
            self.switch_language(locale)

    def dismiss_known_popups(self) -> None:
        for locator in self.selectors.popup_close:
            try:
                self._click_if_exists((locator,), timeout=0.5)
            except Exception:
                continue

    def close_popups(self) -> None:
        """Backward-compatible alias for existing callers."""
        self.dismiss_known_popups()

    def _safe_ele(self, locator: str, timeout: float = 0) -> Any:
        try:
            return self.page.ele(locator, timeout=timeout)
        except Exception:
            return None

    def _first_element(self, locators: Iterable[str], timeout: float = 0) -> Any:
        candidates = tuple(locators)
        if not candidates:
            return None
        deadline = time.monotonic() + max(timeout, 0)
        while True:
            for locator in candidates:
                element = self._safe_ele(locator, timeout=0)
                if element:
                    return element
            if timeout <= 0:
                return None
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            time.sleep(min(0.1, remaining))

    def _click_if_exists(self, locators: Iterable[str], timeout: float = 0) -> bool:
        element = self._first_element(locators, timeout=timeout)
        if not element:
            return False
        element.click()
        return True

    def _text_of(self, locators: Iterable[str], timeout: float = 0) -> str:
        element = self._first_element(locators, timeout=timeout)
        if not element:
            return ""
        try:
            return str(element.text or "")
        except Exception:
            return ""
