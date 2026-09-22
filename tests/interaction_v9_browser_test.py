"""输入：交付源码。输出：v9交互检查与截图。功能：实际DOM/指针/键盘测试；存储、语音与API均为明确替身。"""
from pathlib import Path
import json, os
from playwright.sync_api import sync_playwright
from browser_helpers_v5 import test_document
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('FLUFFY_RESULTS',ROOT/'tests/results/v9'));OUT.mkdir(parents=True,exist_ok=True)
RESULTS=[]
FULL={
 'sport':{'activity':'跑步','durationMinutes':'25','notes':'今天在公园慢跑了一会儿。'},
 'food':{'meal':'午餐','foods':'米饭、鸡肉和西兰花','portion':'一碗','calories':'560','protein':'28','carbs':'65','fat':'19','notes':'吃得很舒服。'},
 'mood':{'mood':'放松，也有一点累','reason':'做完了挂心的工作','notes':'慢慢来就好。'},
 'sleep':{'bedtime':'23:00','wakeTime':'07:00','quality':'醒来精神还好','notes':'昨晚睡得安稳。'},
 'face':{'feeling':'精神还好','eyeArea':'眼周没有明显变化','skinAppearance':'今天在自然光下记录','notes':'留住今天的模样。'},
 'focus':{'task':'阅读论文的方法部分','durationMinutes':'25','notes':'读懂这三个小节。'}
}


def check(name, value):
    """输入：断言名称与真值。输出：记录并在失败时抛出。功能：仅计数实际执行结果。"""
    RESULTS.append({'name':name,'passed':bool(value)});print(('PASS ' if value else 'FAIL ')+name,flush=True);assert value,name


def shot(page,name):
    """输入：页面、文件名。输出：截图文件。功能：保存运行源码的同一手机区域，不生成新界面图片。"""
    page.locator('#phone').screenshot(path=str(OUT/(name+'.png')))


def press(page,selector,milliseconds=520):
    """输入：页面、按钮和时长。输出：按下保持。功能：实际分发鼠标按压，由交付手势控制器判断长按。"""
    box=page.locator(selector).bounding_box();page.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2);page.mouse.down();page.wait_for_timeout(milliseconds)


