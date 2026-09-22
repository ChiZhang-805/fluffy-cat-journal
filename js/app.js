/* Fluffy Cat · 六入口首页与完整记录流程。所有密钥仅在客户端实例的私有内存中。 */
__fluffyModules["app.js"] = (() => {
    "use strict";
    const { CompanionAnimation } = __fluffyModules["animation.js"];
    const { DeepSeekClient } = __fluffyModules["deepseek.js"];
    const { BailianClient } = __fluffyModules["bailian.js"];
    const { BailianSettings } = __fluffyModules["bailian-settings.js"];
    const { AudioSession } = __fluffyModules["audio-session.js"];
    const Sleep = __fluffyModules["sleep-time.js"];
    const { TimeRangePicker } = __fluffyModules["time-range-picker.js"];
    const { FormLayout } = __fluffyModules["form-layout.js"];
    const BubbleCopy = __fluffyModules["bubble-copy.js"];
    const { SpeechSession } = __fluffyModules["speech.js"];
    const { MicrophonePermission } = __fluffyModules["microphone-permission.js"];
    const { HoldGesture } = __fluffyModules["gesture.js"];
    const { PhotoInput } = __fluffyModules["photo-input.js"];
    const { HomeBoard } = __fluffyModules["home-board.js"];
    const { FocusTimer, formatTimer } = __fluffyModules["focus-timer.js"];
    const Catalog = __fluffyModules["catalog.js"], Store = __fluffyModules["journal-store.js"], AI = __fluffyModules["ai-journal.js"];
    const CONFIG = window.FLuffyConfig || {}, icon = FluffyIcons.svg;
    /**
     * 输入：id。
     * 输出：DOM 元素。
     * 功能：定位固定界面节点。
     */
    const $ = id => document.getElementById(id);
    /**
     * 输入：tag、className、text。
     * 输出：新 DOM 元素。
     * 功能：用户文字只经 textContent 渲染，避免 HTML 注入。
     */
    function el(tag, className = "", text = "") {
        const n = document.createElement(tag);
        n.className = className;
        if (text !== "")
            n.textContent = text;
        return n;
    }
    /**
     * 输入：节点、图标名。
     * 输出：无。
     * 功能：替换受控本地图标，不读取网络。
     */
    function setIcon(node, name) {
        node.innerHTML = icon(name);
    }
    const api = new DeepSeekClient({ config: CONFIG, model: CONFIG.model });
    const bailian = new BailianClient({ config: CONFIG });
    const state = {
        recordDate: Sleep.dateKey(), sleepDates: {}, emotionDraft: null, voiceBackend: "text",
        category: "sport", phase: "idle", serial: 0, task: null, record: null, source: "manual", estimated: false, versions: {}, drafts: {}, keySerial: 0, keyTask: null, filter: "all", sheetClose: null, focusRecord: null, timerNotified: false, taskId: null
    };
    const animation = new CompanionAnimation({ onReady, onRender: renderExtras, synchronize: synchronizeUI });
    const microphone = new MicrophonePermission(), photo = new PhotoInput(), timer = new FocusTimer();
    const speech = new SpeechSession({
        onLevel: audioLevel, onText: receivedSpeech, onStarted: listeningStarted, onError: voiceFailed, onLimit: releaseSpeech
    });
    const rawAudio = new AudioSession({ onLevel: audioLevel, onStarted: listeningStarted, onError: voiceFailed, onLimit: releaseSpeech });
    let activeSpeech = speech, bailianSettings;
    let timeRange = null, formLayout = null;
    let gesture, board, toastTimer, homeBubbleTimer, cameraVideo = null, sheetReturn = null, wave = Array(72).fill(0), lastTimerText = "", lastUI = "", lastFocusSave = 0;
    /**
     * 输入：文字、error。
     * 输出：无。
     * 功能：在猫咪右上角给出简短状态，不常驻冗余说明。
     */
    function bubble(text, error = false) {
        const detail = BubbleCopy.render($("entry-bubble"), text, error);
        if (detail) toast(detail);
    }
    /**
     * 输入：text。
     * 输出：无。
     * 功能：仅操作或错误时出现的临时提示。
     */
    function toast(text) {
        clearTimeout(toastTimer);
        $("phone-toast").textContent = text;
        $("phone-toast").hidden = false;
        toastTimer = setTimeout(() => {
            $("phone-toast").hidden = true;
        }, 4300);
    }
    /**
     * 输入：text。
     * 输出：无。
     * 功能：首页互动气泡短暂出现，不遮住卡片。
     */
    function homeBubble(text) {
        clearTimeout(homeBubbleTimer);
        const detail = BubbleCopy.render($("home-bubble"), text);
        if (detail) toast(detail);
        $("home-bubble").classList.add("visible");
        homeBubbleTimer = setTimeout(() => BubbleCopy.render($("home-bubble"), "home"), 4200);
    }
    /**
     * 输入：title、builder、onClose。
     * 输出：面板内容节点。
     * 功能：打开手机内操作面板，管理焦点和关闭回调。
     */
    function showSheet(title, builder, onClose = null) {
        timeRange?.close(false);
        closeSheet(false);
        board?.cancel();
        gesture?.disarm();
        sheetReturn = document.activeElement;
        state.sheetClose = onClose;
        $("sheet-title").textContent = title;
        $("sheet-body").replaceChildren();
        $("sheet-layer").hidden = false;
        builder?.($("sheet-body"));
        for (const child of $("screen").children)
            if (child !== $("sheet-layer") && child !== $("phone-toast"))
                child.inert = true;
        $("sheet-close").focus({ preventScroll: true });
        return $("sheet-body");
    }
    /**
     * 输入：restoreFocus。
     * 输出：无。
     * 功能：关闭面板、释放摄像头并恢复页面可访问性。
     */
    function closeSheet(restoreFocus = true) {
        const callback = state.sheetClose;
        state.sheetClose = null;
        callback?.();
        photo.stopCamera();
        cameraVideo = null;
        $("sheet-layer").hidden = true;
        for (const child of $("screen").children)
            child.inert = false;
        if (restoreFocus && sheetReturn?.isConnected && !sheetReturn.closest("[hidden]"))
            sheetReturn.focus({ preventScroll: true });
        sheetReturn = null;
    }
    /**
     * 输入：parent、text、name、action、danger。
     * 输出：按钮。
     * 功能：生成真正有操作的菜单项。
     */
    function sheetAction(parent, text, name, action, danger = false) {
        const b = el("button", "sheet-action" + (danger ? " danger" : ""));
        b.type = "button";
        b.innerHTML = icon(name);
        b.append(el("span", "", text));
        b.addEventListener("click", action);
        parent.append(b);
        return b;
    }
    /**
     * 输入：title、text、action。
     * 输出：无。
     * 功能：删除、停止、重置前提供明确确认。
     */
    function ask(title, text, action) {
        showSheet(title, b => {
            b.append(el("p", "sheet-text", text));
            const row = el("div", "sheet-buttons"), no = el("button", "", "取消"), yes = el("button", "solid", "确定");
            no.onclick = () => closeSheet();
            yes.onclick = () => {
                closeSheet(false);
                action();
            };
            row.append(no, yes);
            b.append(row);
        });
    }
    /**
     * 输入：scene、options。
     * 输出：无。
     * 功能：集中切页与资源清理，输入草稿保留，退出摄像头/录音。
     */
    function navigate(scene, options = {}) {
        timeRange?.close(false);
        if (animation.scene === "entry")
            preserveDraft();
        cancelWork(false);
        board?.cancel();
        closeSheet(false);
        closeSettings(false);
        bailianSettings?.close(false);
        photo.clear();
        animation.actor && (animation.actor.companionPet = 0);
        animation.setScene(scene, options.time || 0, true);
        $("screen").classList.remove("route-changing");
        if (!animation.reducedMotion && options.transition !== false) {
            void $("screen").offsetWidth;
            $("screen").classList.add("route-changing");
        }
        if (scene === "home") {
            board.update();
            updateHomeStats();
            homeBubble("home");
        }
        if (["history", "tasks", "profile"].includes(scene))
            renderPage(scene);
        synchronizeUI(animation);
    }
    /**
     * 输入：id、values、record（可选）。
     * 输出：无。
     * 功能：进入对应字段表单，绝不把其他类别的草稿串过来。
     */
    function openEntry(id, values = null, record = null) {
        if (id === "focus" && !values && !record && ["running", "paused", "resting"].includes(timer.state)) {
            navigate("focus");
            renderFocus();
            return;
        }
        if (animation.scene === "entry")
            preserveDraft();
        cancelWork(false);
        photo.clear();
        state.category = id;
        state.record = record;
        state.recordDate = record?.data?.recordDate || record?.data?.wakeDate || (record ? Sleep.dateKey(new Date(record.createdAt)) : Sleep.dateKey());
        state.sleepDates = id === "sleep" && record ? { bedDate: record.data.bedDate || Sleep.validDate(String(record.data.bedtime).split("T")[0]), wakeDate: record.data.wakeDate || Sleep.validDate(String(record.data.wakeTime).split("T")[0]) } : {};
        state.emotionDraft = null;
        state.taskId = null;
        state.estimated = Boolean(record?.estimated);
        state.source = "manual";
        const stored = values || state.drafts[id] || {};
        const initial = id === "sport" ? Catalog.sportData(stored) : stored;
        if (id === "sleep" && !record)
            state.sleepDates = { bedDate: initial.bedDate || "", wakeDate: initial.wakeDate || "" };
        renderForm(initial);
        navigate("entry");
        bubble(Catalog.category(id).greeting);
    }
    /**
     * 输入：无。
     * 输出：字段对象。
     * 功能：只读取当前类别已有的输入控件。
     */
    function rawForm() {
        const fields = Object.fromEntries(Catalog.category(state.category).fields.map(f => [f.key, $(`field-${f.key}`)?.value ?? ""]));
        return state.category === "sleep" ? { ...fields, ...state.sleepDates } : fields;
    }
    /**
     * 输入：无。
     * 输出：无。
     * 功能：切页前在内存保留草稿，不自动上传或当作记录。
     */
    function preserveDraft() {
        if ($("entry-form").dataset.category === state.category)
            state.drafts[state.category] = rawForm();
    }
    /**
     * 输入：fields、snapshot（请求开始版本）。
     * 输出：被保护字段数量。
     * 功能：允许 AI 回填但不覆盖请求期间用户的新修改。
     */
    function fillForm(fields, snapshot = null) {
        let protectedCount = 0;
        for (const f of Catalog.category(state.category).fields) {
            const input = $(`field-${f.key}`);
            if (!input || fields[f.key] == null || fields[f.key] === "")
                continue;
            if (snapshot && snapshot[f.key] !== state.versions[f.key]) {
                protectedCount++;
                continue;
            }
            input.value = f.type === "time" ? Sleep.clock(fields[f.key]) : String(fields[f.key]);
            updateFieldDisplay(f, input);
            input.setAttribute("aria-invalid", "false");
        }
        timeRange?.sync();
        formLayout?.schedule();
        preserveDraft();
        return protectedCount;
    }
    /**
     * 输入：field、input。
     * 输出：无。
     * 功能：餐次选择状态跟随真实表单值；情绪和睡眠感受不再使用选项。
     */
    function updateFieldDisplay(field, input) {
        if (field.type === "choice")
            input.parentElement.querySelectorAll(".choice-pill").forEach(b => {
                b.classList.toggle("selected", b.dataset.value === input.value);
                b.setAttribute("aria-pressed", String(b.dataset.value === input.value));
            });
    }
    /**
     * 输入：field、value。
     * 输出：一项表单。
     * 功能：统一全宽字段、预设单位、范围、选择及最长字数。
     */
    function makeField(field, value) {
        const label = el("label", "field"), head = el("span", "field-header"), name = el("span", "", field.label);
        label.dataset.field = field.key;
        head.append(name);
        label.append(head);
        const input = el(field.type === "textarea" ? "textarea" : "input");
        if (field.type === "textarea") {
            label.classList.add("field-long");
            input.rows = 3;
        }
        input.id = `field-${field.key}`;
        input.name = field.key;
        input.autocomplete = "off";
        input.value = field.type === "time" && value ? Sleep.clock(value) : value ?? field.initial ?? "";
        input.setAttribute("aria-label", field.label);
        if (field.max)
            input.maxLength = field.max;
        if (field.required)
            input.required = true;
        input.placeholder = field.placeholder || "";
        if (field.type === "choice") {
            input.type = "hidden";
            label.append(input);
            const choices = el("span", "choice-group");
            choices.setAttribute("role", "group");
            choices.setAttribute("aria-label", field.label);
            field.options.forEach(value => {
                const b = el("button", "choice-pill", value);
                b.type = "button";
                b.dataset.value = value;
                b.onclick = () => {
                    input.value = value;
                    input.dispatchEvent(new Event("input", { bubbles: true }));
                };
                choices.append(b);
            });
            label.append(choices);
        }
        else {
            if (field.type !== "textarea")
                input.type = field.type === "time" ? "time" : "text";
            if (field.type === "time") {
                input.step = "60";
                input.setAttribute("aria-description", "24小时制，只需要时和分");
            }
            if (field.type === "decimal") {
                input.inputMode = "decimal";
                input.maxLength = 16;
            }
            if (field.unit) {
                const wrap = el("span", "input-wrap");
                wrap.append(input, el("span", "unit", field.unit));
                label.append(wrap);
            }
            else
                label.append(input);
        }
        if (field.estimate) {
            const b = el("button", "estimate-time", "让小猫估时");
            b.type = "button";
            b.onclick = estimateTime;
            head.append(b);
        }
        input.addEventListener("input", () => {
            state.versions[field.key] = (state.versions[field.key] || 0) + 1;
            input.setAttribute("aria-invalid", "false");
            // 手动修改任一睡眠时刻后重新推导跨天，不能沿用AI曾猜的另一天。
            if (state.category === "sleep" && ["bedtime", "wakeTime"].includes(field.key))
                state.sleepDates = {};
            updateFieldDisplay(field, input);
            preserveDraft();
        });
        updateFieldDisplay(field, input);
        return label;
    }
    /**
     * 输入：values（草稿）。
     * 输出：无。
     * 功能：按类别构建字段，饮食/面部额外提供真实相机与选择照片入口。
     */
    function renderForm(values = {}) {
        // 阶段一：读取类别并清理上一个表单，不清理其他类别草稿。
        const def = Catalog.category(state.category), form = $("entry-form");
        timeRange?.destroy();
        timeRange = null;
        formLayout?.destroy();
        formLayout = null;
        form.replaceChildren();
        form.dataset.category = state.category;
        state.versions = {};
        $("entry-panel").scrollTop = 0;
        $("entry-heading").querySelector("h1").textContent = def.title;
        // 阶段二：照片相关入口仅给饮食/面部；点击分析前不联网。
        if (def.photo) {
            const preview = el("div", "photo-preview");
            preview.id = "photo-preview";
            preview.setAttribute("aria-label", "照片预览框");
            form.append(preview);
            const tools = el("div", "photo-tools");
            for (const [title, name, action] of [["拍照", "camera", openCamera], ["选择照片", "photo", () => $("photo-library").click()]]) {
                const b = el("button", "photo-tool");
                b.type = "button";
                b.innerHTML = icon(name);
                b.append(el("span", "", title));
                b.onclick = action;
                tools.append(b);
            }
            form.append(tools);
            const analyze = el("button", "analyze-photo");
            analyze.type = "button";
            analyze.id = "analyze-photo";
            analyze.hidden = true;
            analyze.innerHTML = icon("sparkle");
            analyze.append(el("span", "", "让小猫看看"));
            analyze.onclick = analyzePhoto;
            form.append(analyze);
            showPhoto(null);
        }
        // 阶段三：主字段与可折叠营养字段使用同一校验定义。
        const note = el("div", "ai-draft-note");
        note.id = "draft-note";
        note.hidden = true;
        form.append(note);
        const mainFields = def.fields.filter(f => !f.group && !(def.photo && f.key === "notes"));
        mainFields.forEach(f => {
            state.versions[f.key] = 0;
            if (state.category === "sleep" && f.key === "bedtime") {
                timeRange = new TimeRangePicker($("screen"), values, key => {
                    state.versions[key] = (state.versions[key] || 0) + 1;
                    state.sleepDates = {};
                    preserveDraft();
                });
                form.append(timeRange.element);
            } else if (!(state.category === "sleep" && f.key === "wakeTime")) {
                form.append(makeField(f, values[f.key]));
            }
        });
        if (def.fields.some(f => f.group)) {
            const details = el("details", "nutrition-details"), summary = el("summary", "", "营养信息 · 估算"), grid = el("div", "nutrition-fields");
            details.append(summary, grid);
            details.open = true;
            def.fields.filter(f => f.group).forEach(f => {
                state.versions[f.key] = 0;
                grid.append(makeField(f, values[f.key]));
            });
            form.append(details);
        }
        if (def.photo) {
            const last = def.fields.find(f => f.key === "notes");
            if (last) {
                state.versions[last.key] = 0;
                form.append(makeField(last, values[last.key]));
            }
        }
        formLayout = new FormLayout($("entry-panel"), form);
        $("speech-transcript").textContent = `说说今天的${def.name}吧。`;
    }
    /**
     * 输入：errors。
     * 输出：无。
     * 功能：只在提交时标记无效字段。
     */
    function showErrors(errors = {}) {
        for (const f of Catalog.category(state.category).fields)
            $(`field-${f.key}`)?.setAttribute("aria-invalid", String(Boolean(errors[f.key])));
        timeRange?.sync();
    }
    /**
     * 输入：无。
     * 输出：规范化字段或 null。
     * 功能：确认前检查必需项；焦点定位错误而不显示一屏说明。
     */
    function checkedForm() {
        const checked = Catalog.validate(state.category, rawForm(), true, { recordDate: state.recordDate });
        showErrors(checked.errors);
        if (!checked.ok) {
            const key = Object.keys(checked.errors)[0];
            bubble(checked.errors[key], true);
            const input = $(`field-${key}`);
            if (state.category === "sleep" && ["bedtime", "wakeTime"].includes(key)) {
                timeRange?.element.scrollIntoView({ block: "nearest" });
                timeRange?.focus(key);
            } else {
                input?.scrollIntoView({ block: "nearest" });
                input?.focus({ preventScroll: true });
            }
            return null;
        }
        return checked.value;
    }
    /**
     * 输入：data、source。
     * 输出：不可变记录快照。
     * 功能：动画绑定本次确认的数据，实际保存时去掉视图字段。
     */
    function snapshot(data, source = "manual") {
        const r = {
            id: state.record?.id || (crypto.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`), category: state.category, data: { ...data }, createdAt: state.record?.createdAt || new Date().toISOString(), source, estimated: state.estimated
        };
        r.displayRows = Catalog.rows(r);
        return Object.freeze(r);
    }
    /**
     * 输入：无。
     * 输出：无。
     * 功能：普通记录先书写后庆祝，专注先真实倒计时，不颠倒流程。
     */
    function confirmManual() {
        // 整理期间表单仍可编辑；短按同一按钮可取消，不丢失用户填写。
        if (state.phase === "thinking") {
            cancelWork(true);
            return;
        }
        if (state.phase !== "idle" || animation.scene !== "entry" || !animation.ready)
            return;
        const data = checkedForm();
        if (!data)
            return;
        state.record = snapshot(data, state.source);
        preserveDraft();
        cancelWork(false);
        document.activeElement?.blur();
        if (state.category === "focus") {
            beginFocus(state.record);
            return;
        }
        animation.setRecord(state.record);
        navigate("record", { transition: false });
    }
    /**
     * 输入：无。
     * 输出：无。
     * 功能：记录书写后继续才保存；庆祝结束返回首页，不再次创建记录。
     */
    function primaryAction() {
        if ($("primary").disabled)
            return;
        if (animation.scene === "record") {
            if (!Store.save(state.record)) {
                toast("本机暂时无法保存，记录仍在当前页面。");
                return;
            }
            state.drafts[state.category] = {};
            photo.clear();
            animation.saved = true;
            animation.actor.companionPet = 0;
            navigate("celebrate");
        }
        else if (animation.scene === "celebrate") {
            state.record = null;
            navigate("home");
            homeBubble("记下来了，今天也辛苦啦。");
        }
    }
    /**
     * 输入：无。
     * 输出：无。
     * 功能：书写过程中返回同一条记录编辑，而不是清空用户输入。
     */
    function editRecord() {
        const r = state.record;
        if (r)
            openEntry(r.category, r.data, r);
    }
    /**
     * 输入：phase。
     * 输出：无。
     * 功能：角色的倾听/思考连续追踪实际请求状态。
     */
    function setPhase(phase) {
        state.phase = phase;
        animation.entryMode = phase === "thinking" ? "thinking" : ["listening", "requesting"].includes(phase) ? "listening" : "idle";
        $("confirm-entry").classList.toggle("holding", phase === "listening");
        $("confirm-entry").dataset.pending = String(phase === "thinking");
        $("voice-overline").textContent = phase === "thinking" ? "小猫正在整理" : phase === "requesting" ? "等待麦克风" : "正在听你说";
        $("voice-hint").textContent = phase === "thinking" ? "整理好后，你可以修改每个字段" : "松开，交给我整理";
        animation.render();
    }
    /**
     * 输入：announce。
     * 输出：无。
     * 功能：取消所有迟到请求并释放麦克风；用户草稿保持不变。
     */
    function cancelWork(announce = true) {
        state.serial++;
        state.task?.abort();
        state.task = null;
        speech.cancel();
        rawAudio.cancel();
        animation.level = 0;
        wave = Array(72).fill(0);
        state.phase = "idle";
        animation.entryMode = "idle";
        if (animation.scene === "entry") {
            setPhase("idle");
            if (announce)
                bubble("已取消，填过的内容还在。");
        }
    }
    /**
     * 输入：无。
     * 输出：Promise<void>。
     * 功能：首次先授权、下次实际长按收音，不把权限弹窗失焦当作取消授权。
     */
    async function beginSpeech() {
        if (animation.scene !== "entry" || state.phase !== "idle")
            return;
        const useAudio = bailian.configured;
        if (state.category === "mood" && !useAudio) {
            bubble("先启用百炼，让我听懂话里的语气。", true);
            bailianSettings.open();
            return;
        }
        if (!useAudio && !api.configured) {
            bubble("先在右上角启用一个 AI 服务。", true);
            openSettings();
            return;
        }
        activeSpeech = useAudio ? rawAudio : speech;
        state.voiceBackend = useAudio ? "audio" : "text";
        if (!activeSpeech.supported()) {
            bubble(useAudio ? "浏览器暂不能录音，可以直接填写。" : "语音转写不可用，可启用百炼直接听录音。", true);
            return;
        }
        cancelWork(false);
        const serial = state.serial;
        setPhase("requesting");
        try {
            const permission = await microphone.status();
            if (serial !== state.serial)
                return;
            if (permission !== "granted") {
                gesture.disarm();
                setPhase("authorizing");
                if (permission === "denied")
                    throw Error("请在地址栏的网站权限里允许麦克风。");
                bubble("请先允许麦克风。");
                await microphone.authorize();
                if (serial !== state.serial)
                    return;
                setPhase("idle");
                bubble("准备好了，长按开始说话。");
                return;
            }
            if (!gesture.pressed) {
                cancelWork(false);
                return;
            }
            state.voiceVersions = { ...state.versions };
            wave = Array(72).fill(0);
            $("speech-transcript").textContent = `说说今天的${Catalog.category(state.category).name}吧。`;
            await activeSpeech.start({ language: CONFIG.speechLanguage, maximumSeconds: CONFIG.maximumSpeechSeconds });
        }
        catch (error) {
            if (serial === state.serial)
                voiceFailed(error.name === "NotAllowedError" ? "麦克风没有被允许。" : error.message);
        }
    }
    /**
     * 输入：无。
     * 输出：无。
     * 功能：真实识别器启动之后才显示正在倾听。
     */
    function listeningStarted() {
        if (state.phase === "requesting") {
            setPhase("listening");
            bubble("嗯，我在听。");
        }
    }
    /**
     * 输入：level、history。
     * 输出：无。
     * 功能：以真实 RMS 驱动波形和猫耳，不伪造音量。
     */
    function audioLevel(level, history) {
        animation.level = level;
        wave = history.slice();
    }
    /**
     * 输入：text。
     * 输出：无。
     * 功能：展示真实转写。
     */
    function receivedSpeech(text) {
        $("speech-transcript").textContent = text || "慢慢说，我在听。";
    }
    /**
     * 输入：message。
     * 输出：无。
     * 功能：故障时释放资源并保留输入，绝不回填演示数据。
     */
    function voiceFailed(message) {
        cancelWork(false);
        bubble(message, true);
    }
    /**
     * 输入：无。
     * 输出：Promise<void>。
     * 功能：松手后终止录音，实际整理成可修改草稿，等待用户确认。
     */
    async function releaseSpeech() {
        if (state.phase === "authorizing")
            return;
        if (state.phase === "requesting") {
            cancelWork(false);
            return;
        }
        if (state.phase !== "listening")
            return;
        const serial = state.serial, version = { ...state.voiceVersions }, id = state.category, recordDate = state.recordDate, session = activeSpeech;
        setPhase("thinking");
        bubble("听到了，我整理一下。");
        try {
            const result = await session.stop();
            animation.level = 0;
            if (serial !== state.serial || result.canceled)
                return;
            if (!result.text && !result.audio)
                throw Error("没有听清，长按再说一次吧。");
            const controller = state.task = new AbortController();
            const draft = result.audio ? await AI.extractAudio(bailian, id, result.audio, JSON.stringify(rawForm()), controller.signal, { recordDate }) : await AI.extract(api, id, result.text, null, controller.signal, { recordDate });
            // 接口完成即释放本次原始音频引用，历史记录只存用户确认的字段。
            result.audio = null;
            if (serial !== state.serial || id !== state.category)
                return;
            state.task = null;
            state.source = "voice";
            state.estimated = draft.estimated;
            const protectedCount = fillForm(draft.fields, version);
            if (id === "sleep" && version.bedtime === state.versions.bedtime && version.wakeTime === state.versions.wakeTime)
                state.sleepDates = draft.sleepDates || {};
            state.emotionDraft = draft.emotion || null;
            if (protectedCount)
                draft.warnings.push("已保留你刚才手动修改的内容。");
            setPhase("idle");
            showDraft(draft.warnings);
            bubble("写在框里了，确认后交给我记录。");
        }
        catch (e) {
            if (serial === state.serial && e.name !== "AbortError")
                voiceFailed(e.message);
        }
    }
    /**
     * 输入：warnings。
     * 输出：无。
     * 功能：只在 AI 回填后提示核对；未知营养不伪装成精确数据。
     */
    function showDraft(warnings = []) {
        const note = $("draft-note");
        // 专注页不显示成功说明面板；真实异常或须核对信息仍用短暂提示告知。
        if (state.category === "focus") {
            if (note) { note.hidden = true; note.textContent = ""; }
            if (warnings.length) toast(warnings.join(" "));
            return;
        }
        if (note) {
            note.hidden = false;
            note.textContent = warnings.length ? warnings.join(" ") : "整理好了，请核对。";
            $("entry-panel").scrollTop = 0;
        }
    }
    /**
     * 输入：无。
     * 输出：Promise<void>。
     * 功能：按任务估时，保护用户在请求期间改过的分钟数。
     */
    async function estimateTime() {
        if (state.phase !== "idle")
            return;
        if (!api.configured) {
            openSettings();
            return;
        }
        const data = rawForm();
        if (!data.task.trim()) {
            bubble("先写下想做的事情。", true);
            return;
        }
        const serial = ++state.serial, version = { ...state.versions }, controller = state.task = new AbortController();
        bubble("让我把时间估得实际一点。");
        try {
            const result = await AI.estimate(api, data.task, data.notes || "", controller.signal);
            if (serial !== state.serial || state.category !== "focus")
                return;
            fillForm({ durationMinutes: result.minutes }, version);
            // 保留可修改分钟数，但不插入黄色说明，也不自动启动专注。
            const note = $("draft-note");
            note.hidden = true;
            note.textContent = "";
            bubble("estimated");
        }
        catch (e) {
            if (serial === state.serial && e.name !== "AbortError")
                bubble(e.message, true);
        }
        finally {
            if (serial === state.serial)
                state.task = null;
        }
    }
    /**
     * 输入：image（经过重编码的 JPEG）。
     * 输出：无。
     * 功能：显示照片缩略图，尚不上传；等待用户主动点分析。
     */
    function showPhoto(image) {
        const preview = $("photo-preview");
        if (!preview)
            return;
        preview.replaceChildren();
        preview.hidden = false;
        preview.classList.toggle("has-image", Boolean(image));
        $("analyze-photo").hidden = !image;
        if (!image) {
            preview.style.height = state.category === "face" ? "165px" : "96px";
            formLayout?.schedule();
            const placeholder = el("span", "photo-empty");
            placeholder.innerHTML = icon("photo");
            placeholder.append(el("span", "", "等待照片"));
            preview.append(placeholder);
            return;
        }
        const img = el("img");
        img.alt = state.category === "face" ? "本次面部照片" : "本次食物照片";
        /**
         * 输入：无。
         * 输出：无。
         * 功能：按容器可用宽度等比展示整张照片，竖图不裁切或拉伸。
         */
        function fitPhoto() {
            if (img.isConnected && img.naturalWidth)
                preview.style.height = `${preview.clientWidth * img.naturalHeight / img.naturalWidth}px`;
        }
        img.onload = fitPhoto;
        img.src = image;
        const clear = el("button", "photo-remove", "移除");
        clear.type = "button";
        clear.setAttribute("aria-label", "移除照片");
        clear.onclick = () => { cancelWork(false); photo.clear(); showPhoto(null); };
        preview.append(img, clear);
        requestAnimationFrame(fitPhoto);
    }
    /**
     * 输入：无。
     * 输出：Promise<void>。
     * 功能：请求相机预览，支持明确拍摄/取消；离开立即停止所有轨道。
     */
    async function openCamera() {
        const id = state.category;
        let status;
        showSheet("拍一张照片", b => {
            cameraVideo = el("video", "camera-video");
            cameraVideo.autoplay = true;
            cameraVideo.muted = true;
            cameraVideo.playsInline = true;
            b.append(cameraVideo);
            status = el("p", "camera-status", "正在等待摄像头…");
            b.append(status);
            const row = el("div", "sheet-buttons");
            const capture = el("button", "solid", "拍下这一张"), pick = el("button", "", "选择照片");
            capture.onclick = () => {
                try {
                    const image = photo.capture(cameraVideo);
                    closeSheet();
                    showPhoto(image);
                }
                catch (e) {
                    status.textContent = e.message;
                }
            };
            pick.onclick = () => {
                closeSheet();
                $("photo-library").click();
            };
            row.append(pick, capture);
            b.append(row);
        }, () => photo.stopCamera());
        try {
            const started = await photo.openCamera(cameraVideo, id === "face");
            if (started && id === state.category)
                status.textContent = "";
        }
        catch (e) {
            if (!$("sheet-layer").hidden)
                status.textContent = e.name === "NotAllowedError" ? "摄像头未获允许，也可以选择照片。" : e.message;
        }
    }
    /**
     * 输入：无。
     * 输出：Promise<void>。
     * 功能：用户明确分析后才实际发照片；结果是可改估计/观察，不作医疗判断。
     */
    async function analyzePhoto() {
        if (!photo.image || state.phase !== "idle")
            return;
        if (!bailian.configured) {
            bailianSettings.open();
            return;
        }
        const image = photo.image, id = state.category, version = { ...state.versions }, text = JSON.stringify(rawForm()), serial = ++state.serial, controller = state.task = new AbortController();
        setPhase("thinking");
        $("speech-transcript").textContent = "我正在看照片，也会参考你填写的内容。";
        bubble("我看看，再一起核对。");
        try {
            const draft = await AI.extract(bailian, id, text, image, controller.signal, { recordDate: state.recordDate });
            if (serial !== state.serial || id !== state.category || photo.image !== image)
                return;
            fillForm(draft.fields, version);
            state.source = "photo";
            state.estimated = draft.estimated;
            setPhase("idle");
            showDraft(draft.warnings);
            bubble("只记下看得清的部分，你再看看。");
        }
        catch (e) {
            if (serial === state.serial && e.name !== "AbortError") {
                setPhase("idle");
                bubble(e.message, true);
            }
        }
        finally {
            if (serial === state.serial)
                state.task = null;
        }
    }
    /**
     * 输入：record。
     * 输出：无。
     * 功能：专注以已确认任务和时长开始，待办完成与计时完成分别保存。
     */
    function beginFocus(record) {
        if (["running", "paused", "resting"].includes(timer.state)) {
            toast("已有一段专注正在进行，先回到它吧。");
            navigate("focus");
            return;
        }
        state.focusRecord = { ...record, taskId: state.taskId };
        state.timerNotified = false;
        timer.start(record.data.durationMinutes);
        persistFocus();
        lastTimerText = "";
        navigate("focus");
        renderFocus();
    }
    /**
     * 输入：无。
     * 输出：无。
     * 功能：只保存计时数据，不保存照片、API Key、音频。
     */
    function persistFocus() {
        if (state.focusRecord)
            Store.write("fluffy-active-focus-v1", { record: state.focusRecord, timer: timer.snapshot() });
    }
    /**
     * 输入：无。
     * 输出：无。
     * 功能：只更新变化的秒值，后台恢复按绝对时钟结算。
     */
    function renderFocus() {
        const s = timer.tick();
        if (animation.scene !== "focus")
            return;
        const text = formatTimer(s.remainingMs);
        if (text !== lastTimerText) {
            $("timer-time").textContent = text;
            lastTimerText = text;
        }
        $("focus-task").textContent = state.focusRecord?.data.task || "留一点时间给自己";
        $("focus-state").textContent = ({
            running: "安静地，专注当下", paused: "暂停了，不着急", resting: "休息一下，时间为你停留", completed: "这一段时间，认真度过了", stopped: "这一段专注已结束"
        })[s.state] || "准备开始";
        $("timer-caption").textContent = s.state === "resting" ? `休息 ${formatTimer(s.restMs + Math.max(0, Date.now() - s.restStarted))}` : "剩余专注时间";
        $("ring-progress").style.strokeDashoffset = String(885.929 * (1 - s.remainingMs / Math.max(1, s.totalMs)));
        const paused = s.state !== "running";
        $("pause-label").textContent = paused ? "继续" : "暂停";
        $("timer-pause").setAttribute("aria-label", paused ? "继续" : "暂停");
        setIcon($("timer-pause").firstElementChild, paused ? "play" : "pause");
        $("timer-rest").disabled = s.state === "resting";
        animation.focusRestTarget = paused ? 1 : 0;
    }
    /**
     * 输入：无。
     * 输出：无。
     * 功能：定期检查真正的截止时间；不因动画暂停或浏览器掉帧漏算。
     */
    function checkFocus() {
        const s = timer.tick();
        if (animation.scene === "home" && ["running", "paused", "resting"].includes(s.state)) {
            const b = board?.cards.get("focus");
            if (b) {
                b.querySelector(".widget-value").textContent = formatTimer(s.remainingMs);
                b.querySelector(".widget-sub").textContent = s.state === "running" ? "正在专注" : s.state === "resting" ? "休息中" : "已暂停";
            }
        }
        if (["running", "paused", "resting"].includes(s.state) && Date.now() - lastFocusSave > 5000) {
            persistFocus();
            lastFocusSave = Date.now();
        }
        if (s.state === "completed" && state.focusRecord && !state.timerNotified)
            finishFocus();
        if (animation.scene === "focus")
            renderFocus();
    }
    /**
     * 输入：无。
     * 输出：无。
     * 功能：实际结束后保存一次，再庆祝；不自动把待办勾选完成。
     */
    function finishFocus() {
        if (state.timerNotified || !state.focusRecord)
            return;
        const s = timer.stop();
        state.timerNotified = true;
        state.record = { ...state.focusRecord, focus: {
                elapsedMs: s.elapsedMs, restMs: s.restMs, plannedMs: s.totalMs, reachedTarget: s.state === "completed", taskCompleted: false
            } };
        if (!Store.save(state.record)) {
            state.timerNotified = false;
            toast("暂时无法保存专注记录，当前会话仍在。");
            return;
        }
        Store.write("fluffy-active-focus-v1", null);
        animation.setRecord(state.record);
        animation.saved = true;
        navigate("celebrate");
    }
    /**
     * 输入：无。
     * 输出：无。
     * 功能：把当前有效任务放入待办而不是假装已完成。
     */
    function saveTaskLater() {
        const data = checkedForm();
        if (!data)
            return;
        const task = {
            id: state.taskId || crypto.randomUUID?.() || String(Date.now()), data, createdAt: new Date().toISOString(), done: false
        };
        if (!Store.saveTask(task)) {
            toast("暂时无法保存待办。");
            return;
        }
        state.drafts.focus = {};
        navigate("tasks");
        toast("放进待办了，准备好再开始。");
    }
    /**
     * 输入：无。
     * 输出：无。
     * 功能：用真实记录数更新顶栏及本地日期，不显示虚假分数。
     */
    function updateHomeStats() {
        const stats = Store.stats();
        $("today-count").textContent = `${stats.today} / 6`;
        $("days-count").textContent = stats.days;
        $("home-date").textContent = new Date().toLocaleDateString("zh-CN", { month: "long", day: "numeric", weekday: "long" });
    }
    /**
     * 输入：无。
     * 输出：无。
     * 功能：提供恢复布局与查看记录，所有操作都在手机内部。
     */
    function homeMenu() {
        showSheet("今天的小空间", b => {
            sheetAction(b, "查看所有手记", "history", () => navigate("history"));
            sheetAction(b, "看看待办", "tasks", () => navigate("tasks"));
            sheetAction(b, "恢复首页排列", "reset", () => {
                board.reset();
                closeSheet();
                toast("卡片已放回原来的位置。");
            });
            sheetAction(b, "偏好与本机数据", "profile", () => navigate("profile"));
        });
    }
    /**
     * 输入：无。
     * 输出：无。
     * 功能：显示六类真实记录汇总，不以日记覆盖旧运动历史。
     */
    function renderHistory() {
        const root = $("inner-page");
        root.replaceChildren(el("p", "page-kicker", "LITTLE MOMENTS"), el("h1", "page-title", "我的手记"), el("p", "page-sub", "每一个认真生活的片刻，都在这里。"));
        const filter = el("div", "category-filter");
        for (const [id, name] of [["all", "全部"], ...Object.entries(Catalog.CATEGORIES).map(([id, c]) => [id, c.name])]) {
            const b = el("button", state.filter === id ? "active" : "", name);
            b.onclick = () => {
                state.filter = id;
                renderHistory();
            };
            filter.append(b);
        }
        root.append(filter);
        const list = Store.records().filter(r => state.filter === "all" || r.category === state.filter);
        if (!list.length) {
            const empty = el("div", "empty-state");
            empty.innerHTML = icon("history");
            empty.append(el("p", "", "还没有手记。\n从首页选一个入口，记下今天吧。"));
            root.append(empty);
            return;
        }
        let day = "";
        for (const r of list) {
            const d = Store.dayKey(new Date(r.createdAt));
            if (d !== day) {
                root.append(el("h2", "history-day", d));
                day = d;
            }
            const c = Catalog.category(r.category), s = Catalog.summary(r), b = el("button", "history-item"), badge = el("span", "category-badge"), copy = el("span", "history-copy");
            badge.innerHTML = icon(c.icon);
            copy.append(el("strong", "", c.name + " · " + s.value), el("span", "", s.sub));
            b.append(badge, copy, el("small", "", new Date(r.createdAt).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false })));
            b.onclick = () => recordDetails(r);
            root.append(b);
        }
    }
    /**
     * 输入：record。
     * 输出：无。
     * 功能：完整显示确认过的字段，营养估值和自评注明来源。
     */
    function recordDetails(record) {
        showSheet(Catalog.category(record.category).name + "手记", b => {
            const dl = el("dl");
            for (const f of Catalog.category(record.category).fields) {
                const v = record.data[f.key];
                if (v == null || v === "")
                    continue;
                const row = el("div", "detail-row");
                row.append(el("dt", "", f.label), el("dd", "", `${v}${f.unit ? " " + f.unit : ""}`));
                dl.append(row);
            }
            b.append(dl);
            if (record.focus) {
                const p = el("p", "detail-note", `实际专注 ${Math.round(record.focus.elapsedMs / 6000) / 10} 分钟；休息 ${Math.round(record.focus.restMs / 6000) / 10} 分钟。计时结束不等于任务完成。`);
                b.append(p);
            }
            if (record.category === "food")
                b.append(el("p", "detail-note", "营养是估算，不是精确测量；以补充的份量与实际标签为准。"));
            if (record.category === "face")
                b.append(el("p", "detail-note", "外观观察受光照与角度影响；不代表实际疲劳或医学诊断。"));
            if (record.category !== "focus")
                sheetAction(b, "修改这条记录", "edit", () => {
                    closeSheet(false);
                    openEntry(record.category, record.data, record);
                });
            else
                sheetAction(b, "再专注一次", "focus", () => {
                    closeSheet(false);
                    openEntry("focus", record.data);
                });
            sheetAction(b, "删除这条记录", "trash", () => ask("删除这条手记？", "只删除这一条，其他记录保留。", () => {
                if (Store.remove(record.id)) {
                    renderHistory();
                    board.update();
                    updateHomeStats();
                }
                else
                    toast("删除失败，记录仍保留。");
            }), true);
        });
    }
    /**
     * 输入：无。
     * 输出：无。
     * 功能：展示可继续执行的待办，完成状态由用户自己勾选。
     */
    function renderTasks() {
        const root = $("inner-page");
        root.replaceChildren(el("p", "page-kicker", "ONE THING AT A TIME"), el("h1", "page-title", "慢慢做，一件件来"), el("p", "page-sub", "不必一次做完所有事。"));
        const add = el("button", "task-add");
        add.innerHTML = icon("focus");
        add.append(el("span", "", "新增一件待办"));
        add.onclick = () => openEntry("focus");
        root.append(add);
        const tasks = Store.tasks();
        if (!tasks.length)
            root.append(el("div", "empty-state", "待办还是空的。\n先写下想专注的一件小事。"));
        for (const task of tasks) {
            const box = el("article", "task-card" + (task.done ? " done" : ""));
            box.append(el("h3", "", task.data.task), el("small", "", `预计 ${task.data.durationMinutes} 分钟`));
            const row = el("div", "task-actions"), start = el("button", "", "开始专注"), done = el("button", "", task.done ? "标记未完成" : "标记完成"), remove = el("button", "", "删除");
            start.onclick = () => {
                openEntry("focus", task.data);
                state.taskId = task.id;
            };
            done.onclick = () => {
                if (Store.saveTask({ ...task, done: !task.done }))
                    renderTasks();
            };
            remove.onclick = () => ask("删除这件待办？", task.data.task, () => {
                Store.removeTask(task.id);
                renderTasks();
            });
            row.append(start, done, remove);
            box.append(row);
            root.append(box);
        }
    }
    /**
     * 输入：filename、value。
     * 输出：无。
     * 功能：导出用户主动请求的 JSON，绝不包含 Key、音频或照片。
     */
    function downloadJSON(filename, value) {
        const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: "application/json" })), a = el("a");
        a.href = url;
        a.download = filename;
        document.body.append(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
    }
    /**
     * 输入：无。
     * 输出：无。
     * 功能：在手机内部管理偏好与本机记录，不加外部调试菜单。
     */
    function renderProfile() {
        const root = $("inner-page"), s = Store.stats();
        root.replaceChildren(el("p", "page-kicker", "A LITTLE PROGRESS, TOGETHER"), el("h1", "page-title", "这段日子，有你"), el("p", "page-sub", "认真照顾自己的每一天。"));
        const grid = el("div", "profile-stats");
        for (const [n, t] of [[s.days, "天有记录"], [s.count, "条手记"], [s.minutes, "分钟专注"]]) {
            const item = el("div", "profile-stat");
            item.append(el("strong", "", String(n)), el("span", "", t));
            grid.append(item);
        }
        root.append(grid);
        for (const [text, name, action, danger] of [
            [animation.reducedMotion ? "轻柔动效 · 已开启" : "轻柔动效", "leaf", () => {
                    animation.reducedMotion = !animation.reducedMotion;
                    document.body.classList.toggle("reduce-motion", animation.reducedMotion);
                    Store.write("fluffy-reduced-motion", animation.reducedMotion);
                    renderProfile();
                }],
            ["恢复首页布局", "reset", () => {
                    board.reset();
                    toast("布局已恢复。");
                }],
            ["导出我的记录", "export", () => downloadJSON("Fluffy-Cat-My-Journal.json", { version: 1, records: Store.records(), tasks: Store.tasks() })],
            ["API 设置", "sparkle", () => openSettings()],
            ["清除本机手记", "trash", () => ask("清除本机手记？", "这会清除当前浏览器里的手记和待办，不影响 GitHub 源码。建议先导出。", () => {
                    const ok = Store.write(Store.KEY, []) && Store.write(Store.TASKS_KEY, []);
                    if (ok) {
                        localStorage.removeItem("fluffy-cat-minimal-records-v1");
                        renderProfile();
                        board.update();
                        updateHomeStats();
                    }
                    else
                        toast("清除未完成。");
                }), true]
        ]) {
            const b = el("button", "setting-row" + (danger ? " danger" : ""));
            b.innerHTML = icon(name);
            b.append(el("span", "", text));
            const arrow = el("span", "arrow");
            arrow.innerHTML = icon("arrow");
            b.append(arrow);
            b.onclick = action;
            root.append(b);
        }
        root.append(el("p", "profile-foot", "记录保存在当前浏览器，不会自动同步到其他设备。照片只在本次页面内处理，不进入历史或 GitHub。"));
    }
    /**
     * 输入：scene。
     * 输出：无。
     * 功能：渲染底部导航对应的真实子页。
     */
    function renderPage(scene) {
        if (scene === "history")
            renderHistory();
        else if (scene === "tasks")
            renderTasks();
        else if (scene === "profile")
            renderProfile();
    }
    /**
     * 输入：无。
     * 输出：无。
     * 功能：中央对话入口选择类别并真实整理一段文字，或进入该类长按录音。
     */
    function chatSheet() {
        let selected = "sport";
        showSheet("今天，想讲些什么？", b => {
            const topics = el("div", "chat-topics");
            Object.entries(Catalog.CATEGORIES).forEach(([id, c]) => {
                const button = el("button", id === selected ? "active" : "");
                button.innerHTML = icon(c.icon);
                button.append(el("span", "", c.name));
                button.onclick = () => {
                    selected = id;
                    topics.querySelectorAll("button").forEach(n => n.classList.toggle("active", n === button));
                };
                topics.append(button);
            });
            b.append(topics);
            const input = el("textarea", "chat-input");
            input.placeholder = "例如：今天跑了 3 公里，20 分钟，感觉轻松。";
            input.maxLength = 1000;
            input.setAttribute("aria-label", "想对小猫说的话");
            b.append(input);
            const row = el("div", "sheet-buttons"), voice = el("button", "", "说给小猫听"), send = el("button", "solid", "交给小猫整理");
            voice.onclick = () => {
                closeSheet(false);
                openEntry(selected);
                bubble("长按底部按钮，我在听。");
            };
            send.onclick = async () => {
                const text = input.value.trim();
                if (!text) {
                    input.focus();
                    return;
                }
                if (!api.configured && !bailian.configured) {
                    openSettings();
                    return;
                }
                closeSheet(false);
                openEntry(selected);
                const serial = ++state.serial, controller = state.task = new AbortController();
                setPhase("thinking");
                $("speech-transcript").textContent = text;
                try {
                    const draft = await AI.extract(api.configured ? api : bailian, selected, text, null, controller.signal, { recordDate: state.recordDate });
                    if (serial !== state.serial)
                        return;
                    fillForm(draft.fields);
                    if (selected === "sleep")
                        state.sleepDates = draft.sleepDates || {};
                    state.emotionDraft = draft.emotion || null;
                    state.source = "text-ai";
                    state.estimated = draft.estimated;
                    setPhase("idle");
                    showDraft(draft.warnings);
                    bubble("整理好了，确认后我来写。");
                }
                catch (e) {
                    if (serial === state.serial && e.name !== "AbortError")
                        voiceFailed(e.message);
                }
            };
            row.append(voice, send);
            b.append(row);
        });
    }
    /**
     * 输入：无。
     * 输出：无。
     * 功能：保留外部极简下拉框，不回显已有 Key。
     */
    function openSettings() {
        if (!$("api-popover").hidden) {
            closeSettings();
            return;
        }
        cancelWork(false);
        bailianSettings?.close(false);
        gesture?.disarm();
        $("api-key").value = "";
        $("api-feedback").textContent = "";
        $("api-popover").hidden = false;
        $("open-settings").setAttribute("aria-expanded", "true");
        $("api-key").focus({ preventScroll: true });
    }
    /**
     * 输入：restoreFocus。
     * 输出：无。
     * 功能：关闭设置并取消未完成的验证，不破坏此前有效的 Key。
     */
    function closeSettings(restoreFocus = true) {
        state.keyTask?.abort();
        state.keyTask = null;
        state.keySerial++;
        $("api-popover").hidden = true;
        $("open-settings").setAttribute("aria-expanded", "false");
        $("api-key").value = "";
        $("save-api").disabled = false;
        $("save-api").textContent = "启用";
        if (restoreFocus)
            $("open-settings").focus({ preventScroll: true });
    }
    /**
     * 输入：event。
     * 输出：Promise<void>。
     * 功能：先验证候选 Key，再原子替换私有实例；失败保留旧 Key。
     */
    async function saveKey(event) {
        event.preventDefault();
        state.keyTask?.abort();
        const serial = ++state.keySerial, controller = state.keyTask = new AbortController(), candidate = new DeepSeekClient({ config: CONFIG, model: CONFIG.model }), key = $("api-key").value;
        $("api-feedback").textContent = "";
        try {
            candidate.setKey(key);
            $("save-api").disabled = true;
            $("save-api").textContent = "验证中…";
            const models = await candidate.check(controller.signal);
            if (serial !== state.keySerial || controller.signal.aborted)
                return;
            if (!models.includes(candidate.model))
                throw Error("当前 Key 暂时不能访问该模型。");
            api.setKey(key);
            $("key-indicator").classList.add("enabled");
            state.keyTask = null;
            closeSettings();
        }
        catch (e) {
            if (serial === state.keySerial && e.name !== "AbortError")
                $("api-feedback").textContent = e.message;
        }
        finally {
            candidate.clear();
            if (serial === state.keySerial) {
                state.keyTask = null;
                $("save-api").disabled = false;
                $("save-api").textContent = "启用";
            }
        }
    }
    /**
     * 输入：无。
     * 输出：无。
     * 功能：清除 Key 和当前请求，不删除用户记录。
     */
    function clearKey() {
        state.keyTask?.abort();
        state.keySerial++;
        cancelWork(false);
        api.clear();
        $("key-indicator").classList.remove("enabled");
        $("api-key").value = "";
        $("api-feedback").textContent = "";
        $("save-api").disabled = false;
        $("save-api").textContent = "启用";
    }
    /**
     * 输入：animation。
     * 输出：true。
     * 功能：统一管理真实界面的可见性；记录卡沿既有路径连续展开。
     */
    function synchronizeUI(a) {
        // 阶段一：页面级可见性，首页、表单和倒计时互斥。
        const scene = a.scene, home = scene === "home", entry = scene === "entry", record = scene === "record", hero = scene === "celebrate", inside = ["history", "tasks", "profile"].includes(scene), focus = scene === "focus", bridge = record && a.bridge ? M.range(a.time, 0, 1.55) : 1;
        $("screen").dataset.scene = scene;
        $("home-scene").hidden = !home;
        $("home-cat").hidden = !home;
        $("bottom-nav").hidden = !(home || inside);
        $("inner-page").hidden = !inside;
        $("focus-page").hidden = !focus;
        const quiet = ["idle", "authorizing", "thinking"].includes(state.phase);
        $("entry-panel").hidden = !entry || !quiet;
        $("voice-panel").hidden = !entry || quiet;
        $("entry-heading").hidden = !entry && !(record && a.bridge && bridge < .8);
        $("entry-heading").style.opacity = entry ? 1 : 1 - M.range(bridge, 0, .6);
        $("entry-bubble").hidden = !entry && !(record && a.bridge && bridge < .6);
        $("entry-bubble").style.opacity = entry ? 1 : 1 - M.range(bridge, 0, .55);
        // 阶段二：保留原来的表单到记录卡几何过渡，不替换整屏截图。
        $("green-bg").style.opacity = hero ? 1 : 0;
        $("record-card").hidden = !entry && !record;
        const p = entry ? 0 : bridge;
        $("record-card").style.top = `${M.mix(368, 414, p)}px`;
        $("record-card").style.left = `${M.mix(23, 20, p)}px`;
        $("record-card").style.width = `${M.mix(347, 353, p)}px`;
        $("record-card").style.height = `${M.mix(344, 304, p)}px`;
        $("record-card").style.borderRadius = `${M.mix(29, 45, p)}px`;
        $("record-heading").hidden = !record;
        $("record-heading").style.opacity = record ? M.range(a.time, .45, 1.5) : 0;
        $("hero-quote").hidden = !hero;
        $("hero-subtitle").hidden = !hero;
        $("back").hidden = home || inside || hero;
        $("primary").hidden = !(record || hero);
        $("confirm-entry").hidden = !entry;
        // 阶段三：按钮绑定真实阶段；书写与放笔结束后才可以庆祝。
        $("primary").classList.toggle("white", hero);
        $("primary").disabled = !a.ready || (hero ? a.time < 4.93 : record ? a.time < a.writeEnd + 3.5 : false);
        $("primary-label").textContent = hero ? "回到首页" : "继续";
        $("confirm-entry").disabled = !a.ready || ["authorizing"].includes(state.phase);
        $("confirm-label").textContent = ({
            idle: state.category === "focus" ? "开始专注" : "确认并继续", authorizing: "等待麦克风…", requesting: "等待麦克风…", listening: "松开结束", thinking: "停止整理"
        })[state.phase];
        $("hero-quote").style.opacity = M.range(a.time, 1.5, 2.5);
        $("hero-subtitle").style.opacity = M.range(a.time, .8, 1.5);
        $("pet").hidden = !(record || hero);
        $("pet").style.top = hero ? "371px" : "193px";
        $("pet").style.height = hero ? "248px" : "223px";
        $("edit-record").hidden = !record || a.time < 1.6;
        const phase = record ? (a.time < a.writeEnd ? 2 : a.time < a.writeEnd + 3.75 ? 3 : 4) : 0;
        if (record) {
            const title = phase === 2 ? `Log Your ${Catalog.category(state.record?.category || state.category).en}` : phase === 3 ? "Almost done!" : "All set! ♡";
            $("record-title").textContent = title;
            $("record-subtitle").textContent = phase === 2 ? "Write it down, step by step!" : phase === 3 ? "Putting it away…" : "Rest well, you did it.";
        }
        if (hero) {
            const isFocus = state.record?.category === "focus";
            $("hero-subtitle").textContent = isFocus ? "You made time for what matters." : "Another little moment, saved.";
            $("hero-quote").innerHTML = isFocus ? `专注了 ${Math.round((state.record.focus?.elapsedMs || 0) / 6000) / 10} 分钟。<br>每一点认真，都算数。` : "Small steps make<br>a stronger you.";
        }
        // 阶段四：同步可访问性文字与导航，不改动用户输入。
        document.querySelectorAll(".nav-item[data-nav]").forEach(b => {
            b.classList.toggle("active", b.dataset.nav === scene);
            if (b.dataset.nav === scene)
                b.setAttribute("aria-current", "page");
            else
                b.removeAttribute("aria-current");
        });
        if (record && a.lastA11yRecord !== a.record) {
            $("record-a11y").textContent = a.rows.map(r => `${r.label}: ${r.value}`).join("。");
            a.lastA11yRecord = a.record;
        }
        return true;
    }
    /**
     * 输入：无。
     * 输出：无。
     * 功能：波形读取真音量；思考使用不同的等待标记，不冒充输入。
     */
    function renderExtras() {
        if ($("voice-panel").hidden)
            return;
        const ctx = $("voice-wave").getContext("2d");
        ctx.setTransform(2, 0, 0, 2, 0, 0);
        ctx.clearRect(0, 0, 320, 105);
        if (state.phase === "thinking") {
            for (let i = 0; i < 3; i++) {
                ctx.fillStyle = `rgba(86,156,155,${.3 + .5 * (Math.sin(animation.idle * 3 - i * .8) + 1) / 2})`;
                ctx.beginPath();
                ctx.arc(143 + i * 17, 52, 3.5, 0, Math.PI * 2);
                ctx.fill();
            }
            return;
        }
        const colors = ["#8bcbb7", "#84b7d6", "#a5c9bc", "#d8c48f"];
        ctx.lineWidth = 2.6;
        ctx.lineCap = "round";
        wave.forEach((v, i) => {
            const h = 2 + v * 78, x = 13 + i * 4.1;
            ctx.strokeStyle = colors[Math.floor(i / 7) % 4];
            ctx.globalAlpha = .34 + .66 * Math.min(1, i / 13);
            ctx.beginPath();
            ctx.moveTo(x, 52 - h / 2);
            ctx.lineTo(x, 52 + h / 2);
            ctx.stroke();
        });
        ctx.globalAlpha = 1;
    }
    /**
     * 输入：无。
     * 输出：无。
     * 功能：缩放整台手机，状态栏仍用 393×852 设计坐标，避开外部设置按钮。
     */
    function resizePhone() {
        const small = innerWidth <= 650, avail = innerHeight - (small ? 80 : 44), scale = Math.min(1, (innerWidth - (small ? 10 : 32)) / 411, Math.max(300, avail) / 870);
        document.documentElement.style.setProperty("--design-scale", scale.toFixed(6));
        document.documentElement.style.setProperty("--phone-w", `${411 * scale}px`);
        document.documentElement.style.setProperty("--phone-h", `${870 * scale}px`);
    }
    /**
     * 输入：无。
     * 输出：无。
     * 功能：图层就绪后开放首页；恢复计时器而不是悄悄重置。
     */
    function onReady() {
        resizePhone();
        const saved = Store.read("fluffy-active-focus-v1", null);
        if (saved?.record && Catalog.validate("focus", saved.record.data || {}).ok && timer.restore(saved.timer)) {
            state.focusRecord = saved.record;
            state.timerNotified = false;
            navigate("focus");
            checkFocus();
        }
        else {
            navigate("home", { transition: false });
        }
        $("confirm-entry").disabled = false;
    }
    /**
     * 输入：node、action。
     * 输出：无。
     * 功能：为顶栏/导航补充长按快捷操作，不触发双击或改变原点击。
     */
    function bindContextHold(node, action) {
        let timeout = null, long = false;
        node.addEventListener("pointerdown", e => {
            if (e.button !== 0)
                return;
            long = false;
            timeout = setTimeout(() => {
                long = true;
                action();
            }, 500);
        });
        node.addEventListener("pointerup", () => clearTimeout(timeout));
        node.addEventListener("pointercancel", () => clearTimeout(timeout));
        node.addEventListener("pointerleave", () => clearTimeout(timeout));
        node.addEventListener("click", e => {
            if (long) {
                e.preventDefault();
                e.stopImmediatePropagation();
                long = false;
            }
        }, true);
        node.addEventListener("contextmenu", e => {
            e.preventDefault();
            action();
        });
    }
    /**
     * 输入：无。
     * 输出：无。
     * 功能：绑定真实按钮、媒体生命周期、键盘可访问性和计时操作。
     */
    function bind() {
        // 阶段一：首页、短按和长按各自绑定，避免一手势触发两条流程。
        document.querySelectorAll("[data-icon]").forEach(n => setIcon(n, n.dataset.icon));
        bailianSettings = new BailianSettings(bailian, CONFIG, {
            onOpen: () => { cancelWork(false); gesture?.disarm(); closeSettings(false); }, onClear: () => cancelWork(false)
        });
        board = new HomeBoard($("home-board"), {
            open: openEntry, warn: toast, attend: id => {
                animation.homeLookTarget = board.order.indexOf(id) < 3 ? -.2 : .2;
            }, release: () => {
                animation.homeLookTarget = 0;
            }
        });
        gesture = new HoldGesture($("confirm-entry"), {
            short: confirmManual, long: beginSpeech, release: releaseSpeech, cancel: () => {
                if (["requesting", "listening"].includes(state.phase))
                    cancelWork();
            }
        }, CONFIG.longPressMs || 420);
        $("entry-form").addEventListener("submit", e => {
            e.preventDefault();
            confirmManual();
        });
        $("cancel-voice").onclick = () => cancelWork();
        $("primary").onclick = primaryAction;
        $("edit-record").onclick = editRecord;
        $("back").onclick = () => {
            if (animation.scene === "record")
                editRecord();
            else if (animation.scene === "focus") {
                navigate("home");
                homeBubble("计时仍在继续，随时回来。");
            }
            else
                navigate("home");
        };
        $("pet").onclick = () => {
            animation.petAt = animation.idle;
        };
        $("home-cat").onclick = () => {
            animation.petAt = animation.idle;
            homeBubble(["嗯？我在呢", "慢慢来就好\n我会陪着你", "摸摸收到了\n谢谢你呀喵"][(Math.floor(animation.idle / 3)) % 3]);
        };
        bindContextHold($("home-cat"), chatSheet);
        $("home-menu").onclick = homeMenu;
        bindContextHold($("home-menu"), homeMenu);
        $("today-stat").onclick = () => navigate("history");
        bindContextHold($("today-stat"), () => {
            updateHomeStats();
            homeBubble(`今天记了${Store.stats().today}项\n都好好收着呢`);
        });
        $("days-stat").onclick = () => navigate("profile");
        bindContextHold($("days-stat"), () => navigate("profile"));
        document.querySelectorAll("[data-nav]").forEach(b => {
            b.addEventListener("click", () => b.dataset.nav === "chat" ? chatSheet() : navigate(b.dataset.nav));
            bindContextHold(b, () => {
                if (b.dataset.nav === "chat")
                    chatSheet();
                else if (b.dataset.nav === "home")
                    homeMenu();
                else
                    navigate(b.dataset.nav);
            });
        });
        // 阶段二：面板、设置和键盘焦点遵守同一打开/关闭协议。
        $("sheet-close").onclick = () => closeSheet();
        $("sheet-layer").addEventListener("pointerdown", e => {
            if (e.target === $("sheet-layer"))
                closeSheet();
        });
        $("open-settings").onclick = openSettings;
        $("api-form").onsubmit = saveKey;
        $("forget-key").onclick = clearKey;
        document.addEventListener("pointerdown", e => {
            if (!$("api-popover").hidden && !$("api-popover").contains(e.target) && !$("open-settings").contains(e.target))
                closeSettings(false);
        });
        document.addEventListener("keydown", e => {
            if (e.key === "Escape") {
                if (!$("api-popover").hidden)
                    closeSettings();
                else if (!$("sheet-layer").hidden)
                    closeSheet();
                else if (state.phase !== "idle")
                    cancelWork();
                board.cancel();
            }
            if (e.key === "Tab" && !$("sheet-layer").hidden && $("api-popover").hidden) {
                const nodes = [...$("sheet").querySelectorAll("button:not(:disabled),input,textarea,select,[tabindex='0']")].filter(n => !n.closest("[hidden]")), first = nodes[0], last = nodes.at(-1);
                if (e.shiftKey && document.activeElement === first) {
                    e.preventDefault();
                    last?.focus();
                }
                else if (!e.shiftKey && document.activeElement === last) {
                    e.preventDefault();
                    first?.focus();
                }
            }
        });
        // 阶段三：媒体与计时操作必须由真实用户手势触发。
        $("photo-library").onchange = async (e) => {
            const id = state.category;
            try {
                if (e.target.files?.[0])
                    cancelWork(false);
                const image = await photo.readFile(e.target.files?.[0]);
                if (image && id === state.category && animation.scene === "entry")
                    showPhoto(image);
            }
            catch (error) {
                toast(error.message);
            }
            finally {
                e.target.value = "";
            }
        };
        $("timer-pause").onclick = () => {
            timer.state === "running" ? timer.pause() : timer.resume();
            persistFocus();
            renderFocus();
        };
        $("timer-rest").onclick = () => {
            if (timer.state === "paused") {
                timer.resume();
            }
            timer.pause(true);
            persistFocus();
            renderFocus();
        };
        $("timer-reset").onclick = () => ask("重新开始这一段？", "本轮计时将从原定时长重新开始。", () => {
            timer.reset();
            state.timerNotified = false;
            persistFocus();
            renderFocus();
        });
        $("timer-stop").onclick = () => ask("结束这一段专注？", `已认真专注 ${Math.round(timer.tick().elapsedMs / 6000) / 10} 分钟，停止后会保留实际时间。`, finishFocus);
        // 阶段四：离开页面释放音视频，保存专注截止时间，不保存密钥。
        window.addEventListener("resize", resizePhone);
        window.addEventListener("pagehide", () => {
            cancelWork(false);
            photo.stopCamera();
            persistFocus();
            closeSettings(false);
            api.clear();
            $("key-indicator").classList.remove("enabled");
            bailianSettings.close(false);
            bailianSettings.clear();
        });
        document.addEventListener("visibilitychange", () => {
            if (document.hidden) {
                if (state.phase !== "authorizing")
                    cancelWork(false);
                photo.stopCamera();
                persistFocus();
            }
            else {
                checkFocus();
                updateHomeStats();
            }
        });
        setInterval(checkFocus, 200);
    }
    renderForm({});
    resizePhone();
    bind();
    homeBubble("home");
    animation.reducedMotion = Boolean(Store.read("fluffy-reduced-motion", matchMedia("(prefers-reduced-motion: reduce)").matches));
    document.body.classList.toggle("reduce-motion", animation.reducedMotion);
    animation.initialize().catch(() => {
        $("loading").textContent = "小猫图层没有加载完成，请刷新重试。";
    });
    if (new URLSearchParams(location.search).has("debug") || window.FLUFFY_TEST) {
        window.FluffyDebug = {
            animation, state, board, timer, photo, speech, rawAudio, bailianSettings, microphone, gesture, get timeRange() { return timeRange; }, get formLayout() { return formLayout; }, estimateTime, bubble, homeBubble, showPhoto, openEntry, navigate, fillForm, rawForm, confirmManual, primaryAction, beginSpeech, releaseSpeech, cancelWork, finishFocus, checkFocus, showSheet, closeSheet, renderForm, saveTaskLater, apiTest: window.FLUFFY_TEST ? api : undefined, bailianTest: window.FLUFFY_TEST ? bailian : undefined
        };
    }
    return {};
})();
