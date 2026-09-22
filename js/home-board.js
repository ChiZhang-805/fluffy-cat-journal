__fluffyModules["home-board.js"] = (() => {
    "use strict";
    const { CATEGORIES, DEFAULT_ORDER, validOrder, summary } = __fluffyModules["catalog.js"];
    const Store = __fluffyModules["journal-store.js"];
    const SLOTS = [[18, 151], [139, 151], [139, 275], [260, 275], [18, 399], [139, 399]];
    class HomeBoard {
        /**
         * 输入：root、actions（打开、菜单、触摸回调）。
         * 输出：HomeBoard。
         * 功能：创建可单击、长按、拖动的独立组件。
         */
        constructor(root, actions) {
            this.root = root;
            this.actions = actions;
            this.order = validOrder(Store.read("fluffy-home-order-v1", DEFAULT_ORDER));
            this.cards = new Map();
            this.press = null;
            for (const id of DEFAULT_ORDER) {
                const c = CATEGORIES[id], b = document.createElement("button");
                b.type = "button";
                b.className = `home-widget ${c.tone}`;
                b.dataset.category = id;
                b.innerHTML = `${FluffyIcons.svg(c.icon)}<span class="widget-name"></span><strong class="widget-value"></strong><small class="widget-sub"></small><span class="widget-dot" aria-hidden="true"></span>`;
                b.querySelector(".widget-name").textContent = c.name;
                b.setAttribute("aria-label", `${c.name}：点击记录，长按快捷操作，长按后拖动可排序`);
                this.root.append(b);
                this.cards.set(id, b);
                this.bind(b, id);
            }
            // 阶段一：在 window 接住移出卡片后的事件，触摸离开边缘也能可靠结束手势。
            window.addEventListener("pointermove", e => this.move(e));
            window.addEventListener("pointerup", e => this.end(e, false));
            window.addEventListener("pointercancel", e => this.end(e, true));
            window.addEventListener("blur", () => this.cancel());
            document.addEventListener("visibilitychange", () => {
                if (document.hidden)
                    this.cancel();
            });
            this.layout();
            this.update();
        }
        /**
         * 输入：b（按钮）、id。
         * 输出：无。
         * 功能：分开短按、长按和辅助键盘操作，禁止长按后误进入页面。
         */
        bind(b, id) {
            b.addEventListener("pointerdown", e => {
                if (e.button !== 0 || !e.isPrimary)
                    return;
                e.preventDefault();
                this.cancel();
                const p = this.press = {
                    id, pointerId: e.pointerId, x: e.clientX, y: e.clientY, held: false, dragging: false, original: [...this.order]
                };
                b.setPointerCapture?.(e.pointerId);
                b.classList.add("pressing");
                this.actions.attend?.(id);
                p.timer = setTimeout(() => {
                    if (this.press !== p)
                        return;
                    p.held = true;
                    b.classList.add("held");
                    navigator.vibrate?.(12);
                }, 430);
            });
            b.addEventListener("contextmenu", e => {
                e.preventDefault();
                if (!this.press)
                    this.actions.menu(id);
            });
            b.addEventListener("click", e => {
                e.preventDefault();
                if (e.detail === 0 && performance.now() - (this.endedAt || 0) > 250)
                    this.actions.open(id);
            });
            b.addEventListener("keydown", e => {
                if (e.key === "Escape")
                    this.cancel();
                if (e.key === "ContextMenu" || (e.shiftKey && e.key === "F10")) {
                    e.preventDefault();
                    this.actions.menu(id);
                }
                if (e.altKey && ["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(e.key)) {
                    e.preventDefault();
                    this.reorder(id, /Left|Up/.test(e.key) ? -1 : 1);
                }
            });
        }
        /**
         * 输入：event。
         * 输出：无。
         * 功能：长按后才拖动；按设计像素换算并以邻近槽位重排，而非自由漂离屏幕。
         */
        move(event) {
            const p = this.press;
            if (!p || event.pointerId !== p.pointerId)
                return;
            const d = Math.hypot(event.clientX - p.x, event.clientY - p.y);
            if (!p.held) {
                if (d > 11)
                    this.cancel();
                return;
            }
            if (d < 7 && !p.dragging)
                return;
            p.dragging = true;
            const b = this.cards.get(p.id), r = this.root.getBoundingClientRect(), scale = r.width / 393;
            const x = (event.clientX - r.left) / scale, y = (event.clientY - r.top) / scale;
            b.classList.add("dragging");
            b.style.left = `${Math.max(6, Math.min(275, x - 55))}px`;
            b.style.top = `${Math.max(115, Math.min(437, y - 53))}px`;
            const nearest = SLOTS.map(([sx, sy], i) => ({ i, d: Math.hypot(sx + 56 - x, sy + 55 - y) })).sort((a, b) => a.d - b.d)[0];
            if (nearest.d < 78) {
                const a = this.order.indexOf(p.id), target = nearest.i;
                if (a !== target) {
                    [this.order[a], this.order[target]] = [this.order[target], this.order[a]];
                    this.layout(p.id);
                }
            }
        }
        /**
         * 输入：event、canceled。
         * 输出：无。
         * 功能：一次手势只执行打开、菜单、排序三者之一；取消恢复原顺序。
         */
        end(event, canceled) {
            const p = this.press;
            if (!p || event.pointerId !== p.pointerId)
                return;
            this.press = null;
            this.endedAt = performance.now();
            clearTimeout(p.timer);
            const b = this.cards.get(p.id);
            b.classList.remove("pressing", "held", "dragging");
            try {
                if (b.hasPointerCapture(p.pointerId))
                    b.releasePointerCapture(p.pointerId);
            }
            catch {
            }
            if (canceled)
                this.order = p.original;
            if (p.dragging && !canceled)
                Store.write("fluffy-home-order-v1", this.order);
            this.layout();
            if (!canceled && !p.dragging)
                p.held ? this.actions.menu(p.id) : this.actions.open(p.id);
            this.actions.release?.();
        }
        /**
         * 输入：无。
         * 输出：无。
         * 功能：切页/失焦时清理延时和拖拽，防止迟到菜单。
         */
        cancel() {
            if (this.press)
                this.end({ pointerId: this.press.pointerId }, true);
        }
        /**
         * 输入：skip（正在拖动的类别，可空）。
         * 输出：无。
         * 功能：其余组件平滑让位，保持错落而非固定两列三行。
         */
        layout(skip = null) {
            this.order.forEach((id, i) => {
                const b = this.cards.get(id);
                b.style.setProperty("--slot", i);
                if (id !== skip) {
                    b.style.left = `${SLOTS[i][0]}px`;
                    b.style.top = `${SLOTS[i][1]}px`;
                }
            });
        }
        /**
         * 输入：id、step（前/后移动）。
         * 输出：无。
         * 功能：提供键盘和菜单的排序替代方式。
         */
        reorder(id, step) {
            const i = this.order.indexOf(id), j = Math.max(0, Math.min(5, i + step));
            [this.order[i], this.order[j]] = [this.order[j], this.order[i]];
            Store.write("fluffy-home-order-v1", this.order);
            this.layout();
        }
        /**
         * 输入：无。
         * 输出：无。
         * 功能：恢复最初错落布局，不删除记录。
         */
        reset() {
            this.cancel();
            this.order = [...DEFAULT_ORDER];
            Store.write("fluffy-home-order-v1", this.order);
            this.layout();
        }
        /**
         * 输入：无。
         * 输出：无。
         * 功能：从实际保存记录更新六张卡片，不把草稿视为已完成。
         */
        update() {
            const records = Store.records();
            for (const [id, b] of this.cards) {
                const r = records.find(r => r.category === id), s = summary(r);
                b.querySelector(".widget-value").textContent = s.value;
                b.querySelector(".widget-sub").textContent = s.sub;
                b.classList.toggle("has-record", Boolean(r));
            }
        }
    }
    return { HomeBoard, SLOTS };
})();
