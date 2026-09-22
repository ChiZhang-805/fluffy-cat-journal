"""输入：v8源文件。输出：编辑专注、文字整理与日历交互检查。功能：实际UI与明确AI替身，不调用付费接口。"""
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_helpers_v5 import test_document
import os,json
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('FLUFFY_RESULTS',ROOT/'tests/results/v8-extra'));OUT.mkdir(parents=True,exist_ok=True)
RESULTS=[]

def check(name,value):
    """输入：名称和值。输出：断言结果。功能：记录实际检查，不计未执行项目。"""
    RESULTS.append({'name':name,'passed':bool(value)});print(('PASS 'if value else 'FAIL ')+name,flush=True);assert value,name

def run():
    """输入：无。输出：浏览器证据。功能：验证回顾编辑不丢原计时、文字入口不中断、日历不提交草稿。"""
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_BIN','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1000,'height':1000});page.set_default_timeout(6000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.set_content(test_document());page.wait_for_function('window.FluffyDebug?.animation.ready')
        # 阶段一：今天的专注仍启动真正计时；编辑已有计时只修改原记录。
        page.evaluate("FluffyDebug.openEntry('focus',{task:'阅读',durationMinutes:30,notes:'方法章节'})")
        page.locator('#confirm-entry').click()
        check('今日专注仍进入正在运行的倒计时',page.evaluate("FluffyDebug.animation.scene==='focus'&&FluffyDebug.timer.state==='running'"))
        page.evaluate("FluffyDebug.timer.stop();FluffyDebug.state.focusRecord=null;FluffyDebug.navigate('home')")
        page.evaluate("""() => {const S=__fluffyModules['journal-store.js'];window.focusRecord={id:'measured-focus',category:'focus',recordDate:S.dayKey(),createdAt:new Date().toISOString(),data:{task:'读论文',durationMinutes:30,notes:'方法部分'},focus:{elapsedMs:24*60000,restMs:3*60000,plannedMs:30*60000}};S.save(focusRecord);FluffyDebug.openEntry('focus',focusRecord.data,focusRecord)}""")
        check('编辑专注显示实际24分钟而非计划30分钟',page.locator('#field-durationMinutes').input_value()=='24')
        check('编辑专注不再提供估时入口',page.locator('.estimate-time').is_hidden())
        page.locator('#confirm-entry').click();page.locator('.date-confirm-focus').click()
        check('只编辑文字和日期保留测量值及原始计划',page.evaluate("(()=>{let r=__fluffyModules['journal-store.js'].records()[0];return r.focus.elapsedMs===24*60000&&r.focus.plannedMs===30*60000&&r.id==='measured-focus'})()"))
        check('原始24比30仍是80分，不变为100',page.evaluate("__fluffyModules['review-data.js'].build('focus',__fluffyModules['journal-store.js'].dayKey()).today.score===80"))
        page.evaluate("()=>{let r=__fluffyModules['journal-store.js'].records()[0];FluffyDebug.openEntry('focus',r.data,r)}")
        page.locator('#field-durationMinutes').fill('20');page.locator('#confirm-entry').click();page.locator('.date-confirm-focus').click()
        check('用户修改实际时长生效且来源改为自述',page.evaluate("(()=>{let r=__fluffyModules['journal-store.js'].records()[0];return r.focus.elapsedMs===20*60000&&r.focus.provenance==='self-reported'})()"))
        check('编辑专注仍只保存同一条记录',page.evaluate("__fluffyModules['journal-store.js'].records().length===1"))
        # 阶段二：中央文本入口仍能整理，不让新增日期检查引用不存在的变量。
        page.evaluate("""() => {FluffyDebug.navigate('home');FluffyDebug.apiTest.setKey('test-only-invalid-key');window.extractArgs=[];__fluffyModules['ai-journal.js'].extract=async(client,id,text,image,signal,options)=>{extractArgs.push({id,recordDate:options.recordDate});return{fields:id==='sleep'?{bedtime:'23:00',wakeTime:'07:00',quality:'睡得还好',notes:'夜里没醒'}:{activity:'跑步',durationMinutes:20,notes:'跑了3公里'},warnings:[],estimated:false,sleepDates:{wakeDate:__fluffyModules['sleep-time.js'].addDays(options.recordDate,-1)}}}}""")
        for category,name in [('sport','运动'),('sleep','睡眠')]:
            page.locator('.nav-chat').click();page.locator('.chat-topics button').filter(has_text=name).click();page.locator('.chat-input').fill('test: 明确的测试文本，不调用真实接口')
            page.get_by_role('button',name='交给小猫整理',exact=True).click();page.wait_for_function("FluffyDebug.state.phase==='idle'")
            check(category+'中央文字整理保留草稿',page.locator('#field-activity' if category=='sport' else '#field-quality').input_value()==('跑步' if category=='sport' else '睡得还好'))
            if category=='sleep':
                check('另一个睡眠日期不覆盖菜单选定日期',page.evaluate("FluffyDebug.state.recordDate===__fluffyModules['sleep-time.js'].dateKey()&&!FluffyDebug.state.sleepDates.wakeDate"))
                check('日期冲突有可核对提示',page.evaluate("document.querySelector('#entry-form').textContent.includes('核对记录日期')"))
            page.evaluate("FluffyDebug.navigate('home')")
        # 阶段三：日期菜单浏览/取消、语言切换不修改真值或保存条目。
        page.evaluate("FluffyDebug.apiTest.clear();FluffyDebug.openEntry('sleep',{bedtime:'23:00',wakeTime:'07:00',quality:'还不错',notes:'睡得安稳'})")
        old=page.evaluate('FluffyDebug.state.recordDate');count=page.evaluate("__fluffyModules['journal-store.js'].records().length")
        page.locator('#entry-more').click();page.locator('[data-action=date]').click();page.locator('.date-prev').click()
        check('浏览上月不提前改动记录日',page.evaluate('FluffyDebug.state.recordDate')==old)
        check('日历跨月标题和星期网格存在',page.locator('.date-grid .date-day').count()==42 and page.locator('.date-weekdays span').count()==7)
        page.locator('.date-cancel').click();check('取消后没有新增记录',page.evaluate("__fluffyModules['journal-store.js'].records().length")==count)
        page.locator('#entry-more').click();page.locator('[data-action=language]').click();page.locator('[data-language=en]').click()
        page.locator('.time-part').first.click()
        check('英文时间下拉读取翻译后的ARIA名称',page.locator('#sleep-time-options').get_attribute('aria-label')=='Bedtime Hour')
        page.keyboard.press('Escape')
        check('所有补充流程无脚本异常',not errors)
        page.close();browser.close()

if __name__=='__main__':
    try:run()
    finally:(OUT/'results.json').write_text(json.dumps(RESULTS,ensure_ascii=False,indent=2))
