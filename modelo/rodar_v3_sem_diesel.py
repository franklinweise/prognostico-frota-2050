"""
Modelo v3 recalibrado, contando etanol apenas na parcela da frota leve que
nao e movida a diesel.

Segmento diesel (picapes, utilitarios e alguns SUVs):
  - historico: participacao diesel nas vendas da Anfavea por combustivel,
    2019-2025 (comerciais leves 39-49%, automoveis 1-4%); antes de 2019,
    comerciais leves 43,1% e automoveis 0%, calibrado para reproduzir a frota
    leve a diesel do Sindipecas 2016-2025 (participacao diesel nos autoveiculos,
    Grafico 4, menos caminhoes e onibus, supostos 100% diesel);
  - futuro: a fatia de 2025 nas vendas de leves (9,96%) e mantida; esse
    segmento nao consome etanol qualquer que seja a motorizacao.
Segmento nao-diesel: recebe o mix BEV/PHEV/HEV/flex do v3. As trajetorias sao
reancoradas nas vendas nao-diesel de jul/2026 (BEV 9,7% do total = 10,8% do
nao-diesel; hibridos 12,6% -> 14,2% das vendas nao-BEV nao-diesel).
A frota-alvo (composta ou logistica) continua sendo a do total de leves.
"""
import math
import numpy as np
import modelo_frota_etanol_v3 as m
import calibrar_por_safra as cal
from rodar_v3_recalibrado import S_AUTO, S_CL

V = cal.VENDAS
D_CL = {2019: .491, 2020: .483, 2021: .488, 2022: .477, 2023: .393, 2024: .395, 2025: .409}
D_AU = {2019: .023, 2020: .029, 2021: .038, 2022: .029, 2023: .020, 2024: .014, 2025: .013}
D_CL_PRE, D_AU_PRE = 0.431, 0.0

# composicao das vendas de 2025 (Anfavea): base das vendas futuras
AU25, CL25 = V["automoveis"][2025], V["comerciais_leves"][2025]
DIESEL_AU, DIESEL_CL = AU25 * D_AU[2025], CL25 * D_CL[2025]
D_FUT = (DIESEL_AU + DIESEL_CL) / (AU25 + CL25)
S_D = (DIESEL_AU * S_AUTO + DIESEL_CL * S_CL) / (DIESEL_AU + DIESEL_CL)
ND_AU, ND_CL = AU25 - DIESEL_AU, CL25 - DIESEL_CL
S_ND = (ND_AU * S_AUTO + ND_CL * S_CL) / (ND_AU + ND_CL)
S_NOVO = D_FUT * S_D + (1 - D_FUT) * S_ND

# reancoragem no segmento nao-diesel (ABVE jul/2026, total leves 265.695)
TOT_JUL = 265695
ND_JUL = TOT_JUL * (1 - D_FUT)
S_ANC_ND = 25782 / ND_JUL
H_ANC_ND = 30292 / (ND_JUL - 25782)


def legado(t):
    """Frota legada (safras <= 2025) no ano 2025+t: (nao-diesel, diesel)."""
    nd = d = 0.0
    for seg, S, dd, pre in (("automoveis", S_AUTO, D_AU, D_AU_PRE),
                            ("comerciais_leves", S_CL, D_CL, D_CL_PRE)):
        for c, v in V[seg].items():
            x = 2025 + t - c
            if x < len(S):
                fd = dd.get(c, pre)
                d += v * fd * S[x]
                nd += v * (1 - fd) * S[x]
    return nd, d


def mix_nd(nome, h_max=m.H_MAX):
    p = m.TRAJETORIAS[nome]
    k, tm = m.logistica_ancorada(p["assintota"], p["anos"], m.T_ANCORA, S_ANC_ND)
    tc = m.YRS + 0.5
    bev = m.s_bev(tc, p["assintota"], k, tm)
    kh, tmh = m.logistica_ancorada(h_max, m.H_ANOS, m.T_ANCORA, H_ANC_ND)
    hib = (1 - bev) * m.s_bev(tc, h_max, kh, tmh)
    return {"BEV": bev, "PHEV": hib * m.FRAC_PHEV, "HEV": hib * (1 - m.FRAC_PHEV),
            "ICE": 1 - bev - hib}


