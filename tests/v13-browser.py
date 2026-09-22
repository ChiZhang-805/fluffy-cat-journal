"""输入：交付站点源码。输出：断言和运行截图。功能：测试自动选图与用户修改保护，网络仅使用明确替身。"""
from pathlib import Path
import asyncio, io, json, os
from PIL import Image
from playwright.async_api import async_playwright
from browser_helpers_v5 import test_document

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('V13_OUT', ROOT.parent/'verification/v13-browser'))
OUT.mkdir(parents=True,exist_ok=True)
RESULT=[]
SETUP=r'''
window.FLUFFY_TEST=true;window.__mode='ok';window.__posts=[];window.__waiters=[];window.__custom=null;
window.fetch=async function(url,opts={}){
 const p=opts.body?JSON.parse(opts.body):null;
 const response=data=>new Response(JSON.stringify(data),{status:200,headers:{'Content-Type':'application/json'}});
 const completion=data=>response({choices:[{finish_reason:'stop',message:{content:JSON.stringify(data)}}]});
 if(!p)return response({data:[{id:'qwen3-vl-plus'}]});
 const provider=String(url).includes('aliyuncs')?'bailian':'deepseek';
 __posts.push({provider,body:p});
 if(__mode==='defer')return new Promise(resolve=>__waiters.push(data=>resolve(completion(data))));
 if(__mode==='bad')return response({choices:[{finish_reason:'stop',message:{content:'not-json'}}]});
 if(__mode==='denied')return new Response('Do not expose this body or key',{status:401});
 if(__mode==='busy')return new Response('',{status:429});
 if(__mode==='network')throw new TypeError('Failed to fetch');
 if(provider==='deepseek')throw Error('Unexpected DeepSeek image request');
 return completion(__custom||{fields:{foods:'海鲜意面',portion:'一盘',calories:715,protein:29.4,carbs:90.2,fat:24.3},warnings:['份量为目测估算，未称重；热量需依据配方'],estimated:true});
};
'''


def check(name,value):
    """输入：断言名称与结果。输出：验证记录。功能：失败立即抛错，未执行项不计算为通过。"""
    RESULT.append({'name':name,'passed':bool(value)})
    print(('PASS ' if value else 'FAIL ')+name,flush=True)
    assert value,name


def fixture_image(name='fixture.png', size=(360,220), color='#86bcbc'):
    """输入：测试文件名与尺寸。输出：内存PNG。功能：只用于验证上传机制，不作为真实食物推断。"""
    data=io.BytesIO();Image.new('RGB',size,color).save(data,format='PNG')
    return {'name':name,'mimeType':'image/png','buffer':data.getvalue()}


async def entry(p,category='food',key=True):
    """输入：页面与类别。输出：清空的记录页。功能：隔离每个场景，不清理用户真实存储。"""
    await p.evaluate('([c,k])=>{__mode="ok";__custom=null;FluffyDebug.openEntry(c,{});if(k)FluffyDebug.bailianTest.setKey("sk-fixture-vision-key");else FluffyDebug.bailianTest.clear();}',[category,key])
    await p.wait_for_timeout(350)


async def upload(p,name='fixture.png',size=(360,220),color='#86bcbc',wait=True):
    """输入：内存图片与是否等待。输出：无。功能：从真实文件input派发用户选择，不直接调用分析函数。"""
    await p.locator('#photo-library').set_input_files(fixture_image(name,size,color))
    if wait:
        await p.wait_for_function('FluffyDebug.state.photoJob && FluffyDebug.state.phase==="idle" && FluffyDebug.state.photoJob.status!=="selected"')
    else:await p.wait_for_function('FluffyDebug.state.phase==="thinking"')
    await p.wait_for_timeout(120)


async def resolve(p,fields,index=0):
    """输入：模型测试字段、等待队列下标。输出：无。功能：刻意送回迟到响应，检查生产代码的拒收逻辑。"""
    await p.evaluate('([i,d])=>__waiters.splice(i,1)[0]({fields:d,warnings:[],estimated:true})',[index,fields])
    await p.wait_for_timeout(220)


