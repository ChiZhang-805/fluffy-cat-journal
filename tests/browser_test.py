"""旧测试命令兼容入口；界面契约已统一由v5六入口套件验证，不运行废弃的选项/滑条测试。"""
import asyncio
from journal_v5_browser_test import run

if __name__ == "__main__":
    asyncio.run(run())
