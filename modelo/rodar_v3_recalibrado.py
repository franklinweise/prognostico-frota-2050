"""Roda o modelo v3 com:
 (a) curva de sucateamento calibrada por safra (calibrar_por_safra.py):
     automoveis   S(a) = exp(-0,0149 a - (a/23,44)^16,89)
     com. leves   S(a) = exp(-0,0117 a - (a/19,06)^7,60)
     (a = idade na convencao do Sindipecas, safra do ano c tem idade 1 em c);
 (b) frota legada reconstruida a partir das vendas reais da Anfavea (1957-2025)
     em vez do regime estacionario;
 (c) vendas novas com 78% automoveis / 22% comerciais leves (mix de 2025).
Precisa de modelo_frota_etanol_v3.py e dados/anfavea_autos_cl_1957_2025.csv.
"""
import numpy as np
import modelo_frota_etanol_v3 as m
import calibrar_por_safra as cal

A = np.arange(0, 80, dtype=float)
def S_fit(h, lam, k):
    return np.exp(-h * A - (A / lam) ** k)

# convencao do v3: SURV[x] = fracao em circulacao x anos apos o ano de venda
S_AUTO = S_fit(0.0149, 23.4368, 16.8893)[1:]
S_CL = S_fit(0.0117, 19.0579, 7.5984)[1:]
W_CL = 554937 / 2552201            # fatia dos comerciais leves nas vendas de 2025
S_NOVO = (1 - W_CL) * S_AUTO + W_CL * S_CL

def legado(t):
    """Frota (no fim do ano 2025 + t) remanescente das safras <= 2025."""
    tot = 0.0
    for seg, S in (("automoveis", S_AUTO), ("comerciais_leves", S_CL)):
        for c, v in cal.VENDAS[seg].items():
            x = 2025 + t - c
            if x < len(S):
                tot += v * S[x]
    return tot

def rodar(mix, frota_fn=m.frota_composta, escala=True):
    T = m.T
    leg = np.array([legado(t) for t in range(T)])
    if escala:                          # alinha o legado a frota-alvo de 2025
        leg *= m.F0 / leg[0]
    inten = sum(mix[k] * m.INTENS[k] for k in m.INTENS)
    vendas = np.zeros(T)
    for ti in range(1, T):
        sob = leg[ti] + sum(vendas[c] * S_NOVO[ti - c] for c in range(1, ti))
        vendas[ti] = (frota_fn(int(m.YRS[ti])) - sob) / S_NOVO[0]
    eth = leg.copy()                    # legado = flex convencional
    for ti in range(T):
        eth[ti] += sum(vendas[c] * S_NOVO[ti - c] * inten[c] for c in range(1, ti + 1))
    return eth / eth[0], vendas, leg

if __name__ == "__main__":
    print(f"legado reconstruido 2025: {legado(0)/1e6:.2f} M (Sindipecas 46,12 M)")
    for fr in ("composta", "logistica"):
        res = {n: rodar(m.mix_vendas(n), m.FROTAS[fr]) for n in ("rapida", "central", "lenta")}
        ic, v, leg = res["central"]
        suc26 = leg[0] - leg[1] + v[1] * (1 - S_NOVO[0])
        print(f"\nFROTA {fr} | vendas 2026 {v[1]/1e6:.2f} M | sucateamento 2026 {suc26/1e6:.2f} M"
              f" | vendas 2030 {v[5]/1e6:.2f} 2035 {v[10]/1e6:.2f} 2040 {v[15]/1e6:.2f}"
              f" 2050 {v[25]/1e6:.2f}")
        print("  indice  " + " ".join(f"{a:>5}" for a in m.MARCOS))
        for n in ("rapida", "central", "lenta"):
            print(f"  {n:<7} " + " ".join(f"{100*m.em(res[n][0], a):5.0f}" for a in m.MARCOS))
        print(f"  excedente central 2035 {m.excedente(ic, 2035):.1f}  2040 {m.excedente(ic, 2040):.1f}")
