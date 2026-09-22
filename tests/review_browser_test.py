"""输入：交付源码。输出：实际浏览器断言与截图。功能：内存装载真实网页；存储/媒体/API是明确的测试替身，不修改浏览器策略。"""
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_helpers_v5 import test_document
import json, os
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('FLUFFY_RESULTS',ROOT/'tests/results/v7'))
OUT.mkdir(parents=True,exist_ok=True)
RESULTS=[]


def check(name, value):
    """输入：测试名与布尔值。输出：记录或异常。功能：仅报告实际执行的断言。"""
    RESULTS.append({'name':name,'passed':bool(value)})
    print(('PASS ' if value else 'FAIL ')+name,flush=True)
    assert value,name


def load(browser,width=1000,height=1000):
    """输入：浏览器和视口。输出：真实源码页面。功能：隔离测试依赖，不冒充线上或实机验证。"""
    page=browser.new_page(viewport={'width':width,'height':height},device_scale_factor=1)
    page.set_default_timeout(5000)
    page.errors=[]
    page.on('pageerror',lambda e: page.errors.append(str(e)))
    page.set_content(test_document())
    page.wait_for_function('window.FluffyDebug?.animation.ready')
    return page


SEED='''() => {
const S=__fluffyModules['journal-store.js'], D=__fluffyModules['review-data.js'], C=__fluffyModules['catalog.js'];
S.write(S.KEY, []);
const today=S.dayKey();
window.testRecords={};
for(const id of ['sport','sleep','food','mood','face','focus']) for(let i=0;i<7;i++) {
 if(i===3)continue;const day=D.shiftDate(today,i-6);
 const raw={sport:{activity:'跑步',durationMinutes:[12,23,16,0,35,22,25][i],notes:'下班后沿河跑了一会儿'},
 sleep:{bedtime:'23:00',wakeTime:'07:00',quality:'醒来精神不错',notes:'夜里没有醒',recordDate:day},
 food:{meal:'午餐',foods:'米饭、鸡肉和西兰花',portion:'一碗',calories:560,protein:28,carbs:65,fat:19},
 mood:{mood:['平静','有些开心','有点失落','平静','松了一口气','有点累','有些失落，也想休息'][i],reason:'忙完了一件挂心的事',notes:'对自己温柔一点'},
 face:{feeling:'有点困，精神还好',eyeArea:'眼周有些暗',skinAppearance:'今天光线偏暗',notes:'想早点休息'},
 focus:{task:'读论文的方法部分',durationMinutes:30,notes:'读完三页'}}[id];
 const checked=C.validate(id,raw,true,{recordDate:day});
 const r={id:'test-'+id+'-'+i,category:id,data:checked.value,createdAt:day+'T10:00:00',source:'manual',...(id==='focus'?{focus:{elapsedMs:24*60000,restMs:5*60000}}:{})};
 if(!S.save(r))throw Error('fixture invalid '+id);
 if(i===6)testRecords[id]=r;
}
FluffyDebug.openReview(testRecords.sport);
}'''

MOCK='''() => {
window.requests=[]; window.replyText='今天这二十分钟，也是认真付出的呀。';
const R=FluffyDebug.review;
R.h.microphone.status=async()=> 'granted';
R.raw.supported=()=>true;R.raw.start=async()=>{R.raw.active=true;R.started();R.level=.6;R.wave=Array.from({length:72},(_,i)=>.05+(i%12)/18);return true};
R.raw.stop=async()=>{R.raw.active=false;return{audio:{data:'data:audio/wav;base64,AAAA',format:'wav'},canceled:false}};
R.raw.cancel=()=>{R.raw.active=false};
R.h.bailian.setKey('test-only-bailian-not-valid');
R.h.bailian.fetch=async(url,options)=> {
 const body=JSON.parse(options.body);requests.push(body);
 if(window.networkFail)return new Response('{}',{status:429});
 if(window.deferResponse)await new Promise(resolve=>{window.finishDeferred=resolve});
 const result=JSON.stringify({transcript:'今天只练了二十分钟，总觉得没做够。',replies:[{text:replyText,gesture:'wave'},{text:'是时间不太够，还是今天有点累？',gesture:'think'}]});
 if(body.stream){const enc=new TextEncoder();const raw='data: '+JSON.stringify({choices:[{delta:{content:result},finish_reason:null}]})+'\\n\\ndata: '+JSON.stringify({choices:[{delta:{},finish_reason:'stop'}]})+'\\n\\ndata: [DONE]\\n\\n';return new Response(new ReadableStream({start(c){c.enqueue(enc.encode(raw));c.close()}}),{headers:{'Content-Type':'text/event-stream'}});}
 return new Response(JSON.stringify({choices:[{finish_reason:'stop',message:{content:result}}]}),{headers:{'Content-Type':'application/json'}});
};
}'''


