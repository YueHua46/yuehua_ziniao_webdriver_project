"""Amazon 登录相关方法。"""

import logging
import time

from DrissionPage import ChromiumPage
from DrissionPage.errors import ContextLostError

logger = logging.getLogger(__name__)

from .loading import wait_page_load_complete


def is_login(page: ChromiumPage) -> bool:
    """
    判断是否需要登录
    :param page: ChromiumPage实例
    :return: True表示需要登录，False表示不需要登录
    """
    if "signin" in page.url:
        return True
    return False


def handle_login(page: ChromiumPage):
    """
    处理登录
    :param page: ChromiumPage实例
    """
    logger.info("处理登录")
    # 先看下是否要先点击account
    # div，action含有 /ap/switchaccount 的第一个元素
    account_btn = page.ele("xpath://div[contains(@action, '/ap/switchaccount')][1]")
    if account_btn:
        account_btn.click()
        time.sleep(3)
        wait_page_load_complete(page)
    # 需要先点击继续（会触发跳转，先短暂等待）
    continue_btns = page.eles("xpath://input[@id='continue']")
    if continue_btns:
        continue_btns[0].click()
        time.sleep(2)
        wait_page_load_complete(page)
    # 点击登录按钮（会触发跳转，先短暂等待再检测加载，避免 ContextLostError）
    login_btn = page.ele("xpath://input[@id='signInSubmit']")
    if login_btn:
        login_btn.click()
    else:
        logger.error("未找到登录按钮")
        raise Exception("未找到登录按钮")
    time.sleep(2)  # 给跳转一点时间，避免立刻在旧页面上 run_js
    wait_page_load_complete(page)
    time.sleep(1)
    # 检查是否还需要进行两步验证
    if "mfa" in page.url:
        logger.warning("处理登录点击登录按钮后，出现两步验证，将继续处理")
        # 等待 input#auth-mfa-otpcode 有值（不为空）。必须用 JS 取 .value（当前输入），attr('value') 是 HTML 初始属性，用户输入后不会变
        start = time.time()
        while True:
            try:
                current_value = page.run_js(
                    "return (document.getElementById('auth-mfa-otpcode') || {}).value || ''"
                )
                if current_value and str(current_value).strip():
                    break
            except ContextLostError:
                time.sleep(1)
                if time.time() - start > 30:
                    raise TimeoutError("等待两步验证输入超时")
                continue
            if time.time() - start > 30:
                raise TimeoutError("等待两步验证输入超时")
            time.sleep(0.5)
        # 点击确认按钮
        confirm_btn = page.ele("xpath://input[@id='auth-signin-button']")
        if confirm_btn:
            confirm_btn.click()
            time.sleep(2)
            wait_page_load_complete(page)
        else:
            logger.error("未找到两步验证确认按钮")
            raise Exception("未找到两步验证确认按钮")

    if is_login(page):
        logger.error("处理登录点击登录按钮后，依然处于登录状态，处理失败")
        raise Exception("处理登录点击登录按钮后，依然处于登录状态，处理失败")

    logger.info("处理登录成功")
