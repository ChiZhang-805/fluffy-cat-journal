#!/usr/bin/env node
/**
 * 输入：--allow-api、--limit=N、--suite=all|emotion、--id=用例ID、--out=路径，以及环境变量DEEPSEEK_API_KEY。
 * 输出：默认不联网的用例清单；显式启用后输出带耗时的人工复核报告。
 * 功能：使用交付代码的真实DeepSeek客户端、字段契约、解析和流式聊天；不把替身测试冒充真实模型评测。
 */
'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const ROOT=path.resolve(__dirname,'..');
/** 输入：参数名、默认值。输出：选项值。功能：密钥禁止作为命令行参数，避免进入shell历史。 */
function option(name,fallback=''){return process.argv.find(x=>x.startsWith(`--${name}=`))?.slice(name.length+3)??fallback;}
/** 输入：可注入fetch。输出：与网页一致的模块沙箱。功能：隔离合成存储并复用生产提示词，不访问用户浏览器数据。 */
function load(fetchImpl){
 const data=new Map();
 const env={console,fetch:fetchImpl,URL,AbortController,DOMException,TextEncoder,TextDecoder,Response,Headers,setTimeout,clearTimeout,performance,Intl,structuredClone,__fluffyModules:{},localStorage:{getItem:k=>data.get(k)||null,setItem:(k,v)=>data.set(k,String(v))}};
 env.window=env;vm.createContext(env);
 for(const name of ['ai-policy','model','sleep-time','catalog','journal-store','entry-i18n','journal-guidance','companion-policy','chat-text','chat-stream','review-data','deepseek','ai-journal','review-conversation'])vm.runInContext(fs.readFileSync(path.join(ROOT,'js',name+'.js'),'utf8'),env,{filename:name+'.js'});
 return {env,get:name=>env.__fluffyModules[name+'.js']};
}
/** 输入：条目、模型结果。输出：确定性检查列表。功能：只检查明确数值/语言等可计算条件，语气和正确理解留给人工。 */
function checks(item,result){
 const list=[];
 for(const [key,value] of Object.entries(item.expected||{}))list.push({rule:'exact:'+key,passed:String(result.fields?.[key])===String(value)});
 for(const key of item.absent||[])list.push({rule:'absent:'+key,passed:result.fields?.[key]==null||result.fields[key]===''});
 if(item.kind==='chat'&&item.id.includes('no-questions'))list.push({rule:'no-question-mark',passed:!/[?？]/.test(result.text||'')});
 if(item.lang==='en')list.push({rule:'English-visible-copy',passed:!/[\u3400-\u9fff]/.test(item.kind==='chat'?result.text:JSON.stringify(result.fields))});
 return list;
}
/** 输入：命令行与环境变量。输出：Promise<void>。功能：先展示明确费用授权，再逐项限量评测，失败分类但不泄漏供应商响应或Key。 */
async function main(){
 // 阶段一：默认dry-run不进行任何fetch；仅使用仓库内合成用例。
 const suite=option('suite','all');if(!['all','emotion'].includes(suite))throw Error('suite must be all or emotion.');
 const all=require('../tests/ai-v16-cases.cjs').filter(c=>suite!=='emotion'||c.category==='mood');
 const matching=option('id')?all.filter(c=>c.id===option('id')):all;
 const limit=Number(option('limit','6'));if(!Number.isInteger(limit)||limit<1||limit>100)throw Error('limit must be 1..100.');
 const selected=matching.slice(0,limit);if(!selected.length)throw Error('No matching case.');
 if(!process.argv.includes('--allow-api')){console.log(JSON.stringify({mode:'dry-run',requestsSent:0,availableCases:all.length,cases:selected,live:'Set DEEPSEEK_API_KEY, then explicitly pass --allow-api. This incurs API charges.'},null,2));return;}
 if(!process.env.DEEPSEEK_API_KEY)throw Error('Set DEEPSEEK_API_KEY in your local environment, never in source files.');
 // 阶段二：请求总量上限包括生产客户端可能触发的一次重试，不无限消耗额度。
 const maxRequests=selected.length*2;let requests=0;
 const fetchImpl=async(...args)=>{if(requests>=maxRequests)throw Error('Evaluation request budget exhausted.');requests++;return fetch(...args);};
 const modules=load(fetchImpl),Client=modules.get('deepseek').DeepSeekClient;
 const client=new Client({model:process.env.DEEPSEEK_MODEL||'deepseek-flash',fetchImpl,requestTimeoutMs:30000});client.setKey(process.env.DEEPSEEK_API_KEY);
 const results=[];
 try{
  for(const item of selected){
   const start=performance.now(),before=requests,controller=new AbortController(),timer=setTimeout(()=>controller.abort(),35000);
   try{
    modules.get('entry-i18n').setLanguage(item.lang||'zh');
    let result;
    if(item.kind==='chat'){
     const view=modules.get('review-data').build(item.category,'2026-09-22',[]);
     result=await modules.get('review-conversation').request({api:client,view,history:item.history||[],text:item.text,lang:item.lang||'zh',signal:controller.signal});
    }else if(item.kind==='estimate')result=await modules.get('ai-journal').estimate(client,item.text,item.notes||'',controller.signal);
    else result=await modules.get('ai-journal').extract(client,item.category,item.text,null,controller.signal,{recordDate:'2026-09-22',current:item.current||{},operation:item.operation||'new',lastQuestion:item.lastQuestion||null});
    results.push({id:item.id,kind:item.kind,requests:requests-before,milliseconds:Math.round(performance.now()-start),result,checks:checks(item,result),humanRubric:item.review,humanAssessment:null});
    console.log(`${item.id}: response received; human review pending.`);
   }catch(error){results.push({id:item.id,requests:requests-before,milliseconds:Math.round(performance.now()-start),errorCode:error.code||error.name||'unknown',humanRubric:item.review,humanAssessment:null});console.log(`${item.id}: request did not complete.`);}
   finally{clearTimeout(timer);}
  }
 }finally{client.clear();}
 // 阶段三：只保存合成用例响应及判断位，不计算无依据的“情绪准确率”。
 const output=path.resolve(option('out','ai-evaluation.local.json'));
 fs.writeFileSync(output,JSON.stringify({generatedAt:new Date().toISOString(),realRequests:true,requestsSent:requests,model:client.model,results,accuracy:null},null,2),{mode:0o600});
 console.log('Report saved locally. Inspect each human rubric; a response is not proof of correctness.');
}
if(require.main===module)main().catch(error=>{console.error(error.message);process.exitCode=1;});
module.exports={main,load,checks};
