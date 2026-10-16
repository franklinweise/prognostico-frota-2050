"""
PROJECAO DA FROTA DE MOTOCICLETAS E DO SEU CONSUMO DE ETANOL, 2025-2050
(sem eletrificacao, por premissa)

Frota = populacao 18+ (IBGE, 2024) x motos por mil adultos.
  Historico 2016-2025: Sindipecas; 2000-2015: reconstruida com vendas Abraciclo
  e a curva calibrada (motos_calibrar.py).
  Dois limites para a reacao a renda (PIB per capita real 1,0 / 1,5 / 2,0% a.a.):
    inferior: elasticidade de 2015-2025 (~0,1): motorizacao quase estavel;
    superior: elasticidade da retomada de 2021-2025 (~0,9).
Vendas = o necessario para atingir a frota, dado o sucateamento por safra.
Consumo (base 2025): fatias das motos no Inventario Nacional de Emissoes
  Veiculares 2025 (ano-base 2024) aplicadas a base ANP de 2025:
  anidro 0,89 bi L (gasolina C das motos 3,15 bi L) e hidratado 0,69 bi L.
  Por moto: gasolina C e hidratado constantes; anidro = gasolina C x teor (E32).
Tambem recalcula o etanol dos leves sem as motos e soma os dois.

Saidas: resultados/motos_2050.csv e resultados/etanol_leves_motos_2050.csv
"""
import csv
import numpy as np
import motos_calibrar as mc
import motorizacao as mz
import projecao_2050 as pl

ANOS = np.arange(2025, 2051)
T = len(ANOS)
SOL = mc.ajustar()
S = mc.S_of(SOL.x)                    # convencao: idade a = t - c + 1

# ---------------------------------------------------- historico e elasticidades
H = np.arange(2000, 2026)
FROTA_H = np.array([mc.FROTA.get(int(a), mc.por_idade(int(a), S).sum()) for a in H])
MOT_H = 1000 * FROTA_H / np.array([mz.POP[int(a)] for a in H])
Y_H = np.array([mz.PIBPC[int(a)] for a in H])
def elast(lo, hi):
    s = (H >= lo) & (H <= hi)
    return np.polyfit(np.log(Y_H[s]), np.log(MOT_H[s]), 1)[0]
ELAST = {"inferior": elast(2015, 2025), "superior": elast(2021, 2025)}
MOT25, Y25 = MOT_H[-1], Y_H[-1]

# ---------------------------------------------------- consumo por moto (2025)
HID_M, GASC_M = 0.69e9, 0.89e9 / pl.TEOR_25        # litros, motos 2025
HID_L, GASC_L = pl.HIDRATADO_25 * 1e9 - HID_M, pl.GASOLINA_C_25 * 1e9 - GASC_M
F25 = mc.FROTA[2025]


def projetar(lim, g):
    y = Y25 * (1 + g) ** (ANOS - 2025)
    mot = MOT25 * (y / Y25) ** ELAST[lim]
    frota = mot / 1000 * np.array([mz.POP[int(a)] for a in ANOS])
    frota[0] = F25
    # legado: safras <= 2025 (vendas reais), escalado para a frota de 2025
    leg = np.array([sum(v * S[2025 + t - c + 1] for c, v in mc.VENDAS.items() if 2025 + t - c + 1 < len(S))
                    for t in range(T)])
    leg *= F25 / leg[0]
    vendas = np.zeros(T)
    for ti in range(1, T):
        sob = leg[ti] + sum(vendas[c] * S[ti - c + 1] for c in range(1, ti))
        vendas[ti] = (frota[ti] - sob) / S[1]
    idx = frota / F25
    hid = HID_M * idx / 1e9
    anid = np.array([GASC_M * idx[i] * pl.teor(int(a)) for i, a in enumerate(ANOS)]) / 1e9
    return {"mot": mot, "frota": frota, "vendas": vendas, "hid": hid, "anid": anid}


