"""Amazon Seller Central locale selection."""

import time
from typing import Any, Dict, Tuple

from .exceptions import AmazonLocaleError

LOCALES: Dict[str, Tuple[str, Tuple[str, ...]]] = {
    "zh_CN": ("zh_CN", ("ZH", "简体中文", "中文")),
    "zh_TW": ("zh_TW", ("繁體中文", "繁体中文", "ZH-TW")),
    "en_US": ("en_US", ("EN", "English")),
}

LOCALE_ALIASES = {
    "ZH": "zh_CN", "ZH_CN": "zh_CN", "中文": "zh_CN", "简体中文": "zh_CN",
    "ZH_TW": "zh_TW", "繁體中文": "zh_TW", "繁体中文": "zh_TW",
    "EN": "en_US", "EN_US": "en_US", "ENGLISH": "en_US",
}


def normalize_locale(locale: str) -> str:
    value = str(locale or "").strip()
    return LOCALE_ALIASES.get(value.upper(), value)


class AmazonLocaleMixin:
    page: Any
    selectors: Any

    def switch_language(self, locale: str = "zh_CN", timeout: float = 15) -> None:
        target = normalize_locale(locale)
        if target not in LOCALES:
            raise AmazonLocaleError("不支持的亚马逊语言：%s" % locale)
        data_tag, labels = LOCALES[target]
        trigger = self._first_element(self.selectors.locale_trigger, timeout=3)
        if not trigger:
            raise AmazonLocaleError("未找到语言切换入口")
        if self._locale_matches(str(getattr(trigger, "text", "") or ""), labels):
            return

        trigger.hover()
        option = self._first_element(
            (
                "xpath://a[contains(@data-test-tag, '%s')]" % data_tag,
                "css:a[data-test-tag*='%s']" % data_tag,
            ),
            timeout=5,
        )
        if not option:
            raise AmazonLocaleError("未找到语言选项：%s" % target)
        option.click()

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            current = self._first_element(self.selectors.locale_trigger, timeout=0.5)
            if current and self._locale_matches(
                str(getattr(current, "text", "") or ""), labels
            ):
                return
            time.sleep(0.2)
        raise AmazonLocaleError("语言切换后未能验证目标语言：%s" % target)

    @staticmethod
    def _locale_matches(text: str, labels: Tuple[str, ...]) -> bool:
        current = str(text or "").strip().casefold()
        return any(label.casefold() in current for label in labels)


def switch_language_to_cn(page: Any) -> None:
    from .client import AmazonSellerCentral

    AmazonSellerCentral(page).switch_language("zh_CN")
