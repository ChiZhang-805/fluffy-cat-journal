"""输入：交付源码。输出：JSON断言与截图。功能：隔离浏览器记录/网络，仅测试实际程序交互。"""
from pathlib import Path
import asyncio, json, re, sys, os
from playwright.async_api import async_playwright
from browser_helpers_v5 import test_document
ROOT=Path(__file__).resolve().parents[1]; OUT=Path(os.environ.get('V11_OUT', ROOT.parent/'verification/browser')); OUT.mkdir(parents=True,exist_ok=True)
RESULT=[]
FIX={'sport':{'activity':'跑步','durationMinutes':12,'notes':'今天状态不错'},'food':{'meal':'午餐','foods':'米饭','portion':'一碗','notes':'状态不错','calories':500,'protein':20,'carbs':60,'fat':15},'mood':{'mood':'平静','reason':'跑步','notes':'状态不错'},'sleep':{'bedtime':'23:00','wakeTime':'07:00','quality':'很精神','notes':'状态不错'},'face':{'feeling':'状态不错','eyeArea':'状态不错','skinAppearance':'状态不错','notes':'状态不错'},'focus':{'task':'跑步','durationMinutes':20,'notes':'状态不错'}}

def check(name,value):
 """输入：名称与结果。输出：断言。功能：逐条保留测试证据。"""
 RESULT.append({'name':name,'passed':bool(value)});print(('PASS ' if value else 'FAIL ')+name,flush=True);assert value,name

async def settle(p):
 """输入：页面。输出：无。功能：让动画与原生微任务执行一小段真实时间。"""
 await p.wait_for_timeout(130)

async def no_han(p,name):
 """输入：页面和场景名。输出：断言。功能：扫描实际可见标签及可访问名称，不扫描用户正在编辑的值。"""
 await settle(p);text=await p.locator('body').inner_text();lines=[x for x in text.splitlines() if re.search(r'[\u3400-\u9fff]',x)]
 attrs=await p.evaluate('''()=>[...document.querySelectorAll('[aria-label],[title],[placeholder]')].filter(e=>e.checkVisibility()).flatMap(e=>['aria-label','title','placeholder'].map(k=>e.getAttribute(k)).filter(v=>v&&/[\\u3400-\\u9fff]/.test(v)))''')
 if lines or attrs: print('UNTRANSLATED',name,lines,attrs,flush=True)
 check('英文无中文 '+name,not lines and not attrs)

async def finish(p):
 """输入：当前书写页面。输出：回顾场景。功能：测试专用时间推进，不声称真实播放完整时长。"""
 await p.evaluate('FluffyDebug.animation.time=FluffyDebug.animation.writeEnd+10;FluffyDebug.animation.render()');await settle(p);await p.locator('#primary').click();await settle(p)
 await p.evaluate('FluffyDebug.animation.time=7;FluffyDebug.animation.render()');await settle(p);await p.locator('#primary').click();await settle(p)

