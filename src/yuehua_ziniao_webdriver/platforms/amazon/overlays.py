"""Amazon 后台弹窗/遮罩处理相关方法。"""

from DrissionPage import ChromiumPage
from logger import logger


def close_feedback_popup(page: ChromiumPage):
    """
    关闭亚马逊后台的反馈弹窗
    """
    feedback_popups = page.eles('#vibes-close-button')
    logger.info(f"feedback_popups -> {feedback_popups}")
    if feedback_popups and len(feedback_popups) > 0:
        feedback_popups[0].click()
