__fluffyModules["handwriting.js"] = (() => {
const { graphemes } = __fluffyModules["model.js"];
const CACHE = new Map();
/**
 * 输入：x（数值）。
 * 输出：限制在0到1的进度。
 * 功能：防止笔画播放时间超出合法区间。
 */
const clamp = (value, low = 0, high = 1) => Math.min(high, Math.max(low, value));
/**
 * 输入：points（二维路径点）。
 * 输出：各点对应的累计弧长数组。
 * 功能：用实际路程驱动笔尖与墨迹，避免短线和长线以同样时间突变。
 */
function arcLengths(points) {
    const lens = [0];
    for (let i = 1; i < points.length; i++)
        lens.push(lens.at(-1) + Math.hypot(points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1]));
    return lens;
}
/**
 * 输入：mask（二值字形），width、height（像素大小）。
 * 输出：单像素中心线的二值数组。
 * 功能：以 Zhang–Suen 细化提取任意系统字形；这不是汉字标准笔顺引擎。
 */
function thin(mask, width, height) {
    const image = mask.slice();
    for (let pass = 0; pass < 32; pass++) {
        let changed = false;
        for (let phase = 0; phase < 2; phase++) {
            const remove = [];
            for (let y = 1; y < height - 1; y++)
                for (let x = 1; x < width - 1; x++) {
                    const i = y * width + x;
                    if (!image[i])
                        continue;
                    const p = [image[i - width], image[i - width + 1], image[i + 1], image[i + width + 1], image[i + width], image[i + width - 1], image[i - 1], image[i - width - 1]];
                    const count = p.reduce((sum, value) => sum + value, 0);
                    if (count < 2 || count > 6)
                        continue;
                    let transitions = 0;
                    for (let k = 0; k < 8; k++)
                        if (!p[k] && p[(k + 1) % 8])
                            transitions++;
                    if (transitions !== 1)
                        continue;
                    const a = phase ? p[0] * p[2] * p[6] : p[0] * p[2] * p[4];
                    const b = phase ? p[0] * p[4] * p[6] : p[2] * p[4] * p[6];
                    if (!a && !b)
                        remove.push(i);
                }
            if (remove.length)
                changed = true;
            for (const i of remove)
                image[i] = 0;
        }
        if (!changed)
            break;
    }
    return image;
}
/**
 * 输入：mask（中心线像素），width、height（大小）。
 * 输出：有序折线路径数组。
 * 功能：将中心线图拆成可描写的路径，并处理闭环、交点和孤立点。
 */
function trace(mask, width, height) {
    const neighbours = new Map(), edges = new Set(), paths = [];
    /**
     * 输入：a/b（相邻像素的节点索引）。
     * 输出：与方向无关的边标识字符串。
     * 功能：标记已经走过的邻接边，防止同一笔段正反重复描绘。
     */
    const key = (a, b) => a < b ? `${a}:${b}` : `${b}:${a}`;
    for (let i = 0; i < mask.length; i++) {
        if (!mask[i])
            continue;
        const x = i % width, y = Math.floor(i / width), points = [];
        for (let dy = -1; dy <= 1; dy++)
            for (let dx = -1; dx <= 1; dx++) {
                if (!dx && !dy)
                    continue;
                const nx = x + dx, ny = y + dy, n = ny * width + nx;
                if (nx < 0 || nx >= width || ny < 0 || ny >= height || !mask[n])
                    continue;
                // 对直角连接避免再添加对角捷径，否则会在同一小区域反复描写。
                if (dx && dy && (mask[y * width + nx] || mask[ny * width + x]))
                    continue;
                points.push(n);
            }
        neighbours.set(i, points);
    }
    const starts = [...neighbours.keys()].sort((a, b) => (neighbours.get(a).length === 2) - (neighbours.get(b).length === 2) || a - b);
    for (const start of starts) {
        const ns = neighbours.get(start);
        if (!ns.length)
            paths.push([[start % width, Math.floor(start / width)], [start % width + .1, Math.floor(start / width)]]);
        for (const next of ns) {
            if (edges.has(key(start, next)))
                continue;
            const path = [start];
            let previous = start, current = next;
            while (true) {
                edges.add(key(previous, current));
                path.push(current);
                const adjacent = neighbours.get(current), options = adjacent.filter(n => n !== previous && !edges.has(key(current, n)));
                if (adjacent.length !== 2 || !options.length)
                    break;
                previous = current;
                current = options[0];
            }
            if (path.length > 1)
                paths.push(path.map(i => [i % width, Math.floor(i / width)]));
        }
    }
    // 方向由上到下、由左到右启发式排列；不声称这是语言学上的正确笔顺。
    for (const p of paths)
        if (p[0][1] + p[0][0] * .35 > p.at(-1)[1] + p.at(-1)[0] * .35)
            p.reverse();
    return paths.sort((a, b) => a[0][1] + a[0][0] * .35 - b[0][1] - b[0][0] * .35);
}
/**
 * 输入：char（一个字素）。
 * 输出：原字形画布、描写中心线与宽度。
 * 功能：为原手写字库未覆盖的中文、数字和标点生成可描写字形，避免丢字。
 */
function rasterGlyph(char) {
    if (CACHE.has(char))
        return CACHE.get(char);
    const canvas = document.createElement("canvas");
    canvas.width = 104;
    canvas.height = 96;
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    ctx.font = '500 64px "KaiTi","STKaiti","Noto Serif CJK SC",serif';
    ctx.fillStyle = "#113b73";
    ctx.textBaseline = "alphabetic";
    ctx.fillText(char, 8, 76);
    const data = ctx.getImageData(0, 0, canvas.width, canvas.height), mask = new Uint8Array(canvas.width * canvas.height);
    for (let i = 0; i < mask.length; i++)
        mask[i] = data.data[i * 4 + 3] > 48 ? 1 : 0;
    const skeleton = thin(mask, canvas.width, canvas.height);
    const paths = trace(skeleton, canvas.width, canvas.height);
    const value = { raster: true, canvas, width: Math.min(90, Math.max(16, ctx.measureText(char).width)), paths };
    CACHE.set(char, value);
    return value;
}
/**
 * 输入：char（字素），size（目标字号）。
 * 输出：该字素的排版宽度。
 * 功能：优先延续确认稿里的拉丁单线字风格，其他字形采用系统字体。
 */
function glyphWidth(char, size) {
    if (window.Ink.glyphs[char])
        return (window.Ink.glyphs[char].w + .1) * size;
    return (rasterGlyph(char).width / 64 + .13) * size;
}
/**
 * 输入：text（确认后的字段文字），maxWidth、maxHeight（显示区域）。
 * 输出：可绘制、可采样笔尖的 line 对象。
 * 功能：在卡片内自动换行与适量缩字号，不截断内容，不将未知汉字替换为空白。
 */
function makeHandwriting(text, maxWidth = 250, maxHeight = 49) {
    const chars = graphemes(text);
    let size = 25, placements;
    // 阶段一：寻找能完整容纳文本的排版，不通过裁切隐藏用户信息。
    while (size >= 12) {
        placements = [];
        let x = 0, row = 0;
        for (const char of chars) {
            const width = glyphWidth(char, size);
            if (x + width > maxWidth && x > 0) {
                x = 0;
                row++;
            }
            placements.push({ char, x, y: row * size * 1.45, width });
            x += width;
        }
        if ((row + 1) * size * 1.45 <= maxHeight || size === 12)
            break;
        size--;
    }
    const strokes = [], glyphs = [];
    let clock = 0;
    // 阶段二：将每个字的真实路径加入同一时间轴；抬笔间隔也属于时间轴。
    for (const item of placements) {
        const core = window.Ink.glyphs[item.char], scale = size / (core ? 25 : 64);
        const glyph = { ...item, start: clock, strokes: [], raster: !core, scale };
        let paths;
        if (core)
            paths = window.Ink.make(item.char).strokes.map(st => st.pts);
        else {
            glyph.source = rasterGlyph(item.char);
            paths = glyph.source.paths.map(path => path.map(([x, y]) => [x - 8, y - 18]));
        }
        for (const path of paths) {
            const points = path.map(([x, y]) => [item.x + x * scale, item.y + y * scale]);
            const lengths = arcLengths(points), duration = Math.max(.035, lengths.at(-1) / 115);
            const st = { points, lengths, start: clock, duration, glyph };
            strokes.push(st);
            glyph.strokes.push(st);
            clock += duration + .055;
        }
        glyph.end = clock;
        glyphs.push(glyph);
        clock += item.char === " " ? .025 : .018;
    }
    return { text, strokes, glyphs, size, duration: Math.max(clock, .1), width: maxWidth, height: maxHeight };
}
/**
 * 输入：stroke（路径），fraction（弧长比例）。
 * 输出：[x,y]。
 * 功能：沿路径插值得到真实笔尖位置，供绘制与角色共用。
 */
function strokePoint(stroke, fraction) {
    const { points, lengths } = stroke, target = lengths.at(-1) * clamp(fraction);
    let k = 1;
    while (k < lengths.length - 1 && lengths[k] < target)
        k++;
    if (!points[k])
        return points[0] || [0, 0];
    const p = (target - lengths[k - 1]) / Math.max(.00001, lengths[k] - lengths[k - 1]);
    return [points[k - 1][0] + (points[k][0] - points[k - 1][0]) * p, points[k - 1][1] + (points[k][1] - points[k - 1][1]) * p];
}
/**
 * 输入：line（手写排版），time（该排版内时间）。
 * 输出：{x,y,down}；down 表示笔尖是否落纸。
 * 功能：在两笔之间连续抬笔转移，而不是瞬移到下一笔。
 */
function sampleHandwriting(line, time) {
    let previous = line.strokes[0]?.points[0] || [0, 0], previousEnd = 0;
    for (const st of line.strokes) {
        if (time < st.start) {
            const u = clamp((time - previousEnd) / (st.start - previousEnd || 1)), p = u * u * (3 - 2 * u), b = st.points[0];
            return { x: previous[0] + (b[0] - previous[0]) * p, y: previous[1] + (b[1] - previous[1]) * p - Math.sin(u * Math.PI) * 5, down: false };
        }
        if (time <= st.start + st.duration) {
            const p = strokePoint(st, (time - st.start) / st.duration);
            return { x: p[0], y: p[1], down: true };
        }
        previous = st.points.at(-1);
        previousEnd = st.start + st.duration;
    }
    return { x: previous[0], y: previous[1], down: false };
}
/**
 * 输入：ctx（画布上下文），stroke（路径），fraction（完成比例）。
 * 输出：无，向当前画布写入路径。
 * 功能：仅描画到笔尖所在位置，而不是按文字矩形从左到右擦出。
 */
function paintStroke(ctx, stroke, fraction) {
    const target = stroke.lengths.at(-1) * clamp(fraction);
    ctx.beginPath();
    ctx.moveTo(...stroke.points[0]);
    for (let k = 1; k < stroke.points.length; k++) {
        if (stroke.lengths[k] <= target)
            ctx.lineTo(...stroke.points[k]);
        else {
            ctx.lineTo(...strokePoint(stroke, fraction));
            break;
        }
    }
    ctx.stroke();
}
/**
 * 输入：ctx、line、time、x、y（目标绘制位置）。
 * 输出：无。
 * 功能：连续显示当前笔画；完成的字形保持原样，在循环回看时不会重写。
 */
function drawHandwriting(ctx, line, time, x, y) {
    ctx.save();
    ctx.translate(x, y);
    ctx.strokeStyle = "#113b73";
    ctx.lineWidth = 1.95 * (line.size / 25) ** .35;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    for (const glyph of line.glyphs) {
        if (time < glyph.start)
            break;
        if (!glyph.raster) {
            for (const st of glyph.strokes)
                if (time >= st.start)
                    paintStroke(ctx, st, (time - st.start) / st.duration);
            continue;
        }
        const { source, scale } = glyph;
        if (time >= glyph.end) {
            ctx.drawImage(source.canvas, glyph.x - 8 * scale, glyph.y - 18 * scale, 104 * scale, 96 * scale);
            continue;
        }
        // 当前未知字形使用中心线做遮罩，最终轮廓仍来自原始系统字形。
        if (!glyph.buffer) {
            glyph.buffer = document.createElement("canvas");
            glyph.buffer.width = 104;
            glyph.buffer.height = 96;
        }
        const c = glyph.buffer.getContext("2d");
        c.setTransform(1, 0, 0, 1, 0, 0);
        c.clearRect(0, 0, 104, 96);
        c.globalCompositeOperation = "source-over";
        c.save();
        c.translate(8 - glyph.x / scale, 18 - glyph.y / scale);
        c.scale(1 / scale, 1 / scale);
        c.strokeStyle = "#fff";
        c.lineCap = "round";
        c.lineJoin = "round";
        c.lineWidth = 9 * scale;
        for (const st of glyph.strokes)
            if (time >= st.start)
                paintStroke(c, st, (time - st.start) / st.duration);
        c.restore();
        c.globalCompositeOperation = "source-in";
        c.drawImage(source.canvas, 0, 0);
        c.globalCompositeOperation = "source-over";
        ctx.drawImage(glyph.buffer, glyph.x - 8 * scale, glyph.y - 18 * scale, 104 * scale, 96 * scale);
    }
    ctx.restore();
}

return {makeHandwriting,sampleHandwriting,drawHandwriting};
})();
