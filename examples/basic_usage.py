"""基本使用示例

演示如何使用紫鸟浏览器 SDK 的核心功能。
"""

# 未安装包时也可直接运行：将项目 src 加入 path（安装后 pip install -e . 则无需此段）
import sys
from pathlib import Path
_here = Path(__file__).resolve().parent
_src = _here.parent / "src"
if _src.exists() and str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from yuehua_ziniao_webdriver import ZiniaoClient, ZiniaoConfig, StoreOpenOptions, setup_logging
import logging

# ============================================================================
# 配置日志（可选）
# ============================================================================

setup_logging(
    level=logging.INFO,
    log_file="ziniao.log"  # 可选：输出到文件
)


# ============================================================================
# 示例 1: 基本使用 - 通过配置对象
# ============================================================================

def example_basic_usage():
    """基本使用示例"""
    print("\n=== 示例 1: 基本使用 ===\n")
    
    # 创建配置
    config = ZiniaoConfig(
        client_path=r"D:\ziniao\ziniao.exe",  # 修改为你的客户端路径
        company="你的企业名",  # 修改为你的企业名
        username="你的用户名",  # 修改为你的用户名
        password="你的密码",  # 修改为你的密码
        version="v6",  # v5 或 v6
        socket_port=16851  # 通信端口
    )
    
    # 创建客户端
    client = ZiniaoClient(config)
    
    try:
        # 启动客户端
        client.start(
            kill_existing=True,  # 自动关闭已存在的进程
            update_core=True  # 启动后更新内核
        )
        
        # 获取店铺列表
        stores = client.get_store_list()
        print(f"找到 {len(stores)} 个店铺")
        
        # 打印店铺信息
        for i, store in enumerate(stores, 1):
            print(f"{i}. {store['browserName']} (OAuth: {store['browserOauth']})")
        
    finally:
        # 关闭客户端
        client.stop()


# ============================================================================
# 示例 2: 使用上下文管理器（推荐）
# ============================================================================

def example_context_manager():
    """使用上下文管理器自动管理资源"""
    print("\n=== 示例 2: 上下文管理器 ===\n")
    
    config = ZiniaoConfig(
        client_path=r"D:\ziniao\ziniao.exe",
        company="你的企业名",
        username="你的用户名",
        password="你的密码"
    )
    
    # 使用 with 语句，自动启动和关闭
    with ZiniaoClient(config) as client:
        stores = client.get_store_list()
        print(f"共有 {len(stores)} 个店铺")


# ============================================================================
# 示例 3: 通过店铺名称打开单个店铺
# ============================================================================

def example_open_by_name():
    """通过店铺名称打开店铺"""
    print("\n=== 示例 3: 通过名称打开店铺 ===\n")
    
    config = ZiniaoConfig(
        client_path=fr"{Path.home()}\SuperBrowser\starter.exe",
        company="Company Name",
        username="Username",
        password="Password",
        version="v5"
    )
    
    with ZiniaoClient(config) as client:
        # 通过名称打开店铺（支持模糊匹配）
        # 可选：传入 options 字典配置打开方式，键参见 StoreOpenOptions（IDE 有提示）
        options: StoreOpenOptions = {
            "isLoadUserPlugin": True
        }
        session = client.open_store_by_name("Store Name", exact_match=True, options=options)  # 修改为你的店铺名称
        
        print(f"店铺已打开：{session.store_name}")
        
        # 检测 IP
        if session.check_ip():
            print("✓ IP 检测通过")
            
            # 打开启动页面
            session.open_launcher_page()
            
            # 获取标签页进行自动化操作
            tab = session.get_tab()
            
            # 示例：导航到某个页面
            # tab.get("https://www.example.com")
            
            print("可以在这里进行自动化操作...")
            
        else:
            print("✗ IP 检测失败")
        
        # 关闭店铺（也可以使用 session.close()）
        session.close()


# ============================================================================
# 示例 4: 并发打开多个店铺（核心功能）
# ============================================================================

def example_open_multiple_stores():
    """并发打开多个店铺"""
    print("\n=== 示例 4: 并发打开多个店铺 ===\n")
    
    config = ZiniaoConfig(
        client_path=r"D:\ziniao\ziniao.exe",
        company="你的企业名",
        username="你的用户名",
        password="你的密码"
    )
    
    with ZiniaoClient(config) as client:
        # 要打开的店铺名称列表
        store_names = [
            "店铺A",  # 修改为实际的店铺名称
            "店铺B",
            "店铺C",
        ]
        
        # 并发打开多个店铺（最多同时打开3个）
        sessions = client.open_stores_by_names(
            store_names,
            max_workers=3  # 控制并发数
        )
        
        print(f"\n成功打开 {len(sessions)} 个店铺\n")
        
        # 处理每个店铺
        for store_name, session in sessions.items():
            print(f"处理店铺：{store_name}")
            
            # 检测 IP
            if session.check_ip():
                print(f"  ✓ {store_name} - IP 检测通过")
                
                # 获取标签页
                tab = session.get_tab()
                
                # 进行自动化操作
                # tab.get("https://www.example.com")
                
            else:
                print(f"  ✗ {store_name} - IP 检测失败")
        
        # 关闭所有店铺
        print("\n关闭所有店铺...")
        for store_name, session in sessions.items():
            session.close()
            print(f"  已关闭：{store_name}")


