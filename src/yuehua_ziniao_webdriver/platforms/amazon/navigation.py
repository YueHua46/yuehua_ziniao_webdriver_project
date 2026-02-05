"""Amazon 站点/语言切换相关方法。"""

import time

from DrissionPage import ChromiumPage
from logger import logger

from .auth import handle_login, is_login
from .loading import wait_loading_disappear, wait_page_load_complete


def en_site_to_cn_site(en_site):
    """
    英文站点转中文
    :param en_site: 英文站点代码，如 'US', 'UK' 等
    :return: 中文站点名称
    """
    data = {
        'CA': '加拿大', 'US': '美国', 'MX': '墨西哥', 'ES': '西班牙',
        'UK': '英国', 'FR': '法国', 'BE': '比利时', 'NL': '荷兰',
        'DE': '德国', 'IT': '意大利', 'SE': '瑞典', 'PL': '波兰',
        'TR': '土耳其', 'BR': '巴西', 'EG': '埃及', 'SA': '沙特阿拉伯',
        'AE': '阿拉伯联合酋长国', 'IN': '印度', 'SG': '新加坡', 'AU': '澳大利亚',
        'JP': '日本', 'BL': '巴勒斯坦', 'IE': '爱尔兰'
    }
    return data.get(en_site, en_site)


def switch_language_to_cn(page: ChromiumPage):
    """
    切换亚马逊后台语言
    :param page: ChromiumPage实例
    """
    logger.info("切换语言到中文")
    # 获取元素文本内容 .locale-icon-wrapper
    locale_icon_wrapper = page.ele('.locale-icon-wrapper')
    if locale_icon_wrapper:
        locale_icon_wrapper_text = locale_icon_wrapper.text.strip()
        logger.info(f"当前语言 -> {locale_icon_wrapper_text}")
        if locale_icon_wrapper_text == "ZH":
            logger.info("当前语言已切换为中文")
            return

        # hover 语言元素容器
        locale_icon_wrapper.hover()
        wait_loading_disappear(page)
        # 点击中文语言 data-test-tag="locale-list-item-zh_CN"
        target_language_btn = page.ele("xpath://a[contains(@data-test-tag, 'zh_CN')]")
        if target_language_btn:
            target_language_btn.click()
        else:
            logger.error("未找到中文语言切换按钮")
            raise Exception("未找到中文语言切换按钮")
        wait_loading_disappear(page)
        logger.info("切换中文语言成功")
    else:
        logger.error("未找到语言切换元素")
        raise Exception("未找到语言切换元素")


def switch_site(page: ChromiumPage, _site_name: str):
    """
    切换亚马逊站点
    :param page: ChromiumPage实例
    :param _site_name: 站点名称，如 'US', 'UK', 'DE' 等
    """
    logger.info(f"切换站点 -> {_site_name}")
    dropdown_account_switcher_header = page.ele('.dropdown-account-switcher-header')
    dropdown_account_switcher_header.click()
    time.sleep(4)
    # wait_loading_disappear(page)
    dropdown_account_switcher_list_scrollables = page.eles(
        "xpath://div[@class='dropdown-account-switcher-list-item']"
    )
    # 循环点击展开所有店铺
    for dropdown_account_switcher_list_scrollable in dropdown_account_switcher_list_scrollables:
        dropdown_account_switcher_list_scrollable.click()
        # wait_loading_disappear(page)
        time.sleep(0.5)

    site_name = en_site_to_cn_site(_site_name)
    all_dropdown_account_switcher_list_item_indenteds = page.eles(
        "xpath://div[contains(@class, 'dropdown-account-switcher-list-item-indented')]/div"
    )
    target_dropdown_account_switcher_list_item_indenteds = page.eles(
        "xpath://div[contains(@class, 'dropdown-account-switcher-list-item-indented')]/div"
        f"[contains(text(), '{site_name}')]"
    )
    if target_dropdown_account_switcher_list_item_indenteds:
        target_dropdown_account_switcher_list_item_indenteds[0].click()
    else:
        site_list_names = [
            ele.text.strip() for ele in all_dropdown_account_switcher_list_item_indenteds
        ]
        logger.error(
            f"切换站点失败: {site_name}，请检查站点是否存在，"
            f"目前要切换的站点：{site_name}，页面实际站点列表含有的站点名称：{site_list_names}"
        )
        raise Exception(
            f"切换站点: {site_name} 失败，请检查站点是否存在，"
            f"目前要切换的站点：{site_name}，页面实际站点列表含有的站点名称：{site_list_names}"
        )
    # wait_loading_disappear(page)
    time.sleep(4)
    # 等待网页加载完成
    wait_page_load_complete(page)
    # close_feedback_popup(page)
    logger.info(f"切换站点成功: {_site_name}")

    # 处理登录
    if is_login(page):
        handle_login(page)
