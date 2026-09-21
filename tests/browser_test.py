from playwright.sync_api import sync_playwright
from pathlib import Path
from browser_helpers import test_document
import json, os
work=Path(__file__).resolve().parent
mock=(work/'mock-browser.js').read_text()
results=[]
def check(name, value):
    """输入：检查名和布尔结果。输出：无。功能：记录断言并在失败时立即中止。"""
    results.append({'test':name,'passed':bool(value)})
    assert value,name

def load(b):
    """输入：浏览器。输出：已加载页面。功能：使用项目真实源码和显式模拟依赖。"""
    page=b.new_page(viewport={'width':1440,'height':1000})
    page.set_content(test_document(mock),wait_until='load')
    page.wait_for_function('window.FluffyDebug?.animation.ready',timeout=10000)
    return page

def enable(page):
    """输入：页面。输出：无。功能：通过真实下拉框启用测试 Key，模型响应来自测试替身。"""
    page.locator('#open-settings').click()
    page.locator('#api-key').fill('TEST_ONLY_NOT_A_REAL_KEY_2026')
    page.locator('#save-api').click()
    page.wait_for_function('document.getElementById("api-popover").hidden')

def hold(page):
    """输入：页面。输出：无。功能：以鼠标真实按住按钮至长按阈值。"""
    rect=page.locator('#confirm-entry').bounding_box()
    page.mouse.move(rect['x']+rect['width']/2,rect['y']+rect['height']/2)
    page.mouse.down();page.wait_for_timeout(550)

with sync_playwright() as p:
    b=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH'),headless=True,args=['--no-sandbox'])
    page=load(b)
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.locator('#open-settings').click()
    check('下拉框只含标题、输入框、启用、清除', page.locator('#api-popover').inner_text().split()==['DeepSeek','Chat','API','Key','启用','清除'])
    check('设置不是遮罩弹窗',page.locator('dialog').count()==0)
    page.keyboard.press('Escape')
    check('Escape 关闭下拉框',page.locator('#api-popover').is_hidden())
    page.locator('#open-settings').click();page.mouse.click(30,300)
    check('点击外部关闭下拉框',page.locator('#api-popover').is_hidden())
    enable(page)
    check('启用后密码从 DOM 清除',page.locator('#api-key').input_value()=='' and 'TEST_ONLY_NOT_A_REAL_KEY_2026' not in page.locator('body').inner_html())
    hold(page)
    page.wait_for_function('FluffyDebug.state.phase==="authorizing"')
    check('首次只申请一次权限',page.evaluate('TEST.mediaCalls===1 && TEST.prompts===1 && TEST.recognitionStarts===0'))
    page.evaluate('window.dispatchEvent(new Event("blur"));document.getElementById("confirm-entry").dispatchEvent(new Event("lostpointercapture"));')
    page.mouse.up()
    check('授权弹窗失焦及松手不取消许可任务',page.evaluate('FluffyDebug.state.phase==="authorizing"'))
    page.evaluate('TEST.grant()');page.wait_for_function('FluffyDebug.state.phase==="idle"')
    check('首次允许后关闭测试流且没有录音',page.evaluate('TEST.alive===0 && TEST.recognitionStarts===0'))
    hold(page);page.wait_for_function('FluffyDebug.state.phase==="listening"')
    check('第二次长按不会重复预授权',page.evaluate('TEST.prompts===1 && TEST.mediaCalls===2 && TEST.recognitionStarts===1'))
    page.mouse.up();page.wait_for_function('FluffyDebug.animation.scene==="record"',timeout=10000)
    check('松开后停止收音且仅整理一次',page.evaluate('TEST.alive===0 && TEST.extracts===1'))
    check('使用真实响应路径填入草稿',page.locator('#field-distance').input_value()=='5' and page.locator('#field-duration').input_value()=='30')
    check('语音直接衔接书写，不跳庆祝',page.evaluate('FluffyDebug.state.record.source==="voice" && FluffyDebug.animation.scene==="record"'))
    page.evaluate('FluffyDebug.editRecord()')
    hold(page);page.wait_for_function('FluffyDebug.state.phase==="listening"')
    page.evaluate('window.dispatchEvent(new Event("blur"))');page.mouse.up()
    check('正式收音失焦仍及时停止，不误提交',page.evaluate('FluffyDebug.state.phase==="idle" && TEST.alive===0 && TEST.extracts===1'))
    page.locator('#open-settings').click();page.locator('#forget-key').click()
    check('清除按钮删除已配置 Key',not page.locator('#key-indicator').evaluate('(e)=>e.classList.contains("enabled")'))
    page.keyboard.press('Escape');hold(page);page.mouse.up()
    check('没有 Key 时不触发录音',page.evaluate('TEST.mediaCalls===3'))
    page.keyboard.press('Escape')
    # Validate known-grant pending capture cancellation.
    enable(page);page.evaluate('TEST.deferMedia=true')
    hold(page);page.wait_for_function('FluffyDebug.speech.pending')
    page.mouse.up();page.evaluate('TEST.grant()');page.wait_for_timeout(150)
    check('松手后晚到的音频流立即关闭',page.evaluate('TEST.alive===0 && FluffyDebug.state.phase==="idle" && TEST.recognitionStarts===2'))
    page.evaluate('TEST.deferMedia=false')
    # Manual confirmation still reaches the celebration scene.
    page.locator('#field-activity').fill('步行');page.locator('#field-distance').fill('2.5')
    page.locator('#field-duration').fill('20.5');page.locator('#field-notes').fill('轻松')
    page.locator('#confirm-entry').click();page.wait_for_function('FluffyDebug.animation.scene==="celebrate"')
    check('短按手动记录流程保持不变',page.evaluate('FluffyDebug.state.record.distanceKm===2.5'))
    page.evaluate('FluffyDebug.editRecord()')
    # Check responsive dropdown bounds.
    for w,h in [(1440,1000),(1536,864),(390,844),(375,812),(320,720),(430,932)]:
        page.set_viewport_size({'width':w,'height':h});page.wait_for_timeout(100)
        page.locator('#open-settings').click()
        rect=page.locator('#api-popover').bounding_box()
        check(f'下拉框不溢出视口 {w}×{h}',rect['x']>=0 and rect['x']+rect['width']<=w+1)
        page.keyboard.press('Escape')
    check('浏览器无未处理脚本错误',len(errors)==0)
    page.close()
    # Denial and canceled authorization use separate clean pages.
    page=load(b);enable(page);page.evaluate('TEST.permission="denied"')
    hold(page);page.mouse.up();page.wait_for_timeout(80)
    check('已经拒绝时不反复请求麦克风',page.evaluate('TEST.mediaCalls===0 && FluffyDebug.state.phase==="idle"'))
    page.close()
    page=load(b);enable(page);hold(page);page.wait_for_function('FluffyDebug.state.phase==="authorizing"')
    page.evaluate('FluffyDebug.cancelWork(false);TEST.grant()');page.mouse.up();page.wait_for_timeout(100)
    check('取消后完成授权不晚启动录音',page.evaluate('TEST.alive===0 && TEST.recognitionStarts===0 && FluffyDebug.state.phase==="idle"'))
    b.close()
(work/'browser-results.json').write_text(json.dumps({'mode':'in-memory browser document; explicit microphone and API test doubles','results':results},ensure_ascii=False,indent=2))
print(json.dumps({'passed':len(results),'results':results},ensure_ascii=False,indent=2))