# ============================================================================
# 示例 5: 搜索店铺
# ============================================================================

def example_search_stores():
    """搜索店铺"""
    print("\n=== 示例 5: 搜索店铺 ===\n")
    
    config = ZiniaoConfig(
        client_path=r"D:\ziniao\ziniao.exe",
        company="你的企业名",
        username="你的用户名",
        password="你的密码"
    )
    
    with ZiniaoClient(config) as client:
        # 模糊搜索
        keyword = "亚马逊"  # 修改为你要搜索的关键词
        matched_stores = client.find_stores_by_name(keyword, exact_match=False)
        
        print(f"模糊搜索 '{keyword}' 找到 {len(matched_stores)} 个店铺：")
        for store in matched_stores:
            print(f"  - {store['browserName']}")
        
        # 精确搜索
        exact_name = "我的亚马逊店铺"  # 修改为确切的店铺名称
        exact_stores = client.find_stores_by_name(exact_name, exact_match=True)
        
        print(f"\n精确搜索 '{exact_name}' 找到 {len(exact_stores)} 个店铺")


# ============================================================================
# 示例 6: 从字典创建配置
# ============================================================================

def example_config_from_dict():
    """从字典创建配置"""
    print("\n=== 示例 6: 从字典创建配置 ===\n")
    
    # 配置字典
    config_dict = {
        "client_path": r"D:\ziniao\ziniao.exe",
        "company": "你的企业名",
        "username": "你的用户名",
        "password": "你的密码",
        "socket_port": 16851,
        "version": "v6"
    }
    
    # 直接传入字典
    client = ZiniaoClient(config_dict)
    
    try:
        client.start(kill_existing=True)
        stores = client.get_store_list()
        print(f"找到 {len(stores)} 个店铺")
    finally:
        client.stop()


# ============================================================================
# 示例 7: 平台模块（Amazon）
# ============================================================================

def example_amazon_platform():
    """Amazon 平台模块示例"""
    print("\n=== 示例 7: 平台模块（Amazon） ===\n")

    from yuehua_ziniao_webdriver.platforms.amazon import (
        handle_login,
        switch_language_to_cn,
        switch_site,
    )

    config = ZiniaoConfig(
        client_path=r"D:\ziniao\ziniao.exe",
        company="你的企业名",
        username="你的用户名",
        password="你的密码",
        version="v6"
    )

    with ZiniaoClient(config) as client:
        session = client.open_store_by_name("我的店铺")
        if session.check_ip():
            session.open_launcher_page()
            tab = session.get_tab()

            switch_language_to_cn(tab)
            switch_site(tab, "US")
            if "signin" in tab.url:
                handle_login(tab)


# ============================================================================
# 示例 8: 错误处理
# ============================================================================

def example_error_handling():
    """错误处理示例"""
    print("\n=== 示例 8: 错误处理 ===\n")
    
    from yuehua_ziniao_webdriver import (
        StoreNotFoundError,
        MultipleStoresFoundError,
        StoreOperationError
    )
    
    config = ZiniaoConfig(
        client_path=r"D:\ziniao\ziniao.exe",
        company="你的企业名",
        username="你的用户名",
        password="你的密码"
    )
    
    with ZiniaoClient(config) as client:
        try:
            # 尝试打开不存在的店铺
            session = client.open_store_by_name("不存在的店铺")
            
        except StoreNotFoundError as e:
            print(f"店铺未找到：{e.message}")
            print(f"搜索的店铺名称：{e.store_identifier}")
            
        except MultipleStoresFoundError as e:
            print(f"找到多个匹配的店铺：{e.message}")
            print(f"匹配的店铺：{e.store_names}")
            
        except StoreOperationError as e:
            print(f"店铺操作失败：{e.message}")


# ============================================================================
# 主函数
# ============================================================================

def main():
    """运行示例"""
    print("=" * 60)
    print("紫鸟浏览器 SDK 使用示例")
    print("=" * 60)
    
    # 运行你想要的示例
    # 注意：需要修改配置信息为你的实际配置
    
    try:
        # 取消注释运行对应的示例
        # example_basic_usage()
        # example_context_manager()
        example_open_by_name()
        # example_open_multiple_stores()
        # example_search_stores()
        # example_config_from_dict()
        # example_amazon_platform()
        # example_error_handling()
        
        print("\n请取消注释要运行的示例函数")
        
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n\n错误：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
