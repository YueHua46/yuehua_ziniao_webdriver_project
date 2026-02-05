"""Amazon 后台加载等待相关方法。"""

import time

from DrissionPage import ChromiumPage
from DrissionPage.errors import ContextLostError
from logger import logger


def is_loading(page: ChromiumPage):
    """
    判断页面是否正在加载
    :param page: ChromiumPage实例
    :return: True表示正在加载，False表示加载完成
    """
    loading_1 = page.eles("xpath://div[contains(@class, 'kat-progress-circular')]")
    loading_2 = page.eles("xpath://div[contains(@class, 'loading-wrapper-loading')]")
    loading_3 = page.eles("xpath://div[@id='loading-box-style']")
    # loading_4 = page.eles("xpath://kat-spinner")
    # if len(loading_4) > 0:
    #     return True
    loading_3_visible = False
    for ele in loading_3:
        parent = ele.run_js("return arguments[0].parentNode;")
        if parent is not None:
            try:
                display_value = ele.parent().attr('style') or ""
                # 粗略检测'display:none'
                if 'display:none' not in display_value.replace(" ", ""):
                    loading_3_visible = True
                    break
            except Exception:
                loading_3_visible = True
                break
    if loading_1 or loading_2 or loading_3_visible:
        return True
    return False


def wait_loading_disappear(page: ChromiumPage, timeout: int = 60):
    """
    等待页面加载动画消失
    :param page: ChromiumPage实例
    :param timeout: 最大等待秒数
    """
    start_time = time.time()
    while True:
        if not is_loading(page):
            break
        if time.time() - start_time > timeout:
            raise TimeoutError("等待页面加载动画消失超时")
        time.sleep(0.5)


def wait_page_load_complete(page: ChromiumPage, timeout: int = 30):
    """
    等待网页加载完成。
    若发生页面刷新/跳转（ContextLostError），会等待新页面出现后继续检测，避免登录等场景下报错。
    :param page: ChromiumPage实例
    :param timeout: 超时时间（秒）
    """
    start_time = time.time()
    while True:
        try:
            ready_state = page.run_js('return document.readyState')
            if ready_state == 'complete':
                break
        except ContextLostError:
            # 页面正在刷新/跳转，旧上下文已失效，等待新页面加载
            logger.debug("检测到页面刷新/跳转，等待新页面...")
            time.sleep(2)
            if time.time() - start_time > timeout:
                raise TimeoutError("等待网页加载完成超时（页面刷新中）")
            continue
        if time.time() - start_time > timeout:
            raise TimeoutError("等待网页加载完成超时")
        time.sleep(0.5)
