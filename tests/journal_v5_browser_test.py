"""v5 实际 DOM/Canvas/手势回归；API、网站权限、录音源为明确的测试替身。"""
from pathlib import Path
import asyncio, json, os, io, base64
from PIL import Image, ImageDraw
from playwright.async_api import async_playwright
from browser_helpers_v5 import test_document
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tests'/'results'; OUT.mkdir(exist_ok=True)
REVIEW=Path(os.environ.get('FLUFFY_REVIEW',str(OUT/'review')));REVIEW.mkdir(parents=True,exist_ok=True)
RESULTS=[]

def check(name,value):
    """输入：断言名和结果。输出：无。功能：保存真实通过项，失败即停止，不把模型替身当模型准确率。"""
    RESULTS.append({'name':name,'passed':bool(value)})
    print(('PASS ' if value else 'FAIL ')+name,flush=True)
    assert value,name

async def load(browser,seed=None,extra='',width=1440,height=1000):
    """输入：浏览器、显式测试状态和窗口尺寸。输出：就绪页面。功能：在内存文档中装载完整交付源码。"""
    p=await browser.new_page(viewport={'width':width,'height':height});p.errors=[]
    p.on('pageerror',lambda e:p.errors.append(str(e)));p.set_default_timeout(7000)
    await p.set_content(test_document(seed,extra));await p.wait_for_function('window.FluffyDebug?.animation.ready')
    await p.wait_for_timeout(200);return p

async def entry(p,category,values=None):
    """输入：页面、类别和可选草稿。输出：无。功能：进入对应表单并等待路由过渡。"""
    await p.evaluate('([id,v])=>FluffyDebug.openEntry(id,v)',[category,values]);await p.wait_for_timeout(220)

async def screenshot(p,name):
    """输入：页面和名称。输出：PNG文件。功能：截取运行中的手机容器，不生成界面图片。"""
    await p.locator('#phone').screenshot(path=str(REVIEW/(name+'.png')))

async def drag(p,category,target,hold=True):
    """输入：组件、屏幕目标坐标和长按标志。输出：无。功能：使用真实鼠标指针事件验证拖放。"""
    box=await p.locator('[data-category="'+category+'"].home-widget').bounding_box()
    await p.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2);await p.mouse.down()
    if hold: await p.wait_for_timeout(500)
    await p.mouse.move(*target,steps=15);await p.mouse.up();await p.wait_for_timeout(350)

async def slot_center(p,index):
    """输入：槽位号。输出：视口坐标。功能：测试按手机缩放后的真实落点。"""
    return await p.evaluate('i=>{const r=document.querySelector("#home-board").getBoundingClientRect(),s=r.width/393;return [r.left+(18+i%3*121+56)*s,r.top+(151+Math.floor(i/3)*124+55)*s]}',index)

def picture(width,height):
    """输入：测试图片尺寸。输出：PNG二进制。功能：生成非人像几何测试夹具，验证不裁切与长宽比。"""
    im=Image.new('RGB',(width,height),(205,229,232));d=ImageDraw.Draw(im);d.rectangle((0,0,width-1,height-1),outline=(20,80,100),width=7);d.ellipse((width*.2,height*.25,width*.8,height*.75),fill=(246,211,149));b=io.BytesIO();im.save(b,'PNG');return b.getvalue()

