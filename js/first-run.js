/* v17 · 首次引导宿主。独立 frame 隔离两套画布/样式，但资料与首页属于同一站点。 */
__fluffyModules["first-run.js"] = (() => {
    "use strict";
    const Profile = __fluffyModules["first-notes-profile.js"];
    let overlay = null, frame = null, pending = null, appStarted = false, savedInTab = null;
    let messageHandler = null, focusReturn = null, readyTimer = null;
    /** 输入：无。输出：Storage 或 null。功能：隐私模式/禁用存储不抛出未处理异常。 */
    function storage() { try { return localStorage; } catch { return null; } }
    /** 输入：无。输出：有效完成资料或 null。功能：只有七题完整且有完成时间才省略首次引导。 */
    function getProfile() { return savedInTab || Profile.completed(Profile.read(storage())); }
    /** 输入：无。输出：空白个人资料。功能：没有默认性别、年龄或健康习惯，不使用每日记录填造问卷。 */
    function blank() {
        let language = "zh";
        try { language = JSON.parse(storage()?.getItem("fluffy-review-language-v1") || '"zh"') === "en" ? "en" : "zh"; } catch { /* 使用中文，不修改现有键。 */ }
        return { version: 4, language, gender: null, role: null, age: null, interests: [], sleep: null, exercise: null, diet: [] };
    }
    /** 输入：blocked。输出：无。功能：引导期间主程序不可聚焦、不能点穿，不删除首页 DOM 或既有记录。 */
    function block(blocked) {
        for (const node of document.querySelectorAll(".stage,.provider-toolbar,#api-popover,#bailian-popover")) {
            node.inert = blocked;
            if (blocked) node.setAttribute("aria-hidden", "true"); else node.removeAttribute("aria-hidden");
        }
        document.documentElement.dataset.firstRun = blocked ? "pending" : "ready";
    }
    /** 输入：目标 frame、频道、类型、资料。输出：无。功能：网页使用精确 origin；file 预览只对已捕获 frame 放行。 */
    function post(target, channel, type, payload = {}) {
        target?.contentWindow?.postMessage({ channel, type, ...payload }, location.origin === "null" ? "*" : location.origin);
    }
    /** 输入：无。输出：无。功能：清理 frame 与消息监听，避免隐藏的小猫继续跑动画或捕获手势。 */
    function removeOverlay() {
        clearTimeout(readyTimer); readyTimer = null;
        if (messageHandler) window.removeEventListener("message", messageHandler);
        messageHandler = null;
        const current = overlay;
        overlay = null; frame = null; pending = null;
        current?.remove();
        block(false);
        if (focusReturn?.isConnected) focusReturn.focus({ preventScroll: true });
        else document.querySelector('[data-nav="home"]')?.focus({ preventScroll: true });
        focusReturn = null;
    }
    /** 输入：无。输出：Promise<void>。功能：主应用画布准备好再从原汇总页淡入首页；没有中间完成页面。 */
    async function appReady() {
        appStarted = true;
        if (!overlay) { block(false); return; }
        block(false);
        overlay.style.pointerEvents = "auto";
        const duration = matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 320;
        try { await overlay.animate([{ opacity: 1 }, { opacity: 0 }], { duration, easing: "ease-out", fill: "forwards" }).finished; }
        catch { /* 页面离开或减少动画时仍执行清理。 */ }
        removeOverlay();
    }
    /**
     * 输入：options（review 表示从“我的”翻看初见手记）。
     * 输出：Promise<{profile,fresh}>，仅显式完成并保存后 resolve。
     * 功能：首次打开/途中恢复/重新翻看共用入口；随机频道、source、origin 和字段校验防止伪造完成。
     */
    function open(options = {}) {
        if (pending) return pending.promise;
        const previous = getProfile(), draft = Profile.draft(Profile.read(storage(), Profile.DRAFT_KEY));
        const initial = options.review && previous ? { profile: { ...previous, language: __fluffyModules["entry-i18n.js"].language() }, step: "summary" }
            : draft || { profile: blank(), step: "welcome" };
        const bytes = new Uint32Array(4); crypto.getRandomValues(bytes);
        const channel = "nava-first-run-" + Array.from(bytes, n => n.toString(16).padStart(8, "0")).join("");
        let resolve;
        const promise = new Promise(done => { resolve = done; });
        pending = { promise, resolve, committed: false, channel };
        const operation = pending;
        focusReturn = document.activeElement;
        block(true);
        overlay = document.createElement("div"); overlay.id = "nava-first-run";
        frame = document.createElement("iframe"); frame.id = "nava-onboarding-frame"; frame.name = channel;
        frame.title = initial.profile.language === "en" ? "NAVA · Our first notes" : "NAVA · 初见手记";
        frame.setAttribute("sandbox", "allow-scripts allow-same-origin");
        frame.setAttribute("allow", "camera 'none'; microphone 'none'; geolocation 'none'");
        frame.referrerPolicy = "no-referrer";
        const sourceFrame = frame;
        messageHandler = event => {
            if (pending !== operation || event.source !== sourceFrame.contentWindow || event.origin !== location.origin || event.data?.channel !== channel) return;
            const message = event.data;
            if (message.type === "ready") {
                clearTimeout(readyTimer);
                post(sourceFrame, channel, "init", initial);
            } else if (message.type === "draft" && !operation.committed) {
                const next = Profile.draft(message.draft);
                if (next && !options.review) { try { storage()?.setItem(Profile.DRAFT_KEY, JSON.stringify(next)); } catch { /* 完成时另行报告保存失败。 */ } }
            } else if (message.type === "complete" && !operation.committed) {
                // 阶段二：只提交七项偏好，绝不访问手记/待办/计时存储。
                const result = Profile.save(storage(), message.profile, previous);
                if (!result.ok) { post(sourceFrame, channel, "save-error"); return; }
                operation.committed = true;
                savedInTab = result.profile;
                __fluffyModules["entry-i18n.js"].setLanguage(result.profile.language);
                post(sourceFrame, channel, "saved");
                operation.resolve({ profile: result.profile, fresh: !previous });
                if (appStarted) appReady();
            }
        };
        window.addEventListener("message", messageHandler);
        // 阶段三：单文件预览内嵌同一份引导 HTML；线上只访问同目录的 onboarding.html。
        if (typeof window.NAVA_ONBOARDING_HTML === "string") {
            const bootstrap = '<script>window.NAVA_HOST_ORIGIN=' + JSON.stringify(location.origin) + ';<\/script>';
            frame.srcdoc = window.NAVA_ONBOARDING_HTML.replace("<head>", "<head>" + bootstrap);
        } else frame.src = new URL("onboarding.html?v=nava-v17", location.href).href;
        overlay.append(frame); document.body.append(overlay);
        return promise;
    }
    /** 输入：无。输出：初始化许可 Promise。功能：完成用户直接进入既有 APP；无完成资料时才展示首次引导。 */
    function beforeStart() {
        const profile = getProfile();
        if (profile) { block(false); return Promise.resolve({ profile, fresh: false }); }
        return open();
    }
    /** 输入：无。输出：重新确认资料的 Promise。功能：主程序中的手记入口复用同一汇总，没有创建额外结束页。 */
    function openSummary() { return open({ review: true }); }
    return { beforeStart, appReady, getProfile, openSummary };
})();
