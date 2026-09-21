__fluffyModules["app.js"] = (() => {
const { CompanionAnimation } = __fluffyModules["animation.js"];
const { DeepSeekClient } = __fluffyModules["deepseek.js"];
const { SpeechSession } = __fluffyModules["speech.js"];
const { MicrophonePermission } = __fluffyModules["microphone-permission.js"];
const { HoldGesture } = __fluffyModules["gesture.js"];
const { validateRecord, mayApplyField } = __fluffyModules["model.js"];
/**
 * 输入：id（DOM 标识）。
 * 输出：对应元素。
 * 功能：集中定位固定的手机界面元素。
 */
const $ = id => document.getElementById(id);
const CONFIG = window.FLuffyConfig || {};
const FIELDS = { activity: "field-activity", distanceKm: "field-distance", durationMinutes: "field-duration", notes: "field-notes" };
const versions = Object.fromEntries(Object.keys(FIELDS).map(key => [key, 0]));
const state = { phase: "idle", serial: 0, task: null, record: null, source: "manual", voiceVersions: null, keyTask: null, keySerial: 0 };
const api = new DeepSeekClient({ config: CONFIG, model: CONFIG.model });
const animation = new CompanionAnimation({ onReady: onReady, onRender: drawWaveform });
const microphone = new MicrophonePermission();
const speech = new SpeechSession({ onLevel: audioLevel, onText: receivedSpeech, onStarted: listeningStarted, onError: voiceFailed, onLimit: releaseSpeech });
let gesture, toastTimer, loadingTimeout;
let levelHistory = Array(72).fill(0);
/**
 * 输入：message（气泡内容），error（是否错误）。
 * 输出：无。
 * 功能：复用猫咪右上方气泡，不增加状态面板或冗余说明。
 */
function bubble(message, error = false) {
    $("entry-bubble").textContent = message.length > 38 ? (error ? "遇到一点小状况，看看下面的提示。" : "已经整理好，请核对一下记录。") : message;
    if (message.length > 38) toast(message);
    $("entry-bubble").classList.toggle("error", error);
}
/**
 * 输入：message（短提示）。
 * 输出：无。
 * 功能：仅在提交、保存或故障时临时显示提示，不占用正常表单空间。
 */
function toast(message) {
    clearTimeout(toastTimer);
    $("phone-toast").textContent = message;
    $("phone-toast").hidden = false;
    toastTimer = setTimeout(() => { $("phone-toast").hidden = true; }, 4200);
}
/**
 * 输入：phase（idle/authorizing/requesting/listening/thinking）。
 * 输出：无。
 * 功能：只更新真实过程的 UI；倾听和整理的角色参数交由动画器连续追踪。
 */
function setPhase(phase) {
    state.phase = phase;
    animation.entryMode = phase === "idle" || phase === "authorizing" ? "idle" : phase === "thinking" ? "thinking" : "listening";
    $("confirm-entry").classList.toggle("holding", phase === "listening");
    $("confirm-entry").dataset.pending = String(phase === "thinking");
    $("confirm-entry").disabled = phase === "thinking" || phase === "authorizing" || !animation.ready;
    $("confirm-label").textContent = ({ idle: "确认并继续", authorizing: "等待麦克风…", requesting: "等待麦克风…", listening: "松开结束", thinking: "正在整理…" })[phase];
    $("voice-overline").textContent = phase === "thinking" ? "小猫正在整理" : phase === "requesting" ? "等待麦克风授权" : "正在听你说";
    $("voice-hint").textContent = phase === "thinking" ? "你的话，正变成一份记录" : phase === "requesting" ? "允许麦克风后，再长按说话" : "松开，交给我整理";
    $("entry-form").inert = phase !== "idle";
    animation.render();
}
/**
 * 输入：无。
 * 输出：通过统一模型校验的表单结果。
 * 功能：读取四个全宽输入框；公里与分钟只接受数字。
 */
function readForm() {
    return validateRecord(Object.fromEntries(Object.entries(FIELDS).map(([key, id]) => [key, $(id).value])));
}
/**
 * 输入：errors（字段错误映射）。
 * 输出：无。
 * 功能：把错误标在实际输入框上，不在初始页面展示“必填”或字数提示。
 */
function showErrors(errors = {}) {
    for (const [key, id] of Object.entries(FIELDS)) $(id).setAttribute("aria-invalid", String(Boolean(errors[key])));
}
/**
 * 输入：record（草稿），snapshot（请求起始的字段版本）。
 * 输出：未覆盖的字段名数组。
 * 功能：填入真实结果，保护请求期间的新修改；AI 草稿始终可以再编辑。
 */
function fillForm(record, snapshot = null) {
    const protectedFields = [];
    for (const [key, id] of Object.entries(FIELDS)) {
        if (snapshot && !mayApplyField(key, snapshot, versions)) { protectedFields.push(key); continue; }
        $(id).value = record[key] ?? "";
    }
    showErrors();
    return protectedFields;
}
/**
 * 输入：record（规范化字段），source（manual/voice）。
 * 输出：不可变记录快照。
 * 功能：把展示动画和可变输入分开，重播或取消不会改写已进入动画的数据。
 */
function snapshot(record, source) {
    const id = state.record?.id || (crypto.randomUUID?.() || `${Date.now()}-${crypto.getRandomValues(new Uint32Array(1))[0]}`);
    return Object.freeze({ ...record, id, createdAt: state.record?.createdAt || new Date().toISOString(), source });
}
/**
 * 输入：无。
 * 输出：无。
 * 功能：短按校验四项后进入原有庆祝页；语音与长按事件不会误触此提交。
 */
function confirmManual() {
    if (state.phase !== "idle" || animation.scene !== "entry" || !animation.ready) return;
    const checked = readForm();
    if (!checked.ok) {
        showErrors(checked.errors);
        const first = Object.keys(checked.errors)[0];
        bubble(checked.errors[first], true);
        $(FIELDS[first]).focus({ preventScroll: true });
        return;
    }
    // 阶段一：撤销未完成工作并固定用户当前填写值。
    cancelWork(false);
    state.source = "manual";
    state.record = snapshot(checked.value, "manual");
    animation.setRecord(state.record);
    // 阶段二：庆祝一直停留到 Continue；不自动跳去书写。
    document.activeElement?.blur();
    animation.setScene("celebrate", 0, true);
}
/**
 * 输入：无。
 * 输出：Promise<void>。
 * 功能：达到长按阈值才申请录音；缺 Key/能力时清楚提示，不播假识别。
 */
async function beginSpeech() {
    if (animation.scene !== "entry" || state.phase !== "idle") return;
    if (!api.configured) { bubble("先在右上角填写 API Key。", true); openSettings(); return; }
    if (!speech.supported()) { bubble("这个浏览器不能转写语音，先直接填写吧。", true); return; }
    // 阶段一：固定请求版本；查询权限不会弹出麦克风窗口。
    cancelWork(false);
    const serial = state.serial;
    setPhase("requesting");
    try {
        const permission = await microphone.status();
        if (serial !== state.serial) return;
        if (permission !== "granted") {
            // 阶段二：首次只授权，不录音。先清空按压状态，弹窗失焦就不会触发取消。
            gesture.disarm();
            setPhase("authorizing");
            if (permission === "denied") throw Error("麦克风被禁用，请在地址栏的网站设置中允许。");
            bubble("请先允许麦克风。");
            await microphone.authorize();
            if (serial !== state.serial) return;
            setPhase("idle");
            bubble("可以了，长按开始说话。");
            return;
        }
        // 阶段三：已经授权，仅在用户仍按住按钮时才正式收音；松手不会迟开麦克风。
        if (!gesture.pressed) { cancelWork(false); return; }
        state.voiceVersions = { ...versions };
        levelHistory = Array(72).fill(0);
        $("speech-transcript").textContent = "说说今天做了什么运动。";
        bubble("我准备好听你说了。");
        document.activeElement?.blur();
        const started = await speech.start({ language: CONFIG.speechLanguage, maximumSeconds: CONFIG.maximumSpeechSeconds });
        if (serial !== state.serial || !started) return;
    } catch (error) {
        if (serial !== state.serial) return;
        const message = error.name === "NotAllowedError" ? "麦克风未获允许，请在地址栏设置中开启。" : error.message;
        voiceFailed(message);
    }
}
/**
 * 输入：无，由真实识别器启动回调调用。
 * 输出：无。
 * 功能：让“我在听”的姿态和真实麦克风状态一致。
 */
function listeningStarted() {
    if (state.phase !== "requesting") return;
    setPhase("listening");
    bubble("嗯，我在听。");
}
/**
 * 输入：level（真实音量），history（RMS 历史）。
 * 输出：无。
 * 功能：把音量送给柱形波和猫耳动作，不使用随机数据伪装输入。
 */
function audioLevel(level, history) {
    animation.level = level;
    levelHistory = history.slice();
}
/**
 * 输入：text（浏览器收到的真实转写）。
 * 输出：无。
 * 功能：在同一张卡片上展示用户刚说的话。
 */
function receivedSpeech(text) {
    $("speech-transcript").textContent = text || "说说今天做了什么运动。";
    $("speech-transcript").scrollTop = $("speech-transcript").scrollHeight;
}
/**
 * 输入：无。
 * 输出：Promise<void>。
 * 功能：松手关闭麦克风，取得末句并实际请求 DeepSeek，然后直接衔接书写。
 */
async function releaseSpeech() {
    if (state.phase === "authorizing") return;
    if (state.phase === "requesting") {
        cancelWork(false);
        bubble("准备好了，重新长按开始说话。");
        return;
    }
    if (state.phase !== "listening") return;
    const serial = state.serial, fieldSnapshot = state.voiceVersions;
    setPhase("thinking");
    bubble("听到了，我整理一下。");
    try {
        // 阶段一：停止收音；只允许本次会话的最后转写继续向下执行。
        const result = await speech.stop();
        animation.level = 0;
        if (serial !== state.serial || result.canceled) return;
        if (!result.text) throw Error("这次没有听清，长按再说一次吧。");
        receivedSpeech(result.text);
        // 阶段二：真实 Chat 请求与思考姿态共存，取消将同步撤销网络和回填。
        const controller = state.task = new AbortController();
        const extracted = await api.extract(result.text, controller.signal);
        if (serial !== state.serial || controller.signal.aborted) return;
        state.task = null;
        const protectedFields = fillForm(extracted.record, fieldSnapshot);
        const checked = readForm();
        // 阶段三：缺项或歧义不能捏造。保留草稿并让用户确认；完整结果才自动进入动画。
        if (!checked.ok || extracted.warnings.length || protectedFields.length || result.interim) {
            setPhase("idle");
            if (!checked.ok) {
                showErrors(checked.errors);
                bubble("已帮你填好听到的内容，剩下的请补一下。");
            } else bubble(extracted.warnings[0] || "我整理好了，请核对一下再继续。");
            return;
        }
        state.source = "voice";
        state.record = snapshot(checked.value, "voice");
        animation.setRecord(state.record);
        // 保留上一帧的倾听/思考参数和动画时钟，同一只猫原地伸爪拿笔。
        animation.setScene("record", 0, true);
        state.phase = "idle";
        $("confirm-entry").disabled = false;
    } catch (error) {
        if (serial !== state.serial || error.name === "AbortError") return;
        voiceFailed(error.message);
    }
}
/**
 * 输入：message（错误信息）。
 * 输出：无。
 * 功能：失败后释放资源并回到同一份表单，不生成示例数据来冒充成功。
 */
function voiceFailed(message) {
    cancelWork(false);
    bubble(message, true);
}
/**
 * 输入：announce（是否提示）。
 * 输出：无。
 * 功能：使旧识别/API 失效并释放麦克风；清理后的表单内容保持不变。
 */
function cancelWork(announce = true) {
    state.serial++;
    state.task?.abort(); state.task = null;
    speech.cancel();
    animation.level = 0;
    levelHistory = Array(72).fill(0);
    if (animation.scene === "entry") setPhase("idle");
    if (announce) bubble("已取消，填过的内容还在。");
}
/**
 * 输入：无。
 * 输出：无。
 * 功能：在真实收音时滚动 RMS 柱形，整理时改为明确的三点等待标记。
 */
function drawWaveform() {
    if (!$("voice-panel") || $("voice-panel").hidden) return;
    const canvas = $("voice-wave"), ctx = canvas.getContext("2d");
    ctx.setTransform(2, 0, 0, 2, 0, 0); ctx.clearRect(0, 0, 320, 105);
    if (state.phase === "thinking") {
        for (let i = 0; i < 3; i++) {
            const a = .3 + .5 * (Math.sin(animation.idle * 3 - i * .8) + 1) / 2;
            ctx.fillStyle = `rgba(88,153,128,${a})`;ctx.beginPath();ctx.arc(143 + i * 17, 52, 3.5, 0, Math.PI * 2);ctx.fill();
        }
        return;
    }
    const colors = ["#8fc6a2", "#9ebedc", "#b3ccb5", "#e3ce91"];
    ctx.lineWidth = 2.6;ctx.lineCap = "round";
    for (let i = 0; i < levelHistory.length; i++) {
        const h = 2 + levelHistory[i] * 78, x = 13 + i * 4.1;
        ctx.globalAlpha = .34 + .66 * Math.min(1, i / 13);
        ctx.strokeStyle = colors[Math.floor(i / 7) % 4];
        ctx.beginPath();ctx.moveTo(x, 52 - h / 2);ctx.lineTo(x, 52 + h / 2);ctx.stroke();
    }
    ctx.globalAlpha = 1;
}
/**
 * 输入：无。
 * 输出：无。
 * 功能：进入设置前停止收音；Key 输入框不会回显已经启用的密钥。
 */
function openSettings() {
    if (!$("api-popover").hidden) { closeSettings(); return; }
    if (state.phase !== "idle") cancelWork(false);
    gesture?.disarm();
    $("api-feedback").textContent = "";
    $("save-api").disabled = false; $("save-api").textContent = "启用";
    $("api-key").value = "";
    $("api-popover").hidden = false;
    $("open-settings").setAttribute("aria-expanded", "true");
    $("api-key").focus({ preventScroll: true });
}
/**
 * 输入：restoreFocus（是否将键盘焦点返回设置按钮）。
 * 输出：无。
 * 功能：关闭下拉框并撤销未完成的验证，不清除此前已经启用的 Key。
 */
function closeSettings(restoreFocus = true) {
    state.keyTask?.abort(); state.keyTask = null; state.keySerial++;
    $("api-popover").hidden = true;
    $("open-settings").setAttribute("aria-expanded", "false");
    $("api-key").value = "";
    $("save-api").disabled = false; $("save-api").textContent = "启用";
    if (restoreFocus) $("open-settings").focus({ preventScroll: true });
}
/**
 * 输入：提交事件。
 * 输出：Promise<void>。
 * 功能：验证候选 Key，成功后才替换已启用的 Key；关闭下拉框则撤销候选请求。
 */
async function saveKey(event) {
    event.preventDefault();
    state.keyTask?.abort();
    const serial = ++state.keySerial, controller = state.keyTask = new AbortController();
    const candidate = new DeepSeekClient({ config: CONFIG, model: CONFIG.model });
    const key = $("api-key").value;
    $("api-feedback").textContent = "";
    try {
        // 阶段一：临时实例校验，不让无效或取消的新 Key 破坏现有设置。
        candidate.setKey(key);
        $("save-api").disabled = true; $("save-api").textContent = "验证中…";
        const models = await candidate.check(controller.signal);
        if (controller.signal.aborted || serial !== state.keySerial) return;
        if (!models.includes(candidate.model)) throw Error("此 Key 暂时不能访问 Chat 模型。");
        // 阶段二：通过后原子替换。表单清空，密钥仅存在客户端实例私有内存中。
        api.setKey(key);
        $("key-indicator").classList.add("enabled");
        state.keyTask = null;
        closeSettings();
    } catch (error) {
        if (serial === state.keySerial && error.name !== "AbortError") $("api-feedback").textContent = error.message;
    } finally {
        candidate.clear();
        if (serial === state.keySerial) { state.keyTask = null; $("save-api").disabled = false; $("save-api").textContent = "启用"; }
    }
}
/**
 * 输入：无。
 * 输出：无。
 * 功能：清除 Key 并取消正在识别或提交的请求；不删除用户手动填写的内容。
 */
function clearKey() {
    state.keyTask?.abort(); state.keyTask = null; state.keySerial++;
    cancelWork(false); gesture?.disarm(); api.clear();
    $("key-indicator").classList.remove("enabled");
    $("api-key").value = ""; $("api-feedback").textContent = "";
    $("save-api").disabled = false; $("save-api").textContent = "启用";
    $("api-key").focus({ preventScroll: true });
}
/**
 * 输入：无。
 * 输出：无。
 * 功能：保留实际字段返回编辑；再次确认将以修改后的值重做记录。
 */
function editRecord() {
    cancelWork(false);
    animation.setScene("entry", 0, true);
    setPhase("idle");
    showErrors(); bubble("改好了，再交给我。");
}
/**
 * 输入：无。
 * 输出：无。
 * 功能：庆祝的 Continue 开始写字；完成按钮保存一次，下一次点击才开始新记录。
 */
function primaryAction() {
    if ($("primary").disabled) return;
    if (animation.scene === "celebrate") { animation.setScene("record", 0, true); return; }
    if (animation.scene !== "record") return;
    if (animation.saved) {
        state.record = null; state.source = "manual";
        fillForm({});
        animation.setScene("entry", 0, true);
        setPhase("idle"); bubble("今天的努力，我陪你记。");
        return;
    }
    try {
        // 仅保存最终字段；Key、音频和识别原文从不写入本机历史。
        const key = "fluffy-cat-minimal-records-v1", old = JSON.parse(localStorage.getItem(key) || "[]");
        const records = Array.isArray(old) ? old.filter(item => item.id !== state.record.id) : [];
        localStorage.setItem(key, JSON.stringify([state.record, ...records].slice(0, 100)));
        animation.saved = true; toast("已保存在这个浏览器里。");
    } catch { toast("浏览器不能保存到本机，记录仍保留在当前页面。" ); }
    animation.render();
}
/**
 * 输入：无。
 * 输出：无。
 * 功能：按可用视口缩放整台手机，桌面居中，窄屏为外部设置留出空间。
 */
function resizePhone() {
    const small = innerWidth <= 650, usableHeight = innerHeight - (small ? 80 : 48);
    const scale = Math.min(1, (innerWidth - 24) / 411, Math.max(450, usableHeight) / 870);
    document.documentElement.style.setProperty("--design-scale", scale.toFixed(6));
    document.documentElement.style.setProperty("--phone-w", `${411 * scale}px`);
    document.documentElement.style.setProperty("--phone-h", `${870 * scale}px`);
}
/**
 * 输入：无。
 * 输出：无。
 * 功能：角色图层准备好后才开放交互，避免在空画布时提交。
 */
function onReady() {
    clearTimeout(loadingTimeout);
    $("confirm-entry").disabled = false;
    resizePhone();
}
/**
 * 输入：无。
 * 输出：无。
 * 功能：绑定真实产品操作，不创建演示栏、播放条、章节导航或外部历史入口。
 */
function bind() {
    gesture = new HoldGesture($("confirm-entry"), { short: confirmManual, long: beginSpeech, release: releaseSpeech, cancel: () => { if (state.phase === "requesting" || state.phase === "listening") cancelWork(); } }, CONFIG.longPressMs || 420);
    $("entry-form").addEventListener("submit", event => { event.preventDefault(); confirmManual(); });
    for (const [field, id] of Object.entries(FIELDS)) {
        $(id).addEventListener("input", () => { versions[field]++; $(id).setAttribute("aria-invalid", "false"); });
        $(id).addEventListener("keydown", event => { if (event.key === "Enter" && !event.isComposing) { event.preventDefault(); confirmManual(); } });
    }
    $("cancel-voice").addEventListener("click", () => cancelWork());
    $("open-settings").addEventListener("click", openSettings);
    $("api-form").addEventListener("submit", saveKey);
    $("forget-key").addEventListener("click", clearKey);
    document.addEventListener("pointerdown", event => {
        if (!$("api-popover").hidden && !$("api-popover").contains(event.target) && !$("open-settings").contains(event.target)) closeSettings(false);
    });
    document.addEventListener("keydown", event => {
        if (event.key === "Escape" && !$("api-popover").hidden) { event.preventDefault(); closeSettings(); }
    });
    $("primary").addEventListener("click", primaryAction);
    $("back").addEventListener("click", editRecord);
    $("edit-record").addEventListener("click", editRecord);
    $("pet").addEventListener("click", () => { animation.petAt = animation.idle; });
    window.addEventListener("resize", resizePhone);
    window.addEventListener("pagehide", () => { cancelWork(false); closeSettings(false); api.clear(); });
    document.addEventListener("visibilitychange", () => { if (document.hidden && state.phase !== "idle") cancelWork(false); });
    document.addEventListener("keydown", event => { if (event.key === "Escape" && state.phase !== "idle") cancelWork(); });
}
$("confirm-entry").disabled = true;
resizePhone(); bind();
loadingTimeout = setTimeout(() => { if (!animation.ready) $("loading").textContent = "图层加载较慢，请稍候或刷新页面。"; }, 10000);
animation.initialize().catch(() => { clearTimeout(loadingTimeout); $("loading").textContent = "小猫图层未能加载，请刷新网页再试。"; });
// 仅调试 URL 暴露测试入口，正常打开不显示控件，也不把 API Key 暴露到全局。
if (new URLSearchParams(location.search).has("debug")) {
    window.FluffyDebug = { animation, state, speech, fillForm, readForm, confirmManual, beginSpeech, releaseSpeech, cancelWork, editRecord, versions, gesture, microphone };
}

return {};
})();