API_MOCK=r'''window.__apiCalls=[];window.__deferPhoto=false;window.__deferAudio=false;
const fakeResult=(fields,more={})=>({choices:[{finish_reason:'stop',message:{content:JSON.stringify({fields,warnings:[],...more})}}]});
window.fetch=async (url,o={})=>{if(!String(url).startsWith('https://dashscope.aliyuncs.com/')&&!String(url).startsWith('https://api.deepseek.com/'))throw Error('TEST: unexpected network');const body=o.body?JSON.parse(o.body):null;__apiCalls.push({url:String(url),body});
if(String(url).endsWith('/models'))return new Response(JSON.stringify({data:[{id:'qwen3-vl-plus'},{id:'qwen3-omni-flash'}]}),{status:200});
if(body?.stream){const answer=fakeResult({mood:'可能有些失落',reason:'准备的事情没有完成',notes:''},{transcript:'真棒，又白忙了一整天',emotion:{basis:'inferred',evidence:'又白忙了一整天',acousticEvidence:'末尾语速放慢',needsConfirmation:true}});const text=answer.choices[0].message.content;
const result=()=>new Response('data: '+JSON.stringify({choices:[{delta:{content:text},finish_reason:'stop'}]})+'\n\ndata: [DONE]\n\n',{headers:{'Content-Type':'text/event-stream'}});
if(__deferAudio)return new Promise(resolve=>window.__resolveAudio=()=>resolve(result()));return result();}
const result=()=>new Response(JSON.stringify(fakeResult({foods:'米饭和蔬菜',portion:'约一碗',calories:350,protein:9,carbs:58,fat:8,vitamins:'must-be-discarded'},{estimated:true})),{status:200});
if(__deferPhoto)return new Promise(resolve=>window.__resolvePhoto=()=>resolve(result()));return result();};
'''
AUDIO_MOCK=r'''
window.__micTracks=[];window.__syntheticContexts=[];window.__micRequests=0;window.__recognitionStarts=0;
Object.defineProperty(navigator,'permissions',{value:{query:async()=>({state:'granted'})},configurable:true});
Object.defineProperty(navigator,'mediaDevices',{value:{getUserMedia:async()=>{__micRequests++;const ctx=new AudioContext(),osc=ctx.createOscillator(),gain=ctx.createGain(),dest=ctx.createMediaStreamDestination();osc.frequency.value=330;gain.gain.value=.1;osc.connect(gain);gain.connect(dest);osc.start();await ctx.resume();__syntheticContexts.push(ctx);__micTracks.push(...dest.stream.getTracks());return dest.stream;}},configurable:true});
window.SpeechRecognition=class{start(){__recognitionStarts++;throw Error('TEST: emotion raw audio must not call ASR')}};
'''

