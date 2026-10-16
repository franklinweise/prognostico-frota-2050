"""Frota por segmento (automoveis, comerciais leves, motos), 2010-2050.
Historico: Sindipecas (leves 2010-2025; motos 2016-2025, 2010-2015 reconstruida).
Projecao: PIB per capita 1,5% a.a., media dos limites inferior e superior.
Divisao autos/CL da frota projetada: estoque por segmento (vendas Anfavea + curvas
de cada segmento; vendas futuras na proporcao de 2025), reescalado ao total."""
import csv, numpy as np
import projecao_2050 as pl, rodar_v3_sem_diesel as sd, motos_projecao as mp, motos_calibrar as mc
ANOS=pl.ANOS; T=pl.T; g=pl.PIB["PIBpc 1,5%"]
sh_au = sd.V['automoveis'][2025]/(sd.V['automoveis'][2025]+sd.V['comerciais_leves'][2025])
def seg(frota):
    r=pl.projetar(frota,"central"); v=r["vendas"]
    au=np.zeros(T); cl=np.zeros(T)
    for t in range(T):
        for s,S,arr in (("automoveis",sd.S_AUTO,au),("comerciais_leves",sd.S_CL,cl)):
            arr[t]=sum(x*S[2025+t-c] for c,x in sd.V[s].items() if 2025+t-c<len(S))
            arr[t]+=sum(v[c]*(sh_au if s=="automoveis" else 1-sh_au)*S[t-c] for c in range(1,t+1))
    k=frota/(au+cl); return au*k, cl*k
res=[]
for lim in ("inferior","superior"):
    fr=pl.motorizacao(g,lim)/1000*np.array([pl.POP[a] for a in ANOS])
    au,cl=seg(fr); mo=mp.projetar(lim,g)["frota"]; res.append((au,cl,mo))
au=(res[0][0]+res[1][0])/2; cl=(res[0][1]+res[1][1])/2; mo=(res[0][2]+res[1][2])/2
H={int(r['ano']):r for r in csv.DictReader(open('dados/frota_sindipecas_2010_2025.csv'),delimiter=';')}
S=mc.S_of(mc.ajustar().x)
rows=[]
for a in range(2010,2026):
    m=mc.FROTA.get(a, mc.por_idade(a,S).sum())
    rows.append((a,int(H[a]['automoveis'])/1e6,int(H[a]['comerciais_leves'])/1e6,m/1e6))
for i,a in enumerate(ANOS):
    if a>2025: rows.append((int(a),au[i]/1e6,cl[i]/1e6,mo[i]/1e6))
with open('resultados/frota_segmentos_2010_2050.csv','w') as f:
    f.write('ano;automoveis_mi;comerciais_leves_mi;motos_mi\n')
    for r in rows: f.write('%d;%.2f;%.2f;%.2f\n'%r)
for r in rows:
    if r[0] in (2010,2015,2020,2024,2025,2026,2030,2040,2050): print(r, round(sum(r[1:]),1))
