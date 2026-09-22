/* 手绘线性界面图标，与既有状态栏分开；不依赖字体或第三方图标库。 */
window.FluffyIcons = (() => {
    const paths = {
        home: '<path d="m3 11 9-8 9 8v10h-6v-7H9v7H3Z"/>',
        mood: '<path d="M20 13a8 8 0 1 1-9-9M8 14c2 4 6 4 8 0M8 10h.01M13 10h.01M18 2v6M15 5h6"/>',
        food: '<path d="M4 3v6c0 3 5 3 5 0V3M6.5 3v18M19 3c-5 1-5 7-5 10h5M19 3v18"/>',
        sport: '<circle cx="15" cy="4" r="2"/><path d="m12 9 5 3 4 1M12 9l-4 5-6 2M12 9l-1 7 5 6M11 16l-5 5"/>',
        focus: '<circle cx="12" cy="14" r="8"/><path d="M9 2h6M12 9v5l-3 2M18 6l2-2"/>',
        sleep: '<path d="M20.5 15A8.5 8.5 0 0 1 9 3.5 9 9 0 1 0 20.5 15Z"/><path d="m17 2 1 2 2 1-2 1-1 2-1-2-2-1 2-1Z" stroke-width="1.4"/>',
        face: '<path d="M8 3H4v4M16 3h4v4M20 17v4h-4M8 21H4v-4M8 10h.01M16 10h.01M9 15c2 2 4 2 6 0"/><path d="M7 6c3-3 7-3 10 0v9c-3 6-7 6-10 0Z" stroke-width="1.4"/>',
        chat: '<path d="M21 11a9 9 0 0 1-13 8l-6 2 2-6A9 9 0 1 1 21 11Z"/><path d="M8 11h.01M12 11h.01M16 11h.01" stroke-width="3"/>',
        history: '<rect x="4" y="3" width="16" height="18" rx="3"/><path d="m7 10 3-3 3 3 4-4M7 14h10M7 17h10"/>',
        tasks: '<rect x="3" y="5" width="15" height="16" rx="2"/><path d="M7 2h14v15M7 12l3 3 5-6"/>',
        profile: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="9" r="2.5"/><path d="M6.5 18c.7-5 10.3-5 11 0"/>',
        menu: '<path d="M5 6h14M5 12h14M5 18h14"/>',
        close: '<path d="m6 6 12 12M18 6 6 18"/>',
        back: '<path d="m15 4-8 8 8 8"/>',
        arrow: '<path d="m9 4 8 8-8 8"/>',
        check: '<path d="m5 12 4 4L19 6"/>',
        leaf: '<path d="M20 3C8 2 1 10 6 17s16-2 14-14ZM5 21 16 8"/>',
        ring: '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/>',
        mic: '<rect x="9" y="2" width="6" height="12" rx="3"/><path d="M6 10v2a6 6 0 0 0 12 0v-2M12 18v4M8 22h8"/>',
        camera: '<path d="M3 7h4l2-3h6l2 3h4v14H3Z"/><circle cx="12" cy="13" r="4"/>',
        photo: '<rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8" cy="8" r="1.5"/><path d="m4 18 6-6 4 3 3-4 4 5"/>',
        sparkle: '<path d="m12 2 2.4 7.6L22 12l-7.6 2.4L12 22l-2.4-7.6L2 12l7.6-2.4Z"/>',
        pause: '<path d="M8 5v14M16 5v14" stroke-width="3.5"/>',
        play: '<path d="m8 4 12 8-12 8Z"/>',
        stop: '<rect x="5" y="5" width="14" height="14" rx="2"/>',
        reset: '<path d="M4 10a8 8 0 1 1 1 7M4 4v6h6"/>',
        coffee: '<path d="M4 8h12v8a5 5 0 0 1-12 0ZM16 8h2a3 3 0 0 1 0 6h-2M3 22h16M7 2v3M12 2v3"/>',
        move: '<path d="M12 2v20M2 12h20M9 5l3-3 3 3M9 19l3 3 3-3M5 9l-3 3 3 3M19 9l3 3-3 3"/>',
        edit: '<path d="m15 3 6 6-12 12H3v-6ZM13 5l6 6"/>',
        trash: '<path d="M3 6h18M9 3h6M5 6l1 15h12l1-15M10 10v7M14 10v7"/>',
        export: '<path d="M12 3v12M8 7l4-4 4 4M4 13v8h16v-8"/>',
        sun: '<circle cx="12" cy="12" r="4"/><path d="M12 1v3M12 20v3M1 12h3M20 12h3M4 4l2 2M18 18l2 2M4 20l2-2M18 6l2-2"/>',
        heart: '<path d="M12 21 3.7 12.7C-3 5 6 0 12 6 18 0 27 5 20.3 12.7Z"/>',
        send: '<path d="m3 3 18 9-18 9 4-9ZM7 12h14"/>'
    };
    /**
     * 输入：name（图标名），className（可选受控样式）。
     * 输出：SVG 文本。
     * 功能：仅渲染本地白名单路径，不插入用户文本。
     */
    function svg(name, className = "") {
        return `<svg class="icon ${className}" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">${paths[name] || paths.sparkle}</svg>`;
    }
    return { svg };
})();
