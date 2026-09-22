/* 百炼密钥只存在实例私有内存。不得把 Key、音频或照片写入仓库与本机历史。 */
__fluffyModules["bailian.js"] = (() => {
    "use strict";
    /**
     * 输入：公开配置里的 base URL。
     * 输出：受允许的官方 HTTPS 地址。
     * 功能：避免设置错误将密钥发送到任意站点。
     */
    function officialBase(value) {
        const u = new URL(value || "https://dashscope.aliyuncs.com/compatible-mode/v1");
        const official = ["dashscope.aliyuncs.com", "dashscope-intl.aliyuncs.com", "dashscope-us.aliyuncs.com"];
        const workspace = /^[a-z0-9-]+\.(cn-beijing|ap-southeast-1|cn-hongkong|us-east-1|eu-central-1|ap-northeast-1)\.maas\.aliyuncs\.com$/;
        if (u.protocol !== "https:" || u.port || u.username || u.password || u.search || u.hash || (!official.includes(u.hostname) && !workspace.test(u.hostname)) || !/^\/compatible-mode\/v1\/?$/.test(u.pathname))
            throw Error("百炼接口地址必须是对应地域的官方 HTTPS 兼容端点。");
        return u.origin + u.pathname.replace(/\/$/, "");
    }
    /**
     * 输入：HTTP 状态。
     * 输出：简短错误。
     * 功能：不回显可能含敏感数据的上游错误正文。
     */
    function errorMessage(status) {
        return ({ 400: "百炼暂不能处理这份内容，请检查模型配置或缩短输入。", 401: "百炼 Key 无效，或与当前接口地域不匹配。", 402: "百炼余额不足。", 403: "当前百炼 Key 没有该模型的权限。", 404: "当前百炼地域未提供配置的模型或接口。", 413: "音频或照片过大，请缩短录音或换一张照片。", 429: "百炼请求较多或额度已用完，请稍后重试。" })[status] || "百炼服务暂时不可用，请稍后再试。";
    }
    /**
     * 输入：ReadableStream、signal。
     * 输出：标准 Chat Completions 结构。
     * 功能：增量解码 UTF-8 SSE，拒绝截断/上游错误；兼容跨网络块的中文与 CRLF。
     */
    async function readSSE(stream, signal) {
        if (!stream?.getReader)
            throw Error("浏览器无法读取百炼流式响应。");
        const reader = stream.getReader(), decoder = new TextDecoder();
        let buffer = "", text = "", reason = null, doneMarker = false, bytes = 0;
        /**
         * 输入：单个 SSE 事件。
         * 输出：无。
         * 功能：只累积模型正文，不泄漏内部推理文本或把错误事件当成功。
         */
        function consume(event) {
            const data = event.split(/\r?\n/).filter(line => line.startsWith("data:")).map(line => line.slice(5).trimStart()).join("\n");
            if (!data)
                return;
            if (data.trim() === "[DONE]") {
                doneMarker = true;
                return;
            }
            let body;
            try {
                body = JSON.parse(data);
            }
            catch {
                throw Error("百炼响应格式不完整。");
            }
            if (body.error)
                throw Error("百炼在整理时中断了，请重新提交。");
            const c = body.choices?.[0];
            if (!c)
                return;
            if (typeof c.delta?.content === "string")
                text += c.delta.content;
            if (c.finish_reason)
                reason = c.finish_reason;
        }
        try {
            while (true) {
                if (signal?.aborted)
                    throw new DOMException("已取消", "AbortError");
                const part = await reader.read();
                if (part.done)
                    break;
                bytes += part.value.byteLength;
                if (bytes > 2e6)
                    throw Error("返回内容过长，已停止整理。");
                buffer += decoder.decode(part.value, { stream: true });
                let match;
                while ((match = /\r?\n\r?\n/.exec(buffer))) {
                    consume(buffer.slice(0, match.index));
                    buffer = buffer.slice(match.index + match[0].length);
                }
            }
            buffer += decoder.decode();
            if (buffer.trim())
                consume(buffer);
            if (!text.trim() || reason !== "stop" || !doneMarker && !reason)
                throw Error("百炼没有完整返回结果，请重试。");
            return { choices: [{ finish_reason: reason, message: { content: text } }] };
        }
        finally {
            try {
                await reader.cancel();
            }
            catch { /* 网络已经关闭。 */ }
            reader.releaseLock();
        }
    }
    class BailianClient {
        #key = "";
        /**
         * 输入：config、可注入 fetchImpl。
         * 输出：客户端。
         * 功能：隔离百炼与 DeepSeek 密钥和模型选择。
         */
        constructor({ config = {}, fetchImpl = globalThis.fetch?.bind(globalThis) } = {}) {
            this.provider = "bailian";
            this.config = config;
            this.fetch = fetchImpl;
            this.base = officialBase(config.bailianBaseURL);
            this.routes = { chat: this.base + "/chat/completions", models: this.base + "/models" };
            this.model = config.bailianVisionModel || "qwen3-vl-plus";
            this.audioModel = config.bailianAudioModel || "qwen3-omni-flash";
        }
        /**
         * 输入：无。
         * 输出：boolean。
         * 功能：仅说明本次页面有 Key，不宣称模型已经识别成功。
         */
        get configured() { return Boolean(this.#key); }
        /**
         * 输入：key。
         * 输出：无。
         * 功能：仅在内存接收格式合法的 Key。
         */
        setKey(key) { const value = String(key || "").trim(); if (value.length < 12 || value.length > 256 || /\s/.test(value))
            throw Error("请填写完整的百炼 API Key。"); this.#key = value; }
        /**
         * 输入：无。
         * 输出：无。
         * 功能：清除 Key 引用，调用方同时取消该服务的请求。
         */
        clear() { this.#key = ""; }
        /**
         * 输入：固定请求地址、payload/null、signal。
         * 输出：解析后的 JSON。
         * 功能：实际调用百炼，统一超时、取消、跨域/网络错误和 SSE；拒绝重定向。
         */
        async request(path, payload, signal) {
            if (!this.configured)
                throw Error("先在右上角启用阿里云百炼。");
            if (!Object.values(this.routes).includes(path))
                throw Error("不允许向这个地址发送百炼 Key。");
            const controller = new AbortController();
            let timedOut = false;
            /**
             * 输入：无。
             * 输出：无。
             * 功能：用户取消实时传递到 fetch 与流式读取。
             */
            const cancel = () => controller.abort();
            if (signal?.aborted)
                cancel();
            signal?.addEventListener("abort", cancel, { once: true });
            const timeout = setTimeout(() => { timedOut = true; controller.abort(); }, payload ? 65000 : 20000);
            try {
                // 阶段一：只向公开配置中的一个官方端点发送，不自动跨地域探测 Key。
                const response = await this.fetch(path, { method: payload ? "POST" : "GET", mode: "cors", credentials: "omit", cache: "no-store", redirect: "error", referrerPolicy: "no-referrer", signal: controller.signal,
                    headers: { Authorization: `Bearer ${this.#key}`, ...(payload ? { "Content-Type": "application/json" } : {}) }, ...(payload ? { body: JSON.stringify(payload) } : {}) });
                if (!response.ok)
                    throw Error(errorMessage(response.status));
                // 阶段二：音频模型按官方要求使用流式文本输出；非流式图像调用按 JSON 处理。
                const result = payload?.stream ? await readSSE(response.body, controller.signal) : await response.json();
                if (controller.signal.aborted)
                    throw new DOMException("已取消", "AbortError");
                return result;
            }
            catch (e) {
                if (timedOut)
                    throw Error("百炼整理超时了，请稍后重试。");
                if (controller.signal.aborted)
                    throw new DOMException("已取消", "AbortError");
                if (e instanceof TypeError)
                    throw Error("无法连接百炼，请检查网络或接口跨域配置。");
                throw e;
            }
            finally {
                clearTimeout(timeout);
                signal?.removeEventListener("abort", cancel);
            }
        }
        /**
         * 输入：signal。
         * 输出：模型列表。
         * 功能：通过非生成接口校验 Key，不上传照片/声音。
         */
        async check(signal) { const body = await this.request(this.routes.models, null, signal); if (!Array.isArray(body.data))
            throw Error("百炼未返回有效的模型列表。"); return body.data.map(x => x.id).filter(x => typeof x === "string"); }
    }
    return { BailianClient, officialBase, errorMessage, readSSE };
})();
