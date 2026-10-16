import numpy as np, modelo_frota_etanol_v3 as v3, rodar_v3_sem_diesel as sd, projecao_2050 as pl, motos_projecao as mp
T=pl.T; ANOS=pl.ANOS
V26=2.55e6*1.164
def proj(frota_alvo, traj, v26=None, novo_patamar=False):
    leg=np.array([sd.legado(t) for t in range(T)]); esc=frota_alvo[0]/leg[0].sum()
    leg_nd,leg_d=leg[:,0]*esc,leg[:,1]*esc
    S,Snd,Sd,d=sd.S_NOVO,sd.S_ND,sd.S_D,sd.D_FUT
    mix=sd.mix_nd(traj); inten=sum(mix[k]*v3.INTENS[k] for k in v3.INTENS)
    alvo=frota_alvo.copy(); vendas=np.zeros(T); frota=np.zeros(T); frota[0]=alvo[0]
    for ti in range(1,T):
        sob=leg_nd[ti]+leg_d[ti]+sum(vendas[c]*S[ti-c] for c in range(1,ti))
        if ti==1 and v26 is not None:
            vendas[1]=v26
            if novo_patamar:
                f=sob+v26*S[0]; alvo[1:]*=f/alvo[1]
        else:
            vendas[ti]=max((alvo[ti]-sob)/S[0],0)
        frota[ti]=sob+vendas[ti]*S[0]
    eth=leg_nd.copy()
    for ti in range(T):
        for c in range(1,ti+1): eth[ti]+=vendas[c]*(1-d)*Snd[ti-c]*inten[c]
    idx=eth/eth[0]
    lev=np.array([idx[i]*(mp.HID_L+mp.GASC_L*pl.teor(int(a)))/1e9 for i,a in enumerate(ANOS)])
    return frota,vendas,lev
g=pl.PIB["PIBpc 1,5%"]
for lim in ("inferior","superior"):
    fr=pl.motorizacao(g,lim)/1000*np.array([pl.POP[a] for a in ANOS])
    m=mp.projetar(lim,g); motos=m["hid"]+m["anid"]
    for traj in ("rapida","central","lenta"):
        out={}
        for nome,kw in (("base",{}),("antecip",{"v26":V26}),("patamar",{"v26":V26,"novo_patamar":True})):
            out[nome]=proj(fr,traj,**kw)
        if traj=="central":
            for nome,(f,v,l) in out.items():
                print(lim,nome,"vendas 26-30:",[round(x/1e6,2) for x in v[1:6]],"frota 2030/2050:",round(f[5]/1e6,1),round(f[25]/1e6,1))
        b=out["base"][2]+motos
        for nome in ("antecip","patamar"):
            x=out[nome][2]+motos
            print(f"  {lim:9} {traj:8} {nome:8}", " ".join(f"{a}: {b[a-2025]:.1f}->{x[a-2025]:.1f} ({100*(x[a-2025]/b[a-2025]-1):+.1f}%)" for a in (2030,2035,2040,2050)))
