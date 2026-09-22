__fluffyModules["animation.js"] = (() => {
    const { displayRows, circularPositions } = __fluffyModules["model.js"];
    const { makeHandwriting, sampleHandwriting, drawHandwriting } = __fluffyModules["handwriting.js"];
    const M = window.M;
    /**
     * 输入：id（DOM标识）。
     * 输出：对应页面元素或null。
     * 功能：集中按ID定位界面元素。
     */
    const $ = id => document.getElementById(id);
    /**
     * 输入：name（公开图片文件名）。
     * 输出：内嵌图片或相对资源地址。
     * 功能：让同一动画同时支持源码部署和离线HTML。
     */
    const asset = name => window.CAT_ASSETS?.[name] || `assets/${name}`;
    // 活动项的标题、笔路、横线统一使用这个行原点，循环副本只改变整体位移。
    const PAPER = Object.freeze({
        originY: 470, pitch: 90, writingOffset: -22, clipTop: 417, clipBottom: 707, labelOffset: -12
    });
    const HERO_SPEED = 1 / .85;
    const ANCHORS = [[74, 335, 8, "star"], [316, 332, 7, "star"], [348, 518, 8, "star"], [53, 411, 12, "bar"], [41, 472, 8, "bar"], [41, 548, 11, "bar"], [293, 385, 10, "bar"], [337, 426, 12, "bar"], [212, 322, 9, "bar"], [320, 570, 8, "bar"]];
    /**
     * 输入：ctx、x、y、radius、angle、color（星形外观和位置）。
     * 输出：无。
     * 功能：绘制从前爪发射的撒花粒子，不用贴图切换模拟撒花。
     */
    function drawStar(ctx, x, y, radius, angle, color) {
        ctx.save();
        ctx.translate(x, y);
        ctx.rotate(angle);
        ctx.fillStyle = color;
        ctx.strokeStyle = color;
        ctx.lineWidth = 2.4;
        ctx.lineJoin = "round";
        ctx.beginPath();
        for (let i = 0; i < 10; i++) {
            const r = i % 2 ? radius * .53 : radius, a = i * Math.PI / 5 - Math.PI / 2;
            i ? ctx.lineTo(Math.cos(a) * r, Math.sin(a) * r) : ctx.moveTo(Math.cos(a) * r, Math.sin(a) * r);
        }
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
        ctx.restore();
    }
    class CompanionAnimation {
        /**
         * 输入：callbacks（阶段改变、载入完成等回调）。
         * 输出：CompanionAnimation 实例。
         * 功能：建立单一角色、时间轴与画布；记录内容由用户确认后单独注入。
         */
        constructor(callbacks = {}) {
            this.callbacks = callbacks;
            this.canvas = $("actor-canvas");
            this.ctx = this.canvas.getContext("2d");
            this.scene = "home";
            this.time = 0;
            this.idle = 7;
            this.playing = true;
            this.speed = 1;
            this.ready = false;
            this.record = null;
            this.reference = false;
            this.saved = false;
            this.last = 0;
            this.petAt = -999;
            this.level = 0;
            this.entryMode = "idle";
            this.attention = 0;
            this.thinking = 0;
            this.bridge = false;
            this.heroClock = 0;
            this.metrics = {
                frame: 0, penDown: false, penTip: [0, 0], inkTip: [0, 0], paperOffset: 0, renderer: "loading"
            };
        }
        /**
         * 输入：无。
         * 输出：Promise<void>。
         * 功能：读取已确认的原猫图层；整个动作过程不交换姿势图片。
         */
        async initialize() {
            const entries = await Promise.all(Object.entries(window.FLuffyArt).map(([key, meta]) => new Promise((resolve, reject) => {
                const image = new Image();
                image.onload = () => resolve([key, image]);
                image.onerror = () => reject(Error(`无法读取角色图层：${meta.file}`));
                image.src = asset(meta.file);
            })));
            const images = Object.fromEntries(entries);
            this.actor = new window.CatActor(images, window.FLuffyArt);
            this.title = new window.HandTitle(images.title, window.FLuffyArt.title);
            this.ready = true;
            this.metrics.renderer = this.actor.mesh ? "WebGL + Canvas2D" : "Canvas2D CPU mesh";
            $("loading").hidden = true;
            this.render();
            requestAnimationFrame(this.tick.bind(this));
            this.callbacks.onReady?.();
        }
        /**
         * 输入：record（经过字段校验、仍可返回修改的不可变展示快照）。
         * 输出：无。
         * 功能：从真实字段构造笔画和时序；动画重播不会重新调用 AI。
         */
        setRecord(record) {
            this.record = record;
            this.rows = record.displayRows || displayRows(record);
            this.lines = this.rows.map(row => makeHandwriting(row.value, 250, 54));
            let cursor = 2.15;
            this.schedule = this.lines.map(line => {
                const duration = M.clamp(line.duration * .83, 2.25, 6.1), slot = { start: cursor, end: cursor + duration };
                cursor += duration + .95;
                return slot;
            });
            this.writeEnd = this.schedule.at(-1).end;
            this.duration = this.writeEnd + 11;
            this.saved = false;
        }
        /**
         * 输入：无。
         * 输出：当前场景总时长。
         * 功能：入口无剧情时间轴，庆祝和记录分别使用自身时长。
         */
        maximum() {
            return this.scene === "celebrate" ? 7 / HERO_SPEED : this.scene === "record" ? this.duration : 0;
        }
        /**
         * 输入：无。
         * 输出：阶段编号 0..4。
         * 功能：同步记录阶段的标题及可访问性提示。
         */
        phase() {
            return this.scene === "entry" ? 0 : this.scene === "celebrate" ? 1 : this.time < this.writeEnd ? 2 : this.time < this.writeEnd + 3.75 ? 3 : 4;
        }
        /**
         * 输入：scene（entry/celebrate/record）、time（场景时间）、play（是否播放）。
         * 输出：boolean，是否成功切换。
         * 功能：限制未确认记录直接进入动画，同时保持确认后的数据不被重置。
         */
        setScene(scene, time = 0, play = true) {
            if (!["home", "entry", "celebrate", "record", "focus", "history", "tasks", "profile", "review"].includes(scene) || (["celebrate", "record"].includes(scene) && !this.record))
                return false;
            this.bridge = this.scene === "entry" && scene === "record";
            this.bridgeAttention = this.attention;
            this.bridgeThinking = this.thinking;
            this.scene = scene;
            this.time = M.clamp(time, 0, scene === "record" ? this.duration : 7 / HERO_SPEED);
            if (scene === "celebrate")
                this.heroClock = time;
            if (scene === "entry")
                this.entryMode = "idle";
            this.playing = play;
            this.last = 0;
            this.petAt = -999;
            this.render();
            return true;
        }
        /**
         * 输入：time（记录场景时间）。
         * 输出：内页累计纵向偏移，单位设计像素。
         * 功能：完成一项后抬笔再送纸；末尾继续前移一圈，实现无反向跳回的汇总。
         */
        paperOffset(time) {
            if (time < 2.15)
                return PAPER.writingOffset * M.range(time, 1.55, 2.15);
            for (let i = 0; i < 3; i++) {
                const slot = this.schedule[i], offset = PAPER.writingOffset - PAPER.pitch * i;
                if (time <= slot.end)
                    return offset;
                if (i < 2 && time < this.schedule[i + 1].start)
                    return M.mix(offset, offset - PAPER.pitch, M.range(time, slot.end + .12, this.schedule[i + 1].start - .12));
            }
            return M.mix(PAPER.writingOffset - PAPER.pitch * 2, -PAPER.pitch * 3, M.range(time, this.writeEnd + .25, this.writeEnd + 2.25));
        }
        /**
         * 输入：index（逻辑行 0..2）、offset（内页累计偏移）。
         * 输出：内容起点 Y 坐标，尚未做循环取模。
         * 功能：标题和笔尖使用同一个坐标系，避免 Notes 只在底部副本出现。
         */
        rowOrigin(index, offset) {
            return PAPER.originY + PAPER.pitch * index + offset;
        }
        /**
         * 输入：index（记录行）、clock（行内笔画时间）、offset（内页偏移）。
         * 输出：{tip,down}，全局画布坐标中的落笔位置。
         * 功能：将笔画位置映射到固定卡片内；角色笔尖和墨迹直接共用该值。
         */
        linePoint(index, clock, offset) {
            const p = sampleHandwriting(this.lines[index], clock);
            return { tip: [56 + p.x, this.rowOrigin(index, offset) + p.y], down: p.down };
        }
        /**
         * 输入：time（场景时间）。
         * 输出：笔尖位置和落纸状态。
         * 功能：为起笔、书写、换行分别计算连续路径，并在换行时抬笔。
         */
        activeNib(time) {
            if (time < this.schedule[0].start) {
                const dest = this.linePoint(0, 0, PAPER.writingOffset).tip;
                return { tip: M.point([216, 431], dest, M.range(time, 1.45, 2.15)), down: false };
            }
            for (let i = 0; i < 3; i++) {
                const slot = this.schedule[i];
                if (time >= slot.start && time <= slot.end)
                    return this.linePoint(i, (time - slot.start) / (slot.end - slot.start) * this.lines[i].duration, this.paperOffset(time));
                if (i < 2 && time > slot.end && time < this.schedule[i + 1].start) {
                    const a = this.linePoint(i, this.lines[i].duration, this.paperOffset(slot.end)).tip, b = this.linePoint(i + 1, 0, this.paperOffset(this.schedule[i + 1].start)).tip, u = M.range(time, slot.end, this.schedule[i + 1].start), tip = M.point(a, b, u);
                    tip[1] -= Math.sin(u * Math.PI) ** 2 * 12;
                    return { tip, down: false };
                }
            }
            return { ...this.linePoint(2, this.lines[2].duration, PAPER.writingOffset - PAPER.pitch * 2), down: false };
        }
        /**
         * 输入：time（记录场景时间）。
         * 输出：角色所需的笔、前爪、收手与趴睡参数。
         * 功能：使动态长度的记录复用原连续动作，而不是固定示例时长。
         */
        pose(time) {
            const nib = this.activeNib(time), relative = time - this.writeEnd, put = M.range(relative, 0, 2.2), angle = M.mix(-.4 + Math.sin(time * 4.9) * .014 * (1 - put), 1.69, put), tip = M.point(nib.tip, [268, 421], put);
            tip[1] -= Math.sin(put * Math.PI) * 20;
            // 目光稍滞后于笔尖；只平滑头部，笔尖仍紧贴真实墨迹。
            const looked = [0, .06, .12, .18].map(lag => this.activeNib(Math.max(0, time - lag)).tip[0]);
            const look = M.clamp((looked.reduce((a, b) => a + b, 0) / looked.length - 187) / 110, -1, 1) * (1 - put);
            return {
                lookOverride: look, t: time < this.writeEnd ? time / this.writeEnd * 10.8 : 10.8 + relative, idle: this.idle, pen: { tip, angle }, grip: [tip[0] + Math.sin(angle) * 29, tip[1] - Math.cos(angle) * 29], release: time < this.writeEnd ? 1 - M.range(time, .65, 1.65) : M.range(relative, 2.28, 3.45), penOpacity: M.range(time, .6, 1.5), sleep: M.range(relative, 4, 7.8), headSleep: M.range(relative, 4.7, 8.4), tailSleep: M.range(relative, 5.4, 9.45), nib, pet: Math.sin(Math.PI * M.clamp((this.idle - this.petAt) / 1.6))
            };
        }
        /**
         * 输入：time（记录场景时间）。
         * 输出：无。
         * 功能：绘制三份逻辑行的循环副本；所有副本共用各行已完成的墨迹进度。
         */
        drawPaper(time) {
            const ctx = this.ctx, offset = this.paperOffset(time);
            this.metrics.paperOffset = offset;
            this.metrics.paperRows = [];
            const clipBottom = M.mix(686, PAPER.clipBottom, M.range(time, this.writeEnd + .25, this.writeEnd + 2.25));
            this.metrics.paperClip = [PAPER.clipTop, clipBottom];
            ctx.save();
            // 阶段一：遵守卡片圆角，但不裁掉正在写的顶部标题。
            ctx.beginPath();
            ctx.roundRect(21, 415, 351, 302, 44);
            ctx.clip();
            ctx.beginPath();
            ctx.rect(42, PAPER.clipTop, 310, clipBottom - PAPER.clipTop);
            ctx.clip();
            // 阶段二：“标题＋内容＋书写线”作为一个完整单元参与循环。
            for (let i = 0; i < this.rows.length; i++) {
                const slot = this.schedule[i], line = this.lines[i], progress = M.clamp((time - slot.start) / (slot.end - slot.start));
                for (const position of circularPositions(i, offset, PAPER.pitch)) {
                    const y = PAPER.originY + position;
                    if (y + (line.ruleOffsets?.at(-1) || line.height) + 2 < PAPER.clipTop || y - 29 > clipBottom)
                        continue;
                    const labelY = y + PAPER.labelOffset;
                    ctx.fillStyle = "#748caf";
                    ctx.font = '600 17px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif';
                    ctx.fillText(this.rows[i].label, 56, labelY);
                    // 横线紧随本视觉行的墨迹下边缘；折行后每行也各有一条线。
                    const rules = line.ruleOffsets || [line.size + 3];
                    ctx.strokeStyle = "#dce5ee";
                    ctx.lineWidth = 1.25;
                    for (const rule of rules) {
                        ctx.beginPath();
                        ctx.moveTo(53, y + rule);
                        ctx.lineTo(340, y + rule);
                        ctx.stroke();
                    }
                    if (time >= slot.start)
                        drawHandwriting(ctx, line, progress * line.duration, 56, y);
                    this.metrics.paperRows.push({
                        index: i, label: this.rows[i].label, labelY, inkY: y,
                        rules: rules.map(rule => y + rule), active: time >= slot.start && time <= slot.end,
                        canonical: Math.abs(y - this.rowOrigin(i, offset)) < .001
                    });
                }
            }
            ctx.restore();
        }
        /**
         * 输入：time（庆祝场景连续时间）。
         * 输出：无。
         * 功能：四轮撒花与前爪出手同步，最后的彩纸轻微漂浮等待用户继续。
         */
        drawConfetti(time) {
            const ctx = this.ctx, colors = ["#fff39a", "#afe5f5", "#ffffff"];
            for (let burst = 0; burst < 4; burst++)
                for (let i = 0; i < ANCHORS.length; i++) {
                    const birth = .53 + burst * 1.45 + (i % 3) * .034, age = time - birth;
                    if (age < 0)
                        continue;
                    const [ax, ay, r, shape] = ANCHORS[i], left = ax < 194, arms = this.actor.heroArms(birth), root = left ? arms.left : arms.right;
                    const target = [ax + (burst === 3 ? 0 : Math.sin(i * 3 + burst) * 7), ay], u = M.clamp(age / 1.65), point = M.bez([root, [root[0] + (left ? -42 : 42), root[1] - 100], [target[0] + (left ? -20 : 20), target[1] - 37], target], M.easeOut(u));
                    if (u >= 1) {
                        point[0] += Math.sin(time * .8 + i) * 1.6;
                        point[1] += Math.sin(time * .93 + i * 1.4) * 2.1;
                    }
                    const alpha = burst === 3 ? 1 : 1 - M.range(age, 2.45, 3.1);
                    if (alpha < .001)
                        continue;
                    ctx.save();
                    ctx.globalAlpha = alpha;
                    const rotation = age * (left ? 1 : -1) * .65 + i * .65, color = shape === "star" ? "#fff3a0" : colors[i % 3];
                    if (shape === "star")
                        drawStar(ctx, ...point, r, rotation, color);
                    else {
                        ctx.translate(...point);
                        ctx.rotate(rotation);
                        ctx.strokeStyle = color;
                        ctx.lineWidth = 7;
                        ctx.lineCap = "round";
                        ctx.beginPath();
                        ctx.moveTo(0, -r / 2);
                        ctx.lineTo(0, r / 2);
                        ctx.stroke();
                    }
                    ctx.restore();
                }
            ctx.save();
            ctx.globalAlpha = M.range(time, 2.8, 4);
            ctx.strokeStyle = "#fff4a6";
            ctx.lineWidth = 6;
            ctx.lineCap = "round";
            for (const [x, y, xx, yy] of [[51, 144, 56, 153], [31, 165, 42, 171], [30, 184, 39, 185], [338, 135, 333, 145], [354, 160, 344, 165]]) {
                ctx.beginPath();
                ctx.moveTo(x, y);
                ctx.lineTo(xx, yy);
                ctx.stroke();
            }
            ctx.restore();
        }
        /**
         * 输入：无。
         * 输出：无。
         * 功能：同步静态界面、按钮可用状态与当前动画场景，不更新用户输入值。
         */
        synchronize() {
            if (this.callbacks.synchronize?.(this))
                return;
            const entry = this.scene === "entry", hero = this.scene === "celebrate", record = this.scene === "record", phase = this.phase();
            const bridge = record && this.bridge ? M.range(this.time, 0, 1.55) : 1;
            const quiet = this.entryMode === "idle";
            $("screen").dataset.scene = this.scene;
            $("entry-panel").hidden = !entry || !quiet;
            $("voice-panel").hidden = !entry || quiet;
            $("entry-heading").hidden = !entry && !(record && this.bridge && bridge < .8);
            $("entry-heading").style.opacity = entry ? 1 : 1 - M.range(bridge, 0, .6);
            $("entry-bubble").hidden = !entry && !(record && this.bridge && bridge < .6);
            $("entry-bubble").style.opacity = entry ? 1 : 1 - M.range(bridge, 0, .55);
            $("green-bg").style.opacity = hero ? 1 : record && !this.bridge ? 1 - M.range(this.time, 0, .65) : 0;
            $("record-card").hidden = hero;
            const p = entry ? 0 : bridge;
            $("record-card").style.top = `${M.mix(368, 414, p)}px`;
            $("record-card").style.left = `${M.mix(23, 20, p)}px`;
            $("record-card").style.width = `${M.mix(347, 353, p)}px`;
            $("record-card").style.height = `${M.mix(344, 304, p)}px`;
            $("record-card").style.borderRadius = `${M.mix(29, 45, p)}px`;
            $("record-heading").hidden = !record;
            $("record-heading").style.opacity = record ? M.range(this.time, .45, 1.5) : 0;
            $("hero-quote").hidden = !hero;
            $("hero-subtitle").hidden = !hero;
            $("back").hidden = entry;
            $("primary").hidden = entry;
            $("confirm-entry").hidden = !entry;
            $("primary").classList.toggle("white", hero);
            $("primary").disabled = hero ? this.time < 5.8 / HERO_SPEED : record ? this.time < this.writeEnd : false;
            $("primary-label").textContent = hero ? "Continue" : this.saved ? "再记一条" : this.time >= this.writeEnd + 8.4 ? "完成" : "保存记录";
            $("hero-quote").style.opacity = M.range(this.time, 1.5, 2.5);
            $("hero-subtitle").style.opacity = M.range(this.time, .8, 1.5);
            $("pet").hidden = entry;
            $("pet").style.top = hero ? "371px" : "193px";
            $("pet").style.height = hero ? "248px" : "223px";
            $("edit-record").hidden = !record || this.time < 1.6;
            const titles = ["今天的运动，讲给我听。", "Great job!", "Log Your Workout", "Almost done!", "All set! ♡"];
            const subtitles = ["", "", "Write it down, step by step!", "Putting it away…", "Rest well, you did it."];
            $("record-title").textContent = titles[phase];
            $("record-subtitle").textContent = subtitles[phase];
            if (phase !== this.lastPhase) {
                this.lastPhase = phase;
                this.callbacks.onPhase?.(phase);
            }
            if (record && this.lastA11yRecord !== this.record) {
                $("record-a11y").textContent = this.rows.map(row => `${row.label}: ${row.value}`).join("。");
                this.lastA11yRecord = this.record;
            }
        }
        /**
         * 输入：无，读取本实例当前时间与场景。
         * 输出：无，更新 Canvas 和必要 DOM。
         * 功能：以同一套身体、头、尾巴和前爪连续渲染，没有跳跃或姿势帧替换。
         */
        render() {
            if (!this.ready)
                return;
            const ctx = this.ctx, start = performance.now();
            ctx.setTransform(2, 0, 0, 2, 0, 0);
            ctx.clearRect(0, 0, 393, 852);
            this.synchronize();
            // 阶段一：输入、聆听和整理共用记录猫；只改变头部倾斜、耳朵与呼吸。
            if (this.scene === "home") {
                // 首页沿用庆祝页的同一原画，只使用待机参数，不循环播放撒花。
                const pet = Math.sin(Math.PI * M.clamp((this.idle - this.petAt) / 1.8));
                this.actor.companionPet = pet;
                this.actor.homeLook = this.homeLook || 0;
                ctx.save();
                ctx.translate(18, 207);
                ctx.scale(.94, .84);
                this.actor.hero(ctx, 8 + this.idle);
                ctx.restore();
            }
            else if (this.scene === "focus") {
                // 专注时把动作缩小、放慢；暂停与休息姿态仍然平滑追踪。
                const rest = this.focusRest || 0;
                ctx.save();
                ctx.translate(100, 420);
                ctx.scale(.49, .49);
                this.actor.record(ctx, {
                    t: 0, idle: this.idle * .65, sleep: .8 * rest, headSleep: .8 * rest, tailSleep: .9,
                    pen: null, grip: [177, 405], release: 1, lookOverride: 0
                });
                ctx.restore();
            }
            else if (this.scene === "review") {
                // 同一只猫在卡片上方趴着：说话/倾听仅轻抬头与短前爪，身体接触点不平移。
                const listen = this.reviewListen || 0, think = this.reviewThink || 0, talk = this.reviewTalk || 0;
                const nod = (this.reviewNod || 0) * Math.sin(this.idle * 2.4);
                const pulse = .5 + .5 * Math.sin(this.idle * 2.5), wave = (this.reviewWave || 0) * pulse;
                const pet = Math.sin(Math.PI * M.clamp((this.idle - this.petAt) / 1.8));
                ctx.save();
                ctx.translate(17, 45); ctx.scale(.65, .63);
                this.actor.record(ctx, {
                    t: 0, idle: this.idle * .83, sleep: .82, headSleep: .71 - .36 * listen - .25 * talk - .13 * think + .024 * nod,
                    tailSleep: .91, pen: null, grip: [140, 410], release: 1,
                    lookOverride: .12 + .12 * listen, headTilt: -.025 * listen + .024 * think + .011 * talk * Math.sin(this.idle * 2.2) + .01 * nod,
                    attention: listen, thought: think, pet, chatMotion: true,
                    pawLift: wave * .85 + pet * .25, mouthTalk: talk * (.5 + .5 * Math.sin(this.idle * 4.4))
                });
                ctx.restore();
            }
            else if (this.scene === "entry") {
                const idlePose = {
                    t: 0, idle: this.idle, sleep: 0, headSleep: 0, tailSleep: 0,
                    pen: null, grip: [177, 405], release: 1, lookOverride: .08 + this.attention * .22,
                    headTilt: -.072 * this.attention + .023 * this.thinking,
                    attention: this.attention, thought: this.thinking, level: this.level
                };
                ctx.save();
                ctx.translate(43, 35);
                ctx.scale(.78, .78);
                this.actor.record(ctx, idlePose);
                ctx.restore();
            }
            else if (this.scene === "celebrate") {
                this.actor.hero(ctx, this.heroClock * HERO_SPEED);
                this.drawConfetti(this.heroClock * HERO_SPEED);
                this.title.draw(ctx, this.time * HERO_SPEED);
            }
            else if (this.scene === "record") {
                // 阶段二：卡片由表单原位置连续展开，猫的原图层也沿同一路径进入写字姿态。
                ctx.save();
                ctx.globalAlpha = M.range(this.time, .85, 1.8);
                this.drawPaper(this.time);
                ctx.restore();
                const pose = this.pose(this.time), bridge = this.bridge ? M.range(this.time, 0, 1.55) : 1;
                pose.lookOverride = bridge < 1 ? M.mix(.08 + this.bridgeAttention * .22, M.clamp((pose.grip[0] - 176) / 110, -1, 1), bridge) : pose.lookOverride;
                pose.headTilt = (-.072 * this.bridgeAttention + .023 * this.bridgeThinking) * (1 - bridge);
                pose.attention = this.bridgeAttention * (1 - bridge);
                pose.thought = this.bridgeThinking * (1 - bridge);
                ctx.save();
                ctx.translate(43 * (1 - bridge), 35 * (1 - bridge));
                ctx.scale(M.mix(.78, 1, bridge), M.mix(.78, 1, bridge));
                if (!this.bridge)
                    ctx.globalAlpha = M.range(this.time, 0, .5);
                this.actor.record(ctx, pose);
                ctx.restore();
                this.metrics.penTip = pose.pen.tip;
                this.metrics.inkTip = pose.nib.tip;
                this.metrics.penDown = pose.nib.down && this.time <= this.writeEnd;
                this.metrics.bridge = bridge;
                const alpha = M.range(this.time, 1.55, 2.2) * (1 - M.range(this.time, this.writeEnd - 1, this.writeEnd)) * (.8 + .1 * Math.sin(this.idle * 1.8));
                if (alpha > 0) {
                    ctx.save();
                    ctx.globalAlpha = alpha;
                    ctx.strokeStyle = "#65c361";
                    ctx.lineCap = "round";
                    ctx.lineWidth = 6;
                    ctx.beginPath();
                    ctx.moveTo(309, 251);
                    ctx.lineTo(323, 232);
                    ctx.moveTo(318, 270);
                    ctx.lineTo(331, 266);
                    ctx.stroke();
                    ctx.restore();
                }
            }
            this.metrics.renderMs = performance.now() - start;
            this.metrics.frame++;
            this.callbacks.onRender?.();
        }
        /**
         * 输入：now（浏览器高精度时间戳）。
         * 输出：无，预约下一帧。
         * 功能：按真实时间连续播放；页面隐藏、弹窗或原图对照时暂停，避免后台偷跑。
         */
        tick(now) {
            const dt = this.last ? Math.min(.06, (now - this.last) / 1000) : 0;
            this.last = now;
            const blocked = document.hidden || Boolean(document.querySelector("dialog[open]"));
            if (this.ready && this.playing && !blocked) {
                this.idle += dt * this.speed * (this.reducedMotion ? .18 : 1);
                this.heroClock += dt * this.speed;
                this.time = Math.min(this.maximum(), this.time + dt * this.speed);
                const blend = 1 - Math.exp(-dt * 4.6);
                this.homeLook = (this.homeLook || 0) + ((this.homeLookTarget || 0) - (this.homeLook || 0)) * blend;
                this.focusRest = (this.focusRest || 0) + ((this.focusRestTarget || 0) - (this.focusRest || 0)) * blend;
                this.attention += ((this.entryMode === "listening" ? 1 : 0) - this.attention) * blend;
                this.thinking += ((this.entryMode === "thinking" ? 1 : 0) - this.thinking) * blend;
                // 阶段二：回顾的状态变化使用同一低通缓动，不按录音/回复事件硬切姿态。
                this.reviewListen = (this.reviewListen || 0) + ((this.reviewMode === "listen" ? 1 : 0) - (this.reviewListen || 0)) * blend;
                this.reviewThink = (this.reviewThink || 0) + ((this.reviewMode === "think" || this.reviewMode === "talk" && this.reviewGesture === "think" ? 1 : 0) - (this.reviewThink || 0)) * blend;
                this.reviewTalk = (this.reviewTalk || 0) + ((this.reviewMode === "talk" ? 1 : 0) - (this.reviewTalk || 0)) * blend;
                this.reviewWave = (this.reviewWave || 0) + ((this.reviewMode === "talk" && this.reviewGesture === "wave" ? 1 : 0) - (this.reviewWave || 0)) * blend;
                this.reviewNod = (this.reviewNod || 0) + ((this.reviewMode === "talk" && this.reviewGesture === "nod" ? 1 : 0) - (this.reviewNod || 0)) * blend;
                this.render();
            }
            requestAnimationFrame(this.tick.bind(this));
        }
    }
    return { CompanionAnimation };
})();
