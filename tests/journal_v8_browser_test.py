"""输入：实际站点源码。输出：v8浏览器断言和截图。功能：内存文档运行、隔离存储与显式API替身；不调用付费服务。"""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json,os,base64,io,sys
from PIL import Image
from browser_helpers_v5 import test_document
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('FLUFFY_RESULTS',ROOT/'tests/results/v8'));OUT.mkdir(parents=True,exist_ok=True)
RESULTS=[]
USER_VALUES="JSON.stringify(Object.fromEntries(__fluffyModules['catalog.js'].category(FluffyDebug.state.category).fields.map(f=>[f.key,document.getElementById('field-'+f.key).value])))"
FIXTURES={'sport':{'activity':'力量训练','durationMinutes':'25','notes':'练了4组深蹲'},'food':{'meal':'午餐','foods':'米饭和鸡肉','portion':'一碗','calories':'500','protein':'20','carbs':'60','fat':'10','notes':'慢慢吃'},'mood':{'mood':'失落但也松了口气','reason':'做完了一个实验','notes':'今天努力了'},'sleep':{'bedtime':'23:00','wakeTime':'07:00','quality':'醒来还不错','notes':'没有中途醒来'},'face':{'feeling':'精神还好','eyeArea':'眼周有阴影','skinAppearance':'光线偏暗','notes':'想早点休息'},'focus':{'task':'读论文的方法部分','durationMinutes':'25','notes':'先看三页'}}
TITLES={'sport':'Workout review','food':'Meal review','mood':'Mood review','sleep':'Sleep review','face':'Daily check-in','focus':'Focus review'}

def check(name,value):
    """输入：名称和断言值。输出：通过或异常。功能：只记录实际执行的检查。"""
    RESULTS.append({'name':name,'passed':bool(value)});print(('PASS 'if value else 'FAIL ')+name,flush=True);assert value,name

def open_entry(page,id):
    """输入：页面、类别。输出：无。功能：测试钩子只用于进入指定场景，表单与后续按钮均是真实UI。"""
    page.evaluate('([id,values])=>FluffyDebug.openEntry(id,values)',[id,FIXTURES[id]])
    page.wait_for_timeout(250)

def date_ui(page,date):
    """输入：页面、过去日期。输出：无。功能：用真实菜单和确定按钮改变日期，不直接写状态。"""
    page.locator('#entry-more').click();page.locator('#entry-menu [data-action=date]').click()
    while page.locator(f'#entry-options [data-date="{date}"]').count()==0: page.locator('.date-prev').click()
    page.locator(f'#entry-options [data-date="{date}"]').click();page.locator('.date-save').click()

def language_ui(page,code):
    """输入：页面、语言。输出：无。功能：走真实中英文菜单，不重载页面。"""
    page.locator('#entry-more').click();page.locator('#entry-menu [data-action=language]').click();page.locator(f'.language-option[data-language={code}]').click();page.wait_for_timeout(100)

def finish(page,focus=False):
    """输入：页面与是否历史专注。输出：无。功能：推进时间轴仅缩短测试等待，保存和完成走真实按钮。"""
    page.locator('#confirm-entry').click()
    if focus: page.locator('.date-confirm-focus').click()
    else:
        page.evaluate('FluffyDebug.animation.time=FluffyDebug.animation.writeEnd+10;FluffyDebug.animation.render()');page.locator('#primary').click()
    page.evaluate('FluffyDebug.animation.time=6;FluffyDebug.animation.render()');page.locator('#primary').click();page.wait_for_timeout(200)

