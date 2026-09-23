#!/usr/bin/env node
/**
 * 输入：与evaluate-ai相同的参数、DEEPSEEK_API_KEY。
 * 输出：情绪文字整理/陪伴用例的dry-run或显式付费评测报告。
 * 功能：兼容旧npm入口，但不再错误地把语言任务发到百炼音频模型。
 */
'use strict';
if(process.argv.some(x=>x.startsWith('--audio-dir'))){
 console.error('The app now transcribes with the browser and uses DeepSeek for language. Supply text cases; raw-audio scoring is not part of this workflow.');process.exitCode=1;
}else{
 process.argv.push('--suite=emotion');
 require('./evaluate-ai.cjs').main().catch(error=>{console.error(error.message);process.exitCode=1;});
}
