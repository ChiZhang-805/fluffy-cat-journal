/* 六类记录的唯一字段定义；界面、AI 草稿、校验、历史摘要共用同一个模型。 */
__fluffyModules["catalog.js"] = (() => {
    "use strict";
    const { cleanText, decimalNumber } = __fluffyModules["model.js"];
    const CATEGORIES = Object.freeze({
        mood: {
            name: "情绪", en: "Mood", title: "今天的心情，讲给我听。", greeting: "什么心情，都可以放在这里。", icon: "mood", tone: "blue", fields: [
                {
                    key: "mood", label: "现在的心情", type: "choice", options: ["开心", "平静", "低落", "烦躁", "紧张", "复杂"], required: true
                },
                {
                    key: "intensity", label: "这份感受有多强烈", type: "range", min: 1, max: 5, initial: "3", unit: " / 5"
                },
                {
                    key: "reason", label: "发生了什么", placeholder: "例如：完成了一件挂心的事", max: 60
                },
                {
                    key: "notes", label: "留给自己一句话", placeholder: "我想对自己说…", max: 32
                }
            ]
        },
        food: {
            name: "饮食", en: "Meal", title: "今天的美味，记下来吧。", greeting: "拍一张，或者讲给我听。", icon: "food", tone: "light", photo: true, fields: [
                {
                    key: "meal", label: "哪一餐", type: "choice", options: ["早餐", "午餐", "晚餐", "加餐"], required: true
                },
                {
                    key: "foods", label: "吃了什么", placeholder: "例如：米饭、鸡胸肉和西兰花", max: 60, required: true
                },
                {
                    key: "portion", label: "大概份量", placeholder: "例如：米饭半碗，鸡胸肉约 100 g", max: 50
                },
                {
                    key: "notes", label: "一句话备注", placeholder: "慢慢吃，好好照顾自己。", max: 32
                },
                {
                    key: "calories", label: "热量", type: "decimal", unit: "kcal", maxValue: 15000, group: "nutrition"
                },
                {
                    key: "protein", label: "蛋白质", type: "decimal", unit: "g", maxValue: 2000, group: "nutrition"
                },
                {
                    key: "carbs", label: "碳水化合物", type: "decimal", unit: "g", maxValue: 2000, group: "nutrition"
                },
                {
                    key: "fat", label: "脂肪", type: "decimal", unit: "g", maxValue: 2000, group: "nutrition"
                },
                {
                    key: "vitamins", label: "维生素信息", placeholder: "没有可靠依据时留空", max: 80, group: "nutrition"
                }
            ]
        },
        focus: {
            name: "专注", en: "Focus", title: "这一小段时间，留给你。", greeting: "一次一件事，我在旁边陪你。", icon: "focus", tone: "light", fields: [
                {
                    key: "task", label: "想专注做什么", placeholder: "例如：读完论文的方法部分", max: 60, required: true
                },
                {
                    key: "durationMinutes", label: "预计时间", type: "decimal", unit: "分钟", placeholder: "25", minValue: .1, maxValue: 720, required: true, estimate: true
                },
                {
                    key: "notes", label: "希望做到哪一步", placeholder: "把目标写得小一点、具体一点。", max: 60
                }
            ]
        },
        sport: {
            name: "运动", en: "Workout", title: "今天的运动，讲给我听。", greeting: "每一步，我都认真记下来。", icon: "sport", tone: "blue", fields: [
                {
                    key: "activity", label: "运动项目", placeholder: "例如：跑步", max: 40, required: true
                },
                {
                    key: "distanceKm", label: "距离", type: "decimal", unit: "km", placeholder: "5.2", maxValue: 2000, required: true
                },
                {
                    key: "durationMinutes", label: "时长", type: "decimal", unit: "分钟", placeholder: "30", minValue: .01, maxValue: 1440, required: true
                },
                {
                    key: "notes", label: "一句话备注", placeholder: "今天感觉怎么样？", max: 32, required: true
                }
            ]
        },
        sleep: {
            name: "睡眠", en: "Sleep", title: "昨晚，睡得还好吗？", greeting: "把昨晚放下，慢慢迎接今天。", icon: "sleep", tone: "light", fields: [
                {
                    key: "bedtime", label: "什么时候入睡", type: "datetime-local", required: true
                },
                {
                    key: "wakeTime", label: "什么时候醒来", type: "datetime-local", required: true
                },
                {
                    key: "quality", label: "醒来的感受", type: "choice", options: ["很精神", "还不错", "一般", "没睡够"], required: true
                },
                {
                    key: "notes", label: "一句话备注", placeholder: "例如：中途醒过一次", max: 32
                }
            ]
        },
        face: {
            name: "面部", en: "Check-in", title: "今天的状态，轻轻看看。", greeting: "记录变化，不给长相打分。", icon: "face", tone: "blue", photo: true, fields: [
                {
                    key: "feeling", label: "自己的感受", placeholder: "例如：有点困，但精神还好", max: 40, required: true
                },
                {
                    key: "eyeArea", label: "眼周观察", placeholder: "自己填写，或拍照后整理", max: 50
                },
                {
                    key: "skinAppearance", label: "皮肤外观", placeholder: "例如：局部泛红、光照偏暗", max: 60
                },
                {
                    key: "notes", label: "一句话备注", placeholder: "只记下观察，不作诊断。", max: 32
                }
            ]
        }
    });
    const DEFAULT_ORDER = ["mood", "food", "focus", "sport", "sleep", "face"];
    /**
     * 输入：id（类别）。
     * 输出：字段配置。
     * 功能：安全获取类别，未知值不当成运动记录。
     */
    function category(id) {
        if (!CATEGORIES[id])
            throw Error("找不到这个记录入口。");
        return CATEGORIES[id];
    }
    /**
     * 输入：id、raw（用户输入）、strict（是否提交校验）。
     * 输出：{ok,value,errors}。
     * 功能：统一校验数字、长度、选项及跨日睡眠。
     */
    function validate(id, raw, strict = true) {
        const def = category(id), value = {}, errors = {};
        // 阶段一：仅处理白名单字段，不将 API 附加字段直接保存或插入 HTML。
        for (const field of def.fields) {
            const text = cleanText(raw[field.key]);
            if (field.type === "decimal" || field.type === "range") {
                const n = decimalNumber(text);
                value[field.key] = n;
                if ((text || (strict && field.required)) && (n === null || n < (field.minValue ?? field.min ?? 0) || n > (field.maxValue ?? field.max ?? 100000)))
                    errors[field.key] = `${field.label}请填写有效数字。`;
            }
            else {
                value[field.key] = text;
                if (strict && field.required && !text)
                    errors[field.key] = `先填一下${field.label}。`;
                if (text.length > (field.max || 100))
                    errors[field.key] = `${field.label}请写得简短一点。`;
                if (text && field.options && !field.options.includes(text))
                    errors[field.key] = `请选择${field.label}。`;
                if (text && field.type === "datetime-local" && (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(text) || !Number.isFinite(new Date(text).getTime())))
                    errors[field.key] = "请填写有效日期和时间。";
            }
        }
        // 阶段二：睡眠用包含日期的时间相减，不把跨午夜误算成负数。
        if (id === "sleep" && value.bedtime && value.wakeTime && !errors.bedtime && !errors.wakeTime) {
            const hours = (new Date(value.wakeTime).getTime() - new Date(value.bedtime).getTime()) / 3600000;
            if (hours <= 0 || hours > 24)
                errors.wakeTime = "起床时间应晚于入睡时间，且本次不超过 24 小时。";
            else
                value.hours = Math.round(hours * 100) / 100;
        }
        return { ok: !Object.keys(errors).length, value, errors };
    }
    /**
     * 输入：s（日期时间字符串）。
     * 输出：HH:mm 或空串。
     * 功能：显示时分，保留存储中的完整日期。
     */
    function shortTime(s) {
        return String(s || "").split("T")[1]?.slice(0, 5) || "";
    }
    /**
     * 输入：record（已校验记录）。
     * 输出：三项短记录。
     * 功能：用实际确认内容生成猫咪笔路，完整营养信息仍保留在历史。
     */
    function rows(record) {
        const v = record.data, id = record.category;
        if (id === "sport")
            return [{ label: "Activity", value: `${v.activity} · ${v.distanceKm} km` }, { label: "Time", value: `${v.durationMinutes} min` }, { label: "Notes", value: v.notes }];
        if (id === "food")
            return [{ label: v.meal || "Meal", value: v.foods }, { label: "Nutrition · 估算", value: v.calories != null ? `约 ${v.calories} kcal` : v.portion || "份量未记录" }, { label: "Notes", value: v.notes || (v.protein != null ? `蛋白质约 ${v.protein} g` : "未填写备注") }];
        if (id === "mood")
            return [{ label: "Feeling", value: `${v.mood} · ${v.intensity || 3}/5` }, { label: "Moment", value: v.reason || "未填写事件" }, { label: "Notes", value: v.notes || "未填写备注" }];
        if (id === "sleep")
            return [{ label: "Sleep", value: `${shortTime(v.bedtime)} → ${shortTime(v.wakeTime)}` }, { label: "Duration", value: `${v.hours} h · ${v.quality}` }, { label: "Notes", value: v.notes || "未填写备注" }];
        if (id === "face")
            return [{ label: "My feeling · 自评", value: v.feeling }, { label: "Observation", value: v.eyeArea || v.skinAppearance || "未填写外观观察" }, { label: "Notes", value: v.notes || "只记录，不作诊断" }];
        return [{ label: "Focus", value: v.task }, { label: "Time", value: `${v.durationMinutes} min` }, { label: "Notes", value: v.notes || "一次一件事" }];
    }
    /**
     * 输入：record 或空值。
     * 输出：卡片上的简短数据与副标题。
     * 功能：仅展示真实历史，不虚构健康/能量分数。
     */
    function summary(record) {
        if (!record)
            return { value: "— —", sub: "尚未记录" };
        const v = record.data;
        return ({
            sport: { value: `${v.distanceKm} km`, sub: v.activity }, food: { value: v.calories == null ? v.meal : `约 ${v.calories}`, sub: v.calories == null ? v.foods : "kcal · " + v.meal }, mood: { value: v.mood, sub: `${v.intensity || 3} / 5 · 自我感受` }, sleep: { value: `${v.hours} h`, sub: v.quality }, face: { value: "已记录", sub: v.feeling }, focus: { value: `${Math.round((record.focus?.elapsedMs ?? v.durationMinutes * 60000) / 6000) / 10} min`, sub: v.task }
        })[record.category];
    }
    /**
     * 输入：order（任意存储值）。
     * 输出：六个唯一合法类别。
     * 功能：恢复拖拽排序，同时修复旧版或损坏的数据。
     */
    function validOrder(order) {
        return [...new Set([...(Array.isArray(order) ? order : []), ...DEFAULT_ORDER])].filter(id => CATEGORIES[id]).slice(0, 6);
    }
    return {
        CATEGORIES, DEFAULT_ORDER, category, validate, rows, summary, validOrder
    };
})();
