"""输入：发布源码。输出：浏览器断言与截图。功能：内存文档装载实际源码，语音/AI为明确替身，绝不调用付费API。"""
from pathlib import Path
import asyncio, json, os
from browser_helpers_v5 import test_document
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('V12_OUT',ROOT.parent/'verification/v12-browser'));OUT.mkdir(parents=True,exist_ok=True)
RESULT=[]
SETUP=r'''
window.FLUFFY_TEST=true;
window.__mode='ok';window.__requests=[];window.__deep=0;window.__bail=0;window.__resolveLate=null;
window.__payload=null;
window.fetch=async function(url,opts={}){
 const p=opts.body?JSON.parse(opts.body):null;const provider=String(url).includes('aliyuncs')?'bailian':'deepseek';
 if(p){window.__requests.push({provider,body:p});if(provider==='deepseek')__deep++;else __bail++;}
 const wrap=o=>new Response(JSON.stringify(o),{status:200,headers:{'Content-Type':'application/json'}});
 const model=o=>({choices:[{finish_reason:'stop',message:{content:JSON.stringify(o)}}]});
 if(!p)return wrap({data:[{id:'deepseek-flash'},{id:'qwen3-vl-plus'}]});
 if(__mode==='late'){return new Promise(r=>window.__resolveLate=()=>r(wrap(model({fields:{activity:'跑步',durationMinutes:30,notes:'五公里'},warnings:[]}))));}
 if(__mode==='empty')return wrap({choices:[{finish_reason:'stop',message:{content:''}}]});
 if(__mode==='bad')return wrap({choices:[{finish_reason:'stop',message:{content:'{bad'}}]});
 if(__mode==='denied')return new Response('sensitive provider response',{status:401});
 if(__mode==='busy')return new Response('',{status:429,headers:{'Retry-After':'60'}});
 if(__mode==='network')throw new TypeError('Failed to fetch');
 if(__mode==='once503'){window.__mode='ok';return new Response('',{status:503,headers:{'Retry-After':'0'}});}
 const sys=p.messages?.[0]?.content||'';
 if(sys.includes('Translate the provided'))return wrap(model({translations:JSON.parse(p.messages[1].content).strings.map(()=> 'A quiet moment')}));
 if(sys.includes('Classify journal intent'))return wrap(model({operation:'none',targetIndex:null}));
 if(sys.includes('预计分钟数'))return wrap(model({minutes:25,reason:'Fixture'}));
 if(sys.includes('回顾页'))return wrap(model({replies:[{text:document.documentElement.lang==='en'?'I am here with you.':'我在这里陪你呀',gesture:'soft'}]}));
 if(__payload)return wrap(model(__payload));
 if(provider==='bailian')return wrap(model({fields:{foods:'米饭',portion:'一碗',calories:200},warnings:[],estimated:true}));
 return wrap(model({fields:{activity:'跑步',durationMinutes:30,notes:'跑了五公里'},warnings:[]}));
};
window.__stops=0;window.__starts=0;window.__spoken='跑步三十分钟，五公里';window.__partial=false;
class FixtureContext{constructor(){this.state='running';}async resume(){}createMediaStreamSource(){return {connect(){},disconnect(){}}}createAnalyser(){return {fftSize:1024,getByteTimeDomainData(a){a.forEach((_,i)=>a[i]=128+Math.round(22*Math.sin(i/12)));}}}async close(){this.state='closed'}}
class FixtureRecognition{constructor(){window.__recognition=this;}start(){window.__starts++;setTimeout(()=>this.onstart?.(),20);}stop(){setTimeout(()=>{if(window.__spoken!==null){const r=[{transcript:window.__spoken}];r.isFinal=!window.__partial;this.onresult?.({results:[r],resultIndex:0});}this.onend?.();},35);}abort(){}}
window.__speechEnv={Recognition:FixtureRecognition,AudioContext:FixtureContext,mediaDevices:{getUserMedia:async()=>({getTracks:()=>[{stop(){__stops++;}}]})}};
'''

def check(name,ok):
 """输入：断言名/布尔值。输出：记录。功能：失败即停止，不将未执行项算成通过。"""
 RESULT.append({'name':name,'passed':bool(ok)});print(('PASS ' if ok else 'FAIL ')+name,flush=True);assert ok,name

async def settle(p,ms=150):
 """输入：页面与毫秒。输出：无。功能：给真实DOM和动画时间刷新。"""
 await p.wait_for_timeout(ms)

