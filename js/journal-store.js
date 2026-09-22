__fluffyModules["journal-store.js"] = (() => {
    "use strict";
    const KEY = "fluffy-six-journal-v1", TASKS_KEY = "fluffy-six-tasks-v1";
    const { validate, category } = __fluffyModules["catalog.js"];
    /**
     * 输入：key、fallback。
     * 输出：解析结果或默认值。
     * 功能：容错读取本机数据，损坏文件不阻断记录。
     */
    function read(key, fallback) {
        try {
            return JSON.parse(localStorage.getItem(key) || "null") ?? fallback;
        }
        catch {
            return fallback;
        }
    }
    /**
     * 输入：key、value。
     * 输出：boolean。
     * 功能：容量或权限不足时明确返回失败，UI 不虚报保存。
     */
    function write(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        }
        catch {
            return false;
        }
    }
    /**
     * 输入：无。
     * 输出：类别校验后的历史记录。
     * 功能：恢复真实历史，兼容旧版运动记录而不覆盖旧存储。
     */
    function records() {
        const current = read(KEY, null);
        const legacy = read("fluffy-cat-minimal-records-v1", []);
        const source = Array.isArray(current) ? current : (Array.isArray(legacy) ? legacy : []).filter(r => r && typeof r === "object").map(r => ({
            id: r.id, category: "sport", data: r, createdAt: r.createdAt, source: r.source || "manual"
        }));
        return source.filter(r => {
            try {
                return r && typeof r.id === "string" && Number.isFinite(Date.parse(r.createdAt)) && validate(r.category, r.data || {}).ok;
            }
            catch {
                return false;
            }
        }).slice(0, 400);
    }
    /**
     * 输入：record（已确认记录）。
     * 输出：是否成功。
     * 功能：同一 ID 幂等保存，不随动画重播重复添加；不持久化照片或密钥。
     */
    function save(record) {
        const checked = validate(record.category, record.data);
        if (!checked.ok)
            return false;
        const safe = {
            id: record.id, category: record.category, data: checked.value, createdAt: record.createdAt, source: record.source || "manual", estimated: Boolean(record.estimated), focus: record.focus || null
        };
        return write(KEY, [safe, ...records().filter(item => item.id !== record.id)].slice(0, 400));
    }
    /**
     * 输入：id（记录 ID）。
     * 输出：是否删除成功。
     * 功能：用户明确确认后删除一条，不影响其他类别。
     */
    function remove(id) {
        return write(KEY, records().filter(r => r.id !== id));
    }
    /**
     * 输入：date（日期）。
     * 输出：本地日期键。
     * 功能：今日统计使用本地日期，不按 UTC 错分跨夜记录。
     */
    function dayKey(date = new Date()) {
        return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
    }
    /**
     * 输入：list（历史）。
     * 输出：今日类别数、记录总数和陪伴天数。
     * 功能：用真实数据驱动顶部信息条，不创建虚假健康评分。
     */
    function stats(list = records()) {
        const today = dayKey(), days = new Set(list.map(r => dayKey(new Date(r.createdAt))));
        return {
            today: new Set(list.filter(r => dayKey(new Date(r.createdAt)) === today).map(r => r.category)).size, count: list.length, days: days.size, minutes: Math.round(list.filter(r => r.category === "focus").reduce((s, r) => s + (r.focus?.elapsedMs || 0), 0) / 60000)
        };
    }
    /**
     * 输入：无。
     * 输出：有效待办数组。
     * 功能：与完成记录分开保存尚未开始/未勾选完成的任务。
     */
    function tasks() {
        const items = read(TASKS_KEY, []);
        return Array.isArray(items) ? items.filter(t => t && typeof t.id === "string" && validate("focus", t.data || {}).ok).slice(0, 100) : [];
    }
    /**
     * 输入：task（待办）。
     * 输出：成功标记。
     * 功能：同一 ID 更新，不把倒计时结束自动当作完成任务。
     */
    function saveTask(task) {
        return write(TASKS_KEY, [task, ...tasks().filter(t => t.id !== task.id)].slice(0, 100));
    }
    /**
     * 输入：id。
     * 输出：成功标记。
     * 功能：删除选定待办。
     */
    function removeTask(id) {
        return write(TASKS_KEY, tasks().filter(t => t.id !== id));
    }
    return {
        read, write, records, save, remove, dayKey, stats, tasks, saveTask, removeTask, KEY, TASKS_KEY
    };
})();
