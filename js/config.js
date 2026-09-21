/* 只包含公开配置。不要在此文件或仓库中填写 API Key。 */
window.FLuffyConfig = Object.freeze({
    model: "deepseek-flash",
    speechLanguage: "zh-CN",
    // GitHub Pages 为静态站点，直接请求官方 API；同样适用于本地预览。
    // 正式产品请将访问路由迁移到经过鉴权的自有后端。
    localProxy: false,
    longPressMs: 420,
    maximumSpeechSeconds: 90
});
