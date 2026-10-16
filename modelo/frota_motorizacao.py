"""
Frota de leves (automoveis + comerciais leves) por motorizacao, 2025-2050, nas tres
trajetorias de eletrificacao, sobre a frota da estimativa central (PIBpc 1,5% a.a.,
media dos limites de motorizacao). Mesma contabilidade de projecao_2050.projetar:
safras ate 2025 = flex (nao-diesel) ou diesel; safras novas repartidas pelo mix de vendas.
Saida: resultados/frota_motorizacao_2025_2050.csv
"""
import csv
import numpy as np
import projecao_2050 as pl
import rodar_v3_sem_diesel as sd
import cenario_central as cc

T, ANOS = pl.T, pl.ANOS


def compor(frota_alvo, traj):
    leg = np.array([sd.legado(t) for t in range(T)])
    esc = frota_alvo[0] / leg[0].sum()
    leg_nd, leg_d = leg[:, 0] * esc, leg[:, 1] * esc
    S, Snd, Sd, d = sd.S_NOVO, sd.S_ND, sd.S_D, sd.D_FUT
    mix = sd.mix_nd(traj)
    vendas = np.zeros(T)
    for ti in range(1, T):
        sob = leg_nd[ti] + leg_d[ti] + sum(vendas[c] * S[ti - c] for c in range(1, ti))
        vendas[ti] = (frota_alvo[ti] - sob) / S[0]
    out = {k: np.zeros(T) for k in ("BEV", "PHEV", "HEV", "ICE")}
    out["ICE"] += leg_nd
    dsl = leg_d.copy()
    for ti in range(T):
        for c in range(1, ti + 1):
            nd = vendas[c] * (1 - d) * Snd[ti - c]
            for k in out:
                out[k][ti] += nd * mix[k][c]
            dsl[ti] += vendas[c] * d * Sd[ti - c]
    out["diesel"] = dsl
    return out


if __name__ == "__main__":
    with open("resultados/frota_motorizacao_2025_2050.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["ano", "trajetoria", "bev", "phev", "hev_flex", "flex", "diesel", "total"])
        for t in ("rapida", "central", "lenta"):
            r = compor(cc.frota_l, t)
            for i, a in enumerate(ANOS):
                v = [r[k][i] for k in ("BEV", "PHEV", "HEV", "ICE", "diesel")]
                w.writerow([int(a), t] + [round(x) for x in v] + [round(sum(v))])
    print("gravado: resultados/frota_motorizacao_2025_2050.csv")