def run():
    """输入：无。输出：JSON和截图。功能：验证六类双语、补记、空回顾、媒体保留与窄屏日历。"""
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_BIN','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
        context=browser.new_context(viewport={'width':1100,'height':1000},timezone_id='Asia/Shanghai')
        context.add_init_script('window.FLUFFY_TEST=true;')
        page=context.new_page();page.set_default_timeout(6000);errors=[];page.on('pageerror',lambda e:(errors.append(str(e)),print('SCRIPT ERROR: '+str(e),flush=True)))
        page.set_content(test_document());page.wait_for_function('window.FluffyDebug?.animation.ready');page.wait_for_timeout(350)
        check('交付源码通过内存文档加载全部模块',not errors)
        today=page.evaluate("__fluffyModules['journal-store.js'].dayKey()")
        past=page.evaluate("__fluffyModules['sleep-time.js'].addDays(__fluffyModules['journal-store.js'].dayKey(),-2)")
        check('首页组件禁放位仍然保留',page.evaluate('FluffyDebug.board.order[8]===null'))
        check('首页气泡仍为原始对白形状而不是组件',page.evaluate("getComputedStyle(document.querySelector('#home-bubble')).borderBottomLeftRadius==='3px'&&!document.querySelector('#home-bubble').classList.contains('home-widget')"))
        check('首页气泡移近小猫但不铺满格子',page.evaluate("(()=>{const s=getComputedStyle(document.querySelector('#home-bubble'));return parseFloat(s.top)===485&&parseFloat(s.width)<125})()"))
        page.locator('#phone-wrap').screenshot(path=str(OUT/'home.png'))
        # 阶段一：六类都能从记录菜单进入空回顾，不伪造历史或把草稿保存。
        for id in FIXTURES:
            open_entry(page,id)
            page.locator('#entry-more').click()
            labels=page.locator('#entry-menu button').all_text_contents()
            check(f'{id}记录菜单均为图标加四字短语',labels==['调整日期','语言切换','数据回顾'] and page.locator('#entry-menu svg').count()==3)
            page.locator('[data-action=history]').click()
            check(f'{id}空数据也有对应回顾页',page.evaluate(f"FluffyDebug.review.active&&FluffyDebug.review.view.id==='{id}'&&FluffyDebug.review.view.today.count===0"))
            check(f'{id}查看回顾不提交草稿',page.evaluate("__fluffyModules['journal-store.js'].records().length===0"))
            page.locator('#review-home').click()
        # 阶段二：六类补记的完整保存与庆祝路由，创建日期与事件日期不同。
        for id in FIXTURES:
            open_entry(page,id);before=page.evaluate(USER_VALUES)
            date_ui(page,past)
            check(f'{id}选日不丢失已填内容',page.evaluate(USER_VALUES)==before)
            check(f'{id}补记日期与标题明确',page.evaluate(f"FluffyDebug.state.recordDate==='{past}'&&!document.querySelector('#entry-date-badge').hidden&&!document.querySelector('#entry-heading h1').textContent.includes('今天')"))
            if id=='sleep': page.locator('#phone-wrap').screenshot(path=str(OUT/'sleep-date.png'))
            finish(page,id=='focus')
            check(f'{id}完成后进入该历史日回顾',page.evaluate(f"FluffyDebug.animation.scene==='review'&&FluffyDebug.review.view.id==='{id}'&&FluffyDebug.review.view.date==='{past}'&&FluffyDebug.review.view.today.count===1"))
            check(f'{id}标题不标记为今天',not ('今天' in page.locator('#review-date').inner_text()))
            check(f'{id}创建时间真实且不伪装成补记当天',page.evaluate(f"(()=>{{let r=__fluffyModules['journal-store.js'].records().find(r=>r.category==='{id}');return r.recordDate==='{past}'&&__fluffyModules['journal-store.js'].dayKey(new Date(r.createdAt))==='{today}'}})()"))
            if id=='sleep':check('睡眠时刻跨午夜仍按补记醒来日计算',page.evaluate(f"FluffyDebug.review.view.today.data.wakeDate==='{past}'&&FluffyDebug.review.view.today.value===8"))
            if id=='focus':check('补记专注没有启动现在的计时器且来源为自述',page.evaluate("FluffyDebug.timer.state==='idle'&&FluffyDebug.review.view.today.last.focus.provenance==='self-reported'&&FluffyDebug.review.view.today.score===null"))
            page.locator('#phone-wrap').screenshot(path=str(OUT/f'recap-{id}.png'))
            page.locator('#review-home').click()
        check('六类都补在过去，不误算今日完成度',page.locator('#today-count').inner_text()=='0 / 6')
        check('同一天六类补记只算一天陪伴',page.locator('#days-count').inner_text()=='1')
        check('保存六类各一次没有重复',page.evaluate("__fluffyModules['journal-store.js'].records().length===6"))
        # 阶段三：每一类中英切换都保留输入，餐次值继续使用原存储值。
        for id in FIXTURES:
            open_entry(page,id);before=page.evaluate(USER_VALUES)
            language_ui(page,'en')
            check(f'{id}英文标签/标题/主按钮已切换',page.evaluate("!/\\p{Script=Han}/u.test(document.querySelector('#entry-heading h1').textContent+document.querySelector('#confirm-label').textContent+[...document.querySelectorAll('#entry-form .field-header')].map(n=>n.textContent).join(''))"))
            check(f'{id}语言切换完全保留用户原文',page.evaluate(USER_VALUES)==before)
            check(f'{id}英文气泡不超出两行',page.evaluate("(()=>{const n=document.querySelector('#entry-bubble');return n.textContent.split('\\n').length<=2&&n.scrollWidth<=n.clientWidth+1})()"))
            page.locator('#entry-more').click();page.locator('[data-action=history]').click()
            check(f'{id}回顾跟随英文偏好',page.locator('#review-title').inner_text()==TITLES[id])
            page.locator('#review-home').click();open_entry(page,id);language_ui(page,'zh')
            check(f'{id}切回中文字段完整',page.evaluate(USER_VALUES)==before)
        # 照片、滚动位置、日期/语言：不刷新整个表单。
        open_entry(page,'food');img=Image.new('RGB',(360,180),'#9bcad0');buf=io.BytesIO();img.save(buf,format='PNG');url='data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode()
        page.evaluate('(url)=>{FluffyDebug.photo.image=url;FluffyDebug.showPhoto(url)}',url);page.wait_for_timeout(400)
        page.evaluate("document.querySelector('#entry-panel').scrollTop=90")
        language_ui(page,'en');date_ui(page,past)
        check('照片切换语言和日期后仍保留原图',page.locator('#photo-preview img').get_attribute('src')==url)
        check('照片比例继续保持2比1',page.evaluate("Math.abs(document.querySelector('#photo-preview').clientWidth/document.querySelector('#photo-preview').clientHeight-2)<.05"))
        check('餐次只翻译显示，不重写保存值',page.locator('#field-meal').input_value()=='午餐')
        # 日历取消、键盘、无效日期防御及API迟到保护。
        language_ui(page,'zh');open_entry(page,'sport');base=page.evaluate('FluffyDebug.state.recordDate')
        page.locator('#entry-more').click();page.locator('[data-action=date]').click();page.locator(f'[data-date="{past}"]').click();page.keyboard.press('Escape')
        check('日历取消不修改记录日期',page.evaluate('FluffyDebug.state.recordDate')==base)
        page.locator('#entry-more').click();page.locator('[data-action=date]').click();page.keyboard.press('ArrowLeft');page.keyboard.press('Enter')
        chosen=page.evaluate('FluffyDebug.entryMenu.candidate');page.locator('.date-save').click();check('日历键盘选日可以确认',page.evaluate('FluffyDebug.state.recordDate')==chosen)
        check('程序拒绝非法和未来日期',page.evaluate("!FluffyDebug.changeRecordDate('2026-02-30')&&!FluffyDebug.changeRecordDate('2099-01-01')"))
        # 改日期不会覆盖其他类别草稿，也不会重复新增正在编辑的记录。
        date_ui(page,past);page.evaluate("FluffyDebug.navigate('home');FluffyDebug.openEntry('food');FluffyDebug.openEntry('sport')")
        check('返回表单恢复该类别自己的补记日期',page.evaluate('FluffyDebug.state.recordDate')==past)
        r=page.evaluate("__fluffyModules['journal-store.js'].records().find(r=>r.category==='sport')");earlier=page.evaluate("__fluffyModules['sleep-time.js'].addDays(FluffyDebug.state.recordDate,-1)")
        page.evaluate('(r)=>FluffyDebug.openEntry(r.category,r.data,r)',r);date_ui(page,earlier);finish(page)
        check('编辑旧记录日期后保留ID且只有六条记录',page.evaluate(f"__fluffyModules['journal-store.js'].records().length===6&&FluffyDebug.review.view.today.last.id==='{r['id']}'&&FluffyDebug.review.view.date==='{earlier}'"))
        check('编辑旧记录不改写最初创建时间',page.evaluate('FluffyDebug.review.view.today.last.createdAt')==r['createdAt'])
        # 有编辑竞争时，不让被取消请求回填旧日期的数据。
        open_entry(page,'focus')
        page.evaluate("""() => {const api=FluffyDebug.apiTest;api.setKey('test-only-not-a-real-key');api.fetch=async()=>{await new Promise(r=>window.finishDelayed=r);return new Response(JSON.stringify({choices:[{finish_reason:'stop',message:{content:'{\"minutes\":99,\"reason\":\"test\"}'}}]}),{headers:{'Content-Type':'application/json'}})};FluffyDebug.estimateTime()}""")
        page.wait_for_function('typeof window.finishDelayed==="function"');date_ui(page,past);page.locator('#field-durationMinutes').fill('17');page.evaluate('window.finishDelayed()');page.wait_for_timeout(250)
        check('改日期取消旧AI请求，迟到结果不覆盖新输入',page.locator('#field-durationMinutes').input_value()=='17')
        # 视口检查：日期面板和三个点始终在手机安全区内。
        for w,h in [(320,740),(375,812),(393,852),(430,932),(768,1024),(1440,1000)]:
            page.set_viewport_size({'width':w,'height':h});page.wait_for_timeout(250);open_entry(page,'sleep');page.locator('#entry-more').click();page.locator('[data-action=date]').click()
            b=page.locator('#screen').bounding_box();c=page.locator('#entry-options').bounding_box()
            check(f'{w}x{h}日历完整在屏幕内',c['x']>=b['x'] and c['x']+c['width']<=b['x']+b['width']+1 and c['y']>b['y']+25 and c['y']+c['height']<b['y']+b['height'])
            page.keyboard.press('Escape')
        page.set_viewport_size({'width':1100,'height':1000});open_entry(page,'food');language_ui(page,'en');page.locator('#phone-wrap').screenshot(path=str(OUT/'food-english.png'))
        stored=page.evaluate('Object.fromEntries(window.__testStore)');page.close();page=context.new_page();page.set_default_timeout(6000);page.on('pageerror',lambda e:errors.append(str(e)));page.set_content(test_document(stored));page.wait_for_function('window.FluffyDebug?.animation.ready');open_entry(page,'sleep')
        check('重新载入源码后记住语言偏好',page.locator('#confirm-label').inner_text()=='Confirm & continue')
        check('重新载入源码后六类历史与补记日仍在',page.evaluate("__fluffyModules['journal-store.js'].records().length===6"))
        language_ui(page,'zh');open_entry(page,'sport');page.locator('#entry-more').click();page.locator('#phone-wrap').screenshot(path=str(OUT/'menu.png'))
        page.locator('[data-action=date]').click();page.locator('#phone-wrap').screenshot(path=str(OUT/'calendar.png'))
        check('整个浏览器流程无脚本异常',not errors)
        browser.close()
    (OUT/'results.json').write_text(json.dumps({'transport':'in-memory document / actual site files, isolated storage; HTTP navigation blocked by browser policy','api':'explicit delayed response stub only','count':len(RESULTS),'results':RESULTS},ensure_ascii=False,indent=2))
    print('TOTAL',len(RESULTS))
if __name__=='__main__':
    try: run()
    finally: (OUT/'results.json').write_text(json.dumps({'transport':'in-memory document; actual source; isolated storage; explicit API stub','count':len(RESULTS),'results':RESULTS},ensure_ascii=False,indent=2))
