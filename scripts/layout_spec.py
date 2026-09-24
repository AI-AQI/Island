"""Authored reference-layout geometry; samples are also exported to the viewer."""
import math
import numpy as np

RADIUS = (28, 21.5)
CONTROLS = [(-4,21,.80),(-3,17,.9),(1.5,12.5,1.05),(7.5,9.3,1.18),(9.8,5.8,1.35),(9,1.4,1.5),(7.2,-2.2,1.75),(9,-4.8,2.0),(14,-6.1,2.25),(16,-9,2.5),(15,-13.8,2.8),(12,-18,3.15),(11,-19.8,3.4)]

def samples():
    result=[]
    for i in range(len(CONTROLS)-1):
        a=np.array(CONTROLS[max(0,i-1)]);b=np.array(CONTROLS[i]);c=np.array(CONTROLS[i+1]);d=np.array(CONTROLS[min(len(CONTROLS)-1,i+2)])
        for j in range(16):
            t=j/16
            p=.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t)
            result.append([float(v) for v in p])
    result.append(list(CONTROLS[-1]))
    return result

RIVER=samples()
_A=np.array(RIVER[:-1]);_B=np.array(RIVER[1:]);_D=_B[:,:2]-_A[:,:2];_L=(_D*_D).sum(axis=1)

def closest(x,y):
    q=np.array([x,y])-_A[:,:2]
    t=np.clip((q*_D).sum(axis=1)/_L,0,1)
    delta=q-t[:,None]*_D
    ds=(delta*delta).sum(axis=1);i=int(np.argmin(ds))
    return math.sqrt(ds[i]),float(_A[i,2]+t[i]*(_B[i,2]-_A[i,2])),i,float(t[i])

def ground(x,y):
    distance,width,_,_=closest(x,y)
    base=10.72+.18*math.sin(x*.10)+.13*math.cos(y*.17)
    return base-1.20*math.exp(-((distance/(width+.35))**6))

def bridge_pose():
    i=min(range(len(RIVER)),key=lambda i:abs(RIVER[i][1]+10.5))
    p=RIVER[i];a=RIVER[max(0,i-1)];b=RIVER[min(len(RIVER)-1,i+1)]
    dx,dy=b[0]-a[0],b[1]-a[1]
    return [p[0],p[1],10.35],math.atan2(dx,-dy)
