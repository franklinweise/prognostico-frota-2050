"""
PROGNOSTICO DE FROTA, VENDAS E CONSUMO DE ETANOL DOS VEICULOS LEVES, 2026-2050
Usa somente as estimativas construidas nesta sessao (11/out/2026):

  Frota total = populacao 18+ (IBGE, projecao 2024) x motorizacao projetada
    motorizacao (leves por 1.000 adultos), dois limites:
      superior: curva de Gompertz com ajuste parcial (motorizacao.py), M = 500,
                calibrada em 2000-2025 (elasticidade-renda ~1,4, como em
                2000-2014), reancorada para que 2025 seja equilibrio: so o
                crescimento da renda move a motorizacao;
      inferior: elasticidade-renda observada em 2015-2025 (0,08): a motorizacao
                quase nao reage a renda.
    PIB per capita real: 1,0 / 1,5 / 2,0% a.a. a partir de 2026.
  Vendas = o necessario para atingir a frota, dado o sucateamento por safra
    (curvas de calibrar_por_safra.py; legado reconstruido com vendas Anfavea).
  Segmento diesel (9,9% das vendas, frota legada calibrada) nao consome etanol.
  Eletrificacao do segmento nao-diesel: trajetorias rapida/central/lenta e
    intensidades do artigo (unica premissa externa), reancoradas no nao-diesel.
  Consumo de etanol = indice da frota nao-diesel (2025 = 1) x base ANP 2025:
    hidratado 21,24 bi L + anidro = gasolina C 46,65 bi L x teor de mistura
    (E27 jan-jul/2025, E30 ago/2025-jul/2026, E32 desde 1/ago/2026 - CNPE;
    E32 mantido no futuro).
    A base inclui o consumo das motocicletas (sem dado para separar).

Saida: resultados/projecao_2050.csv (todas as combinacoes, ano a ano).
"""
import csv
import os
import numpy as np
import modelo_frota_etanol_v3 as v3
import motorizacao as mz
import rodar_v3_sem_diesel as sd

ANOS = np.arange(2025, 2051)
T = len(ANOS)
POP = {a: mz.POP[a] for a in ANOS}

# ---------------------------------------------------------------- etanol base
HIDRATADO_25, GASOLINA_C_25 = 21.24, 46.65            # bi L, ANP (distribuidoras)
TEOR_25 = (7 * 0.27 + 5 * 0.30) / 12                  # E27 ate jul, E30 desde ago
TEOR_26 = (7 * 0.30 + 5 * 0.32) / 12                  # E30 ate jul, E32 desde ago/2026
def teor(a): return TEOR_25 if a == 2025 else TEOR_26 if a == 2026 else 0.32
def etanol_base(a): return HIDRATADO_25 + GASOLINA_C_25 * teor(a)

# ------------------------------------------------------------- motorizacao
M_SAT = 500
P_GOMP, _ = mz.ajustar(M_SAT)
ELAST_RECENTE = np.polyfit(np.log(mz.Y[mz.ANOS >= 2015]), np.log(mz.MOT[mz.ANOS >= 2015]), 1)[0]
Y25, MOT25 = mz.Y[-1], mz.MOT[-1]
PIB = {"PIBpc 1,0%": 0.010, "PIBpc 1,5%": 0.015, "PIBpc 2,0%": 0.020}

def motorizacao(g, limite):
    y = Y25 * (1 + g) ** (ANOS - 2025)
    if limite == "inferior":
        return MOT25 * (y / Y25) ** ELAST_RECENTE
    # superior: reancorado para que 2025 seja ponto de equilibrio (sem o
    # "atraso" de ~50 veiculos/1.000 adultos que a curva atribui a 2025)
    m_ef = M_SAT * MOT25 / mz.m_eq(Y25, M_SAT, *P_GOMP[:2])
    return np.concatenate([[MOT25], mz.simular(P_GOMP, m_ef, y[1:], MOT25)])

