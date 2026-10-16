"""
Estimativa central de frota e vendas: PIB per capita de 1,5% a.a. e motorizacao
igual a media dos limites inferior e superior (leves e motos).
As vendas sao recalculadas a partir da frota central (nao sao a media das vendas).
Saida: resultados/cenario_central.csv
"""
import csv
import numpy as np
import projecao_2050 as pl
import motos_projecao as mp

G = pl.PIB["PIBpc 1,5%"]
ANOS = pl.ANOS
POP = np.array([pl.POP[a] for a in ANOS])

# leves
mot_l = (pl.motorizacao(G, "inferior") + pl.motorizacao(G, "superior")) / 2
frota_l = mot_l / 1000 * POP
vendas_l = pl.projetar(frota_l, "central")["vendas"]

# motos: mesma rotina de motos_projecao, com a frota central
inf, sup = mp.projetar("inferior", G), mp.projetar("superior", G)
mot_m = (inf["mot"] + sup["mot"]) / 2
frota_m = (inf["frota"] + sup["frota"]) / 2
S, T = mp.S, mp.T
leg = np.array([sum(v * S[2025 + t - c + 1] for c, v in mp.mc.VENDAS.items() if 2025 + t - c + 1 < len(S))
                for t in range(T)])
leg *= mp.F25 / leg[0]
vendas_m = np.zeros(T)
for ti in range(1, T):
    sob = leg[ti] + sum(vendas_m[c] * S[ti - c + 1] for c in range(1, ti))
    vendas_m[ti] = (frota_m[ti] - sob) / S[1]

if __name__ == "__main__":
    with open("resultados/cenario_central.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["ano", "leves_por_1000_adultos", "frota_leves", "vendas_leves",
                    "motos_por_1000_adultos", "frota_motos", "vendas_motos"])
        for i, a in enumerate(ANOS):
            w.writerow([int(a), round(mot_l[i], 1), round(frota_l[i]), round(vendas_l[i]) if i else "",
                        round(mot_m[i], 1), round(frota_m[i]), round(vendas_m[i]) if i else ""])
    print("ano | leves: mot frota vendas | motos: mot frota vendas | total frota")
    for a in (2025, 2026, 2030, 2033, 2034, 2035, 2040, 2045, 2050):
        i = a - 2025
        print(f"{a} | {mot_l[i]:5.0f} {frota_l[i]/1e6:5.1f} {vendas_l[i]/1e6:5.2f} | "
              f"{mot_m[i]:4.0f} {frota_m[i]/1e6:5.1f} {vendas_m[i]/1e6:5.2f} | {(frota_l[i]+frota_m[i])/1e6:5.1f}")
