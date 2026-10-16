"""
Calibracao da curva de sucateamento por reconstrucao de safras.

frota(t, faixa) = soma das vendas da safra c x S(t - c), para as idades da faixa.
Vendas: Anfavea, emplacamentos de automoveis e comerciais leves, 1957-2025.
Alvos: Abipecas/Sindipecas, Relatorio da Frota Circulante (ed. 2023 e 2026):
  - frota total por segmento, 2010-2025 (16 pontos);
  - frota por faixa etaria quinquenal, 2016-2025 (50 pontos).
Convencao de idade: o melhor ajuste conta a safra vendida no ano c com idade 1
no proprio ano c (idade = t - c + 1), como no relatorio. Com idade = t - c o
erro nas faixas sobe de 0,2 para 3,3 p.p. (ver OFFSET).

Formas:
  weibull       S(a) = exp(-(a/lam)^k)
  weibull_fundo S(a) = exp(-h*a - (a/lam)^k)
"""
import csv
import json
import numpy as np
from scipy.optimize import least_squares

VENDAS = {"automoveis": {}, "comerciais_leves": {}}
for r in csv.reader(open("dados/anfavea_autos_cl_1957_2025.csv", encoding="utf-8"), delimiter=";"):
    if r and r[0].isdigit():
        VENDAS["automoveis"][int(r[0])] = int(r[1])
        VENDAS["comerciais_leves"][int(r[0])] = int(r[2])

FROTA = {
    "automoveis": [26507928, 28629421, 30898766, 32992248, 34712948, 35621014,
                   35996611, 36430823, 37098282, 37970401, 38149197, 38235585,
                   38338829, 38401527, 39006708, 39471493],
    "comerciais_leves": [3549031, 3889646, 4199866, 4522584, 4853583, 4996122,
                         5072404, 5173023, 5333843, 5523823, 5649895, 5849943,
                         5995263, 6147727, 6433915, 6652206],
}
ANOS_F = list(range(2010, 2026))
PART = {  # % por faixa 0-5, 6-10, 11-15, 16-20, >20; anos 2016-2025
    "automoveis": [
        [33.8, 30.1, 27.2, 25.4, 23.9, 23.5, 22.7, 21.3, 20.6, 21.3],
        [31.6, 33.8, 34.8, 34.4, 32.5, 29.5, 26.5, 24.3, 22.8, 21.4],
        [15.7, 17.4, 19.6, 22.0, 24.9, 27.6, 29.8, 31.2, 31.0, 29.1],
        [13.4, 12.6, 12.4, 13.0, 13.2, 13.7, 15.3, 17.5, 19.8, 22.3],
        [5.4, 6.1, 6.0, 5.3, 5.5, 5.7, 5.7, 5.7, 5.7, 5.9]],
    "comerciais_leves": [
        [42.5, 38.0, 34.0, 30.7, 29.8, 30.8, 31.1, 30.9, 32.1, 34.0],
        [34.2, 38.0, 40.3, 41.7, 38.9, 34.2, 30.4, 27.4, 24.5, 23.5],
        [14.1, 15.2, 17.7, 20.0, 23.8, 27.5, 30.4, 32.5, 33.3, 30.7],
        [7.5, 6.8, 6.1, 6.0, 5.9, 5.9, 6.6, 7.9, 8.9, 10.6],
        [1.8, 1.9, 1.9, 1.5, 1.6, 1.5, 1.4, 1.3, 1.2, 1.2]],
}
FAIXAS = [(0, 5), (6, 10), (11, 15), (16, 20), (21, 70)]
ANOS_B = list(range(2016, 2026))
OFFSET = 1          # idade = t - c + OFFSET
A = np.arange(0, 71, dtype=float)


def S_of(p, forma):
    if forma == "weibull":
        lam, k = p
        return np.exp(-(A / lam) ** k)
    h, lam, k = p
    return np.exp(-h * A - (A / lam) ** k)


def por_idade(seg, t, S):
    """Frota do ano t por idade, a partir das vendas e de S."""
    v = VENDAS[seg]
    return np.array([v.get(t - a + OFFSET, 0) * S[a] if a >= OFFSET else 0.0
                     for a in range(len(A))])


def previsto(seg, S):
    tot = [por_idade(seg, t, S).sum() for t in ANOS_F]
    fx = [[por_idade(seg, t, S)[lo:hi + 1].sum() for t in ANOS_B] for lo, hi in FAIXAS]
    return np.array(tot), np.array(fx)


def observado(seg):
    f = np.array(FROTA[seg], float)
    fx = np.array(PART[seg]) / 100 * f[6:]
    return f, fx


def ajustar(seg, forma):
    f_obs, fx_obs = observado(seg)
    def resid(p):
        tot, fx = previsto(seg, S_of(p, forma))
        r_tot = (tot - f_obs) / f_obs
        r_fx = (fx - fx_obs) / f_obs[6:]        # erro de cada faixa em % da frota
        return np.concatenate([r_tot, r_fx.ravel()])
    if forma == "weibull":
        x0, lb, ub = (20, 4), (8, 1), (45, 40)
    else:
        x0, lb, ub = (0.015, 23, 8), (0, 12, 1), (0.1, 45, 40)
    return least_squares(resid, x0, bounds=(lb, ub))


if __name__ == "__main__":
    out = {}
    for seg in VENDAS:
        f_obs, fx_obs = observado(seg)
        out[seg] = {}
        print(f"\n===== {seg}")
        for forma in ("weibull", "weibull_fundo"):
            sol = ajustar(seg, forma)
            S = S_of(sol.x, forma)
            tot, fx = previsto(seg, S)
            vida = S.sum() - 0.5
            rmse_tot = 100 * np.sqrt(np.mean(((tot - f_obs) / f_obs) ** 2))
            rmse_fx = 100 * np.sqrt(np.mean(((fx - fx_obs) / f_obs[6:]) ** 2))
            print(f"[{forma}] params={np.round(sol.x, 4).tolist()} vida media {vida:.1f} a"
                  f" | erro frota total {rmse_tot:.1f}% | erro faixas {rmse_fx:.1f} p.p.")
            print("   frota 2010/2015/2020/2025 prevista: "
                  + " ".join(f"{tot[i]/1e6:.2f}" for i in (0, 5, 10, 15))
                  + "  observada: " + " ".join(f"{f_obs[i]/1e6:.2f}" for i in (0, 5, 10, 15)))
            print("   faixas 2025 prevista %: " + " ".join(f"{100*x/f_obs[-1]:.1f}" for x in fx[:, -1])
                  + " | observada: " + " ".join(f"{p[-1]:.1f}" for p in PART[seg]))
            out[seg][forma] = {"params": sol.x.tolist(), "vida_media": vida,
                               "erro_total_pct": rmse_tot, "erro_faixas_pp": rmse_fx}
    json.dump(out, open("resultados/calibracao_por_safra.json", "w"), indent=1)
