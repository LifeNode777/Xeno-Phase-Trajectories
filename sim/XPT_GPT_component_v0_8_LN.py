#!/usr/bin/env python3
"""
XPT component-profile experiment v0.8-LN

Purpose:
    Test whether transition information is better represented as a profile of
    component stability than as one universal transition signature.

Design:
    1. Reuse the frozen v0.7 synthetic generators and seeds.
    2. One observable per system (the registered quadratic/energy-like scalar).
    3. One Takens embedding for the WHOLE frozen transition window.
    4. Slice that already-embedded trajectory into fixed fractional components.
       No component gets its own tau or a new embedding.
    5. Two window modes:
       - detector: clean CUSUM/change-point window; nulls inherit it.
       - control: onset is anchored at known control time; relaxation is the
         same operational endpoint used by v0.7 detector after the anchor.
         This is explicitly a control-anchored sensitivity analysis, not an
         independent oracle for the true physical relaxation.
    6. Local stability: shift each component boundary by +/-5 and +/-10
       embedded samples and compare component geometry with the original.
    7. Null stability: phase-randomized nulls use the same clean window.
    8. No post-hoc component promotion. Component status is pre-declared.

This is an experiment on the existing synthetic XPT benchmark, not validation
of XPT or any anomalous interpretation.
"""
from __future__ import annotations
import argparse, json, hashlib
from dataclasses import dataclass, asdict
from pathlib import Path
import numpy as np

SEED=20260920
N_RUNS=32
N_NULL=32
M=4
MI_BINS=32
CONTROL_TIME=4.0
U_POINTS=128
MIN_COMPONENT_POINTS=8

COMPONENTS=(
    ("onset",0.00,0.15),
    ("deformation",0.15,0.70),
    ("relaxation",0.70,0.90),
    ("new_regime",0.90,1.00),
)

@dataclass
class TS:
    system:str; seed:int; tau:int; t0:int; t1:int; onset:int; peak:int; relax:int
    X:np.ndarray


def zscore(x):
    x=np.asarray(x,float)
    return (x-x.mean())/(x.std()+1e-12)

def mutual_information(x,lag,bins=MI_BINS):
    x=zscore(x)
    if lag<=0 or lag>=len(x)-2:return np.inf
    a,b=x[:-lag],x[lag:]
    edges=np.histogram_bin_edges(x,bins=bins)
    ia=np.clip(np.digitize(a,edges[:-1]),0,bins-1)
    ib=np.clip(np.digitize(b,edges[:-1]),0,bins-1)
    joint=np.zeros((bins,bins)); np.add.at(joint,(ia,ib),1); joint/=joint.sum()
    px,py=joint.sum(1),joint.sum(0); den=px[:,None]*py[None,:]
    nz=joint>0
    return float(np.sum(joint[nz]*np.log(joint[nz]/den[nz])))

