"""
# 适用环境python3
"""
import os
import platform
import shutil
import time
import traceback
import uuid
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Literal

import requests
import subprocess
from DrissionPage import Chromium
from DrissionPage.common import By


def kill_process(version: Literal["v5", "v6"]):
    """
    杀紫鸟客户端进程（自动执行，无需确认）
    :param version: 客户端版本
    """
    print("正在关闭紫鸟浏览器主进程...")
    if is_windows:
        if version == "v5":
            process_name = 'SuperBrowser.exe'
        else:
            process_name = 'ziniao.exe'
        os.system('taskkill /f /t /im ' + process_name)
        time.sleep(3)
    elif is_mac:
        os.system('killall ziniao')
        time.sleep(3)
    elif is_linux:
        os.system('killall ziniaobrowser')
        time.sleep(3)
    print("紫鸟浏览器主进程已关闭")


def start_browser():
    """
    启动客户端
    :return:
    """
    try:
        if is_windows:
            cmd = [client_path, '--run_type=web_driver', '--ipc_type=http', '--port=' + str(socket_port)]
        elif is_mac:
            cmd = ['open', '-a', client_path, '--args', '--run_type=web_driver', '--ipc_type=http',
                   '--port=' + str(socket_port)]
        elif is_linux:
            cmd = [client_path, '--no-sandbox', '--run_type=web_driver', '--ipc_type=http', '--port=' + str(socket_port)]
        else:
            exit()
        subprocess.Popen(cmd)
        time.sleep(5)
    except Exception:
        print('start browser process failed: ' + traceback.format_exc())
        exit()


def update_core():
    """
    下载所有内核，打开店铺前调用，需客户端版本5.285.7以上
    因为http有超时时间，所以这个action适合循环调用，直到返回成功
    """
    data = {
        "action": "updateCore",
        "requestId": str(uuid.uuid4()),
    }
    data.update(user_info)
    while True:
        result = send_http(data)
        print(result)
        if result is None:
            print("等待客户端启动...")
            time.sleep(2)
            continue
        if result.get("statusCode") is None or result.get("statusCode") == -10003:
            print("当前版本不支持此接口，请升级客户端")
            return
        elif result.get("statusCode") == 0:
            print("更新内核完成")
            return
        else:
            print(f"等待更新内核: {json.dumps(result)}")
            time.sleep(2)


def send_http(data):
    """
    通讯方式
    :param data:
    :return:
    """
    try:
        url = 'http://127.0.0.1:{}'.format(socket_port)
        response = requests.post(url, json.dumps(data).encode('utf-8'), timeout=120)
        return json.loads(response.text)
    except Exception as err:
        print(err)


def delete_all_cache():
    """
    删除所有店铺缓存
    非必要的，如果店铺特别多、硬盘空间不够了才要删除
    """
    if not is_windows:
        return
    local_appdata = os.getenv('LOCALAPPDATA')
    cache_path = os.path.join(local_appdata, 'SuperBrowser')
    if os.path.exists(cache_path):
        shutil.rmtree(cache_path)


def delete_all_cache_with_path(path):
    """
    :param path: 启动客户端参数使用--enforce-cache-path时设置的缓存路径
    删除所有店铺缓存
    非必要的，如果店铺特别多、硬盘空间不够了才要删除
    """
    if not is_windows:
        return
    cache_path = os.path.join(path, 'SuperBrowser')
    if os.path.exists(cache_path):
        shutil.rmtree(cache_path)


def open_store(store_info, isWebDriverReadOnlyMode=0, isprivacy=0, isHeadless=0, cookieTypeSave=0, jsInfo=""):
    request_id = str(uuid.uuid4())
    data = {
        "action": "startBrowser"
        , "isWaitPluginUpdate": 0
        , "isHeadless": isHeadless
        , "requestId": request_id
        , "isWebDriverReadOnlyMode": isWebDriverReadOnlyMode
        , "cookieTypeLoad": 0
        , "cookieTypeSave": cookieTypeSave
        , "runMode": "1"
        , "isLoadUserPlugin": False
        , "pluginIdType": 1
        , "privacyMode": isprivacy
    }
    data.update(user_info)

    if store_info.isdigit():
        data["browserId"] = store_info
    else:
        data["browserOauth"] = store_info

    if len(str(jsInfo)) > 2:
        data["injectJsInfo"] = json.dumps(jsInfo)

    r = send_http(data)
    if str(r.get("statusCode")) == "0":
        return r
    elif str(r.get("statusCode")) == "-10003":
        print(f"login Err {json.dumps(r, ensure_ascii=False)}")
        exit()
    else:
        print(f"Fail {json.dumps(r, ensure_ascii=False)} ")
        exit()


def close_store(browser_oauth):
    request_id = str(uuid.uuid4())
    data = {
        "action": "stopBrowser"
        , "requestId": request_id
        , "duplicate": 0
        , "browserOauth": browser_oauth
    }
    data.update(user_info)

    r = send_http(data)
    if str(r.get("statusCode")) == "0":
        return r
    elif str(r.get("statusCode")) == "-10003":
        print(f"login Err {json.dumps(r, ensure_ascii=False)}")
        exit()
    else:
        print(f"Fail {json.dumps(r, ensure_ascii=False)} ")
        exit()


def get_browser_list() -> list:
    request_id = str(uuid.uuid4())
    data = {
        "action": "getBrowserList",
        "requestId": request_id
    }
    data.update(user_info)

    r = send_http(data)
    if str(r.get("statusCode")) == "0":
        print(r)
        return r.get("browserList")
    elif str(r.get("statusCode")) == "-10003":
        print(f"login Err {json.dumps(r, ensure_ascii=False)}")
        exit()
    else:
        print(f"Fail {json.dumps(r, ensure_ascii=False)} ")
        exit()