# ------------------------------------------------- frota -> vendas -> etanol
def projetar(frota_alvo, traj):
    """frota_alvo: array 2025-2050. Retorna dict de series anuais."""
    leg = np.array([sd.legado(t) for t in range(T)])
    esc = frota_alvo[0] / leg[0].sum()
    leg_nd, leg_d = leg[:, 0] * esc, leg[:, 1] * esc
    S, Snd, Sd, d = sd.S_NOVO, sd.S_ND, sd.S_D, sd.D_FUT
    mix = sd.mix_nd(traj)
    inten = sum(mix[k] * v3.INTENS[k] for k in v3.INTENS)   # indexado por v3.YRS (2025..)
    vendas = np.zeros(T)
    for ti in range(1, T):
        sob = leg_nd[ti] + leg_d[ti] + sum(vendas[c] * S[ti - c] for c in range(1, ti))
        vendas[ti] = (frota_alvo[ti] - sob) / S[0]
    f_nd, f_d, eth = leg_nd.copy(), leg_d.copy(), leg_nd.copy()
    bev = np.zeros(T)
    for ti in range(T):
        for c in range(1, ti + 1):
            nd = vendas[c] * (1 - d) * Snd[ti - c]
            f_nd[ti] += nd
            f_d[ti] += vendas[c] * d * Sd[ti - c]
            eth[ti] += nd * inten[c]
            bev[ti] += nd * mix["BEV"][c]
    idx = eth / eth[0]
    consumo = np.array([idx[i] * etanol_base(a) for i, a in enumerate(ANOS)])
    return {"frota": frota_alvo, "frota_nao_diesel": f_nd, "frota_diesel": f_d,
            "frota_bev": bev, "vendas": vendas, "indice": idx, "etanol_bi_l": consumo}


if __name__ == "__main__":
    os.makedirs("resultados", exist_ok=True)
    linhas, res = [], {}
    for lim in ("inferior", "superior"):
        for pn, g in PIB.items():
            mot = motorizacao(g, lim)
            frota = mot / 1000 * np.array([POP[a] for a in ANOS])
            for traj in ("rapida", "central", "lenta"):
                r = projetar(frota, traj)
                res[(lim, pn, traj)] = r | {"motorizacao": mot}
                for i, a in enumerate(ANOS):
                    linhas.append([a, lim, pn, traj, POP[a], round(mot[i], 1),
                                   round(r["frota"][i]), round(r["frota_nao_diesel"][i]),
                                   round(r["frota_diesel"][i]), round(r["frota_bev"][i]),
                                   round(r["vendas"][i]) if i else "",
                                   round(r["indice"][i], 4), round(r["etanol_bi_l"][i], 2)])
    with open("resultados/projecao_2050.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["ano", "motorizacao_limite", "cenario_pib", "trajetoria_eletrificacao",
                    "pop_18mais", "leves_por_1000_adultos", "frota_leves", "frota_nao_diesel",
                    "frota_diesel", "frota_bev_vendidos_desde_2026", "vendas_leves",
                    "indice_etanol_2025_1", "consumo_etanol_bi_l"])
        w.writerows(linhas)

    print(f"Gompertz M={M_SAT}: alpha={P_GOMP[0]:.2f} beta={P_GOMP[1]:.3f} theta={P_GOMP[2]:.3f}"
          f" | elasticidade recente {ELAST_RECENTE:.2f}")
    print(f"base etanol 2025: {etanol_base(2025):.1f} bi L (hidratado {HIDRATADO_25} + anidro"
          f" {GASOLINA_C_25*TEOR_25:.1f}); E32 o ano todo (2027+): {etanol_base(2027):.1f}")
    print("\nFROTA DE LEVES (M) e MOTORIZACAO, 2030 / 2040 / 2050")
    for lim in ("inferior", "superior"):
        for pn in PIB:
            r = res[(lim, pn, "central")]
            print(f"  {lim:<8} {pn}: " + " | ".join(
                f"{a}: {r['frota'][a-2025]/1e6:5.1f} M ({r['motorizacao'][a-2025]:.0f})" for a in (2030, 2040, 2050)))
    print("\nVENDAS DE LEVES (M/ano), trajetoria central, 2026 / 2030 / 2035 / 2040 / 2050")
    for lim in ("inferior", "superior"):
        for pn in PIB:
            v = res[(lim, pn, "central")]["vendas"]
            print(f"  {lim:<8} {pn}: " + " ".join(f"{v[a-2025]/1e6:5.2f}" for a in (2026, 2030, 2035, 2040, 2050)))
    print("\nCONSUMO DE ETANOL (bi L), 2030 / 2035 / 2040 / 2050")
    for traj in ("rapida", "central", "lenta"):
        lo = res[("inferior", "PIBpc 1,0%", traj)]["etanol_bi_l"]
        hi = res[("superior", "PIBpc 2,0%", traj)]["etanol_bi_l"]
        print(f"  {traj:<7} " + " | ".join(f"{a}: {lo[a-2025]:4.1f}-{hi[a-2025]:4.1f}" for a in (2030, 2035, 2040, 2050)))
