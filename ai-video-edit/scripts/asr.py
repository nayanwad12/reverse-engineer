import sherpa_onnx, wave, numpy as np, json, sys
d=sys.argv[1]
rec=sherpa_onnx.OfflineRecognizer.from_transducer(encoder=d+"/encoder.int8.onnx",decoder=d+"/decoder.int8.onnx",joiner=d+"/joiner.int8.onnx",tokens=d+"/tokens.txt",model_type="nemo_transducer",num_threads=4)
w=wave.open(sys.argv[2]); a=np.frombuffer(w.readframes(w.getnframes()),dtype=np.int16).astype(np.float32)/32768
st=rec.create_stream(); st.accept_waveform(16000,a); rec.decode_stream(st)
r=st.result
print(r.text)
# merge tokens into words
words=[]
for t,ts in zip(r.tokens,r.timestamps):
    if t.startswith("▁") or t.startswith(" ") or not words:
        words.append({"w":t.replace("▁","").strip(),"s":ts})
    else: words[-1]["w"]+=t
for i,wd in enumerate(words):
    wd["e"]=words[i+1]["s"] if i+1<len(words) else len(a)/16000
json.dump(words,open(sys.argv[3],"w"),indent=0)