async def run():
    """输入：无。输出：断言报告与运行截图。功能：分阶段验证新功能及关键旧流程，不调用付费API。"""
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(executable_path=os.getenv('CHROMIUM_BIN','/usr/bin/chromium'),headless=True,args=['--no-sandbox','--enable-unsafe-swiftshader','--autoplay-policy=no-user-gesture-required'])
        p=await load(browser,extra=API_MOCK+AUDIO_MOCK)
        # 阶段一：首页九位置与真实长按，不依赖伪代码排序调用。
        check('六张卡片，九个隐藏槽位',await p.locator('.home-widget').count()==6 and await p.locator('.home-slot-guide').count()==9)
        check('默认三空位',await p.evaluate('FluffyDebug.board.order.filter(x=>!x).length===3'))
        await screenshot(p,'home')
        await drag(p,'mood',await slot_center(p,2))
        check('长按拖到空位后源空目标占',await p.evaluate('FluffyDebug.board.order[2]==="mood"&&FluffyDebug.board.order[0]===null'))
        check('拖动松手不弹菜单不打开记录页',await p.evaluate('FluffyDebug.animation.scene==="home"&&document.querySelector("#sheet-layer").hidden'))
        await drag(p,'mood',await slot_center(p,5))
        check('占位交换只有两个组件改变',await p.evaluate('FluffyDebug.board.order[5]==="mood"&&FluffyDebug.board.order[2]==="sport"&&FluffyDebug.board.order[4]==="focus"'))
        before=await p.evaluate('FluffyDebug.board.order.slice()');await drag(p,'mood',(40,40))
        check('落在网格外返回原位',await p.evaluate('FluffyDebug.board.order.slice()')==before)
        box=await p.locator('.home-widget[data-category="food"]').bounding_box();await p.mouse.move(box['x']+25,box['y']+25);await p.mouse.down();await p.wait_for_timeout(500);await p.mouse.up();await p.wait_for_timeout(200)
        check('只长按松开不再弹快捷菜单',await p.evaluate('FluffyDebug.animation.scene==="home"&&document.querySelector("#sheet-layer").hidden'))
        await p.locator('.home-widget[data-category="mood"]').focus();await p.keyboard.press('Alt+ArrowLeft');await p.wait_for_timeout(300)
        check('键盘也可交换九位置',await p.evaluate('FluffyDebug.board.order[4]==="mood"'))
        saved=await p.evaluate('Object.fromEntries(__testStore)');p2=await load(browser,seed=saved)
        check('重新装载恢复九格用户布局',await p2.evaluate('FluffyDebug.board.order.slice()')==await p.evaluate('FluffyDebug.board.order.slice()'));await p2.close()
        await p.locator('.home-widget[data-category="food"]').click();await p.wait_for_timeout(250)
        check('轻点仍进入饮食',await p.evaluate('FluffyDebug.animation.scene==="entry"&&FluffyDebug.state.category==="food"'))
        # 阶段二：表单的照片框、单列、自由输入、时分与无滚动条。
        for category in ['food','face','sleep','mood','focus','sport']:
            await entry(p,category)
            check(category+'无横向溢出',await p.evaluate('(()=>{const e=document.querySelector("#entry-panel");return e.scrollWidth<=e.clientWidth+1})()'))
            check(category+'隐藏滚动条且保留滚动',await p.locator('#entry-panel').evaluate('e=>getComputedStyle(e).scrollbarWidth==="none"&&["auto","scroll"].includes(getComputedStyle(e).overflowY)'))
            check(category+'没有数值滑块/情绪强度',await p.locator('input[type="range"],#field-intensity').count()==0)
            check(category+'最后备注是多行且大于单行',await p.locator('#field-notes').evaluate('e=>e.tagName==="TEXTAREA"&&e.clientHeight>=65'))
            if category in ['food','face']:
                check(category+'相框位于拍照按钮上方',await p.evaluate('(()=>{const p=document.querySelector("#photo-preview"),t=document.querySelector(".photo-tools");return p.compareDocumentPosition(t)&Node.DOCUMENT_POSITION_FOLLOWING})()'))
                check(category+'空相框可见',await p.locator('.photo-empty').is_visible())
                form_text=await p.locator('#entry-form').inner_text();check(category+'删除旧说明',not any(s in form_text for s in ['仅观察外观','营养为估算，份量']))
            if category=='food':
                check('维生素整项删除',await p.locator('#field-vitamins').count()==0)
                boxes=[await p.locator('#field-'+key).bounding_box() for key in ['calories','protein','carbs','fat']]
                check('四项营养严格单列等宽',max(b['x'] for b in boxes)-min(b['x'] for b in boxes)<1 and all(boxes[i+1]['y']>boxes[i]['y']+boxes[i]['height'] for i in range(3)))
            if category=='sleep':
                check('睡眠只有time，不是日期输入',await p.locator('input[type="time"]').count()==2 and await p.locator('input[type="datetime-local"]').count()==0)
                check('醒来感受无选项',await p.locator('#field-quality').get_attribute('type')=='text' and await p.locator('.choice-pill').count()==0)
            if category=='mood':check('情绪自由文本，无选项',await p.locator('#field-mood').get_attribute('type')=='text' and await p.locator('.choice-pill').count()==0)
            if category in ['food','sleep','mood','focus']:await screenshot(p,category)
        # 阶段三：两个Key入口独立，失败不清旧Key；配置/图片只有显式请求。
        await p.locator('#open-bailian').click();await p.locator('#bailian-key').fill('sk-v5-test-bailian-only');await p.locator('#save-bailian').click();await p.wait_for_timeout(200)
        check('百炼通过真实客户端协议校验流程启用',await p.evaluate('FluffyDebug.bailianTest.configured&&document.querySelector("#bailian-popover").hidden'))
        check('Key没有进入持久存储',not any('sk-v5-test' in v for v in (await p.evaluate('Object.fromEntries(__testStore)')).values()))
        await p.locator('#open-bailian').click();check('下拉只含必要文案',await p.locator('#bailian-popover').inner_text() in ['阿里云百炼\n启用\n清除','阿里云百炼\nAPI Key\n启用\n清除'])
        await screenshot(p,'bailian')
        await p.locator('#open-settings').click();check('打开DeepSeek关闭百炼下拉',await p.locator('#bailian-popover').is_hidden());await p.keyboard.press('Escape')
        await entry(p,'food');before=await p.evaluate('__apiCalls.length')
        for width,height,name in [(300,500,'portrait'),(600,250,'landscape')]:
            await p.locator('#photo-library').set_input_files({'name':name+'.png','mimeType':'image/png','buffer':picture(width,height)})
            await p.wait_for_timeout(450)
            ratio=await p.locator('#photo-preview img').evaluate('e=>{const r=e.getBoundingClientRect();return r.height/r.width;}')
            check(name+'整图按比例，不裁切/拉伸',abs(ratio-height/width)<.005)
            frame=await p.locator('#photo-preview').bounding_box();img=await p.locator('#photo-preview img').bounding_box()
            check(name+'相框跟随高度而非固定框',abs(frame['height']-img['height'])<3)
        check('选择照片尚未提交API',await p.evaluate('__apiCalls.length')==before)
        await screenshot(p,'food-photo')
        await p.evaluate('__deferPhoto=true');await p.locator('#analyze-photo').click();await p.wait_for_function('typeof __resolvePhoto==="function"')
        await p.locator('#field-foods').fill('我自己改的食物');await p.evaluate('__resolvePhoto()');await p.wait_for_timeout(300)
        check('照片API回填不覆盖期间手动修改',await p.locator('#field-foods').input_value()=='我自己改的食物')
        check('图片实际作为image_url传给百炼',await p.evaluate('__apiCalls.at(-1).url.includes("dashscope")&&__apiCalls.at(-1).body.messages[1].content.some(x=>x.type==="image_url")'))
        check('营养数值填入而维生素丢弃',await p.locator('#field-calories').input_value()=='350' and await p.locator('#field-vitamins').count()==0)
        await p.evaluate('__resolvePhoto=null');await p.locator('#analyze-photo').click();await p.wait_for_function('typeof __resolvePhoto==="function"')
        await p.locator('.photo-remove').click();await p.evaluate('__resolvePhoto()');await p.wait_for_timeout(250)
        check('移除照片取消迟到结果，恢复相框',await p.locator('.photo-empty').is_visible() and await p.locator('#field-foods').input_value()=='我自己改的食物')
        # 阶段四：真正的音频采集源码处理一个人工正弦麦克风流；未调用ASR或付费服务。
        await entry(p,'mood');await p.evaluate('__deferAudio=true');box=await p.locator('#confirm-entry').bounding_box();await p.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2);await p.mouse.down()
        await p.wait_for_function('FluffyDebug.state.phase==="listening"',timeout=6000);await p.wait_for_timeout(950)
        check('音频输入使用真实采样波形，不用随机数',await p.evaluate('FluffyDebug.rawAudio.samplesCount>6000&&FluffyDebug.animation.level>0'))
        calls=await p.evaluate('__apiCalls.length');await p.mouse.up();await p.wait_for_function('typeof __resolveAudio==="function"',timeout=6000)
        check('松手之后才提交原始音频',await p.evaluate('__apiCalls.length')==calls+1 and await p.evaluate('__apiCalls.at(-1).body.messages[1].content[0].type==="input_audio"'))
        check('原始音频没有走浏览器Google识别',await p.evaluate('__recognitionStarts===0'))
        check('松手后立即关闭麦克风轨道',await p.evaluate('__micTracks.every(t=>t.readyState==="ended")'))
        await p.locator('#field-mood').fill('我自己觉得很平静');await p.evaluate('__resolveAudio()');await p.wait_for_function('FluffyDebug.state.phase==="idle"')
        check('语气草稿不覆盖用户明确的新自述',await p.locator('#field-mood').input_value()=='我自己觉得很平静')
        check('语音整理后等待用户确认，不自动庆祝',await p.evaluate('FluffyDebug.animation.scene==="entry"'))
        check('推断证据为可确认草稿，没有评分',await p.evaluate('FluffyDebug.state.emotionDraft.basis==="inferred"&&!Object.hasOwn(FluffyDebug.state.emotionDraft,"score")'))
        check('录音样本和完成Promise引用释放',await p.evaluate('FluffyDebug.rawAudio.chunks.length===0&&FluffyDebug.rawAudio.stopPromise===null'))
        # 阶段五：普通记录写字→庆祝、专注先计时，旧流程保留。
        await p.locator('#confirm-entry').click();await p.wait_for_timeout(450)
        check('用户确认后才进入小猫书写',await p.evaluate('FluffyDebug.animation.scene==="record"'))
        await p.evaluate('FluffyDebug.animation.time=FluffyDebug.animation.writeEnd+9;FluffyDebug.animation.render()');await p.wait_for_timeout(100);await p.locator('#primary').click();await p.wait_for_timeout(220)
        check('记录结束后才Great job',await p.evaluate('FluffyDebug.animation.scene==="celebrate"'))
        await p.evaluate('FluffyDebug.animation.time=6;FluffyDebug.animation.render()');await p.locator('#primary').click();await p.wait_for_timeout(200)
        check('庆祝结束回首页',await p.evaluate('FluffyDebug.animation.scene==="home"'))
        await entry(p,'sleep',{'bedtime':'23:00','wakeTime':'07:00','quality':'睡得不错','notes':'中途没有醒'})
        await p.locator('#confirm-entry').click();await p.wait_for_timeout(220)
        check('睡眠提交包含自动补齐日期和8小时',await p.evaluate('FluffyDebug.state.record.data.hours===8&&FluffyDebug.state.record.data.bedDate!==FluffyDebug.state.record.data.wakeDate'))
        await entry(p,'focus',{'task':'读完论文方法','durationMinutes':'25','notes':'理解实验流程'})
        await p.locator('#confirm-entry').click();await p.wait_for_timeout(300)
        check('专注提交先计时，不提前庆祝',await p.evaluate('FluffyDebug.animation.scene==="focus"&&FluffyDebug.timer.state==="running"'))
        await screenshot(p,'timer')
        await p.evaluate('FluffyDebug.timer.pause(true)');old=await p.evaluate('FluffyDebug.timer.snapshot().elapsedMs');await p.wait_for_timeout(250)
        check('休息不累计专注时长',abs(await p.evaluate('FluffyDebug.timer.tick().elapsedMs')-old)<1)
        await p.evaluate('FluffyDebug.timer.resume()');await p.wait_for_timeout(100);await p.evaluate('FluffyDebug.finishFocus(false)');await p.wait_for_timeout(200)
        check('完全停止实际计时后才庆祝',await p.evaluate('FluffyDebug.animation.scene==="celebrate"'))
        # 阶段六：清Key/离开取消、响应式、安全区域与运行错误。
        await p.locator('#open-bailian').click();await p.locator('#forget-bailian').click()
        check('清除独立Key生效',await p.evaluate('!FluffyDebug.bailianTest.configured'))
        await p.keyboard.press('Escape')
        for w,h in [(320,740),(375,812),(393,852),(430,932),(768,1024),(1440,1000)]:
            await p.set_viewport_size({'width':w,'height':h});await entry(p,'food');await p.locator('#open-bailian').click();await p.wait_for_timeout(120)
            b=await p.locator('#bailian-popover').bounding_box();check(f'{w}宽度下拉菜单不越界',b['x']>=-1 and b['x']+b['width']<=w+1)
            check(f'{w}宽度页面无横向溢出',await p.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
            await p.keyboard.press('Escape')
        check('完整流程无JavaScript错误',not p.errors)
        await p.evaluate('Promise.all(__syntheticContexts.map(c=>c.close()))');await browser.close()
    (OUT/'journal-v5-browser-results.json').write_text(json.dumps({'passed':len(RESULTS),'tests':RESULTS,'media':'synthetic oscillator source, actual PCM recorder','network':'explicit model API protocol mocks','navigation':'in-memory HTML of actual source'},ensure_ascii=False,indent=2))

if __name__=='__main__':asyncio.run(run())
