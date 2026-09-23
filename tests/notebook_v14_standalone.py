"""输入：最终单文件HTML。输出：UI操作与自然播放检查。功能：不启用debug、不给AI成功替身，验证真实交付产物。"""
from pathlib import Path
import json,sys
from playwright.sync_api import sync_playwright
SRC=Path(sys.argv[1]).resolve();OUT=Path(__file__).resolve().parents[2]/'verification/v14-standalone';OUT.mkdir(parents=True,exist_ok=True)
RESULT=[]

def check(name,ok):
    """输入：名称与结果。输出：无。功能：失败立即停止，保留实际执行断言。"""
    RESULT.append({'name':name,'passed':bool(ok)});print(('PASS ' if ok else 'FAIL ')+name,flush=True);assert ok,name

def run():
    """输入：无。输出：结果JSON。功能：最终HTML逐帧自然播放一条短记录，并操作原生滚动层。"""
    with sync_playwright() as pw:
        b=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        p=b.new_page(viewport={'width':1100,'height':1000});errors=[];requests=[]
        p.on('pageerror',lambda e:errors.append(str(e)));p.on('request',lambda r:requests.append(r.url) if r.url.startswith('http') else None)
        p.route('https://**/*',lambda route:route.abort())
        p.set_content(SRC.read_text());p.locator('.home-widget[data-category=sport]').wait_for(state='visible')
        p.locator('.home-widget[data-category=sport]').click()
        check('单文件没有开启调试接口',p.evaluate('!window.FluffyDebug'))
        p.locator('#field-activity').fill('跑步');p.locator('#field-durationMinutes').fill('30');p.locator('#field-notes').fill('轻松')
        p.locator('#confirm-entry').click()
        p.wait_for_function('document.getElementById("screen").dataset.scene==="record"')
        check('手工输入真实进入写字场景',p.locator('#record-heading').is_visible())
        check('写字时阅读滚动层隐藏',not p.locator('#record-notebook').is_visible())
        p.locator('#record-notebook').wait_for(state='visible',timeout=90000)
        check('不跳时自然播放后进入有限阅读',p.locator('#record-notebook').is_visible())
        p.wait_for_function('document.getElementById("record-title").textContent.includes("All set")',timeout=15000)
        check('真实流程显示完成标题', 'All set' in p.locator('#record-title').inner_text())
        check('短内容完成后没有额外滚动',p.locator('#record-notebook').evaluate('e=>e.scrollTop===0&&e.scrollHeight===e.clientHeight'))
        check('最终文件不创建修改记录控件',p.locator('#edit-record').count()==0)
        check('最终完整笔记含输入的三项',all(v in p.locator('#record-a11y').inner_text() for v in ['跑步','30 min','轻松']))
        p.locator('#phone').screenshot(path=str(OUT/'finished.png'))
        check('手动记录不触发网络或付费API',not requests)
        check('最终文件没有脚本异常',not errors)
        b.close()
    (OUT/'results.json').write_text(json.dumps({'source':str(SRC),'results':RESULT,'passed':len(RESULT),'notes':'Delivered HTML, in-memory document, no debug interface, no model calls, no clock seeking. Natural animation playback. Saving is tested separately with isolated storage.'},ensure_ascii=False,indent=2))
if __name__=='__main__':run()
