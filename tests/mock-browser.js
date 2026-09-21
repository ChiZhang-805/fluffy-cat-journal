// 仅测试替身：不调用真实麦克风、网络或付费模型。
window.TEST = { permission: 'prompt', mediaCalls: 0, prompts: 0, stops: 0, recognitionStarts: 0, extracts: 0, alive: 0, deferMedia: false, grant: null };
function testStream() {
  TEST.alive++;
  let live = true;
  return {getTracks: () => [{stop: () => {if(live){live=false;TEST.stops++;TEST.alive--;}}}]};
}
Object.defineProperty(navigator, 'permissions', {configurable:true,value:{query:async()=>({state:TEST.permission})}});
Object.defineProperty(navigator, 'mediaDevices', {configurable:true,value:{getUserMedia:async()=>{
 TEST.mediaCalls++;
 if(TEST.permission==='prompt' || TEST.deferMedia){
   if(TEST.permission==='prompt')TEST.prompts++;
   return new Promise((resolve,reject)=>{TEST.grant=()=>{TEST.permission='granted';resolve(testStream());};TEST.deny=()=>reject(new DOMException('denied','NotAllowedError'));});
 }
 if(TEST.permission==='denied')throw new DOMException('denied','NotAllowedError');
 return testStream();
}}});
class TestAudioContext {
 constructor(){this.state='running';}
 async resume(){}
 createMediaStreamSource(){return {connect(){},disconnect(){}};}
 createAnalyser(){return {fftSize:1024,getByteTimeDomainData(a){a.fill(133);}};}
 async close(){this.state='closed';}
}
window.AudioContext = TestAudioContext;
class TestSpeechRecognition {
 start(){TEST.recognitionStarts++;TEST.rec=this;this.timer=setTimeout(()=>this.onstart?.(),60);}
 stop(){clearTimeout(this.timer);const r=[{transcript:'跑步五公里，三十分钟，感觉不错。'}];r.isFinal=true;setTimeout(()=>{this.onresult?.({results:[r]});this.onend?.();},20);}
 abort(){clearTimeout(this.timer);}
}
window.SpeechRecognition=TestSpeechRecognition;
window.fetch=async (url,init={})=>{
 if(init.signal?.aborted)throw new DOMException('abort','AbortError');
 if(String(url).endsWith('/models'))return new Response(JSON.stringify({data:[{id:'deepseek-flash'}]}),{status:200});
 if(String(url).includes('/chat/completions')){
  TEST.extracts++;
  return new Response(JSON.stringify({choices:[{finish_reason:'stop',message:{content:JSON.stringify({activity:'跑步',distanceKm:5,durationMinutes:30,notes:'感觉不错',warnings:[]})}}]}),{status:200});
 }
 throw Error('Unexpected test URL');
};
