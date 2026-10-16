"""
Sucateamento de motocicletas calibrado por safra.

frota(t, faixa) = soma das vendas da safra c x S(t - c + 1)  (convencao do Sindipecas)
Vendas: Abraciclo, varejo 2003-2025; antes de 2003, producao x 0,86.
Alvos: Abipecas/Sindipecas, Relatorio da Frota Circulante 2026:
  frota de motos 2016-2025 (Tabela 1) e participacao por faixa (Grafico 17:
  0-5, 6-10, 11-15, 16-20 anos; o relatorio nao registra motos com mais de 20).
Forma: S(a) = exp(-h*a - (a/lam)^k), com S = 0 acima de 20 anos.
"""
import csv
import numpy as np
from scipy.optimize import least_squares

VENDAS = {int(r[0]): int(r[1]) for r in csv.reader(open("dados/motos_vendas_abraciclo.csv"), delimiter=";") if r[0].isdigit()}
FROTA = dict(zip(range(2016, 2026), [13529204, 13286420, 13121015, 13099707, 12877610,
                                      12870983, 13035988, 13261784, 14014294, 14583338]))
PART = [  # % por faixa, 2016-2025
    [42.1, 37.8, 34.7, 32.9, 31.3, 32.6, 35.6, 38.3, 42.5, 47.4],
    [40.0, 40.3, 39.0, 38.0, 36.1, 31.7, 27.5, 24.6, 22.1, 19.2],
    [13.8, 17.1, 20.6, 22.5, 25.0, 27.0, 26.3, 24.7, 22.7, 20.0],
    [4.1, 4.8, 5.7, 6.6, 7.5, 8.8, 10.5, 12.4, 12.8, 13.4]]
FAIXAS = [(1, 5), (6, 10), (11, 15), (16, 20)]   # idade 0 vazia na convencao t-c+1
IDADE_MAX = 20
A = np.arange(0, 61, dtype=float)
ANOS = list(range(2016, 2026))


def S_of(p):
    h, lam, k = p
    s = np.exp(-h * A - (A / lam) ** k)
    s[A > IDADE_MAX] = 0.0
    return s


def por_idade(t, S):
    return np.array([VENDAS.get(t - a + 1, 0) * S[a] if a >= 1 else 0.0 for a in range(len(A))])


def previsto(S):
    tot = np.array([por_idade(t, S).sum() for t in ANOS])
    fx = np.array([[por_idade(t, S)[lo:hi + 1].sum() for t in ANOS] for lo, hi in FAIXAS])
    return tot, fx


def ajustar():
    f = np.array([FROTA[t] for t in ANOS], float)
    fx_obs = np.array(PART) / 100 * f
    def resid(p):
        tot, fx = previsto(S_of(p))
        return np.concatenate([(tot - f) / f, ((fx - fx_obs) / f).ravel()])
    sol = least_squares(resid, (0.05, 15, 3), bounds=((0, 3, 1), (0.5, 60, 40)))
    return sol


if __name__ == "__main__":
    sol = ajustar()
    S = S_of(sol.x)
    tot, fx = previsto(S)
    f = np.array([FROTA[t] for t in ANOS], float)
    print("params h, lam, k:", np.round(sol.x, 4))
    print("erro frota %.1f%% | erro faixas %.1f p.p." % (
        100 * np.sqrt(np.mean(((tot - f) / f) ** 2)),
        100 * np.sqrt(np.mean(((fx - np.array(PART) / 100 * f) / f) ** 2))))
    print("vida media (anos): %.1f" % (S[1:].sum()))
    print("S(1,5,10,15,20):", [round(S[a], 2) for a in (1, 5, 10, 15, 20)])
    for i, t in enumerate(ANOS):
        print(t, "frota prev %.2f obs %.2f | faixas prev" % (tot[i] / 1e6, f[i] / 1e6),
              [round(100 * x / f[i], 1) for x in fx[:, i]], "obs", [p[i] for p in PART])
    # sucateamento implicito
    for t in range(2017, 2026):
        print(t, "sucateamento obs %.2f M" % ((VENDAS[t] - (FROTA[t] - FROTA[t - 1])) / 1e6))
