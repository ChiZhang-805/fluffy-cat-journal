#!/usr/bin/env node
/**
 * 输入：--allow-api（显式允许真实付费请求）、--audio-dir（可选自有WAV）、--limit=N、--out=路径，以及环境变量DASHSCOPE_API_KEY。
 * 输出：本地人工复核报告。默认仅列出用例，不请求网络。
 * 功能：使用和APP完全相同的提示词、API客户端和草稿校验，实测语义或音频模型；不生成虚假的准确率。
 */
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const cases = require('../tests/emotion-cases.cjs');
const root = path.resolve(__dirname, '..');
/**
 * 输入：process.argv中的参数。
 * 输出：参数值或默认值。
 * 功能：避免把密钥设计成命令行参数，密钥只从环境变量读取。
 */
function option(name, fallback = '') {
    const prefix = `--${name}=`;
    return process.argv.find(value => value.startsWith(prefix))?.slice(prefix.length) ?? fallback;
}
/**
 * 输入：无。
 * 输出：与APP共享的AI模块及百炼客户端构造器。
 * 功能：不复制一份会漂移的提示词，直接载入交付代码。
 */
function loadModules() {
    const context = vm.createContext({console,Date,Intl,Math,Set,Map,JSON,Object,Array,Number,String,Promise,Error,TypeError,URL,AbortController,DOMException,TextDecoder,TextEncoder,setTimeout,clearTimeout,fetch});
    vm.runInContext('const __fluffyModules = {};', context);
    for (const file of ['model.js','sleep-time.js','catalog.js','bailian.js','ai-journal.js']) {
        vm.runInContext(fs.readFileSync(path.join(root,'js',file),'utf8'), context, {filename:file});
    }
    return vm.runInContext('({AI:__fluffyModules["ai-journal.js"],Client:__fluffyModules["bailian.js"].BailianClient})',context);
}
/**
 * 输入：无，读取CLI配置。
 * 输出：Promise<void>，生成仅在本机的复核报告。
 * 功能：先确认用户显式授权，再逐条发送；不上传无关文件，不做情绪“真值”判断。
 */
async function main() {
    // 阶段一：默认无网络，先让维护者查看评测材料与复核标准。
    const limit = Number(option('limit','4'));
    if (!Number.isInteger(limit) || limit<1 || limit>cases.length) throw Error(`limit应为1至${cases.length}的整数。`);
    const selected = cases.slice(0,limit);
    if (!process.argv.includes('--allow-api')) {
        console.log(JSON.stringify({mode:'dry-run',requestsSent:0,cases:selected,notice:'加--allow-api会产生真实API费用；音频须由本人同意提供。'},null,2));
        return;
    }
    const key = process.env.DASHSCOPE_API_KEY;
    if (!key) throw Error('请先设置DASHSCOPE_API_KEY环境变量，不要把Key写进源码。');
    const {AI,Client} = loadModules();
    const client = new Client({config:{bailianBaseURL:process.env.DASHSCOPE_BASE_URL,bailianVisionModel:process.env.DASHSCOPE_VISION_MODEL,bailianAudioModel:process.env.DASHSCOPE_AUDIO_MODEL}});
    client.setKey(key);
    const audioDir = option('audio-dir');
    const results = [];
    try {
        // 阶段二：有音频时只发送明确列出的用例WAV，不读取整个目录；无音频不声称分析语气。
        for (const item of selected) {
            const started = Date.now();
            try {
                let result;
                if (audioDir) {
                    const file = path.resolve(audioDir,`${item.id}.wav`);
                    const bytes = fs.readFileSync(file);
                    if (bytes.length>7e6 || bytes.toString('ascii',0,4)!=='RIFF' || bytes.toString('ascii',8,12)!=='WAVE') throw Error('用例需要7MB以内的WAV文件。');
                    const audio = {format:'wav',data:'data:;base64,'+bytes.toString('base64')};
                    result = await AI.extractAudio(client,'mood',audio);
                    audio.data = '';
                } else {
                    result = await AI.extract(client,'mood',item.text,null);
                }
                results.push({id:item.id,review:item.review,mode:audioDir?'raw-audio':'text-only',result,milliseconds:Date.now()-started,humanAssessment:null});
                console.log(`${item.id}: 已返回，等待人工复核`);
            } catch (error) {
                results.push({id:item.id,review:item.review,error:error.message,milliseconds:Date.now()-started});
                console.log(`${item.id}: 未完成（见本地报告）`);
            }
        }
    } finally { client.clear(); }
    // 阶段三：保留人工判断位，不用简单关键词匹配冒充情绪识别准确率。
    const output = path.resolve(option('out','emotion-evaluation.local.json'));
    fs.writeFileSync(output,JSON.stringify({generatedAt:new Date().toISOString(),realRequests:true,model:audioDir?client.audioModel:client.model,results,accuracy:null},null,2),{mode:0o600});
    console.log(`报告已保存：${output}。不要把私人录音与报告提交到公开仓库。`);
}
main().catch(error => { console.error(error.message);process.exitCode=1; });
