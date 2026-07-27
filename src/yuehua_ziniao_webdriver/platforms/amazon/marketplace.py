"""Amazon Seller Central marketplace selection."""

import logging
import time
from typing import Any, Dict, Tuple

from .exceptions import AmazonMarketplaceError

logger = logging.getLogger(__name__)


MARKETPLACE_ALIASES: Dict[str, Tuple[str, ...]] = {
    "美国": ("美国", "美國", "United States"),
    "加拿大": ("加拿大", "Canada"),
    "墨西哥": ("墨西哥", "Mexico", "México"),
    "巴西": ("巴西", "Brazil", "Brasil"),
    "英国": ("英国", "英國", "United Kingdom"),
    "德国": ("德国", "德國", "Germany", "Deutschland"),
    "法国": ("法国", "法國", "France"),
    "意大利": ("意大利", "義大利", "Italy", "Italia"),
    "西班牙": ("西班牙", "Spain", "España"),
    "荷兰": ("荷兰", "荷蘭", "Netherlands", "Nederland"),
    "瑞典": ("瑞典", "Sweden", "Sverige"),
    "波兰": ("波兰", "波蘭", "Poland", "Polska"),
    "比利时": ("比利时", "比利時", "Belgium", "België", "Belgique"),
    "土耳其": ("土耳其", "Türkiye", "Turkey"),
    "日本": ("日本", "Japan"),
    "澳大利亚": ("澳大利亚", "澳大利亞", "澳洲", "Australia"),
    "澳洲": ("澳洲", "澳大利亚", "澳大利亞", "Australia"),
    "印度": ("印度", "India"),
    "新加坡": ("新加坡", "Singapore"),
    "阿联酋": ("阿联酋", "阿聯酋", "United Arab Emirates", "UAE"),
    "沙特": ("沙特", "沙烏地阿拉伯", "Saudi Arabia"),
}

MARKETPLACE_CODES = {
    "US": "美国", "CA": "加拿大", "MX": "墨西哥", "BR": "巴西",
    "UK": "英国", "GB": "英国", "DE": "德国", "FR": "法国",
    "IT": "意大利", "ES": "西班牙", "NL": "荷兰", "SE": "瑞典",
    "PL": "波兰", "BE": "比利时", "TR": "土耳其", "JP": "日本",
    "AU": "澳大利亚", "IN": "印度", "SG": "新加坡", "AE": "阿联酋",
    "SA": "沙特",
}


def normalize_marketplace(value: str) -> str:
    stripped = str(value or "").strip()
    return MARKETPLACE_CODES.get(stripped.upper(), stripped)


class AmazonMarketplaceMixin:
    page: Any
    selectors: Any

    def switch_marketplace(self, marketplace: str) -> None:
        target = normalize_marketplace(marketplace)
        failures = []
        for attempt in range(1, 4):
            logger.info("【站点切换尝试】目标=%s | 尝试=%d/3 | URL=%s", target, attempt, self.url)
            try:
                self._switch_marketplace_once(target)
                if attempt > 1:
                    logger.info("【站点切换重试成功】目标=%s | 尝试=%d/3", target, attempt)
                return
            except Exception as exc:
                failures.append("第%d次: %s" % (attempt, exc))
                if attempt >= 3:
                    raise AmazonMarketplaceError(
                        "切换站点“%s”连续 3 次失败；失败明细=%s；URL=%s"
                        % (target, "；".join(failures), self.url)
                    ) from exc
                logger.warning(
                    "【站点切换失败，将重试】目标=%s | 尝试=%d/3 | URL=%s | 错误=%s",
                    target,
                    attempt,
                    self.url,
                    exc,
                )
                self._reload_marketplace_switcher(target, attempt + 1)
                time.sleep(1)

    def _reload_marketplace_switcher(self, target: str, next_attempt: int) -> None:
        try:
            self.page.get("%s/account-switcher/default/merchantMarketplace" % self.base_url)
        except Exception as exc:
            logger.warning(
                "【站点切换恢复加载异常】目标=%s | 下次尝试=%d/3 | URL=%s | 错误=%s",
                target, next_attempt, self.url, exc,
            )

    def _switch_marketplace_once(self, target: str) -> None:
        self.dismiss_known_popups()
        current = ""
        if "/account-switcher/" not in self.url:
            current = self._text_of(self.selectors.country_label, timeout=3)
        if self._site_label_matches(target, current):
            return

        if "/account-switcher/" not in self.url:
            self.page.get("%s/account-switcher/default/merchantMarketplace" % self.base_url)

        first_option = self._safe_ele(
            "css:button.full-page-account-switcher-account-details", timeout=30
        )
        if not first_option:
            self.ensure_logged_in(context="切换站点")
            first_option = self._safe_ele(
                "css:button.full-page-account-switcher-account-details", timeout=30
            )
        if not first_option:
            raise AmazonMarketplaceError("切换站点页面加载失败：URL=%s" % self.url)

        wrapper = self._safe_ele(
            "css:div.full-page-account-switcher-accounts-wrapper", timeout=10
        )
        if wrapper:
            try:
                wrapper.set.attr("style", "max-height: max-content")
            except Exception:
                try:
                    self.page.run_js("arguments[0].style.maxHeight='max-content'", wrapper)
                except Exception:
                    pass

        selected = False
        observed = []
        deadline = time.monotonic() + 30
        while True:
            try:
                options = self.page.eles(self.selectors.marketplace_option_buttons[0], timeout=0.5)
            except Exception:
                options = []
            for option in options:
                option_text = " ".join(str(getattr(option, "text", "") or "").split())
                if option_text and option_text not in observed:
                    observed.append(option_text)
                if self._site_label_matches(target, option_text):
                    option.click()
                    selected = True
                    break
            if selected or time.monotonic() >= deadline:
                break
            time.sleep(0.2)
        if not selected:
            actual = "；".join(observed) if observed else "未读取到任何账户/站点按钮文字"
            raise AmazonMarketplaceError(
                "切换站点页面未找到目标站点“%s”（页面实际识别=%s | URL=%s）"
                % (target, actual, self.url)
            )

        if not self._click_if_exists(self.selectors.marketplace_confirm, timeout=10):
            raise AmazonMarketplaceError("已选择站点 %s，但未找到选择账户按钮" % target)
        self._wait_marketplace_transition(target)
        self.ensure_logged_in(context="切换站点")
        self.dismiss_known_popups()
        switched = self._text_of(self.selectors.country_label, timeout=2)
        if switched and not self._site_label_matches(target, switched):
            raise AmazonMarketplaceError(
                "站点切换后校验失败：目标=%s，当前=%s，URL=%s" % (target, switched, self.url)
            )

    def _wait_marketplace_transition(self, target: str, timeout: float = 20) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if "/account-switcher/" not in self.url:
                try:
                    self.page.wait.doc_loaded(timeout=10)
                except Exception:
                    pass
                return
            time.sleep(0.2)
        raise AmazonMarketplaceError(
            "已选择站点“%s”并确认，但页面在 %g 秒内未跳转（URL=%s）"
            % (target, timeout, self.url)
        )

    @staticmethod
    def _site_label_matches(target: str, displayed_text: str) -> bool:
        text = str(displayed_text or "").casefold()
        aliases = MARKETPLACE_ALIASES.get(target, (target,))
        return any(alias.casefold() in text for alias in aliases if alias)


def en_site_to_cn_site(site: str) -> str:
    return normalize_marketplace(site)


def switch_site(page: Any, site: str) -> None:
    from .client import AmazonSellerCentral

    AmazonSellerCentral(page).switch_marketplace(site)
