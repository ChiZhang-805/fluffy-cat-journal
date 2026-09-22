"""浏览器测试装载工具：真实源码，隔离的存储/网络替身。

输入：项目目录以及 CHROMIUM_BIN（可选）。
输出：home-browser-results.json / 可选截图。
功能：在内存文档中执行发布源码，不绕过本地导航策略，不调用付费 API。
"""
from pathlib import Path
import asyncio, base64, json, os, re
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'tests' / 'results'
OUT.mkdir(exist_ok=True)
RESULTS = []


def test_document(seed=None, extra=''):
    """输入：测试存储与脚本。输出：自包含测试 HTML。功能：加载同一份交付代码，替身只注入测试文档。"""
    soup = BeautifulSoup((ROOT / 'index.html').read_text(), 'html.parser')
    for link in soup.find_all('link', rel='stylesheet'):
        style = soup.new_tag('style')
        style.string = (ROOT / link['href'].split('?')[0]).read_text()
        link.replace_with(style)
    assets = {p.name: 'data:' + ('image/svg+xml' if p.suffix == '.svg' else 'image/png') + ';base64,' + base64.b64encode(p.read_bytes()).decode() for p in (ROOT / 'assets').iterdir() if p.suffix in ['.png', '.svg']}
    soup.find('link', rel='icon')['href'] = assets['favicon.svg']
    setup = soup.new_tag('script')
    setup.string = 'window.CAT_ASSETS=' + json.dumps(assets) + ';window.FLUFFY_TEST=true;\n' + 'window.__testStore=new Map(Object.entries(' + json.dumps(seed or {}) + '''));
Object.defineProperty(window,'localStorage',{value:{getItem:k=>__testStore.get(k)??null,setItem:(k,v)=>__testStore.set(k,String(v)),removeItem:k=>__testStore.delete(k)}});
''' + extra
    soup.body.append(setup)
    for script in list(soup.find_all('script', src=True)):
        code = (ROOT / script['src'].split('?')[0]).read_text()
        script.extract()
        new = soup.new_tag('script')
        new.string = code
        soup.body.append(new)
    return str(soup)


def check(name, result):
    """输入：断言名称、真值。输出：通过或抛错。功能：逐项记录可复核结果。"""
    RESULTS.append({'name': name, 'passed': bool(result)})
    print(('PASS ' if result else 'FAIL ') + name, flush=True)
    assert result, name


async def load(browser, seed=None, extra='', width=1440, height=1000):
    """输入：浏览器和场景数据。输出：就绪页面。功能：统一附加脚本错误收集与确定性装载。"""
    p = await browser.new_page(viewport={'width': width, 'height': height})
    p._fluffy_errors = []
    p.on('pageerror', lambda e: p._fluffy_errors.append(str(e)))
    await p.set_content(test_document(seed, extra))
    await p.wait_for_function('window.FluffyDebug && FluffyDebug.animation.ready', timeout=20000)
    await p.wait_for_timeout(250)
    return p


async def settle(p):
    """输入：页面。输出：无。功能：等待一小段真实动画，允许 DOM 与 Canvas 同步。"""
    await p.wait_for_timeout(250)


async def complete_record(p):
    """输入：记录场景。输出：无。功能：测试专用推进时间轴，不冒充真实播放时长。"""
    await p.evaluate('FluffyDebug.animation.time=FluffyDebug.animation.writeEnd+9;FluffyDebug.animation.render()')
    await p.locator('#primary').click()
    await settle(p)
    await p.evaluate('FluffyDebug.animation.time=6;FluffyDebug.animation.render()')
    await p.locator('#primary').click()
    await settle(p)


