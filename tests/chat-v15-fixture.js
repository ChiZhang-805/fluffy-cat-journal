/* 仅测试：可控的浏览器听写与SSE网络边界。此文件不会进入单文件产物的运行脚本。 */
window.__chatPlans=[];window.__chatRequests=[];window.__streams=[];window.__spoken='今天只有十二分钟';window.__tailDelay=35;window.__stops=0;window.__starts=0;window.__apiRequests=[];
/** 输入：正文/选项。输出：SSE Response。功能：显式模拟分块、等待、截断及取消，不调用真实AI。 */
function fixtureStream(plan,signal){let ctl,closed=false,timer;const entry={cancelled:false,controller:null};__streams.push(entry);
 const event=delta=>'data: '+JSON.stringify({choices:[{index:0,delta:{content:delta},finish_reason:null}]})+'\n\n';
 const push=s=>{if(!closed){try{ctl.enqueue(new TextEncoder().encode(s))}catch{closed=true}}};
 entry.deliver=(text,finish='stop')=>{push(event(text));push('data: '+JSON.stringify({choices:[{index:0,delta:{},finish_reason:finish}]})+'\n\ndata: [DONE]\n\n');if(!closed){closed=true;ctl.close()}};
 const stream=new ReadableStream({start(c){ctl=c;entry.controller=c;const text=plan.text??'这一刻我在听。你可以慢慢说。';if(plan.wait)return;const chars=[...text];let at=0;function next(){if(closed)return;if(at<chars.length){push(event(chars.slice(at,at+3).join('')));at+=3;timer=setTimeout(next,plan.delay??6)}else{entry.deliver('',plan.finish||'stop')}}timer=setTimeout(next,plan.initialDelay||5);},cancel(){entry.cancelled=true;closed=true;clearTimeout(timer)}});
 return new Response(stream,{headers:{'Content-Type':'text/event-stream'}});
}
/** 输入：请求URL和选项。输出：协议Response。功能：只有回顾正文走人工SSE，其余JSON任务保留各自结构。 */
window.fetch=async function(url,o={}){const p=o.body?JSON.parse(o.body):null;__apiRequests.push({url:String(url),payload:p});const json=body=>Response.json(body),wrap=body=>json({choices:[{finish_reason:'stop',message:{content:JSON.stringify(body)}}]});
 if(!p)return json({data:[{id:'deepseek-flash'}]});
 const sys=p.messages?.[0]?.content||'';
 if(sys.includes('Classify journal intent'))return wrap({operation:'none',targetIndex:null});
 if(sys.includes('Translate the provided'))return wrap({translations:JSON.parse(p.messages[1].content).strings.map(()=> 'A quiet moment')});
 if(p.stream){const plan=__chatPlans.shift()||{};__chatRequests.push(p);if(plan.lateHeaders)return new Promise(resolve=>{window.__lateHeaders=()=>resolve(Response.json({choices:[{finish_reason:'stop',message:{content:'迟到的旧答案绝不显示。'}}]}))});if(plan.status)return new Response('PRIVATE_UPSTREAM',{status:plan.status,headers:{'Retry-After':'60'}});if(plan.network)throw new TypeError('network');if(plan.json)return wrap(plan.json);return fixtureStream(plan,o.signal)}
 return wrap({fields:{activity:'跑步',durationMinutes:30,notes:'轻松'},warnings:[]});
};
class FixtureContext{constructor(){this.state='running'}async resume(){}createMediaStreamSource(){return{connect(){},disconnect(){}}}createAnalyser(){return{fftSize:1024,getByteTimeDomainData(a){a.forEach((_,i)=>a[i]=128+Math.round((16+8*Math.sin(performance.now()/200))*Math.sin(i/10)))}}}async close(){this.state='closed'}}
class FixtureRecognition{constructor(){window.__recognition=this}start(){__starts++;setTimeout(()=>this.onstart?.(),15)}stop(){const spoken=__spoken;setTimeout(()=>{if(spoken!==null){const row=[{transcript:spoken}];row.isFinal=true;this.onresult?.({results:[row],resultIndex:0})}this.onend?.()},__tailDelay)}abort(){}}
window.__speechEnv={Recognition:FixtureRecognition,AudioContext:FixtureContext,mediaDevices:{getUserMedia:async()=>({getTracks:()=>[{stop(){__stops++}}]})}};
