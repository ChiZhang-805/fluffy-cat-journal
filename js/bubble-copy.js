/* 小猫对白只承载短句；详细错误仍由 toast 保留，不把长段报告塞入气泡。 */
__fluffyModules["bubble-copy.js"] = (() => {
    "use strict";
    const COPY = Object.freeze({
        home: "把今天的小事\n慢慢讲给我听",
        listening: "你慢慢地讲呀\n我在认真听呢",
        thinking: "让我想一想\n马上就写好",
        ready: "已经填好啦\n你再看一看",
        canceled: "先停在这里\n内容还留着",
        permission: "先允许麦克风\n再说给小猫听",
        voiceReady: "准备好啦\n长按说吧",
        voiceInvite: "长按下面按钮\n慢慢说给我听",
        estimating: "我来排排时间\n陪你专心做好",
        estimated: "时间安排好啦\n我们一起开始",
        photo: "让我仔细看看\n记下清楚的事",
        error: "遇到小问题啦\n看看下方提示",
        saved: "今天也辛苦啦\n都替你记好啦",
        focusAway: "时间还在走呀\n随时回来找我"
    });
    const ALIASES = Object.freeze({
        "已取消，填过的内容还在。": "canceled",
        "请先允许麦克风。": "permission",
        "准备好了，长按开始说话。": "voiceReady",
        "嗯，我在听。": "listening",
        "听到了，我整理一下。": "thinking",
        "写在框里了，确认后交给我记录。": "ready",
        "让我把时间估得实际一点。": "estimating",
        "我看看，再一起核对。": "photo",
        "只记下看得清的部分，你再看看。": "ready",
        "长按底部按钮，我在听。": "voiceInvite",
        "整理好了，确认后我来写。": "ready",
        "记下来了，今天也辛苦啦。": "saved",
        "计时仍在继续，随时回来。": "focusAway"
    });
    /**
     * 输入：text（语义键或受控对白）、error（是否错误）。
     * 输出：{text, detail}；text 为一至两行短句，detail 为须另外展示的完整信息。
     * 功能：固定对白显式平衡换行；动态长错误不缩字、不丢失，也不扩张气泡。
     */
    function prepare(text, error = false) {
        const original = String(text || "").trim();
        const key = ALIASES[original] || original;
        if (COPY[key]) return { text: COPY[key], detail: "" };
        const lines = original.split("\n");
        // 阶段一：受控双行以自然语义断句，不做拉大字距的强制两端对齐。
        if (!error && lines.length <= 2 && lines.every(line => [...line].length <= 7))
            return { text: original, detail: "" };
        // 阶段二：未知消息显示完整 toast；对白本身保持简短，不将错误伪装成成功。
        return { text: error ? COPY.error : COPY.ready, detail: original };
    }
    /**
     * 输入：node（气泡元素）、text、error。
     * 输出：须由外层展示的完整消息，或空串。
     * 功能：仅用 textContent 更新对白，避免来自模型/错误信息的 HTML 注入。
     */
    function render(node, text, error = false) {
        const copy = prepare(text, error);
        node.textContent = copy.text;
        node.classList.toggle("error", error);
        node.dataset.lines = String(copy.text.split("\n").length);
        const locale = __fluffyModules["entry-i18n.js"];
        if(locale?.language()==="en") {
            node.textContent=locale.bubble(ALIASES[String(text||"").trim()]||String(text||"").trim(),copy.text);
            node.dataset.lines=String(node.textContent.split("\n").length);
        }
        return copy.detail;
    }
    return { COPY, prepare, render };
})();
