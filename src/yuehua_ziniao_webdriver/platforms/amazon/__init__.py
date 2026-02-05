"""Amazon 平台相关方法入口。"""

from .auth import handle_login, is_login
from .loading import is_loading, wait_loading_disappear, wait_page_load_complete
from .navigation import en_site_to_cn_site, switch_language_to_cn, switch_site
from .overlays import close_feedback_popup

__all__ = [
    "close_feedback_popup",
    "en_site_to_cn_site",
    "handle_login",
    "is_loading",
    "is_login",
    "switch_language_to_cn",
    "switch_site",
    "wait_loading_disappear",
    "wait_page_load_complete",
]