def hold(page, ms=520):
    """输入：页面、按住毫秒。输出：无。功能：执行真实指针按压，不直接调用开始方法。"""
    box=page.locator('#review-chat').bounding_box()
    page.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2)
    page.mouse.down()
    page.wait_for_timeout(ms)


def run():
    """输入：无。输出：JSON证据。功能：覆盖路由、只读数据、长按授权、异步取消、气泡和窄屏边界。"""
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_BIN','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
        page=load(browser)
        # 阶段一：真正的记录、书写、庆祝和回顾入口。
        page.evaluate("FluffyDebug.openEntry('sport',{activity:'力量训练',durationMinutes:20,notes:'深蹲四组'})")
        before=page.locator('#entry-form').inner_text()
        check('记录页仍为项目/时长/备注', '运动项目' in before and '时长' in before and '距离' not in before)
        check('记录页没有回顾聊天按钮', page.locator('#review-page').is_hidden())
        page.locator('#confirm-entry').click()
        check('原手动填写仍进入小猫书写',page.evaluate("FluffyDebug.animation.scene==='record'"))
        page.evaluate('FluffyDebug.animation.time=FluffyDebug.animation.writeEnd+9;FluffyDebug.animation.render()')
        page.locator('#primary').click()
        check('书写后进入Great job',page.evaluate("FluffyDebug.animation.scene==='celebrate'"))
        page.evaluate('FluffyDebug.animation.time=6;FluffyDebug.animation.render()')
        check('庆祝按钮文案改为完成', page.locator('#primary-label').inner_text()=='完成')
        page.locator('#primary').click()
        check('庆祝完成进入对应运动回顾',page.evaluate("FluffyDebug.animation.scene==='review'&&FluffyDebug.review.view.id==='sport'"))
        check('回顾没有重复保存',page.evaluate("__fluffyModules['journal-store.js'].records().length===1"))
        page.wait_for_timeout(1000)
        check('当日真实运动显示20分钟', page.locator('.review-fact-value').inner_text()=='20 分钟')
        check('缺失的6天留空不填假分数',page.locator('.review-bar.missing').count()==6)
        check('首屏只有底部长按聊天主按钮',page.locator('#review-page .primary').count()==1 and '长按和小猫聊两句' in page.locator('#review-chat').inner_text())
        check('不常驻显示仅供参考文案','仅供参考' not in page.locator('#review-page').inner_text())
        page.locator('#review-home').click()
        check('房屋按钮返回首页',page.evaluate("FluffyDebug.animation.scene==='home'"))
        check('首页退出使回顾隐藏',page.locator('#review-page').is_hidden())
        # 阶段二：实际7天数据和各类别视图。
        page.evaluate(SEED)
        page.wait_for_timeout(1000)
        page.locator('#phone').screenshot(path=str(OUT/'sport.png'))
        for category in ['sport','sleep','food','mood','face','focus']:
            page.evaluate('(id)=>FluffyDebug.openReview(testRecords[id])',category)
            page.wait_for_timeout(300)
            check(category+'回顾保持一屏且无横向溢出',page.evaluate("(()=>{const e=document.querySelector('#review-page');return e.scrollWidth===393&&e.scrollHeight===852})()"))
            check(category+'只读快照归到对应板块',page.evaluate('(id)=>FluffyDebug.review.view.records.every(r=>r.category===id)',category))
        page.evaluate("FluffyDebug.openReview(testRecords.mood)")
        check('情绪展示自己的混合感受而不是评分',page.locator('.review-mood-text').inner_text()=='有些失落，也想休息' and page.locator('#review-score').count()==0)
        page.wait_for_timeout(300);page.locator('#phone').screenshot(path=str(OUT/'mood.png'))
        page.evaluate("FluffyDebug.openReview(testRecords.sleep)")
        page.wait_for_timeout(1000);page.locator('#phone').screenshot(path=str(OUT/'sleep.png'))
        check('睡眠回顾标题清楚标为目标匹配',page.locator('.review-score-label').inner_text()=='时长目标匹配分')
        page.evaluate("FluffyDebug.openReview(testRecords.focus)")
        check('专注显示实际24分钟不是计划30分钟',page.locator('.review-fact-value').inner_text()=='24 分钟')
        # 阶段三：菜单、目标、英语和分享。
        page.evaluate("FluffyDebug.openReview(testRecords.sport)")
        page.locator('#review-more').click()
        labels=page.locator('#review-menu button span').all_inner_texts()
        check('菜单每项都是四字短语',all(len(x)==4 for x in labels))
        check('菜单每项都有图标',page.locator('#review-menu button svg').count()==len(labels))
        check('评分依据只在菜单', '评分依据' in labels and page.locator('#review-page > button').all_inner_texts().count('评分依据')==0)
        page.locator('#phone').screenshot(path=str(OUT/'menu.png'))
        page.keyboard.press('Escape');check('Escape收起菜单',page.locator('#review-menu').is_hidden())
        page.locator('#review-more').click();page.get_by_role('menuitem',name='调整目标',exact=True).click()
        page.locator('#sheet-body input').fill('50');page.get_by_role('button',name='保存目标',exact=True).click()
        page.wait_for_timeout(1000)
        check('个人目标修改重算分数为50',page.locator('#review-score').inner_text()=='50')
        page.locator('#review-more').click();page.get_by_role('menuitem',name='语言切换').click();page.get_by_role('button',name='English',exact=True).click()
        check('回顾语言切为English',page.locator('#review-title').inner_text()=='Workout review' and 'Hold to talk' in page.locator('#review-chat').inner_text())
        check('英文气泡不超两行',page.evaluate("document.querySelector('#review-bubble').textContent.split('\\n').length<=2"))
        page.wait_for_timeout(900);page.locator('#phone').screenshot(path=str(OUT/'english.png'))
        page.locator('#review-more').click();page.get_by_role('menuitem',name='Language',exact=True).click();page.get_by_role('button',name='中文',exact=True).click()
        page.locator('#review-more').click();page.get_by_role('menuitem',name='分享卡片').click()
        page.wait_for_selector('.review-share-preview',timeout=15000)
        check('分享先展示图片预览不自动发布',page.locator('.review-share-preview').is_visible())
        with page.expect_download() as dl:
            page.get_by_role('button',name='保存图片',exact=True).click()
        download=dl.value;download.save_as(OUT/'share-card.png')
        check('分享图片真实输出PNG', (OUT/'share-card.png').stat().st_size>10000)
        page.locator('#sheet-close').click()
        # 阶段四：真实UI长按，明确媒体与API替身。
        page.evaluate(MOCK)
        page.evaluate('window.beforeChat=JSON.stringify(__fluffyModules["journal-store.js"].records())')
        hold(page);check('长按进入真实媒体回调的倾听状态',page.evaluate("FluffyDebug.review.phase==='listening'"))
        check('按住时文字隐藏、同一按钮展示波形',page.evaluate("getComputedStyle(document.querySelector('#review-chat-label')).visibility==='hidden'&&!document.querySelector('#review-chat-wave').hidden"))
        page.wait_for_timeout(100);page.locator('#phone').screenshot(path=str(OUT/'listening.png'))
        check('音量历史来自输入而非随机',page.evaluate('FluffyDebug.review.wave[11]>.5'))
        page.mouse.up();page.wait_for_function("requests.length>=1&&FluffyDebug.review.phase==='speaking'")
        check('松手只提交一次音频请求',page.evaluate('requests.length===1'))
        check('回复期间麦克风已停止',page.evaluate('!FluffyDebug.review.raw.active'))
        check('请求里有确认数据和7天上下文',page.evaluate("JSON.stringify(requests[0].messages).includes('weekly')&&JSON.stringify(requests[0].messages).includes('下班后沿河')"))
        check('回应显示一句1到2行',page.evaluate("document.querySelector('#review-bubble').textContent.split('\\n').length<=2"))
        page.wait_for_timeout(500);page.locator('#phone').screenshot(path=str(OUT/'reply.png'))
        check('小猫自然举爪参数在缓动',page.evaluate('FluffyDebug.animation.reviewWave>0.1&&FluffyDebug.animation.reviewWave<=1'))
        check('聊天不会写入或改动已确认记录',page.evaluate('beforeChat===JSON.stringify(__fluffyModules["journal-store.js"].records())'))
        # 把阅读时间推进到末尾，检查淡出/下一句而不等待每句话完整时长。
        first=page.locator('#review-bubble').inner_text()
        page.evaluate('FluffyDebug.review.queueElapsed=FluffyDebug.review.queueDuration+400')
        page.wait_for_timeout(120)
        check('长回复会进入下一句',page.locator('#review-bubble').inner_text()!=first)
        hold(page);page.mouse.up();page.wait_for_function('requests.length===2&&FluffyDebug.review.phase==="speaking"')
        check('第二轮API包含第一轮用户与小猫的上下文',page.evaluate("requests[1].messages.some(m=>m.role==='assistant')&&requests[1].messages.some(m=>typeof m.content==='string'&&m.content.includes('今天只练了二十分钟'))"))
        check('说完仍留在数据回顾而非庆祝',page.evaluate("FluffyDebug.animation.scene==='review'"))
        # 阶段五：迟到响应、失败、授权弹窗与清除Key。
        page.evaluate('window.deferResponse=true')
        hold(page);page.mouse.up();page.wait_for_function('typeof finishDeferred==="function"')
        page.locator('#review-home').click();page.evaluate('finishDeferred();window.deferResponse=false')
        page.wait_for_timeout(200)
        check('离开回顾取消迟到API且不自动跳回',page.evaluate("FluffyDebug.animation.scene==='home'&&!FluffyDebug.review.active"))
        page.evaluate("FluffyDebug.openReview(testRecords.sport)");page.wait_for_timeout(180);page.evaluate('requests=[];window.networkFail=true')
        hold(page);page.mouse.up();page.wait_for_function("FluffyDebug.review.phase==='idle'")
        check('服务错误不伪装成功回复',page.locator('#phone-toast').is_visible() and page.locator('#phone-toast').inner_text()!='')
        check('失败也不改数据',page.evaluate('beforeChat===JSON.stringify(__fluffyModules["journal-store.js"].records())'))
        page.evaluate("()=>{networkFail=false;FluffyDebug.review.h.microphone.status=async()=> 'prompt';FluffyDebug.review.h.microphone.authorize=()=>new Promise(resolve=>window.allowMic=resolve);}")
        hold(page);check('首次授权与录音分开',page.evaluate("FluffyDebug.review.phase==='authorizing'"))
        page.evaluate("window.dispatchEvent(new Event('blur'))")
        page.mouse.up();page.evaluate('allowMic(true)');page.wait_for_timeout(100)
        check('授权弹窗失焦不取消授权，允许后回到待机',page.evaluate("FluffyDebug.review.phase==='idle'&&!FluffyDebug.review.raw.active"))
        page.evaluate("FluffyDebug.review.h.microphone.status=async()=> 'granted'")
        hold(page);page.locator('#open-bailian').dispatch_event('click');page.mouse.up()
        check('打开Key设置会关闭回顾麦克风',page.evaluate('!FluffyDebug.review.raw.active&&FluffyDebug.review.phase==="idle"'))
        page.locator('#forget-bailian').click();page.evaluate('FluffyDebug.bailianSettings.close(false)')
        hold(page);page.mouse.up();page.wait_for_timeout(120)
        check('无Key不会伪造成功对话',page.evaluate('!FluffyDebug.review.raw.active'))
        page.evaluate('FluffyDebug.review.h.api.clear();FluffyDebug.review.h.bailian.clear();')
        page.locator('#api-popover').evaluate('(n)=>n.hidden=true')
        check('浏览器无未捕获异常',not page.errors)
        # 阶段六：六种视口同一设计坐标；UI不出现滑条、横向溢出。
        for w,h in [(1440,1000),(1000,850),(393,852),(375,812),(320,700),(430,932)]:
            page.set_viewport_size({'width':w,'height':h})
            page.wait_for_timeout(90)
            good=page.evaluate('''()=>{const s=document.querySelector('#screen').getBoundingClientRect(),b=document.querySelector('#review-chat').getBoundingClientRect(),r=document.querySelector('#review-page');return r.scrollWidth===393&&r.scrollHeight===852&&b.left>=s.left&&b.right<=s.right+1&&b.bottom<s.bottom&&document.documentElement.scrollWidth<=innerWidth}''')
            check(f'{w}×{h}回顾按钮与内容在安全范围',good)
        page.close();browser.close()
    (OUT/'results.json').write_text(json.dumps(RESULTS,ensure_ascii=False,indent=2))

if __name__=='__main__':
    try: run()
    finally: (OUT/'results.json').write_text(json.dumps(RESULTS,ensure_ascii=False,indent=2))
