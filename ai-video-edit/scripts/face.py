import cv2, json, sys, numpy as np
cap=cv2.VideoCapture(sys.argv[1]); cc=cv2.CascadeClassifier(cv2.data.haarcascades+"haarcascade_frontalface_default.xml")
res=[];i=0
while True:
    ok,f=cap.read()
    if not ok: break
    if i%3==0:
        g=cv2.cvtColor(f,cv2.COLOR_BGR2GRAY)
        fs=cc.detectMultiScale(g,1.1,6,minSize=(50,50))
        if len(fs):
            x,y,w,h=max(fs,key=lambda r:r[2]*r[3]); res.append([i,float(x+w/2),float(y+h/2),float(w)])
    i+=1
json.dump(res,open(sys.argv[2],"w"))
print(i,len(res))
for shot in [(0,192),(192,432),(432,672),(672,912)]:
    a=np.array([r for r in res if shot[0]<=r[0]<shot[1]])
    print(shot, a[:,1].min().round(), a[:,1].max().round(), np.median(a[:,1]).round(), np.median(a[:,2]).round(), np.median(a[:,3]).round())
