/* 只包含公开配置。不要在此文件或仓库中填写 API Key。 */
window.FLuffyConfig = Object.freeze({
    // 百炼默认北京地域。其他地域修改此公开端点，Key 不通用，不自动跨地域探测。
    bailianBaseURL: "https://dashscope.aliyuncs.com/compatible-mode/v1",
    bailianVisionModel: "qwen3-vl-plus",
    // 所有语言任务固定DeepSeek Chat；音频先经浏览器听写，不发送给百炼Omni。
    model: "deepseek-flash",
    speechLanguage: "zh-CN",
    // GitHub Pages 为静态站点，直接请求官方 API；同样适用于本地预览。
    // 正式产品请将访问路由迁移到经过鉴权的自有后端。
    localProxy: false,
    longPressMs: 420,
    maximumSpeechSeconds: 90
});