async def run():
    """输入：无。输出：JSON和截图。功能：执行真实页面路径；不申请真实麦克风、不调用付费模型。"""
    async with async_playwright() as a:
        browser=await a.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        p=await browser.new_page(viewport={'width':1100,'height':1000})
        p.set_default_timeout(8000);errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
        await p.set_content(test_document(extra=SETUP))
        await p.wait_for_function('window.FluffyDebug?.animation.ready')
        await entry(p)
        check('饮食页不创建让小猫看看按钮',await p.locator('#analyze-photo').count()==0)
        check('不创建营养details/summary或单独外框',await p.locator('.nutrition-details,.nutrition-fields').count()==0)
        check('四个营养字段直接属于主表单',await p.evaluate('["calories","protein","carbs","fat"].every(k=>document.querySelector(`[data-field="${k}"]`).parentElement.id==="entry-form")'))
        check('字段顺序为热量蛋白质碳水脂肪',await p.evaluate('Array.from(document.querySelectorAll("#entry-form>.field")).map(n=>n.dataset.field).join(",").includes("calories,protein,carbs,fat")'))
        check('照片不成为必填项',await p.evaluate('!__fluffyModules["catalog.js"].category("food").fields.some(f=>f.key==="photo")'))
        check('首屏吃了什么输入框完整可见',await p.evaluate('document.querySelector("#field-foods").getBoundingClientRect().bottom<=document.querySelector("#entry-panel").getBoundingClientRect().bottom-4'))
        await p.locator('.phone').screenshot(path=str(OUT/'food-empty.png'))
        count=await p.evaluate('__posts.length');await upload(p)
        check('用户选图后无须第二次点击自动请求一次',await p.evaluate('__posts.length')==count+1)
        check('图像只调用百炼不调用DeepSeek',await p.evaluate('__posts.every(x=>x.provider==="bailian"&&x.body.messages[1].content.some(c=>c.type==="image_url"))'))
        check('回填食物、份量、四个营养数据',await p.evaluate('FluffyDebug.rawForm().foods==="海鲜意面"&&FluffyDebug.rawForm().portion==="一盘"&&FluffyDebug.rawForm().calories==="720"&&FluffyDebug.rawForm().protein==="29"&&FluffyDebug.rawForm().carbs==="90"&&FluffyDebug.rawForm().fat==="24"'))
        check('模型无transcript依然正常，餐次不瞎猜',await p.locator('#field-meal').input_value()=='')
        check('原来的黄色条与底部错误条均不可见',not await p.locator('#draft-note').is_visible() and not await p.locator('#phone-toast').is_visible())
        text=await p.locator('#entry-bubble').inner_text()
        check('猫咪不重复免责声明',not any(t in text for t in ['估算','未称重','仅供参考','看看下方']))
        check('照片分析不自动保存或庆祝',await p.evaluate('FluffyDebug.animation.scene==="entry"&&__fluffyModules["journal-store.js"].records().length===0'))
        check('图片实际宽高保持原比例',await p.evaluate('(()=>{const n=document.querySelector(".photo-preview img"),r=n.getBoundingClientRect();return Math.abs(r.width/r.height-n.naturalWidth/n.naturalHeight)<.03})()'))
        await p.evaluate('(()=>{const panel=document.querySelector("#entry-panel"),field=document.querySelector("[data-field=calories]");panel.scrollTop+= (field.getBoundingClientRect().top-panel.getBoundingClientRect().top)/(document.querySelector("#screen").getBoundingClientRect().width/393)-16;})()')
        await p.wait_for_timeout(250)
        await p.locator('.phone').screenshot(path=str(OUT/'food-nutrition.png'))
        count=await p.evaluate('__posts.length');await upload(p)
        check('相同已完成图片再次选择不重复请求',await p.evaluate('__posts.length')==count)
        await p.evaluate('FluffyDebug.showPhoto(FluffyDebug.photo.image)');await p.wait_for_timeout(250)
        check('仅重新渲染照片不提交请求',await p.evaluate('__posts.length')==count)
        await p.locator('#field-protein').fill('77')
        await p.evaluate('__mode="defer"');await upload(p,'other.png',(220,360),'#709cad',False)
        check('换图清除旧图自动结果却保留手改值',await p.evaluate('FluffyDebug.rawForm().calories===""&&FluffyDebug.rawForm().foods===""&&FluffyDebug.rawForm().protein==="77"'))
        check('分析中表单、照片仍在原处可见可编辑',await p.locator('#entry-panel').is_visible() and not await p.locator('#voice-panel').is_visible() and await p.locator('#field-foods').is_enabled())
        await p.locator('#field-foods').fill('我自己写的菜名');await p.locator('#field-fat').fill('99');await p.locator('#field-fat').fill('')
        await resolve(p,{'foods':'新模型菜名','portion':'半盘','calories':450,'protein':20,'carbs':48,'fat':13})
        check('上传前及请求中的手动值均不覆盖',await p.evaluate('FluffyDebug.rawForm().foods==="我自己写的菜名"&&FluffyDebug.rawForm().protein==="77"'))
        check('主动清空字段不被迟到结果填回',await p.locator('#field-fat').input_value()=='')
        check('其余未改字段正常回填',await p.locator('#field-calories').input_value()=='450')
        await p.evaluate('FluffyDebug.removePhoto()')
        check('移除照片清掉AI-only数据，手动内容保留',await p.evaluate('!FluffyDebug.photo.image&&FluffyDebug.rawForm().calories===""&&FluffyDebug.rawForm().foods==="我自己写的菜名"&&FluffyDebug.rawForm().protein==="77"'))
        # Explicit errors are handled in the cat bubble; one click retries once.
        for mode,code in [('denied','Key'),('busy','忙'),('network','网络'),('bad','整理')]:
            await entry(p);await p.evaluate('(m)=>__mode=m',mode);count=await p.evaluate('__posts.length');await upload(p)
            text=await p.locator('#entry-bubble').inner_text()
            check(mode+' 在猫咪气泡说明且可重试',code in text and await p.locator('#entry-bubble').get_attribute('data-retry')=='true')
            check(mode+' 不自动反复提交',await p.evaluate('__posts.length')==count+1)
            check(mode+' 不出现黄条或toast',not await p.locator('#draft-note').is_visible() and not await p.locator('#phone-toast').is_visible())
        await p.evaluate('__mode="ok"');count=await p.evaluate('__posts.length');await p.locator('#entry-bubble').click();await p.wait_for_timeout(220)
        check('显式点击小猫重试成功一次',await p.evaluate('__posts.length')==count+1 and await p.locator('#field-foods').input_value()=='海鲜意面')
        # Upload with no key; enabling is an explicit action and resumes only that pending photo.
        await entry(p,key=False);count=await p.evaluate('__posts.length');await upload(p)
        check('未配置百炼Key不发送照片',await p.evaluate('__posts.length')==count)
        check('照片保留，气泡提示配置百炼',await p.evaluate('!!FluffyDebug.photo.image&&FluffyDebug.state.photoJob.status==="waiting-key"') and '百炼' in await p.locator('#entry-bubble').inner_text())
        await p.locator('#open-bailian').click();await p.locator('#bailian-key').fill('sk-fixture-new-bailian-key');await p.locator('#save-bailian').click();await p.wait_for_function('FluffyDebug.state.photoJob.status==="done"')
        check('启用Key后自动分析刚才那张且仅一次',await p.evaluate('__posts.length')==count+1)
        # Multiple pending replies / cancellation must not mutate current page.
        await entry(p);await p.evaluate('__mode="defer"');await upload(p,'old.png',(360,200),'#aa8888',False);await upload(p,'new.png',(240,360),'#88aa99',False)
        await resolve(p,{'foods':'新的照片','calories':500},1);await resolve(p,{'foods':'旧照片不该出现','calories':900},0)
        check('两张图乱序返回仅使用最后一张',await p.locator('#field-foods').input_value()=='新的照片' and await p.locator('#field-calories').input_value()=='500')
        for action in ['remove','home','date','language','clear-key','cancel']:
            await entry(p);await p.evaluate('__mode="defer"');await upload(p,wait=False)
            if action=='remove':await p.evaluate('FluffyDebug.removePhoto()')
            elif action=='home':await p.evaluate('FluffyDebug.navigate("home")')
            elif action=='date':await p.evaluate('FluffyDebug.changeRecordDate("2026-09-20")')
            elif action=='language':await p.evaluate('FluffyDebug.changeLanguage("en")')
            elif action=='clear-key':await p.evaluate('FluffyDebug.bailianSettings.clear()')
            else:await p.locator('#confirm-entry').click()
            await resolve(p,{'foods':'迟到结果','calories':900})
            check(action+' 后迟到模型不能回填',await p.evaluate('FluffyDebug.rawForm().foods!=="迟到结果"'))
        await entry(p);count=await p.evaluate('__posts.length')
        await p.locator('#photo-library').set_input_files({'name':'broken.png','mimeType':'image/png','buffer':b'Not a valid image'})
        await p.wait_for_timeout(220)
        check('损坏图片不发送且由猫咪提示',await p.evaluate('__posts.length')==count and bool(await p.locator('#entry-bubble').inner_text()))
        # Non-food / unclear photo keeps numbers unknown, rather than inventing values.
        await entry(p);await p.evaluate('__custom={fields:{},warnings:["这是空盘，无法估算"]}');await upload(p)
        check('无可辨食物不编造营养数字',await p.evaluate('["calories","protein","carbs","fat"].every(k=>FluffyDebug.rawForm()[k]==="")'))
        check('无可辨食物只在气泡请求新照片', 'photo' in (await p.locator('#entry-bubble').inner_text()).lower() or '照片' in await p.locator('#entry-bubble').inner_text())
        # Adding portion detail after a partial result can explicitly retry through the same cat bubble.
        await entry(p);await p.evaluate('__custom={fields:{foods:"意面"},warnings:[]}');await upload(p)
        check('部分结果保留且小猫允许重试',await p.locator('#field-foods').input_value()=='意面' and await p.locator('#entry-bubble').get_attribute('data-retry')=='true')
        await p.locator('#field-portion').fill('我吃了半盘')
        await p.evaluate('__custom={fields:{foods:"意面",portion:"一整盘",calories:350,protein:15,carbs:42,fat:12},warnings:[]}')
        count=await p.evaluate('__posts.length');await p.locator('#entry-bubble').click();await p.wait_for_timeout(200)
        check('补充份量后点猫重新分析，不添加新按钮',await p.evaluate('__posts.length')==count+1 and await p.locator('#analyze-photo').count()==0)
        check('重新分析保留用户指定的半盘份量',await p.locator('#field-portion').input_value()=='我吃了半盘' and await p.locator('#field-calories').input_value()=='350')
        # Synthetic camera stream: tests the actual openCamera/video/capture/encode path, not a physical camera.
        await entry(p)
        await p.evaluate(r'''()=>{const c=document.createElement("canvas");c.width=360;c.height=220;const g=c.getContext("2d");g.fillStyle="#9abbab";g.fillRect(0,0,360,220);window.__cameraCanvas=c;window.__cameraStream=c.captureStream(10);Object.defineProperty(navigator,"mediaDevices",{configurable:true,value:{getUserMedia:async()=>__cameraStream}});}''')
        count=await p.evaluate('__posts.length');await p.locator('.photo-tool').first.click()
        await p.wait_for_function('document.querySelector("video.camera-video")?.videoWidth>0')
        await p.locator('#sheet-body .sheet-buttons .solid').click();await p.wait_for_function('FluffyDebug.state.photoJob?.status==="done"')
        check('拍摄确认后也自动分析，不需第二次点击',await p.evaluate('__posts.length')==count+1)
        check('拍摄完成关闭全部合成视频轨道',await p.evaluate('__cameraStream.getTracks().every(t=>t.readyState==="ended")'))
        # English interface, manual notes, and original face upload workflow stay intact.
        await entry(p);await p.evaluate('FluffyDebug.changeLanguage("en");__custom={fields:{foods:"Pasta",portion:"One plate",calories:710,protein:30,carbs:85,fat:25},warnings:[]}');await upload(p)
        check('英文自动分析文案无中文',not await p.evaluate('/[\\u3400-\\u9fff]/.test(document.querySelector("#entry-bubble").innerText)'))
        check('英文四字段仍独立全宽',await p.evaluate('[...document.querySelectorAll("#entry-form>.field")].filter(n=>["calories","protein","carbs","fat"].includes(n.dataset.field)).length===4'))
        await p.locator('.phone').screenshot(path=str(OUT/'food-english.png'))
        await entry(p,'face');count=await p.evaluate('__posts.length')
        await p.locator('#photo-library').set_input_files(fixture_image());await p.wait_for_timeout(220)
        check('面部页不被此次饮食自动分析改动',await p.evaluate('__posts.length')==count and await p.locator('#analyze-photo').is_visible())
        await p.evaluate('__custom={fields:{eyeArea:"No obvious change"},warnings:[]}');await p.locator('#analyze-photo').click();await p.wait_for_timeout(220)
        check('原面部手动分析入口仍可工作',await p.evaluate('__posts.length')==count+1)
        # Multiple viewport sizes; empty placeholder auto-fit and normal scrolling stay unchanged.
        await p.evaluate('FluffyDebug.changeLanguage("zh")')
        for w,h in [(1440,1000),(1100,900),(393,852),(375,812),(320,700),(430,932)]:
            await p.set_viewport_size({'width':w,'height':h});await entry(p)
            check(f'{w}x{h}首屏完整食物输入和无横向溢出',await p.evaluate('(()=>{const p=document.querySelector("#entry-panel"),f=document.querySelector("#field-foods");return f.getBoundingClientRect().bottom<=p.getBoundingClientRect().bottom-1&&p.scrollWidth<=p.clientWidth+1;})()'))
        check('所有实际页面动作无JavaScript错误',not errors)
        check('测试未写入Key、图片或餐次记录',await p.evaluate('![...__testStore.values()].some(v=>String(v).includes("sk-fixture")||String(v).includes("data:image"))&&__fluffyModules["journal-store.js"].records().length===0'))
        (OUT/'results.json').write_text(json.dumps({'passed':len(RESULT),'assertions':RESULT,'pageErrors':errors,'fixtureDisclosure':'PNG fixtures and mocked model replies; no paid API or real camera calls.'},ensure_ascii=False,indent=2))
        await browser.close()

if __name__=='__main__':asyncio.run(run())