async def main():
 """输入：无。输出：可复核检查报告。功能：覆盖首页路由、追加/修改、英文与只读意图流程。"""
 async with async_playwright() as a:
  b=await a.chromium.launch(executable_path=os.environ.get('CHROMIUM_BIN','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
  p=await b.new_page(viewport={'width':1100,'height':1050});p.set_default_timeout(5000);errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
  await p.set_content(test_document());await p.wait_for_function('window.FluffyDebug?.animation.ready');await settle(p)
  for cat in FIX:
   await p.locator(f'.home-widget[data-category={cat}]').click();await settle(p)
   check(cat+' 未记今日从首页进入填写',await p.evaluate(f'FluffyDebug.animation.scene==="entry"&&FluffyDebug.state.category==="{cat}"'))
   await p.locator('#back').click();await settle(p)
  await p.evaluate('''data=>{const S=__fluffyModules['journal-store.js'];for(const [cat,fields]of Object.entries(data)){S.save({id:'fixture-'+cat,category:cat,data:fields,recordDate:S.dayKey(),createdAt:new Date().toISOString(),focus:cat==='focus'?{elapsedMs:12*60000,restMs:0,plannedMs:20*60000}:null});}FluffyDebug.navigate('home');}''',FIX)
  for cat in FIX:
   await p.locator(f'.home-widget[data-category={cat}]').click();await settle(p)
   check(cat+' 今日有保存直接回顾',await p.evaluate(f'FluffyDebug.review.active&&FluffyDebug.review.view.id==="{cat}"'))
   await p.locator('#review-more').click()
   texts=await p.locator('#review-menu button').all_text_contents();check(cat+' 新增修改和当日列表均可用',all(k in texts for k in ['新增记录','修改记录','当日记录']))
   check(cat+' 菜单中文均四字',all(len(x.strip())==4 for x in texts))
   await p.evaluate('FluffyDebug.review.closeMenu()');await p.locator('#review-home').click();await settle(p)
  await p.screenshot(path=str(OUT/'home-zh.png'))
  # 真正走按钮完成一次新增，再选择具体条目修改。
  await p.locator('.home-widget[data-category=sport]').click();await settle(p);await p.locator('#review-more').click();await p.get_by_role('menuitem',name='新增记录',exact=True).click();await settle(p)
  check('新增不带入上一条ID和字段',await p.evaluate('FluffyDebug.state.editingId===null&&FluffyDebug.rawForm().activity===""'))
  await p.locator('#field-activity').fill('骑车');await p.locator('#field-durationMinutes').fill('20');await p.locator('#field-notes').fill('状态不错');await p.locator('#confirm-entry').click();await settle(p)
  check('新增经过原书写动画',await p.evaluate('FluffyDebug.animation.scene==="record"'))
  await finish(p)
  check('新增后运动共两条32分钟',await p.evaluate('FluffyDebug.review.view.today.count===2&&FluffyDebug.review.view.today.value===32'))
  await p.locator('#review-more').click();await p.get_by_role('menuitem',name='修改记录',exact=True).click();await settle(p)
  check('修改必须选择明细',await p.locator('.entry-picker-item').count()==2)
  await p.screenshot(path=str(OUT/'choose-entry-zh.png'))
  await p.locator('[data-record-id="fixture-sport"]').click();await settle(p);check('带回指定原条目而非最新一条',await p.locator('#field-activity').input_value()=='跑步')
  await p.locator('#field-durationMinutes').fill('30');check('编辑完成按钮写保存修改',await p.locator('#confirm-label').inner_text()=='保存修改')
  await p.locator('#confirm-entry').click();await settle(p);await finish(p)
  check('修改不重复计数：两条50分钟',await p.evaluate('FluffyDebug.review.view.today.count===2&&FluffyDebug.review.view.today.value===50'))
  check('保留原条修订副本',await p.evaluate('__fluffyModules["journal-store.js"].records().find(r=>r.id==="fixture-sport").revisions.length===1'))
  # 全局英文，包括用户中文记录的只读投影，用户原值不变。
  raw=await p.evaluate('JSON.stringify(__fluffyModules["journal-store.js"].records())');await p.evaluate('FluffyDebug.changeLanguage("en");FluffyDebug.navigate("home")');await no_han(p,'首页');await p.screenshot(path=str(OUT/'home-en.png'))
  for cat in FIX:
   await p.evaluate(f'FluffyDebug.newEntry("{cat}")');await no_han(p,'记录-'+cat)
   await p.locator('#entry-more').click();await no_han(p,'记录菜单-'+cat);await p.evaluate('FluffyDebug.entryMenu.close()')
   await p.evaluate(f'FluffyDebug.openCategory("{cat}")');await no_han(p,'回顾-'+cat)
   await p.locator('#review-more').click();await no_han(p,'回顾菜单-'+cat);await p.evaluate('FluffyDebug.review.closeMenu()')
   await p.evaluate('FluffyDebug.review.entriesSheet()');await no_han(p,'当日多条-'+cat);await p.evaluate('FluffyDebug.closeSheet()')
   await p.evaluate('FluffyDebug.review.basisSheet()');await no_han(p,'评分依据-'+cat);await p.evaluate('FluffyDebug.closeSheet()')
  for scene in ['history','tasks','profile']:
   await p.evaluate(f'FluffyDebug.navigate("{scene}")');await no_han(p,scene)
  await p.evaluate('FluffyDebug.languageSheet()');await no_han(p,'全局语言菜单');await p.evaluate('FluffyDebug.closeSheet()')
  check('英文切换没有改原记录',raw==await p.evaluate('JSON.stringify(__fluffyModules["journal-store.js"].records())'))
  await p.evaluate('FluffyDebug.newEntry("sport");FluffyDebug.fillForm({activity:"原始中文内容",durationMinutes:20,notes:"用户亲自写的备注"})')
  check('正在编辑的用户原文不被强行翻译',await p.locator('#field-activity').input_value()=='原始中文内容')
  await p.evaluate('FluffyDebug.changeLanguage("zh")');check('切回中文还原用户原值',await p.locator('#field-notes').input_value()=='用户亲自写的备注')
  # API 模拟明确限定，不使用真实Key或声称真实语音准确率。
  await p.evaluate('''()=>{FluffyDebug.apiTest.setKey('s'+'k-'+ 'x'.repeat(32));FluffyDebug.apiTest.request=async(url,payload)=>{
    const system=payload.messages[0].content;
    let body=system.includes('minimal journal field patch')?{fields:{durationMinutes:35}}:system.includes('Classify journal intent')?{operation:'none',targetIndex:null}:system.includes('Translate the provided')?{translations:JSON.parse(payload.messages.at(-1).content).strings.map(()=>"An English note")}: {replies:[{text:__fluffyModules['entry-i18n.js'].language()==='en'?'Let us check that entry together.':'我们一起核对\\n你选好再修改',gesture:'nod'}]};
    return{choices:[{finish_reason:'stop',message:{content:JSON.stringify(body)}}]};};FluffyDebug.openCategory('sport');}''');await settle(p)
  before=await p.evaluate('JSON.stringify(__fluffyModules["journal-store.js"].records())')
  await p.evaluate('FluffyDebug.review.send("把跑步时长改成35分钟")');await settle(p)
  check('聊天提出操作但没有写入',before==await p.evaluate('JSON.stringify(__fluffyModules["journal-store.js"].records())'))
  check('聊天出现待确认记事入口',await p.locator('#review-intent').is_visible())
  await p.locator('#review-intent').click();await settle(p);check('新增和修改由用户确认',set(['新增一条','修改原条']).issubset(set((await p.locator('#sheet-body').inner_text()).splitlines())))
  await p.get_by_role('button',name='取消操作',exact=True).click();check('取消意图不保存',before==await p.evaluate('JSON.stringify(__fluffyModules["journal-store.js"].records())'))
  await p.locator('#review-intent').click();await p.get_by_role('button',name='修改原条',exact=True).click();await settle(p)
  await p.locator('[data-record-id="fixture-sport"]').click();await p.wait_for_timeout(300)
  check('确认编辑只提取指定字段',await p.locator('#field-durationMinutes').input_value()=='35' and await p.locator('#field-activity').input_value()=='跑步')
  check('API回填仍未保存',before==await p.evaluate('JSON.stringify(__fluffyModules["journal-store.js"].records())'))
  await p.evaluate('FluffyDebug.apiTest.clear();FluffyDebug.changeLanguage("en");FluffyDebug.openCategory("sleep")');await settle(p);await p.screenshot(path=str(OUT/'sleep-en.png'))
  await p.locator('#review-more').click();await p.screenshot(path=str(OUT/'menu-en.png'));await p.evaluate('FluffyDebug.review.closeMenu()')
  await p.evaluate('FluffyDebug.review.textSheet()');await no_han(p,'文字聊天');await p.evaluate('FluffyDebug.closeSheet()')
  # 真实专注状态：活动计时仍优先，无记录页面不可吞掉正在执行的计时器。
  await p.evaluate('FluffyDebug.newEntry("focus");FluffyDebug.fillForm({task:"Read 20 pages",durationMinutes:25,notes:"Finish the chapter"});FluffyDebug.confirmManual()');await settle(p)
  await no_han(p,'倒计时');await p.locator('#timer-rest').click();await no_han(p,'休息计时')
  await p.evaluate('FluffyDebug.navigate("home")');await p.locator('.home-widget[data-category=focus]').click();await settle(p);check('已有专注记录且正在计时仍回计时器',await p.evaluate('FluffyDebug.animation.scene==="focus"'))
  await p.evaluate('FluffyDebug.timer.stop();FluffyDebug.finishFocus()');await no_han(p,'结束专注')
  # 多屏宽重排/文本边界，不更改原画位置。
  for width,height in [(390,844),(393,852),(430,932),(768,1024),(1440,900)]:
   await p.set_viewport_size({'width':width,'height':height});await p.evaluate('FluffyDebug.navigate("home")');await settle(p)
   check(f'视口{width}x{height}无横向溢出',await p.evaluate('document.documentElement.scrollWidth<=innerWidth'))
   await p.evaluate('FluffyDebug.openCategory("food");FluffyDebug.review.toggleMenu()');await settle(p)
   check(f'视口{width}x{height}菜单在手机内',await p.evaluate('''()=>{const a=document.getElementById('review-menu').getBoundingClientRect(),b=document.getElementById('screen').getBoundingClientRect();return a.left>=b.left-1&&a.right<=b.right+1&&a.bottom<=b.bottom;}'''))
  check('整个测试无脚本异常',not errors)
  (OUT/'results.json').write_text(json.dumps({'checks':RESULT,'pageErrors':errors,'method':'Actual bundled sources; isolated storage and explicit model fixtures; no real microphone/API calls.'},ensure_ascii=False,indent=2))
  await b.close()
try:asyncio.run(main())
finally:(OUT/'checks-partial.json').write_text(json.dumps(RESULT,ensure_ascii=False,indent=2))