# 获取drissionpage浏览器会话
def get_browser(port) -> Chromium:
    browser = Chromium(port)
    return browser


def open_ip_check(browser: Chromium, ip_check_url: str):
    """
    打开ip检测页检测ip是否正常
    :param browser: drissionpage浏览器会话
    :param ip_check_url ip检测页地址
    :return 检测结果
    """
    try:
        tab = browser.latest_tab
        tab.get(ip_check_url)
        success_button = tab.ele((By.XPATH, '//button[contains(@class, "styles_btn--success")]'), timeout=60) # 等待查找元素60秒
        if success_button:
            print("ip检测成功")
            return True
        else:
            print("ip检测超时")
            return False
    except Exception as e:
        print("ip检测异常:" + traceback.format_exc())
        return False


def open_launcher_page(browser: Chromium, launcher_page: str):
    tab = browser.latest_tab
    tab.get(launcher_page)
    time.sleep(6)


def get_exit():
    """
    关闭客户端
    :return:
    """
    data = {"action": "exit", "requestId": str(uuid.uuid4())}

    data.update(user_info)

    print('@@ get_exit...')
    send_http(data)


def use_one_browser_run_task(browser):
    """
    打开一个店铺运行脚本
    :param browser: 店铺信息
    """
    # 如果要指定店铺ID, 获取方法:登录紫鸟客户端->账号管理->选择对应的店铺账号->点击"查看账号"进入账号详情页->账号名称后面的ID即为店铺ID
    store_id = browser.get('browserOauth')
    store_name = browser.get("browserName")
    # 打开店铺
    print(f"=====打开店铺：{store_name}=====")
    ret_json = open_store(store_id)
    print(ret_json)
    store_id = ret_json.get("browserOauth")
    if store_id is None:
        store_id = ret_json.get("browserId")
    try:
        # 获取drissionpage浏览器会话
        browser = get_browser(ret_json.get('debuggingPort'))
        if browser is None:
            print(f"=====关闭店铺：{store_name}=====")
            close_store(store_id)
            return

        # 获取ip检测页地址
        ip_check_url = ret_json.get("ipDetectionPage")
        if not ip_check_url:
            print("ip检测页地址为空，请升级紫鸟浏览器到最新版")
            print(f"=====关闭店铺：{store_name}=====")
            close_store(store_id)
            exit()
        ip_usable = open_ip_check(browser, ip_check_url)
        if ip_usable:
            print("ip检测通过，打开店铺平台主页")
            open_launcher_page(browser, ret_json.get("launcherPage"))
            # 打开店铺平台主页后进行后续自动化操作
            # todo 后续的自动化操作
            time.sleep(10)
        else:
            print("ip检测不通过，请检查")
    except:
        print("脚本运行异常:" + traceback.format_exc())
    finally:
        print(f"=====关闭店铺：{store_name}=====")
        close_store(store_id)


def use_all_browser_run_task(browser_list):
    """
    循环打开所有店铺运行脚本
    :param browser_list: 店铺列表
    """
    for browser in browser_list:
        use_one_browser_run_task(browser)


def use_all_browser_run_task_with_thread_pool(browser_list, max_threads=3):
    """
    使用线程池控制最大并发线程数
    :param browser_list: 店铺列表
    :param max_threads: 最大并发线程数
    """
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        executor.map(use_one_browser_run_task, browser_list)


if __name__ == "__main__":
    """ 需要从系统角标将紫鸟浏览器完全退出后再运行"""
    is_windows = platform.system() == 'Windows'
    is_mac = platform.system() == 'Darwin'
    is_linux = platform.system() == 'Linux'

    # todo 1、修改client_path：紫鸟客户端在本设备的路径
    if is_windows:
        client_path = R'C:\Users\DIANCHEN\SuperBrowser\starter.exe'  # 紫鸟客户端在本设备的路径，V5程序名为starter.exe，V6程序名为ziniao.exe
    elif is_linux:
        client_path = R'/opt/ziniao/ziniaobrowser'  # 紫鸟客户端在本设备的路径
    else:
        client_path = R'ziniao'  # 客户端程序名称
    socket_port = 16851  # 系统未被占用的端口

    # todo 2、修改用户登录信息，使用企业登录
    user_info = {
        "company": "深圳市点辰实业有限公司",
        "username": "jennov89",
        "password": "Rpa@88365656"
    }

    """  
    windows用，V5版本
    有店铺运行的时候，会删除失败
    删除所有店铺缓存，非必要的，如果店铺特别多、硬盘空间不够了才要删除
    delete_all_cache()

    启动客户端参数使用--enforce-cache-path时用这个方法删除，传入设置的缓存路径删除缓存
    delete_all_cache_with_path(path)
    """

    # 终止紫鸟客户端已启动的进程
    # todo 3、v5与v6的进程名不同，按版本修改v5或v6
    kill_process(version="v5")

    print("=====启动客户端=====")
    start_browser()
    print("=====更新内核=====")
    update_core()

    """获取店铺列表"""
    print("=====获取店铺列表=====")
    browser_list = get_browser_list()
    if not browser_list:
        print("browser list is empty")
        exit()


    """打开第一个店铺运行脚本"""
    use_one_browser_run_task(browser_list[0])

    """循环打开所有店铺运行脚本"""
    # use_all_browser_run_task(browser_list)

    """多线程并发打开所有店铺运行脚本，max_threads设置最大线程数"""
    # use_all_browser_run_task_with_thread_pool(browser_list, max_threads=3)


    """关闭客户端"""
    get_exit()
