"""v3：状态栏、活动记录定位、手写线和连续笔尖的浏览器回归检查。"""
from pathlib import Path
import json
import os
from playwright.sync_api import sync_playwright
from browser_helpers import test_document

RESULTS = []
ROOT = Path(__file__).resolve().parents[1]


def check(name, value):
    """输入：名称、断言结果。输出：无。功能：记录检查结果，失败时立即停止。"""
    RESULTS.append({"test": name, "passed": bool(value)})
    assert value, name


def seek(page, time):
    """输入：浏览器页面、场景秒数。输出：无。功能：用真实角色渲染器定位时刻。"""
    page.evaluate("(t)=>{const a=FluffyDebug.animation;a.time=t;a.idle=7+t;a.render()}", time)


with sync_playwright() as pw:
    # 阶段一：控制测试时钟，检查跨分钟与恢复；不替换实际应用中的时间实现。
    browser = pw.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH", "/usr/bin/chromium"), headless=True, args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    mock_clock = '''window.RealDate=Date;window.testNow=new RealDate(2026,8,21,9,59,59).getTime();
    window.Date=class extends RealDate {constructor(...args){super(...(args.length?args:[testNow]));} static now(){return testNow;}};'''
    page.set_content(test_document(mock_clock), wait_until="load")
    page.wait_for_function("window.FluffyDebug?.animation.ready")
    page.evaluate("FluffyDebug.animation.playing=false")
    check("状态栏读取设备时间而非固定 9:41", page.locator("#system-clock").inner_text() == "9:59")
    page.evaluate("testNow=new RealDate(2026,8,21,10,0,1).getTime();window.dispatchEvent(new Event('focus'))")
    check("跨分钟后同步为 10:00", page.locator("#system-clock").inner_text() == "10:00")
    page.evaluate("testNow=new RealDate(2026,8,21,23,47).getTime();document.dispatchEvent(new Event('visibilitychange'))")
    check("后台恢复重新读取设备时间", page.locator("#system-clock").inner_text() == "23:47")
    check("三个图标使用独立矢量尺寸", page.locator(".system-icons svg").evaluate_all("es=>es.map(e=>e.getAttribute('width')).join(',')") == "18,17,27.5")
    check("系统时间不跟随动画暂停", page.evaluate("!FluffyDebug.animation.playing && document.getElementById('system-clock').textContent==='23:47'"))

    # 阶段二：标题、内容、横线必须跟随同一个循环副本，活动项不能只出现在底部。
    page.evaluate("FluffyDebug.animation.setRecord({activity:'跑步',distanceKm:3,durationMinutes:10,notes:'今天感觉很好，很轻松'});FluffyDebug.animation.setScene('record',0,false)")
    schedule = page.evaluate("FluffyDebug.animation.schedule")
    for index, slot in enumerate(schedule):
        values = []
        for fraction in [.01, .25, .5, .8, .99]:
            seek(page, slot["start"] + (slot["end"] - slot["start"]) * fraction)
            values.append(page.evaluate("""()=>{const m=FluffyDebug.animation.metrics,r=m.paperRows.find(r=>r.active&&r.canonical);
              return {y:r.labelY,visible:r.labelY-18>=m.paperClip[0],gap:r.inkY-r.labelY,
              sync:!m.penDown||Math.hypot(m.penTip[0]-m.inkTip[0],m.penTip[1]-m.inkTip[1])<1e-7};}"""))
        check(f"第 {index+1} 项活动标题完整保留在顶部", all(v["visible"] and v["y"] == 436 for v in values))
        check(f"第 {index+1} 项标题和内容间距固定", all(v["gap"] == 12 for v in values))
        check(f"第 {index+1} 项笔尖与墨迹同步", all(v["sync"] for v in values))
    check("跑步、数字、km 使用自绘笔路", page.evaluate("[...'跑步1234567890km'].every(c=>Ink.glyphs[c]) && Ink.glyphs['跑'].authored"))
    check("每条横线在对应墨迹下方 3 像素", page.evaluate("""()=>FluffyDebug.animation.lines.every(line=>line.ruleOffsets.every((rule,row)=>{
      const ink=line.strokes.filter(s=>s.glyph.row===row).flatMap(s=>s.points.map(p=>p[1]));return Math.abs(rule-Math.max(...ink)-3)<1e-6;
    }))"""))
    check("循环回来字形和字迹不重新随机生成", page.evaluate("""()=>{const a=FluffyDebug.animation,before=JSON.stringify(a.lines.map(l=>l.strokes.map(s=>s.points)));a.time=a.writeEnd+11;a.render();a.time=a.schedule[2].start+1;a.render();return before===JSON.stringify(a.lines.map(l=>l.strokes.map(s=>s.points)));}"""))
    continuity = page.evaluate("""()=>{const a=FluffyDebug.animation,es=a.schedule.flatMap(s=>[s.start,s.end]);let max=0;
      for(const t of es){const l=a.activeNib(t-1e-5).tip,r=a.activeNib(t+1e-5).tip;max=Math.max(max,Math.hypot(l[0]-r[0],l[1]-r[1]));}return max;}""")
    check("起笔、换项、末笔无位置跳变", continuity < .02)
    check("换项时抬笔，不在移动纸面画连线", page.evaluate("""()=>{const a=FluffyDebug.animation;return a.schedule.slice(0,-1).every((s,i)=>!a.activeNib((s.end+a.schedule[i+1].start)/2).down);}"""))
    check("庆祝时序整体缩短 15%", page.evaluate("(()=>{const a=FluffyDebug.animation;a.setScene('celebrate',0,false);return Math.abs(a.maximum()-5.95)<1e-9})()"))
    seek(page, 4.94)
    check("手写和撒花收尾后可点击 Continue", not page.locator("#primary").is_disabled())

    # 阶段三：最大长度记录和英文下伸笔画也必须留在各自书写区域内。
    for name, activity, notes in [
        ("长中文", "今天慢跑骑行游泳力量训练" * 3, "今天感觉不错跑步很轻松，结束后喝水休息，一点点坚持下去"),
        ("英文下伸字母", "Morning running and cycling", "Feeling good, keeping it easy!"),
    ]:
        page.evaluate("(r)=>{const a=FluffyDebug.animation;a.setRecord(r);a.setScene('record',0,false)}", {"activity": activity[:40], "distanceKm": 12.35, "durationMinutes": 40.5, "notes": notes[:32]})
        check(f"{name}完整生成而非截断", page.evaluate("FluffyDebug.animation.lines.every((l,i)=>l.text===FluffyDebug.animation.rows[i].value)"))
        check(f"{name}末行横线在卡片内", page.evaluate("FluffyDebug.animation.lines.every((l,i)=>470+90*i+l.ruleOffsets.at(-1)<=707)"))

    # 阶段四：保留居中手机，不增加外部导航、播放器、教程。
    page.evaluate("FluffyDebug.animation.setScene('entry',0,false)")
    for width, height in [(1440,1000),(1536,864),(390,844),(375,812),(320,720),(430,932)]:
        page.set_viewport_size({"width": width, "height": height})
        page.wait_for_timeout(70)
        check(f"手机居中且不水平溢出 {width}×{height}", page.locator("#phone").evaluate("e=>{const r=e.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth+1&&Math.abs(r.left+r.width/2-innerWidth/2)<1;}"))
    check("无未处理脚本异常", not errors)
    browser.close()

(ROOT / "tests" / "refinement-results.json").write_text(json.dumps({"environment": "Chromium, exact source in memory; explicit test clock; no microphone/API requests", "results": RESULTS}, ensure_ascii=False, indent=2))
print(json.dumps({"passed": len(RESULTS), "results": RESULTS}, ensure_ascii=False, indent=2))