async def entry(p,cat='sport'):
 """输入：类别。输出：就绪记录页。功能：测试辅助仅跳到既有入口，不改变生产逻辑。"""
 await p.evaluate('(c)=>{FluffyDebug.openEntry(c,{});FluffyDebug.speech.env=__speechEnv;FluffyDebug.review.speech.env=__speechEnv;FluffyDebug.microphone.status=async()=>"granted";}',cat);await settle(p)

async def hold(p,selector='#confirm-entry',release=True):
 """输入：真实按钮选择器。输出：无。功能：按真实鼠标动作驱动长按，非直接调用状态回调。"""
 needs=await p.evaluate('FluffyDebug.apiTest.configured')
 bb=await p.locator(selector).bounding_box()
 await p.mouse.move(bb['x']+bb['width']/2,bb['y']+bb['height']/2)
 await p.mouse.down()
 if needs:
  await p.wait_for_function('(s)=>s==="#confirm-entry"?FluffyDebug.state.phase==="listening":FluffyDebug.review.phase==="listening"',arg=selector,timeout=6000)
  await settle(p,200)
 else:await settle(p,800)
 if release:
  await p.mouse.up()
  if await p.evaluate('__mode!=="late"'):
   await p.wait_for_function('(s)=>s==="#confirm-entry"?FluffyDebug.state.phase==="idle":FluffyDebug.review.phase==="speaking"',arg=selector,timeout=6000)
  else:await p.wait_for_function('!!window.__resolveLate',timeout=6000)
  await settle(p,80)

async def check_clean(p,label):
 """输入：页面与标签。输出：断言。功能：验证旧toast/黄框不再在用户页面出现。"""
 check(label+' 无按钮上方提示条',not await p.locator('#phone-toast').is_visible())
 check(label+' 无黄色草稿说明',not await p.locator('#draft-note').is_visible())

