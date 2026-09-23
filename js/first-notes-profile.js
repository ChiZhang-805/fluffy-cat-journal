/* 首次引导资料只存本机；与手记、计时、AI Key、评分和账户完全分离。 */
(() => {
    "use strict";
    const KEY = "nava-first-notes-v3", DRAFT_KEY = "nava-first-notes-draft-v1";
    const ENUMS = Object.freeze({
        gender: ["male", "female", "private"],
        role: ["student", "professional", "freelancer", "caregiver", "retired", "other"],
        age: ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"],
        interests: ["movement", "reading", "music", "games", "outdoors", "creative"],
        sleep: ["under5", "5to6", "6to7", "7to8", "8to9", "9plus"],
        exercise: ["rarely", "under1", "1to2", "2to4", "4to7", "7plus"],
        diet: ["none", "light", "protein", "lowcarb", "plant", "restrictions"]
    });
    const STEPS = ["welcome", ...Object.keys(ENUMS), "summary"];
    /**
     * 输入：value（不受信任的资料）、partial（是否允许未回答）。
     * 输出：仅含白名单资料的副本，非法内容返回 null。
     * 功能：枚举、互斥与完整性统一校验，不把个人习惯伪造为每日记录。
     */
    function normalize(value, partial = false) {
        if (!value || typeof value !== "object" || Array.isArray(value)) return null;
        if (!["zh", "en"].includes(value.language)) return null;
        const safe = { version: 4, language: value.language };
        // 阶段一：逐字段验证语义键；不接受任意文字、ID、原型字段或人口资料猜测。
        for (const [key, allowed] of Object.entries(ENUMS)) {
            const answer = value[key];
            if (["interests", "diet"].includes(key)) {
                if (!Array.isArray(answer) || answer.length > allowed.length ||
                    answer.some(item => !allowed.includes(item)) || new Set(answer).size !== answer.length ||
                    (!partial && answer.length === 0)) return null;
                if (key === "diet" && answer.includes("none") && answer.length > 1) return null;
                safe[key] = allowed.filter(item => answer.includes(item));
            } else if (partial && answer === null) safe[key] = null;
            else if (!allowed.includes(answer)) return null;
            else safe[key] = answer;
        }
        return safe;
    }
    /** 输入：value（保存对象）。输出：有效完成资料或 null。功能：完成时间与七项答案同时有效才跳过引导。 */
    function completed(value) {
        const safe = normalize(value);
        if (!safe || ![3, 4].includes(value.version) || typeof value.completedAt !== "string" || !Number.isFinite(Date.parse(value.completedAt))) return null;
        return { ...safe, completedAt: value.completedAt,
            updatedAt: typeof value.updatedAt === "string" && Number.isFinite(Date.parse(value.updatedAt)) ? value.updatedAt : value.completedAt };
    }
    /** 输入：draft（草稿对象）。输出：安全草稿或 null。功能：恢复途中回答，禁止通过伪造 step 跳过未回答的问题。 */
    function draft(value) {
        const safe = normalize(value?.profile, true);
        if (!safe || !STEPS.includes(value?.step)) return null;
        let last = 8;
        for (let i = 1; i <= 7; i++) {
            const item = safe[STEPS[i]];
            if (item === null || Array.isArray(item) && !item.length) { last = i; break; }
        }
        return { version: 1, profile: safe, step: STEPS[Math.min(STEPS.indexOf(value.step), last)] };
    }
    /** 输入：storage（可注入存储）、key。输出：JSON 内容或 null。功能：损坏或禁用存储不删除其他数据。 */
    function read(storage, key = KEY) { try { return JSON.parse(storage?.getItem(key) || "null"); } catch { return null; } }
    /** 输入：storage、资料、既有资料、当前时间。输出：{ok, profile}。功能：验证完成后原子写单个 key；失败不标为已完成。 */
    function save(storage, value, previous = null, now = new Date()) {
        const safe = normalize(value);
        if (!safe || !storage) return { ok: false, profile: null };
        const stamp = now.toISOString(), data = { ...safe, completedAt: completed(previous)?.completedAt || stamp, updatedAt: stamp };
        try {
            // 阶段二：只写个人资料键；写完读回确认，不调用 clear 或改写任一日记键。
            storage.setItem(KEY, JSON.stringify(data));
            const stored = completed(read(storage));
            if (!stored || JSON.stringify(stored) !== JSON.stringify(data)) return { ok: false, profile: null };
            try { storage.removeItem(DRAFT_KEY); } catch { /* 有效完成资料优先于残留草稿。 */ }
            return { ok: true, profile: data };
        } catch { return { ok: false, profile: null }; }
    }
    const api = Object.freeze({ KEY, DRAFT_KEY, ENUMS, STEPS, normalize, completed, draft, read, save });
    globalThis.NavaFirstNotesProfile = api;
    if (typeof __fluffyModules !== "undefined") __fluffyModules["first-notes-profile.js"] = api;
})();
