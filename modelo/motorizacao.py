"""
Curva de motorizacao: veiculos leves por 1.000 adultos (18+) em funcao do PIB
per capita real.

Dados:
  - frota leve 2010-2025: Sindipecas (ed. 2023 e 2026);
  - frota leve 2000-2009: reconstruida pelas vendas Anfavea (1957-2009) x curva
    de sucateamento calibrada (calibrar_por_safra.py); nos anos com dado
    observado a reconstrucao difere em menos de 0,8%;
  - populacao 18+: IBGE, projecao edicao 2024;
  - PIB per capita: IBGE, variacao real (SIDRA 6784, 2000-2023; 2024 derivado;
    2025 Contas Trimestrais), indice 2000 = 100.

Modelo (Dargay & Gately, com ajuste parcial):
  m*(y) = M * exp(-alpha * exp(-beta * y/100))     motorizacao de equilibrio
  m(t)  = m(t-1) + theta * (m*(y_t) - m(t-1))
M (saturacao) nao e identificavel com 26 anos de dados; o ajuste e feito para
varios valores fixos de M.
"""
import csv
import numpy as np
from scipy.optimize import least_squares
import calibrar_por_safra as cal
from rodar_v3_recalibrado import S_AUTO, S_CL

POP = {int(r[0].strip('"')): int(r[1]) for r in csv.reader(
    open("dados/pop18_ibge_2024.csv", encoding="latin-1"), delimiter=";")
    if r and r[0].strip('"').isdigit()}
V = cal.VENDAS
OBS = dict(zip(range(2010, 2026), [
    30056959, 32519067, 35098632, 37514832, 39566531, 40617136, 41069015,
    41603846, 42432125, 43494224, 43799092, 44085528, 44334092, 44549254,
    45440623, 46123699]))


def frota_reconstruida(t):
    return sum(V["automoveis"][c] * S_AUTO[t - c] + V["comerciais_leves"][c] * S_CL[t - c]
               for c in range(1957, t + 1) if t - c < len(S_AUTO))


ANOS = np.arange(2000, 2026)
PIBPC = {}
y = 100.0
for r in csv.reader(open("dados/pib_per_capita_ibge.csv"), delimiter=";"):
    if r[0].isdigit():
        if int(r[0]) > 2000:
            y *= 1 + float(r[1]) / 100
        PIBPC[int(r[0])] = y
FROTA = np.array([OBS.get(a, frota_reconstruida(a)) for a in ANOS])
MOT = 1000 * FROTA / np.array([POP[a] for a in ANOS])
Y = np.array([PIBPC[a] for a in ANOS])


def m_eq(y, M, alpha, beta):
    return M * np.exp(-alpha * np.exp(-beta * y / 100))


def simular(params, M, y_path, m0):
    alpha, beta, theta = params
    out, m = [], m0
    for y in y_path:
        m = m + theta * (m_eq(y, M, alpha, beta) - m)
        out.append(m)
    return np.array(out)


def ajustar(M):
    def resid(p):
        return (simular(p, M, Y[1:], MOT[0]) - MOT[1:]) / MOT[1:]
    sol = least_squares(resid, (3, 1.5, 0.2), bounds=((0.01, 0.01, 0.01), (50, 20, 1)))
    rmse = 100 * np.sqrt(np.mean(sol.fun ** 2))
    return sol.x, rmse


if __name__ == "__main__":
    print("ano  PIBpc(2000=100)  frota(M)  leves/1000 adultos")
    for a, y, f, mz in zip(ANOS, Y, FROTA, MOT):
        print(f"{a}  {y:6.1f}  {f/1e6:6.2f}  {mz:5.0f}")
    print("\nM fixo -> alpha beta theta | erro % | m* em 2025 | elasticidade-renda de m* em 2025")
    for M in (350, 400, 450, 500, 600, 700):
        p, e = ajustar(M)
        me = m_eq(Y[-1], M, *p[:2])
        el = p[0] * p[1] * Y[-1] / 100 * np.exp(-p[1] * Y[-1] / 100)
        print(f"  M={M}: {np.round(p, 3).tolist()} | {e:.2f}% | {me:.0f} | {el:.2f}")