def run():
    """输入：无。输出：检查证据。功能：覆盖六类完成度、两种录音位置、聊天排版和提交，以及不同尺寸与语言。"""
    with sync_playwright() as pw:
        b=pw.chromium.launch(executable_path=os.environ.get('CHROMIUM_BIN','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
        p=b.new_page(viewport={'width':1080,'height':1000});p.set_default_timeout(7000)
        errors=[];requests=[];p.on('pageerror',lambda e:errors.append(str(e)))
        p.route('https://**/*',lambda route:(requests.append(route.request.url),route.abort()))
        p.set_content(test_document());p.wait_for_function('window.FluffyDebug?.animation.ready');p.wait_for_timeout(250)
        # 阶段一：六类都只根据记录字段完成度切换，照片不参与。
        for category,data in FULL.items():
            p.evaluate('(id)=>FluffyDebug.openEntry(id,{})',category)
            check(category+'空白表单显示长按邀请',p.locator('#confirm-label').inner_text()=='长按向小猫倾诉' and p.locator('#confirm-entry').get_attribute('data-action')=='invite')
            check(category+'空表单可长按且无前进箭头',not p.locator('#confirm-entry').is_disabled() and not p.locator('#confirm-entry .chevron').is_visible())
            p.evaluate('(fields)=>FluffyDebug.fillForm(fields)',data)
            expected='开始专注' if category=='focus' else '完成并继续'
            check(category+'填满立即恢复继续动作',p.locator('#confirm-label').inner_text()==expected and p.locator('#confirm-entry .chevron').is_visible())
            if category in ['food','face']:
                check(category+'没有上传照片也能完整',p.locator('#photo-preview img').count()==0 and p.evaluate('FluffyDebug.state.entryComplete'))
            p.locator('#field-notes').fill('')
            check(category+'删除最后一空立即回到倾诉',p.locator('#confirm-entry').get_attribute('data-action')=='invite')
            p.locator('#field-notes').fill(data['notes'])
            check(category+'重新填写又恢复且不误提交',p.locator('#confirm-label').inner_text()==expected and p.evaluate('FluffyDebug.animation.scene')=='entry')
        p.evaluate('FluffyDebug.openEntry("food",{})');p.wait_for_timeout(300);shot(p,'food-empty')
        check('首屏饮食字段仍完整显示',p.evaluate('()=>{const a=document.querySelector("#field-foods").getBoundingClientRect(),b=document.querySelector("#entry-panel").getBoundingClientRect();return a.bottom<=b.bottom&&a.top>=b.top}'))
        p.evaluate('FluffyDebug.openEntry("sport",{})');p.wait_for_timeout(300);shot(p,'sport-empty')
        check('邀请态图标和文字作为一组居中',p.evaluate('()=>{let g=document.querySelector(".entry-action-content").getBoundingClientRect(),b=document.querySelector("#confirm-entry").getBoundingClientRect();return Math.abs(g.x+g.width/2-b.x-b.width/2)<1}'))
        p.evaluate('(d)=>FluffyDebug.fillForm(d)',FULL['sport']);p.wait_for_timeout(200);shot(p,'sport-ready')
        p.locator('#field-durationMinutes').fill('-3')
        check('有文字但无效的数字不误显示完成',p.locator('#confirm-entry').get_attribute('data-action')=='invite')
        p.locator('#field-durationMinutes').fill('25');p.locator('#field-notes').fill('  ')
        check('空格备注不算填写',p.locator('#confirm-entry').get_attribute('data-action')=='invite')
        p.evaluate('()=>{const e=document.querySelector("#field-notes");e.value="自动填充后的备注";e.dispatchEvent(new Event("change",{bubbles:true}))}')
        check('只触发change的自动填充也更新',p.locator('#confirm-label').inner_text()=='完成并继续')
        p.evaluate('FluffyDebug.changeLanguage("en")')
        check('完整按钮跟随英文语言',p.locator('#confirm-label').inner_text()=='Finish & continue')
        p.locator('#field-notes').fill('');check('英文不完整提示',p.locator('#confirm-label').inner_text()=='Hold to tell your cat')
        p.evaluate('FluffyDebug.changeLanguage("zh");FluffyDebug.changeRecordDate("2026-01-01")')
        check('补记日期切换不造成空表单误完成',p.locator('#confirm-entry').get_attribute('data-action')=='invite')
        p.evaluate('FluffyDebug.openEntry("food",{meal:"午餐",foods:"自己准备的午餐"})');p.locator('#confirm-entry').click()
        check('未提供可选营养不强迫编造仍可按原规则提交',p.evaluate('FluffyDebug.animation.scene')=='record')
        # 阶段二：记录页录音还是上方模块，回顾页录音仍在底部按钮。
        p.evaluate('''() => {
            const D=FluffyDebug; D.openEntry('sport',{});D.apiTest.setKey('test-only-not-real-key');D.microphone.status=async()=> 'granted';
            window.voiceCalls={start:0,stop:0,cancel:0,extract:0};
            D.speech.supported=()=>true;
            D.speech.start=async()=>{voiceCalls.start++;D.speech.active=true;D.speech.callbacks.onStarted();D.speech.callbacks.onLevel(.65,Array.from({length:72},(_,i)=>(i%12)/18));D.speech.callbacks.onText('测试转写：跑步二十五分钟');return true;};
            D.speech.stop=async()=>{voiceCalls.stop++;D.speech.active=false;return{text:'跑步二十五分钟',canceled:false};};
            D.speech.cancel=()=>{voiceCalls.cancel++;D.speech.active=false;};
            __fluffyModules['ai-journal.js'].extract=async()=>{voiceCalls.extract++;return await new Promise(resolve=>window.finishEntryAI=resolve);};
        }''')
        press(p,'#confirm-entry');check('实际长按触发记录倾听',p.evaluate('FluffyDebug.state.phase')=='listening')
        check('记录波形仍在上方卡片模块',p.locator('#voice-panel').is_visible() and p.locator('#voice-wave').is_visible() and p.locator('#entry-panel').is_hidden())
        check('记录底部按钮没有波形画布',p.locator('#confirm-entry canvas').count()==0 and p.locator('#confirm-label').is_visible() and p.locator('#confirm-label').inner_text()=='松开结束')
        p.wait_for_timeout(150);shot(p,'entry-listening')
        p.mouse.up();p.wait_for_function('typeof window.finishEntryAI === "function"')
        check('松手只整理一次且保留取消按钮',p.evaluate('voiceCalls.stop===1&&voiceCalls.extract===1') and p.locator('#confirm-label').inner_text()=='停止整理')
        p.evaluate('(d)=>finishEntryAI({fields:d,warnings:[],estimated:false})',FULL['sport']);p.wait_for_function('FluffyDebug.state.phase==="idle"')
        check('AI完整回填后恢复继续且没有自动写入',p.locator('#confirm-label').inner_text()=='完成并继续' and p.evaluate('FluffyDebug.animation.scene')=='entry')
        p.locator('#field-notes').fill('');press(p,'#confirm-entry');p.keyboard.press('Escape');p.mouse.up()
        check('取消录音后回到正确完成度且不提交',p.locator('#confirm-label').inner_text()=='长按向小猫倾诉' and p.evaluate('voiceCalls.extract===1'))
        p.evaluate('''() => {const R=FluffyDebug.review;FluffyDebug.apiTest.clear();FluffyDebug.openReview('sport');R.h.microphone.status=async()=> 'granted';R.h.bailian.setKey('test-only-bailian');R.raw.supported=()=>true;R.raw.start=async()=>{R.raw.active=true;R.started();R.wave=Array.from({length:72},(_,i)=>(i%10)/14);return true};R.raw.cancel=()=>{R.raw.active=false};}''')
        press(p,'#review-chat')
        check('回顾页仍在底部聊天按钮中显示波形',p.locator('#review-chat-wave').is_visible() and p.locator('#voice-panel').is_hidden() and p.evaluate('getComputedStyle(document.querySelector("#review-chat-label")).visibility')=='hidden')
        check('回顾录音时图表仍在原位可见',p.locator('#review-week').is_visible() and p.locator('#review-summary').is_visible())
        p.keyboard.press('Escape');p.mouse.up()
        # 阶段三：文字弹层布局、键盘和同一上下文发送；不触发真实API。
        p.evaluate('''() => {FluffyDebug.bailianTest.clear();window.sentMessages=[];FluffyDebug.review.send=async(text)=>{sentMessages.push(text)};window.recordsBeforeChat=JSON.stringify(__fluffyModules['journal-store.js'].records());FluffyDebug.review.textSheet();}''');p.wait_for_timeout(350)
        check('标题左侧包含对话图标',p.locator('#sheet-title .icon').count()==1 and '文字聊聊' in p.locator('#sheet-title').inner_text())
        check('发送按钮有本地发送图标',p.locator('.review-text-submit .icon').count()==1)
        check('输入框和按钮间有14设计像素间距',p.evaluate('()=>{const a=document.querySelector(".review-text-input").getBoundingClientRect(),b=document.querySelector(".review-text-submit").getBoundingClientRect(),s=document.querySelector("#screen").getBoundingClientRect().width/393;return Math.abs((b.top-a.bottom)/s-14)<1}'))
        check('发送文字放大且整体居中',p.evaluate('()=>{let b=document.querySelector(".review-text-submit"),t=b.querySelector("span").getBoundingClientRect(),i=b.querySelector("svg").getBoundingClientRect(),r=b.getBoundingClientRect(),c=getComputedStyle(b);return parseFloat(c.fontSize)===17&&c.justifyContent==="center"&&Math.abs((i.left+t.right)/2-r.left-r.width/2)<1}'))
        p.locator('#review-text-input').fill('今天有一点累，想慢慢说。');shot(p,'text-chat')
        p.locator('#review-text-input').fill('  ');p.locator('.review-text-submit').click()
        check('空白发送不请求且保留输入焦点',p.evaluate('sentMessages.length')==0 and p.locator('#sheet-layer').is_visible() and p.locator('#review-text-input').get_attribute('aria-invalid')=='true')
        p.locator('#review-text-input').fill('第一句');p.keyboard.press('Enter');p.keyboard.insert_text('第二句')
        check('普通Enter只换行不发送',p.locator('#review-text-input').input_value()=='第一句\n第二句' and p.evaluate('sentMessages.length')==0)
        p.evaluate('document.querySelector("#review-text-input").dispatchEvent(new KeyboardEvent("keydown",{key:"Enter",ctrlKey:true,isComposing:true,bubbles:true}))')
        check('中文输入法合成确认不误发送',p.evaluate('sentMessages.length')==0)
        p.keyboard.press('Control+Enter')
        check('Ctrl加Enter只发送一次且关闭弹层',p.evaluate('sentMessages.length===1&&sentMessages[0]==="第一句\\n第二句"') and p.locator('#sheet-layer').is_hidden())
        p.evaluate('FluffyDebug.review.textSheet()');p.locator('#review-text-input').fill('<img src=x onerror=alert(1)> 想聊聊')
        p.evaluate('()=>{const f=document.querySelector(".review-text-compose");f.requestSubmit();f.requestSubmit()}')
        check('重复提交最多发送一次并以纯文本交给对话模块',p.evaluate('sentMessages.length===2&&sentMessages[1].startsWith("<img")'))
        check('文字聊聊不修改已确认记录',p.evaluate('JSON.stringify(__fluffyModules["journal-store.js"].records())===recordsBeforeChat'))
        p.evaluate('FluffyDebug.review.historySheet()')
        check('其他面板不继承文字聊天图标或布局',p.locator('#sheet-title .icon').count()==0 and p.locator('#sheet').get_attribute('data-variant')=='')
        p.locator('#sheet-close').click()
        p.evaluate('FluffyDebug.review.lang="en";FluffyDebug.review.textSheet()');p.wait_for_timeout(200);shot(p,'text-chat-en')
        check('英文文字面板同样包含图标与居中按钮',p.locator('#sheet-title').inner_text()=='Text chat' and p.locator('.review-text-submit').inner_text()=='Send to the cat' and p.locator('#sheet-title .icon').count()==1)
        p.locator('#sheet-close').click()
        # 阶段四：两种语言与手机/桌面宽度；按统一设计坐标检查不溢出。
        for width,height in [(375,812),(393,852),(430,932),(650,900),(1000,1000),(1440,1000)]:
            p.set_viewport_size({'width':width,'height':height});p.evaluate('FluffyDebug.openEntry("food",{});FluffyDebug.changeLanguage("en")');p.wait_for_timeout(130)
            check(str(width)+'英文邀请一行且图标文字不越界',p.evaluate('()=>{let b=document.querySelector("#confirm-entry").getBoundingClientRect(),g=document.querySelector(".entry-action-content"),r=g.getBoundingClientRect(),t=document.querySelector("#confirm-label").getBoundingClientRect();return r.left>=b.left&&r.right<=b.right&&r.height<=b.height&&t.height<30&&document.querySelector("#screen").scrollWidth===393}'))
            p.evaluate('FluffyDebug.openReview("sport");FluffyDebug.review.textSheet()');p.locator('#sheet').evaluate('(el)=>Promise.all(el.getAnimations().map(a=>a.finished))')
            check(str(width)+'文字面板按钮与安全区域不重叠',p.evaluate('()=>{let b=document.querySelector(".review-text-submit").getBoundingClientRect(),s=document.querySelector("#screen").getBoundingClientRect(),h=document.querySelector("#home-indicator").getBoundingClientRect();return b.left>=s.left&&b.right<=s.right&&b.bottom<h.top}'))
            p.locator('#sheet-close').click()
        check('全部检查无脚本异常',not errors)
        check('测试不向付费服务发出真实请求',not requests)
        p.close();b.close()


if __name__=='__main__':
    try:run()
    finally:(OUT/'results.json').write_text(json.dumps(RESULTS,ensure_ascii=False,indent=2),encoding='utf-8')
