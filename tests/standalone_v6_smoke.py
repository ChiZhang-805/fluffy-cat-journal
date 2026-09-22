"""输入：构建好的单文件路径。输出：JSON检查报告。功能：验证实际交付物，而不是另做一份原型。"""
import asyncio
import json
import os
import sys
from pathlib import Path
from playwright.async_api import async_playwright

RESULTS = []


def check(name, condition):
    """输入：名称、条件。输出：检查记录或异常。功能：保存单文件产物实际执行的结果。"""
    RESULTS.append({'name': name, 'passed': bool(condition)})
    print(('PASS ' if condition else 'FAIL ') + name, flush=True)
    assert condition, name


async def run(target):
    """输入：HTML文件。输出：无，记录断言。功能：用原始产物装载程序；存储替身只存在测试文档。"""
    html = target.read_text(encoding='utf-8')
    check('产物带有v6版本标识', 'fluffy-journal-20260922-v6' in html)
    check('产物不包含测试开关赋值或示例响应', 'window.FLUFFY_TEST=true' not in html and '__testStore=new Map' not in html and 'sk-test-only' not in html)
    # 阶段一：此运行环境禁止URL导航，使用内存文档；不伪装成file://或线上网站测试。
    setup = '''<script>window.FLUFFY_TEST=true;window.__store=new Map();Object.defineProperty(window,'localStorage',{value:{getItem:k=>__store.get(k)??null,setItem:(k,v)=>__store.set(k,String(v)),removeItem:k=>__store.delete(k)}});</script>'''
    doc = html.replace('<head>', '<head>' + setup, 1)
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=os.environ.get('CHROMIUM_BIN') or None, headless=True, args=['--no-sandbox'])
        page = await browser.new_page(viewport={'width': 1200, 'height': 1000})
        errors, external = [], []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('request', lambda request: external.append(request.url) if request.url.startswith('http') else None)
        await page.set_content(doc)
        await page.wait_for_function('window.FluffyDebug?.animation.ready', timeout=25000)
        await page.wait_for_timeout(350)
        check('单文件实际启动六组件首页', await page.locator('.home-widget').count() == 6 and await page.evaluate('FluffyDebug.board.order[8]===null'))
        # 阶段二：不需要外部图片、脚本、样式或字体就能完整构造表单。
        await page.locator('.home-widget[data-category=food]').click()
        await page.wait_for_timeout(420)
        check('单文件照片准备框已加载', await page.locator('#photo-preview').is_visible())
        check('食物输入框完整显示', await page.evaluate('(()=>{const p=document.querySelector("#entry-panel").getBoundingClientRect(),f=document.querySelector("#field-foods").getBoundingClientRect();return f.bottom<=p.bottom})()'))
        await page.evaluate('FluffyDebug.openEntry("sleep")')
        await page.get_by_role('combobox', name='入睡小时', exact=True).click()
        await page.get_by_role('option', name='23', exact=True).click()
        check('内嵌时间控件可真实选择', await page.locator('#field-bedtime').input_value() == '23:00')
        await page.evaluate('FluffyDebug.openEntry("sport",{activity:"力量训练",durationMinutes:35,notes:"深蹲4组，每组8次"})')
        await page.wait_for_timeout(300)
        check('内嵌运动表单仅有三项', await page.locator('#entry-form > .field').count() == 3)
        await page.locator('#confirm-entry').click()
        check('单文件按钮进入连续书写状态', await page.evaluate('FluffyDebug.animation.scene==="record"&&FluffyDebug.animation.rows[2].value==="深蹲4组，每组8次"'))
        check('无外部静态资源请求', not external)
        check('单文件运行无脚本错误', not errors)
        await browser.close()


if __name__ == '__main__':
    try:
        asyncio.run(run(Path(sys.argv[1])))
    finally:
        out = Path(__file__).resolve().parent / 'results' / 'standalone-v6-results.json'
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps({'environment':'Chromium in-memory document of delivered HTML; explicit test storage; no microphone or paid API','results':RESULTS},ensure_ascii=False,indent=2),encoding='utf-8')
