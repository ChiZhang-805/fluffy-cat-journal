"""六入口浏览器回归：真实 DOM/Canvas/事件；存储、网络、麦克风为明确测试替身。

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


async def run():
    """输入：无。输出：回归报告。功能：覆盖首页手势、六类数据、计时、媒体边界与响应式布局。"""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(executable_path=os.getenv('CHROMIUM_BIN', '/usr/bin/chromium'), headless=True, args=['--no-sandbox', '--enable-unsafe-swiftshader'])
        p = await load(browser)
        check('default route is home with six separate buttons', await p.evaluate('FluffyDebug.animation.scene==="home" && document.querySelectorAll("button.home-widget").length===6'))
        check('staggered slots use three x positions, not a two-column menu', await p.evaluate('new Set([...FluffyDebug.board.cards.values()].map(b=>b.style.left)).size===3'))
        check('clock reflects local system time', await p.evaluate('document.getElementById("system-clock").textContent===`${new Date().getHours()}:${String(new Date().getMinutes()).padStart(2,"0")}`'))
        first = await p.locator('#actor-canvas').screenshot()
        await p.wait_for_timeout(600)
        second = await p.locator('#actor-canvas').screenshot()
        check('same original actor canvas changes continuously during idle', first != second)
        await p.locator('#home-cat').click()
        check('cat tap gives visible companion response', await p.locator('#home-bubble').evaluate('(n)=>n.classList.contains("visible")'))
        await p.locator('#open-settings').click()
        check('DeepSeek dropdown keeps minimal controls', await p.locator('#api-heading').inner_text() == 'DeepSeek Chat' and await p.locator('#api-key').is_visible())
        await p.keyboard.press('Escape')
        check('Escape closes external API dropdown', await p.locator('#api-popover').is_hidden())
        card = p.locator('button[data-category="mood"]')
        box = await card.bounding_box()
        await p.mouse.move(box['x'] + 35, box['y'] + 35)
        await p.mouse.down()
        await p.wait_for_timeout(540)
        await p.mouse.up()
        await settle(p)
        check('long press opens category menu, not entry', await p.locator('#sheet-layer').is_visible() and await p.evaluate('FluffyDebug.animation.scene==="home"'))
        await p.locator('#sheet-body button').filter(has_text='往后放一格').click()
        check('menu reorder persists category order', await p.evaluate('FluffyDebug.board.order.indexOf("mood")===1 && JSON.parse(localStorage.getItem("fluffy-home-order-v1"))[1]==="mood"'))
        await p.evaluate('FluffyDebug.board.reset()')
        await settle(p)
        a, b = await p.locator('button[data-category="mood"]').bounding_box(), await p.locator('button[data-category="sport"]').bounding_box()
        await p.mouse.move(a['x']+a['width']/2, a['y']+a['height']/2)
        await p.mouse.down(); await p.wait_for_timeout(510)
        await p.mouse.move(b['x']+b['width']/2, b['y']+b['height']/2, steps=12); await p.mouse.up(); await settle(p)
        check('hold then drag rearranges without navigation', await p.evaluate('FluffyDebug.board.order.indexOf("mood")===3 && FluffyDebug.animation.scene==="home" && document.getElementById("sheet-layer").hidden'))
        await p.evaluate('FluffyDebug.board.reset()'); await settle(p)
        await card.focus(); await p.keyboard.press('Shift+F10'); await settle(p)
        check('keyboard context menu is supported', await p.locator('#sheet-layer').is_visible())
        await p.keyboard.press('Escape'); await card.focus(); await p.keyboard.press('Alt+ArrowRight')
        check('keyboard reorder is supported', await p.evaluate('FluffyDebug.board.order[1]==="mood"'))
        await p.evaluate('FluffyDebug.board.reset()'); await settle(p)
        for category in ['sport', 'food', 'mood', 'sleep', 'face', 'focus']:
            await p.locator('button[data-category="'+category+'"]').click(); await settle(p)
            check(category+' entry opens actual category fields', await p.evaluate('(id)=>FluffyDebug.animation.scene==="entry"&&FluffyDebug.state.category===id',category))
            await p.locator('#back').click(); await settle(p)
        await p.locator('button[data-category="sport"]').click(); await settle(p)
        await p.locator('#confirm-entry').click()
        check('empty manual sport record is rejected', await p.evaluate('FluffyDebug.animation.scene==="entry"') and await p.locator('#field-activity').get_attribute('aria-invalid')=='true')
        data = {'activity':'跑步','distanceKm':'3.5','durationMinutes':'25.5','notes':'今天很轻松'}
        for key, value in data.items(): await p.fill('#field-'+key,value)
        await p.locator('#confirm-entry').click(); await settle(p)
        check('manual submission goes to cat writing BEFORE celebration', await p.evaluate('FluffyDebug.animation.scene==="record" && FluffyDebug.animation.rows[0].value.includes("3.5")'))
        check('record cannot skip pen-putdown by early Continue', await p.locator('#primary').is_disabled())
        await complete_record(p)
        check('saved sport updates home card and daily count', await p.locator('button[data-category="sport"] .widget-value').inner_text()=='3.5 km' and await p.locator('#today-count').inner_text()=='1 / 6')
        check('record saved once through writing and celebration', await p.evaluate('__fluffyModules["journal-store.js"].records().length===1'))
        await p.locator('[data-nav="history"]').click(); await settle(p)
        check('history has real saved item', await p.locator('.history-item').count()==1)
        await p.locator('.history-item').click(); await settle(p)
        check('history shows complete fields', '25.5 分钟' in await p.locator('#sheet-body').inner_text())
        await p.locator('#sheet-body button').filter(has_text='修改这条记录').click(); await settle(p)
        await p.fill('#field-notes','修改后的备注'); await p.locator('#confirm-entry').click(); await complete_record(p)
        check('editing updates same ID rather than adding duplicate', await p.evaluate('__fluffyModules["journal-store.js"].records().length===1&&__fluffyModules["journal-store.js"].records()[0].data.notes==="修改后的备注"'))
        await p.locator('[data-nav="chat"]').click(); await settle(p)
        check('center chat opens six topic choices and actual text input', await p.locator('.chat-topics button').count()==6 and await p.locator('.chat-input').is_visible())
        await p.locator('#sheet-body .chat-topics button').filter(has_text='睡眠').click()
        await p.locator('#sheet-body button').filter(has_text='说给小猫听').click(); await settle(p)
        check('chat voice shortcut opens chosen category, not automatic microphone', await p.evaluate('FluffyDebug.state.category==="sleep" && FluffyDebug.state.phase==="idle"'))
        await p.evaluate('FluffyDebug.navigate("home")'); await settle(p)
        for id, fields in [
            ('mood', {'mood':'平静','intensity':4,'reason':'散步以后','notes':'慢慢来'}),
            ('food', {'meal':'午餐','foods':'米饭和鸡蛋','portion':'一碗','calories':420,'protein':18,'carbs':55,'fat':13,'notes':'好好吃饭'}),
            ('sleep', {'bedtime':'2026-09-21T23:30','wakeTime':'2026-09-22T07:15','quality':'还不错','notes':'中途没醒'}),
            ('face', {'feeling':'有一点困','eyeArea':'眼周有阴影','skinAppearance':'光线偏暗','notes':'待光线好时再看'})]:
            await p.evaluate('([id,fields])=>{FluffyDebug.openEntry(id);FluffyDebug.fillForm(fields);FluffyDebug.confirmManual();}',[id,fields]); await settle(p)
            check(id+' produces correct three handwriting rows', await p.evaluate('FluffyDebug.animation.scene==="record" && FluffyDebug.animation.rows.length===3'))
            await complete_record(p)
        check('all five non-focus types appear in saved history', await p.evaluate('new Set(__fluffyModules["journal-store.js"].records().map(r=>r.category)).size===5'))
        await p.locator('[data-nav="tasks"]').click(); await p.locator('.task-add').click(); await settle(p)
        await p.fill('#field-task','读论文'); await p.fill('#field-durationMinutes','25'); await p.locator('.form-secondary').click(); await settle(p)
        check('task can be queued without creating completed record', await p.locator('.task-card').count()==1 and await p.evaluate('__fluffyModules["journal-store.js"].records().length===5'))
        await p.locator('.task-card button').filter(has_text=re.compile(r"^标记完成$")).click()
        check('task completion is explicitly user controlled', await p.locator('.task-card.done').count()==1)
        await p.locator('.task-card button').filter(has_text=re.compile(r"^标记未完成$")).click()
        await p.locator('.task-card button').filter(has_text='开始专注').click(); await p.locator('#confirm-entry').click(); await settle(p)
        check('focus entry starts real timer rather than celebration', await p.evaluate('FluffyDebug.animation.scene==="focus"&&FluffyDebug.timer.state==="running"'))
        await p.wait_for_timeout(550); await p.locator('#timer-pause').click(); r1=await p.evaluate('FluffyDebug.timer.tick().remainingMs'); await p.wait_for_timeout(550); r2=await p.evaluate('FluffyDebug.timer.tick().remainingMs')
        check('pause stops countdown accumulation',r1==r2)
        await p.locator('#timer-pause').click(); await p.locator('#timer-rest').click(); await p.wait_for_timeout(750)
        check('rest state counts rest separately and cat relaxes continuously',await p.evaluate('FluffyDebug.timer.state==="resting" && FluffyDebug.animation.focusRest>0 && Number.isFinite(FluffyDebug.animation.focusRest)'))
        await p.locator('#timer-pause').click(); await p.locator('#back').click(); await settle(p)
        check('ongoing focus is visible on homepage widget', '正在专注' in await p.locator('button[data-category="focus"]').inner_text())
        await p.locator('button[data-category="focus"]').click(); await settle(p)
        check('tap ongoing focus returns directly to timer', await p.evaluate('FluffyDebug.animation.scene==="focus"'))
        await p.locator('#timer-reset').click(); await p.locator('#sheet-body button').filter(has_text=re.compile(r"^取消$")).click()
        check('cancel reset preserves running session',await p.evaluate('FluffyDebug.timer.totalMs===1500000&&FluffyDebug.timer.state==="running"'))
        await p.locator('#timer-stop').click(); await p.locator('#sheet-body button').filter(has_text=re.compile(r"^确定$")).click(); await settle(p)
        check('explicit stop celebrates actual elapsed time, not planned completion', await p.evaluate('FluffyDebug.animation.scene==="celebrate" && FluffyDebug.state.record.focus.elapsedMs>0 && !FluffyDebug.state.record.focus.reachedTarget && !FluffyDebug.state.record.focus.taskCompleted'))
        check('timer end does not mark queued task done', await p.evaluate('!__fluffyModules["journal-store.js"].tasks()[0].done'))
        await p.evaluate('FluffyDebug.openEntry("focus",{task:"六秒测试",durationMinutes:.1});FluffyDebug.confirmManual()')
        await p.wait_for_timeout(6400)
        check('deadline expiry automatically saves once and celebrates', await p.evaluate('FluffyDebug.animation.scene==="celebrate" && FluffyDebug.state.record.focus.reachedTarget && FluffyDebug.state.record.focus.elapsedMs===6000'))
        count=await p.evaluate('__fluffyModules["journal-store.js"].records().length');await p.evaluate('FluffyDebug.checkFocus();FluffyDebug.finishFocus()')
        check('timer finish cannot duplicate record', count==await p.evaluate('__fluffyModules["journal-store.js"].records().length'))
        await p.evaluate('FluffyDebug.navigate("profile")');await settle(p)
        await p.locator('#inner-page .setting-row').filter(has_text='轻柔动效').click()
        check('reduced motion preference persists',await p.evaluate('FluffyDebug.animation.reducedMotion && JSON.parse(localStorage.getItem("fluffy-reduced-motion"))'))
        check('no uncaught script errors across routes',not p._fluffy_errors)
        await p.close()
        # 阶段二：刷新恢复使用显式测试存储种子，不声称已经验证真实设备后台策略。
        p=await load(browser)
        await p.evaluate('FluffyDebug.openEntry("focus",{task:"恢复计时",durationMinutes:10});FluffyDebug.confirmManual()')
        await p.wait_for_timeout(600)
        await p.locator('#timer-pause').click()
        seed=await p.evaluate('Object.fromEntries(__testStore)')
        remaining=await p.evaluate('FluffyDebug.timer.remainingMs')
        q=await load(browser,seed=seed)
        check('page reload restores paused timer state and remaining time', await q.evaluate('FluffyDebug.animation.scene==="focus"&&FluffyDebug.timer.state==="paused"') and await q.evaluate('FluffyDebug.timer.remainingMs')==remaining)
        await q.close();await p.close()
        # 阶段三：显式假网络检测图片 JSON 与用户确认边界；完全不连接外部付费 API。
        extra='''window.__network=[]; window.fetch=async(path,opt={})=>{__network.push({path,body:opt.body?JSON.parse(opt.body):null});
 if(String(path).endsWith('/models'))return {ok:true,json:async()=>({data:[{id:'deepseek-flash'}]})};
 return {ok:true,json:async()=>({choices:[{finish_reason:'stop',message:{content:JSON.stringify({fields:{meal:'午餐',foods:'测试鸡蛋',portion:'100g',calories:150,protein:13,carbs:1,fat:10,notes:'测试草稿'},estimated:true,warnings:['测试估值，需核对']})}}]})};};'''
        p=await load(browser,extra=extra)
        await p.locator('#open-settings').click();await p.fill('#api-key','sk-test-only-not-a-real-secret');await p.locator('#save-api').click();await settle(p)
        check('API enable validates model via actual client code with test response',await p.evaluate('FluffyDebug.apiTest.configured') and await p.locator('#api-popover').is_hidden())
        await p.locator('button[data-category="food"]').click();await settle(p)
        await p.locator('#photo-library').set_input_files(str(ROOT/'assets/hero-body.png'));await settle(p)
        check('select photo decodes and previews without uploading automatically', await p.locator('#photo-preview img').count()==1 and await p.evaluate('__network.length===1'))
        await p.locator('#analyze-photo').click();await settle(p)
        check('explicit analyze sends actual image_url data, not a fake text-only request',await p.evaluate('__network[1].body.messages.at(-1).content.some(p=>p.type==="image_url"&&p.image_url.url.startsWith("data:image/jpeg;base64,"))'))
        check('vision results remain editable draft, not auto-saved or auto-celebrated',await p.evaluate('FluffyDebug.animation.scene==="entry" && __fluffyModules["journal-store.js"].records().length===0') and await p.input_value('#field-foods')=='测试鸡蛋')
        await p.fill('#field-foods','用户确认的食物');await p.locator('#confirm-entry').click();await complete_record(p)
        check('confirmed edits, not original AI guess, reach history',await p.evaluate('__fluffyModules["journal-store.js"].records()[0].data.foods==="用户确认的食物"'))
        check('raw images and API key are absent from stored record',await p.evaluate('![...__testStore.values()].join("").includes("sk-test") && ![...__testStore.values()].join("").includes("data:image")'))
        await p.locator('#open-settings').click();await p.locator('#forget-key').click();await settle(p)
        check('clear key disables client without deleting record',await p.evaluate('!FluffyDebug.apiTest.configured&&__fluffyModules["journal-store.js"].records().length===1'))
        # 相机被阻止时允许选择照片；晚到流取消与播放失败必须停止轨道。
        result=await p.evaluate('''async()=>{let stopped=0,resolve;const stream={getTracks:()=>[{stop:()=>stopped++}]};
Object.defineProperty(navigator,'mediaDevices',{configurable:true,value:{getUserMedia:()=>new Promise(r=>resolve=r)}});
const Photo=__fluffyModules['photo-input.js'].PhotoInput,photo=new Photo();const pending=photo.openCamera({play:async()=>{}},false);photo.stopCamera();resolve(stream);const success=await pending;return {stopped,success};}''')
        check('late camera permission cannot start recording after cancel',result['stopped']==1 and not result['success'])
        result=await p.evaluate('''async()=>{let stopped=0;Object.defineProperty(navigator,'mediaDevices',{configurable:true,value:{getUserMedia:async()=>({getTracks:()=>[{stop:()=>stopped++}]})}});const p=new (__fluffyModules['photo-input.js'].PhotoInput)();try{await p.openCamera({play:async()=>{throw Error('blocked')}});}catch{}return stopped;}''')
        check('camera play failure releases stream',result==1)
        check('no uncaught errors in API/photo branches',not p._fluffy_errors)
        await p.close()
        # 阶段四：不同尺寸下的真实布局；不伪称 iPhone 实机验证。
        for w,h in [(320,568),(375,667),(393,852),(430,932),(768,1024),(1440,900),(844,390)]:
            p=await load(browser,width=w,height=h)
            rect=await p.locator('#phone-wrap').bounding_box()
            check(f'viewport {w}x{h}: phone stays within available width',rect['x']>=-1 and rect['x']+rect['width']<=w+1)
            check(f'viewport {w}x{h}: all six entry cards remain inside phone',await p.evaluate('''()=>{const s=document.getElementById('screen').getBoundingClientRect();return [...document.querySelectorAll('.home-widget')].every(b=>{const r=b.getBoundingClientRect();return r.left>=s.left&&r.right<=s.right+1&&r.top>=s.top&&r.bottom<=s.bottom;});}'''))
            await p.locator('#open-settings').click();box=await p.locator('#api-popover').bounding_box()
            check(f'viewport {w}x{h}: dropdown fits viewport',box['x']>=0 and box['x']+box['width']<=w+1)
            await p.close()
        await browser.close()
    report={'passed':sum(x['passed'] for x in RESULTS),'total':len(RESULTS),'checks':RESULTS,'limits':'DOM/Canvas真实运行；存储和网络为测试替身；未验证实际麦克风、摄像头、API Key、iPhone/Safari或GitHub Pages线上部署。'}
    (OUT/'home-browser-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({'passed':report['passed'],'total':report['total']}))

if __name__=='__main__':
    asyncio.run(run())