async def run():
 """输入：无。输出：验证文件。功能：内存文档运行发布HTML/CSS/JS，网关与听写事件使用人工替身。"""
 async with async_playwright() as a:
  b=await a.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  context=await b.new_context(viewport={'width':1100,'height':1000})
  p=await context.new_page();p.set_default_timeout(7000);errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
  await p.set_content(test_document(extra=SETUP));check('实际发布源码在测试文档装载',await p.locator('#screen').count()==1)
  await p.wait_for_function('window.FluffyDebug?.animation.ready');await settle(p)
  # 所有缺项均由小猫自己说，表单不丢失，主按钮邀请保持分类文案。
  expected={'sport':'运动项目','food':'哪一餐','mood':'心情','sleep':'几点','face':'感觉','focus':'专心'}
  for cat,word in expected.items():
   await entry(p,cat);await p.locator('#confirm-entry').click();await settle(p)
   text=await p.locator('#entry-bubble').inner_text();check(cat+' 首个缺项出现在气泡',word in text)
   check(cat+' 不让用户看下方提示','下方' not in text and '遇到小问题' not in text)
   await check_clean(p,cat)
  await entry(p);await p.locator('#confirm-entry').click();await p.locator('.phone').screenshot(path=str(OUT/'validation-zh.png'))
  # Key分工：只有百炼时不得发语言；已有两份Key时仍选browser ASR + DeepSeek。
  await p.evaluate('FluffyDebug.bailianTest.setKey("sk-fixture-bailian-only");');await hold(p)
  check('只开百炼仍提示缺DeepSeek', 'DeepSeek' in await p.locator('#entry-bubble').inner_text())
  check('百炼未接管普通语音',await p.evaluate('__bail===0&&__deep===0&&__starts===0'))
  await p.evaluate('FluffyDebug.closeSheet(false);document.querySelector("#api-popover").hidden=true;FluffyDebug.apiTest.setKey("sk-fixture-deepseek-enabled");')
  await entry(p);await hold(p,release=False)
  check('两份Key均启用仍选择浏览器听写',await p.evaluate('FluffyDebug.state.voiceBackend==="text"&&FluffyDebug.state.phase==="listening"'))
  check('记录页波形在原上方模块',await p.locator('#voice-panel').is_visible() and not await p.locator('#review-chat-wave').is_visible())
  check('真实记录模块接收测试音量变化',await p.evaluate('FluffyDebug.animation.level>0'))
  await p.locator('.phone').screenshot(path=str(OUT/'listening-fixture.png'))
  await p.mouse.up();await settle(p,300)
  check('原失败场景修复：模型无transcript仍回填',await p.locator('#field-activity').input_value()=='跑步' and await p.locator('#field-durationMinutes').input_value()=='30')
  check('普通语音只发DeepSeek而不发百炼',await p.evaluate('__deep===1&&__bail===0'))
  check('请求禁用思考且仅含转写文本',await p.evaluate('__requests[0].body.thinking.type==="disabled"&&typeof __requests[0].body.messages[1].content==="string"&&!JSON.stringify(__requests).includes("input_audio")'))
  check('回填不自动保存或庆祝',await p.evaluate('FluffyDebug.animation.scene==="entry"&&__fluffyModules["journal-store.js"].records().length===0'))
  check('松手释放测试麦克风',await p.evaluate('__stops>0&&!FluffyDebug.speech.active'))
  await p.locator('.phone').screenshot(path=str(OUT/'draft-fixture.png'))
  # 空ASR不上模型；音频错误与文本接口错误分别说。
  for mode,spoken,key in [('ok',None,'没听到内容'),('bad','测试说话','没整理好'),('denied','测试说话','Key'),('busy','测试说话','有点忙'),('network','测试说话','网络')]:
   await entry(p);before=await p.evaluate('__deep');await p.evaluate('([m,t])=>{__mode=m;__spoken=t;}',[mode,spoken]);await hold(p)
   text=await p.locator('#entry-bubble').inner_text();check(mode+str(spoken)+' 在气泡说明原因',key in text)
   await check_clean(p,'故障'+mode)
   check('故障'+mode+' 不回填假记录',await p.locator('#field-activity').input_value()=='')
   if spoken is None:check('没有转写原文就不调用模型',await p.evaluate('__deep')==before)
  # API失败保留听写原话并显式重试，手动改过的字段不能被旧快照覆盖。
  await entry(p);await p.evaluate('__mode="bad";__spoken="我今天跑步三十分钟五公里"');await hold(p)
  check('接口失败原话只留内存待重试',await p.evaluate('FluffyDebug.state.pendingUtterance.text===__spoken&&FluffyDebug.state.speechRetry'))
  await p.locator('.phone').screenshot(path=str(OUT/'api-error-zh.png'))
  await p.locator('#field-activity').fill('力量训练');await p.evaluate('__mode="ok"');before=await p.evaluate('__deep');await p.locator('#entry-bubble').click();await settle(p,240)
  check('显式点击气泡重试只有一个请求',await p.evaluate('__deep')==before+1)
  check('重试保留用户在等待期间修改的项目',await p.locator('#field-activity').input_value()=='力量训练')
  check('重试仍填写其他未动的字段',await p.locator('#field-durationMinutes').input_value()=='30')
  # 迟到结果不得跨类别/日期写入。
  await entry(p);await p.evaluate('__mode="late";__spoken="跑步三十分钟"');await hold(p)
  check('迟到测试已进入等待',await p.evaluate('FluffyDebug.state.phase==="thinking"&&!!__resolveLate'))
  await p.evaluate('FluffyDebug.openEntry("food");__resolveLate();');await settle(p,250)
  check('离开后的迟到回复不能覆盖饮食草稿',await p.evaluate('FluffyDebug.state.category==="food"&&FluffyDebug.rawForm().foods===""'))
  # 音频尾句不完整时保留可编辑草稿并说核对，避免假装完全正确。
  await entry(p);await p.evaluate('__mode="ok";__partial=true;__spoken="跑步三十分钟"');await hold(p)
  check('临时转写会提醒用户核对', '没听全' in await p.locator('#entry-bubble').inner_text())
  await p.evaluate('__partial=false');
  # 情绪现在也走文本，API不因百炼Key出现音调输入。
  await entry(p,'mood');await p.evaluate('__payload={fields:{mood:"失落但也释然",reason:"事情结束了",notes:""},emotion:{basis:"explicit",acousticEvidence:"不应进入草稿"},warnings:[]};__spoken="有点失落但也释然"');before=await p.evaluate('__bail');await hold(p)
  check('情绪允许DeepSeek转写语义整理',await p.locator('#field-mood').input_value()=='失落但也释然')
  check('情绪不声称声音分析也不发送百炼',await p.evaluate(f'FluffyDebug.state.emotionDraft.acousticEvidence===""&&__bail==={before}'))
  await p.evaluate('__payload=null')
  # 图像仍然百炼；创建仅用于测试的照片，不调用外部文件。
  await entry(p,'food');before=await p.evaluate('__bail')
  await p.evaluate('async()=>{const c=document.createElement("canvas");c.width=80;c.height=60;c.getContext("2d").fillRect(0,0,80,60);await FluffyDebug.acceptPhoto(c.toDataURL("image/jpeg"));}');await settle(p,250)
  check('照片分析只调用百炼视觉',await p.evaluate('__bail')==before+1)
  check('视觉分析结果仍可编辑',await p.locator('#field-foods').input_value()=='米饭')
  # 专注请求并发门闩与错误出口。
  await entry(p,'focus');await p.locator('#field-task').fill('读二十页书');before=await p.evaluate('__deep');await p.locator('.estimate-time').click();await settle(p,170)
  check('专注估时还是DeepSeek',await p.evaluate('__deep')==before+1 and await p.locator('#field-durationMinutes').input_value()=='25')
  check('估时结束回到可交互状态',await p.evaluate('FluffyDebug.state.phase==="idle"'))
  # 回顾：语音使用底部波形，图表保持在位；文本失败可重试，不改记录。
  await p.evaluate('FluffyDebug.openReview({category:"sport",recordDate:__fluffyModules["journal-store.js"].dayKey()});');await settle(p,230)
  r=await p.locator('#review-week').bounding_box();await hold(p,'#review-chat',release=False)
  check('回顾仍用底部按钮波形',await p.locator('#review-chat-wave').is_visible())
  rr=await p.locator('#review-week').bounding_box();check('回顾录音不移动图表',r==rr)
  await p.mouse.up();await settle(p,230);check('回顾语音完成进入逐句回应',await p.evaluate('FluffyDebug.review.phase==="speaking"'))
  await p.evaluate('FluffyDebug.review.cancel(false);__mode="bad";FluffyDebug.review.send("今天总觉得没做够");');await settle(p,220)
  check('回顾错误也由气泡说', '没整理好' in await p.locator('#review-bubble').inner_text())
  check('回顾错误不再显示底部状态条',not await p.locator('#review-status').is_visible() and not await p.locator('#phone-toast').is_visible())
  check('失败的聊天原文可以找回',await p.evaluate('FluffyDebug.review.textDrafts.get(FluffyDebug.review.sessionKey)==="今天总觉得没做够"'))
  await p.locator('.phone').screenshot(path=str(OUT/'review-error-zh.png'))
  await p.evaluate('__mode="ok"');await p.locator('#review-bubble').click();await settle(p,200)
  check('回顾点击气泡重试成功后清理待发原文',await p.evaluate('!FluffyDebug.review.retryPending&&FluffyDebug.review.history().some(x=>x.role==="user"&&x.content==="今天总觉得没做够")'))
  check('所有聊天和草稿操作都未暗中保存记录',await p.evaluate('__fluffyModules["journal-store.js"].records().length===0'))
  # 英文校验与横向布局：所有新提示和ARIA均英文；无提示条。
  await p.evaluate('FluffyDebug.changeLanguage("en");');await entry(p)
  for field,value in [('activity','Running'),('durationMinutes','30'),('notes','Five kilometers')]:
   await p.locator('#confirm-entry').click();await settle(p,120)
   text=await p.locator('#entry-bubble').inner_text();check('英文缺项提示 '+field,not any('\u3400'<=c<='\u9fff' for c in text))
   await p.locator('#field-'+field).fill(value)
  await entry(p);await p.evaluate('__mode="network";__spoken="I ran for thirty minutes"');await hold(p)
  check('英文API故障提示没有中文',not any('\u3400'<=c<='\u9fff' for c in await p.locator('#entry-bubble').inner_text()))
  await p.locator('.phone').screenshot(path=str(OUT/'network-en.png'))
  for width,height in [(375,812),(393,852),(430,932),(768,1024),(1440,900)]:
   await p.set_viewport_size({'width':width,'height':height});await settle(p,150)
   check(f'{width}x{height} 气泡不越过手机边界',await p.evaluate('()=>{const b=document.querySelector("#entry-bubble").getBoundingClientRect(),s=document.querySelector("#screen").getBoundingClientRect();return b.left>=s.left&&b.right<=s.right&&b.bottom<s.bottom;}'))
  check('全流程无未捕获脚本错误',len(errors)==0)
  await b.close()
  (OUT/'results.json').write_text(json.dumps({'source':'actual source in in-memory document; isolated storage; mocked provider/recognition boundary','assertions':RESULT,'errors':errors},ensure_ascii=False,indent=2))

if __name__=='__main__':
 try:asyncio.run(run())
 finally:(OUT/'attempt-results.json').write_text(json.dumps(RESULT,ensure_ascii=False,indent=2))
