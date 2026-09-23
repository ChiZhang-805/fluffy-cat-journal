"""输入：最终HTML。输出：交付产物检查。功能：不启用调试接口，真实DOM操作；外部网络为明确的SSE测试响应。"""
from pathlib import Path
import asyncio,json,sys
from playwright.async_api import async_playwright
SRC=Path(sys.argv[1]).resolve();ROOT=Path(__file__).resolve().parents[1];OUT=ROOT.parent/'verification/v15-standalone';OUT.mkdir(parents=True,exist_ok=True);RESULT=[]

def check(name,value):
    """输入：断言。输出：记录。功能：只统计执行成功的项目。"""
    RESULT.append({'name':name,'passed':bool(value)});print(('PASS ' if value else 'FAIL ')+name,flush=True);assert value,name

async def run():
    """输入：无。输出：JSON报告。功能：在最终文件上通过可见菜单配置测试Key，验证连续文字聊天及无Key情况。"""
    async with async_playwright() as pw:
        b=await pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        p=await b.new_page(viewport={'width':1100,'height':1000});errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
        await p.evaluate((ROOT/'tests/chat-v15-fixture.js').read_text())
        await p.set_content(SRC.read_text());p.set_default_timeout(8000)
        await p.locator('.home-widget[data-category=sport]').wait_for(state='visible')
        check('最终单文件未启用FluffyDebug',await p.evaluate('!window.FluffyDebug'))
        check('交付文件不包含测试转写函数', 'FixtureRecognition' not in SRC.read_text())
        await p.locator('.home-widget[data-category=sport]').click();await p.locator('#entry-more').click()
        await p.locator('#entry-menu button').filter(has_text='数据回顾').click()
        await p.locator('#review-title').wait_for(state='visible')
        check('通过正式菜单进入运动回顾','运动回顾' in await p.locator('#review-title').inner_text())
        await p.locator('#open-settings').click();await p.locator('#api-key').fill('sk-fixture-key-not-a-real-secret');await p.locator('#save-api').click()
        await p.wait_for_function('document.getElementById("api-popover").hidden')
        check('通过可见界面启用测试Key',await p.locator('#key-indicator').evaluate('e=>e.classList.contains("enabled")'))
        # 不用debug方法，三次都从三点菜单真实打开文字输入。
        for i in range(3):
            await p.evaluate('(i)=>{__chatPlans.push({text:`第${i+1}次也听到啦。我们继续慢慢聊。`})}',i)
            await p.locator('#review-more').click();await p.locator('#review-menu button').filter(has_text='文字聊聊').click()
            await p.locator('#review-text-input').fill(f'这是我的第{i+1}句话')
            await p.locator('.review-text-submit').click()
            await p.wait_for_function('(n)=>document.getElementById("review-bubble").textContent.includes(`第${n}次`)',arg=i+1)
            check(f'最终文件第{i+1}轮对话成功',True)
        check('三个用户问题各提交一次',await p.evaluate('__chatRequests.filter(p=>p.messages.at(-1).content.includes("这是我的第")).length===3'))
        await p.locator('#review-more').click();await p.locator('#review-menu button').filter(has_text='对话记录').click()
        text=await p.locator('.review-chat-log').inner_text()
        check('正式对话记录包含三轮用户原话',all(f'第{i}句话' in text for i in [1,2,3]))
        check('被打断未展示的第二句不在对话记录中','我们继续慢慢聊' not in text)
        check('单文件没有脚本异常',not errors)
        check('诊断读取不含密钥',not 'sk-' in await p.evaluate('JSON.stringify(FluffyChatDiagnostics.snapshot())'))
        await b.close()
    (OUT/'results.json').write_text(json.dumps({'passed':len(RESULT),'results':RESULT,'scope':'Final delivered HTML, no debug interface. Real UI interaction, explicit fake transport; not a real API test.'},ensure_ascii=False,indent=2))
if __name__=='__main__':asyncio.run(run())
