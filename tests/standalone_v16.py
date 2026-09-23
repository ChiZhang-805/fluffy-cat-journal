"""输入：最终单文件路径。输出：实际交付物测试。功能：无调试钩子、通过DOM交互验证两秒跳过与完整保存；存储隔离，无付费API。"""
from pathlib import Path
import asyncio,json,sys
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path(sys.argv[1]).resolve()
OUT=ROOT.parent/'verification/v16-standalone';OUT.mkdir(parents=True,exist_ok=True)
CHECKS=[]

def check(name,value):
    """输入：名称/判断。输出：断言记录。功能：只记录实际执行结果。"""
    CHECKS.append({'name':name,'passed':bool(value)});print(('PASS ' if value else 'FAIL ')+name,flush=True);assert value,name

async def main():
    """输入：无。输出：测试报告。功能：执行未填提示、早点击、跳过保存和多次点击幂等。"""
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        p=await browser.new_page(viewport={'width':1000,'height':1050});p.set_default_timeout(8000)
        errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
        await p.evaluate("window.__isolatedStore=new Map();Object.defineProperty(window,'localStorage',{value:{getItem:k=>__isolatedStore.get(k)??null,setItem:(k,v)=>__isolatedStore.set(k,String(v)),removeItem:k=>__isolatedStore.delete(k)}})")
        await p.evaluate((ROOT/'tests/chat-v15-fixture.js').read_text())
        await p.set_content(SOURCE.read_text());await p.locator('.home-widget[data-category=sport]').wait_for(state='visible')
        check('产物没有调试实例或替身正文',await p.evaluate('!window.FluffyDebug') and 'FixtureRecognition' not in SOURCE.read_text())
        check('产物加载v16标记',await p.locator('meta[name=build-id]').get_attribute('content')=='fluffy-ai-20260923-v16')
        await p.locator('.home-widget[data-category=sport]').click()
        await p.locator('#confirm-entry').click()
        check('缺字段只用气泡提示',await p.locator('#phone-toast').is_hidden() and len(await p.locator('#entry-bubble').inner_text())>0)
        await p.locator('#phone').screenshot(path=str(OUT/'field-question.png'))
        values={'activity':'力量训练','durationMinutes':'45','notes':'深蹲四组，卧推三组，今天结束后腿有点累'}
        for field,value in values.items():await p.locator('#field-'+field).fill(value)
        await p.locator('#confirm-entry').click()
        await p.wait_for_function('document.getElementById("screen").dataset.scene==="record"')
        check('点击确认进入书写页',True)
        await p.locator('#primary').click(force=True)
        check('早于两秒点击不跳转',await p.locator('#screen').get_attribute('data-scene')=='record')
        phone_text=await p.locator('#phone').inner_text()
        check('早点击不保存且不显示防误触说明',await p.evaluate('JSON.parse(localStorage.getItem("fluffy-six-journal-v1")||"[]").length===0') and not any(w in phone_text for w in ['防误触','等待两秒']))
        await p.wait_for_timeout(2050)
        check('按钮开放且仍称继续',await p.locator('#primary').get_attribute('aria-disabled')=='false' and (await p.locator('#primary-label').inner_text())=='继续')
        await p.locator('#phone').screenshot(path=str(OUT/'skip-writing.png'))
        await p.locator('#primary').click();await p.locator('#primary').click(force=True)
        check('跳过进入庆祝页',await p.locator('#screen').get_attribute('data-scene')=='celebrate')
        rows=await p.evaluate('JSON.parse(localStorage.getItem("fluffy-six-journal-v1")||"[]")')
        check('重复点击只保存一条',len(rows)==1)
        check('未画出的备注仍完整保存',rows[0]['data']['notes']==values['notes'] and rows[0]['data']['durationMinutes']==45)
        await p.wait_for_timeout(5100);await p.locator('#primary').click()
        check('庆祝完成正常进入对应回顾',await p.locator('#screen').get_attribute('data-scene')=='review' and '运动回顾' in await p.locator('#review-title').inner_text())
        check('全程没有脚本异常',not errors)
        (OUT/'results.json').write_text(json.dumps({'passed':len(CHECKS),'checks':CHECKS,'pageErrors':errors,'boundary':'Real delivered HTML, production DOM interaction. Isolated storage, no user credentials or live speech/API calls.'},ensure_ascii=False,indent=2))
        await browser.close()
if __name__=='__main__':asyncio.run(main())