if __name__ == "__main__":
    print("curva: h=%.4f lam=%.2f k=%.3f, corte 20 anos; vida media %.1f anos" % (*SOL.x, S[1:].sum()))
    print("elasticidades: inferior %.2f | superior %.2f" % (ELAST["inferior"], ELAST["superior"]))
    print("base 2025: motos hidratado %.2f + anidro %.2f = %.2f bi L | leves %.2f bi L" % (
        HID_M / 1e9, 0.89, HID_M / 1e9 + 0.89, (HID_L + GASC_L * pl.TEOR_25) / 1e9))
    res = {}
    for lim in ("inferior", "superior"):
        for pn, g in pl.PIB.items():
            res[(lim, pn)] = projetar(lim, g)
    print("\nFROTA DE MOTOS (M) e motos por mil adultos")
    for (lim, pn), r in res.items():
        print(f"  {lim:<8} {pn}: " + " | ".join(f"{a}: {r['frota'][a-2025]/1e6:5.1f} ({r['mot'][a-2025]:.0f})" for a in (2030, 2040, 2050)))
    print("\nVENDAS DE MOTOS (M/ano): 2026 / 2030 / 2040 / 2050")
    for (lim, pn), r in res.items():
        print(f"  {lim:<8} {pn}: " + " ".join(f"{r['vendas'][a-2025]/1e6:5.2f}" for a in (2026, 2030, 2040, 2050)))
    print("\nETANOL DAS MOTOS (bi L): 2025 / 2030 / 2040 / 2050")
    for (lim, pn), r in res.items():
        e = r["hid"] + r["anid"]
        print(f"  {lim:<8} {pn}: " + " ".join(f"{e[a-2025]:5.2f}" for a in (2025, 2030, 2040, 2050)))

    # ------------------------------------------------------------ saidas
    with open("resultados/motos_2050.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["ano", "motorizacao_limite", "cenario_pib", "motos_por_1000_adultos", "frota_motos",
                    "vendas_motos", "etanol_hidratado_bi_l", "etanol_anidro_bi_l", "etanol_motos_bi_l"])
        for (lim, pn), r in res.items():
            for i, a in enumerate(ANOS):
                w.writerow([a, lim, pn, round(r["mot"][i], 1), round(r["frota"][i]), round(r["vendas"][i]) if i else "",
                            round(r["hid"][i], 3), round(r["anid"][i], 3), round(r["hid"][i] + r["anid"][i], 3)])
    # leves (indice do projecao_2050) com a base sem as motos + motos
    proj = list(csv.DictReader(open("resultados/projecao_2050.csv"), delimiter=";"))
    out = []
    for r in proj:
        a = int(r["ano"]); i = a - 2025
        leves = float(r["indice_etanol_2025_1"]) * (HID_L + GASC_L * pl.teor(a)) / 1e9
        m = res[(r["motorizacao_limite"], r["cenario_pib"])]
        motos = m["hid"][i] + m["anid"][i]
        out.append([a, r["motorizacao_limite"], r["cenario_pib"], r["trajetoria_eletrificacao"],
                    round(leves, 2), round(motos, 2), round(leves + motos, 2)])
    with open("resultados/etanol_leves_motos_2050.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["ano", "motorizacao_limite", "cenario_pib", "trajetoria_eletrificacao",
                    "etanol_leves_bi_l", "etanol_motos_bi_l", "etanol_total_bi_l"])
        w.writerows(out)
    print("\nETANOL TOTAL LEVES + MOTOS (bi L), faixa entre cenarios de frota e PIB")
    for t in ("rapida", "central", "lenta"):
        row = []
        for a in (2030, 2035, 2040, 2050):
            v = [o[6] for o in out if o[0] == a and o[3] == t]
            mm = [o[5] for o in out if o[0] == a and o[3] == t]
            row.append(f"{a}: {min(v):.1f}-{max(v):.1f} (motos {min(mm):.1f}-{max(mm):.1f})")
        print(f"  {t:<7} " + " | ".join(row))