def first_mi_minimum(x):
    max_lag=min(len(x)//8,250)
    vals=np.array([mutual_information(x,k) for k in range(1,max_lag+1)])
    for i in range(1,len(vals)-1):
        if vals[i]<vals[i-1] and vals[i]<=vals[i+1]: return i+1
    return int(np.argmin(vals)+1)

def delay_embed(y,tau):
    y=zscore(y); n=len(y)-(M-1)*tau
    if n<MIN_COMPONENT_POINTS: raise ValueError("series too short for embedding")
    return np.column_stack([y[i*tau:i*tau+n] for i in range(M)])

def phase_randomize(y,rng):
    y=np.asarray(y,float); mu=y.mean(); F=np.fft.rfft(y-mu); phase=np.angle(F)
    if len(F)>2: phase[1:-1]=rng.uniform(-np.pi,np.pi,len(F)-2)
    return np.fft.irfft(np.abs(F)*np.exp(1j*phase),n=len(y))+mu

def rk4(f,s,dt,t,*args):
    k1=f(s,t,*args); k2=f(s+.5*dt*k1,t+.5*dt,*args)
    k3=f(s+.5*dt*k2,t+.5*dt,*args); k4=f(s+dt*k3,t+dt,*args)
    return s+dt*(k1+2*k2+2*k3+k4)/6

def rossler(seed,dt=.01,T=20):
    rng=np.random.default_rng(seed); s=np.array([.1,0.,0.]); ts=[]; ys=[]
    def f(s,t,a):
        x,y,z=s; return np.array([-y-z,x+a*y,.2+z*(x-5.7)])
    for i in range(int(T/dt)):
        t=i*dt; a=.2 if t<CONTROL_TIME else .38
        s=rk4(f,s,dt,t,a)+rng.normal(0,5e-5,3)
        if i%2==0: ts.append(t); ys.append(np.sum(s*s))
    return np.array(ts),np.array(ys)

def vdp(seed,dt=.01,T=20):
    rng=np.random.default_rng(seed); s=np.array([.1,0.]); ts=[]; ys=[]
    def f(s,t,mu):
        x,v=s; return np.array([v,mu*(1-x*x)*v-x])
    for i in range(int(T/dt)):
        t=i*dt; mu=1. if t<CONTROL_TIME else 5.
        s=rk4(f,s,dt,t,mu)+rng.normal(0,3e-5,2)
        if i%2==0: ts.append(t); ys.append(np.sum(s*s))
    return np.array(ts),np.array(ys)

def duffing(seed,dt=.005,T=20):
    rng=np.random.default_rng(seed); s=np.array([.1,0.]); ts=[]; ys=[]
    def f(s,t,drive):
        x,v=s; return np.array([v,x-x**3-.2*v+drive*np.cos(t)])
    for i in range(int(T/dt)):
        t=i*dt; drive=.30 if t<CONTROL_TIME else .65
        s=rk4(f,s,dt,t,drive)+rng.normal(0,2e-5,2)
        if i%2==0: ts.append(t); ys.append(np.sum(s*s))
    return np.array(ts),np.array(ys)

def nlse(seed,n=128,L=30,dt=.003,T=10):
    rng=np.random.default_rng(seed); x=np.linspace(-L/2,L/2,n,endpoint=False)
    dx=x[1]-x[0]; k=2*np.pi*np.fft.fftfreq(n,d=dx)
    psi=np.exp(-(x/3)**2).astype(complex); psi*=np.exp(1j*.03*rng.standard_normal(n))
    psi/=np.sqrt(np.sum(abs(psi)**2)*dx); ts=[]; ys=[]
    for j in range(int(T/dt)):
        t=j*dt; kap=-1. if t<CONTROL_TIME else 1.
        half=np.exp(-.5j*k*k*dt/2); psi=np.fft.ifft(np.fft.fft(psi)*half)
        psi*=np.exp(-1j*kap*abs(psi)**2*dt); psi=np.fft.ifft(np.fft.fft(psi)*half)
        if j%4==0:
            rho=abs(psi)**2; ys.append(np.sum(rho*rho)*dx); ts.append(t)
    return np.array(ts),np.array(ys)

SYSTEMS={"NLSE":nlse,"Rossler":rossler,"VanDerPol":vdp,"Duffing":duffing}

def transition_indices(X,anchor=None):
    speed=np.linalg.norm(np.gradient(X,axis=0),axis=1); n=len(speed)
    if anchor is not None: onset=int(anchor); search_start=onset
    else: search_start=max(8,n//6); onset=None
    peak=search_start+int(np.argmax(speed[search_start:]))
    baseline=np.median(speed[:max(8,n//6)]); excursion=max(speed[peak]-baseline,1e-12)
    if onset is None:
        threshold=baseline+.20*excursion
        for i in range(search_start,peak+1):
            if np.all(speed[i:min(i+5,n)]>=threshold): onset=i; break
        if onset is None:return None
    terminal=np.median(speed[max(peak+1,int(.8*n)):])
    tol=.10*max(abs(terminal-speed[peak]),1e-12)
    relax=None
    for i in range(peak+1,n-5):
        if np.all(np.abs(speed[i:i+5]-terminal)<=tol): relax=i; break
    if relax is None or relax-onset<MIN_COMPONENT_POINTS:return None
    return onset,peak,relax

def build(system,seed,t,y,mode="detector",tau=None):
    if tau is None: tau=first_mi_minimum(y)
    X=delay_embed(y,tau); te=t[(M-1)*tau:]
    if mode=="control":
        anchor=int(np.argmin(abs(te-CONTROL_TIME)))
        tr=transition_indices(X,anchor=anchor)
    elif mode=="detector":
        tr=transition_indices(X,anchor=None)
    else:
        raise ValueError("mode must be control or detector")
    if tr is None: raise ValueError("transition not detected")
    onset,peak,relax=tr
    if relax-onset<4*MIN_COMPONENT_POINTS: raise ValueError("transition window too short for 4 components")
    return TS(system,seed,int(tau),int(onset),int(relax),int(onset),int(peak),int(relax),X[onset:relax+1])

def components(ts):
    X=ts.X; out={}
    for name,a,b in COMPONENTS:
        i=int(round(a*(len(X)-1))); j=int(round(b*(len(X)-1)))
        j=max(j,i+1); C=X[i:j+1]
        if len(C)<MIN_COMPONENT_POINTS: raise ValueError(f"component {name} too short: {len(C)}")
        C=C-C[0]; scale=np.sqrt(np.mean(np.sum(C*C,axis=1))); C=C/max(scale,1e-12)
        out[name]=C
    return out

def resample(C,n=128):
    if len(C)<2: raise ValueError("too short")
    u=np.linspace(0,1,len(C)); v=np.linspace(0,1,n)
    return np.column_stack([np.interp(v,u,C[:,j]) for j in range(C.shape[1])])

def proc(A,B):
    A=resample(A); B=resample(B); A=A-A.mean(0); B=B-B.mean(0)
    A/=np.linalg.norm(A)+1e-12; B/=np.linalg.norm(B)+1e-12
    Mx=B.T@A; U,_,Vt=np.linalg.svd(Mx); R=U@Vt
    return float(np.sqrt(np.mean(np.sum((A-B@R)**2,axis=1))))

def pairwise(arr):
    d=[]
    for i in range(len(arr)):
        for j in range(i+1,len(arr)): d.append(proc(arr[i],arr[j]))
    return np.array(d)

def summary(d):
    d=np.asarray(d,float)
    if len(d)==0:return {"n":0}
    return {"n":int(len(d)),"median":float(np.median(d)),"q95":float(np.quantile(d,.95)),"q05":float(np.quantile(d,.05))}

def local_shift_profile(ts,component,shifts=(-10,-5,5,10)):
    C=components(ts)[component]; base_idx=dict((n,(a,b)) for n,a,b in COMPONENTS)[component]
    a,b=base_idx; N=len(ts.X); i0=int(round(a*(N-1))); i1=int(round(b*(N-1)))
    vals=[]
    for s in shifts:
        j0=max(0,i0+s); j1=min(N-1,i1+s)
        if j1-j0+1<MIN_COMPONENT_POINTS: continue
        C2=ts.X[j0:j1+1]; C2=C2-C2[0]; scale=np.sqrt(np.mean(np.sum(C2*C2,axis=1))); C2=C2/max(scale,1e-12)
        vals.append(proc(C,C2))
    return vals

def run_system(name,base_seed,mode="control"):
    fn=SYSTEMS[name]; clean=[]; rejected=[]; raw={}
    for i in range(N_RUNS):
        seed=base_seed+i; t,y=fn(seed); raw[seed]=(t,y)
        try: clean.append(build(name,seed,t,y,mode))
        except ValueError as e: rejected.append({"seed":seed,"reason":str(e)})
    if not clean:return {"system":name,"mode":mode,"status":"OUT_OF_SCOPE","clean_n":0,"clean_rejected":rejected}
    clean_comp={cname:[components(c)[cname] for c in clean] for cname,_,_ in COMPONENTS}
    result={"system":name,"mode":mode,"clean_n":len(clean),"clean_rejected":rejected,"components":{}}
    for cname,_,_ in COMPONENTS:
        cs=clean_comp[cname]; dcc=pairwise(cs); shifts=[]; dcn=[]; null_rej=0
        for ci,c in enumerate(clean):
            shifts.extend(local_shift_profile(c,cname))
            t,y=raw[c.seed]; rng=np.random.default_rng(c.seed+10_000_000)
            C0=cs[ci]
            for _ in range(N_NULL):
                try:
                    Yn=phase_randomize(y,rng); Xn=delay_embed(Yn,c.tau)
                    if c.t1>=len(Xn): raise ValueError("clean window outside null embedding")
                    nTs=TS(name,c.seed,c.tau,c.t0,c.t1,c.onset,c.peak,c.relax,Xn[c.t0:c.t1+1])
                    dcn.append(proc(C0,components(nTs)[cname]))
                except Exception: null_rej+=1
        cc95=np.quantile(dcc,.95) if len(dcc) else np.nan
        cn05=np.quantile(dcn,.05) if len(dcn) else np.nan
        medcc=np.median(dcc) if len(dcc) else np.nan; medcn=np.median(dcn) if len(dcn) else np.nan
        result["components"][cname]={
            "CC":summary(dcc),"CN":summary(dcn),"shift":summary(shifts),
            "primary_pass":bool(cc95<cn05) if np.isfinite(cc95+cn05) else False,
            "ratio":float(medcn/medcc) if medcc>0 and np.isfinite(medcn) else None,
            "shift_median_over_CC_median":float(np.median(shifts)/medcc) if len(shifts) and medcc>0 else None,
        }
    result["null_rejected_total"]=null_rej
    return result

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--output",default="XPT_component_v0_8_LN_results.json"); args=ap.parse_args()
    results=[]
    systems_run={"NLSE":nlse,"VanDerPol":vdp,"Duffing":duffing}
    for mode in ("control","detector"):
        for k,name in enumerate(systems_run):
            print("RUN",mode,name); results.append(run_system(name,SEED+1000*k,mode))
    payload={"protocol":"XPT-component-v0.8-LN","seed":SEED,"N_RUNS":N_RUNS,"N_NULL":N_NULL,"m":M,"components":COMPONENTS,"window":"whole-window Takens then component slicing","modes":["control","detector"],"results":results}
    text=json.dumps(payload,indent=2,ensure_ascii=False); Path(args.output).write_text(text+"\n",encoding="utf-8")
    print("SHA256",hashlib.sha256(text.encode()).hexdigest())
    for r in results:
        print("\n",r["system"],r.get("status","OK"))
        for c,v in r.get("components",{}).items(): print(c,"CC",v["CC"],"CN",v["CN"],"ratio",v["ratio"],"primary",v["primary_pass"],"shift",v["shift"])
if __name__=="__main__": main()