def rodar(mix, frota_fn=m.frota_composta):
    T = m.T
    leg = np.array([legado(t) for t in range(T)])
    esc = m.F0 / leg[0].sum()                # alinha o legado a frota de 2025
    leg_nd, leg_d = leg[:, 0] * esc, leg[:, 1] * esc
    vendas = np.zeros(T)
    for ti in range(1, T):
        sob = leg_nd[ti] + leg_d[ti] + sum(vendas[c] * S_NOVO[ti - c] for c in range(1, ti))
        vendas[ti] = (frota_fn(int(m.YRS[ti])) - sob) / S_NOVO[0]
    inten = sum(mix[k] * m.INTENS[k] for k in m.INTENS)
    eth, f_nd, f_d = leg_nd.copy(), leg_nd.copy(), leg_d.copy()
    for ti in range(T):
        for c in range(1, ti + 1):
            vnd = vendas[c] * (1 - D_FUT)
            eth[ti] += vnd * S_ND[ti - c] * inten[c]
            f_nd[ti] += vnd * S_ND[ti - c]
            f_d[ti] += vendas[c] * D_FUT * S_D[ti - c]
    return eth / eth[0], vendas, f_nd, f_d


if __name__ == "__main__":
    import rodar_v3_recalibrado as rec
    nd0, d0 = legado(0)
    print(f"frota leve 2025 reconstruida: nao-diesel {nd0/1e6:.2f} M, diesel {d0/1e6:.2f} M "
          f"({100*d0/(nd0+d0):.1f}%) | Sindipecas: diesel ~3,27 M")
    print(f"diesel nas vendas futuras: {100*D_FUT:.2f}% | ancora BEV nao-diesel {100*S_ANC_ND:.1f}%"
          f" | hibridos {100*H_ANC_ND:.1f}%")
    for fr in ("composta", "logistica"):
        fn = m.FROTAS[fr]
        print(f"\n===== FROTA {fr}")
        res = {n: rodar(mix_nd(n), fn) for n in ("rapida", "central", "lenta")}
        ant = {n: rec.rodar(m.mix_vendas(n), fn)[0] for n in ("rapida", "central", "lenta")}
        _, v, fnd, fd = res["central"]
        for a in (2025, 2035, 2050):
            i = a - 2025
            print(f"  {a}: frota nao-diesel {fnd[i]/1e6:.1f} M | diesel {fd[i]/1e6:.1f} M ({100*fd[i]/(fnd[i]+fd[i]):.1f}%)")
        print("  indice (2025=100)       " + " ".join(f"{a:>5}" for a in m.MARCOS))
        for n in ("rapida", "central", "lenta"):
            print(f"  {n:<7} recalibrado   " + " ".join(f"{100*m.em(ant[n], a):5.0f}" for a in m.MARCOS))
            print(f"  {n:<7} sem diesel    " + " ".join(f"{100*m.em(res[n][0], a):5.0f}" for a in m.MARCOS))
        ic = res["central"][0]
        print("  Tabela 3 (ciclo leve, bi L): " + " ".join(
            f"{a}: " + "/".join(f"{m.ciclo_leve(res[n][0], a):.1f}" for n in ("rapida", "central", "lenta"))
            for a in (2030, 2035, 2040, 2050)))
        print(f"  excedente central 2035 {m.excedente(ic, 2035):.1f} | 2040 {m.excedente(ic, 2040):.1f}"
              f" | (recalibrado: {m.excedente(ant['central'], 2035):.1f} | {m.excedente(ant['central'], 2040):.1f})")
