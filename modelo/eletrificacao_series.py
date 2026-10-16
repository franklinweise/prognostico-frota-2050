"""
Series de eletrificacao de leves (automoveis + comerciais leves) nas tres trajetorias:
mix de vendas por motorizacao (participacao no total, com diesel fora da eletrificacao)
e participacao dos BEV na frota (estimativa central: PIBpc 1,5%, media dos limites).
Saidas: resultados/eletrificacao_mix_vendas.csv e resultados/eletrificacao_frota_bev.csv
"""
import csv
import numpy as np
import modelo_frota_etanol_v3 as m
import rodar_v3_sem_diesel as r

TRAJ = ("rapida", "central", "lenta")
ND = 1 - r.D_FUT

with open("resultados/eletrificacao_mix_vendas.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["ano", "trajetoria", "bev_pct", "phev_pct", "hev_flex_pct", "flex_pct", "diesel_pct", "recarregaveis_bev_phev_pct"])
    for t in TRAJ:
        x = r.mix_nd(t)
        for i, a in enumerate(m.YRS):
            if 2026 <= a <= 2050:
                w.writerow([a, t] + [round(100 * x[k][i] * ND, 1) for k in ("BEV", "PHEV", "HEV", "ICE")]
                           + [round(100 * r.D_FUT, 1), round(100 * (x["BEV"][i] + x["PHEV"][i]) * ND, 1)])

fl = {}
for row in csv.DictReader(open("resultados/projecao_2050.csv", encoding="utf-8"), delimiter=";"):
    if row["cenario_pib"] == "PIBpc 1,5%":
        fl.setdefault((int(row["ano"]), row["trajetoria_eletrificacao"]), []).append(
            (float(row["frota_bev_vendidos_desde_2026"]), float(row["frota_leves"])))
with open("resultados/eletrificacao_frota_bev.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["ano", "trajetoria", "frota_bev", "frota_leves", "bev_pct_frota"])
    for t in TRAJ:
        for a in range(2025, 2051):
            b = np.mean([p[0] for p in fl[(a, t)]]); tot = np.mean([p[1] for p in fl[(a, t)]])
            w.writerow([a, t, round(b), round(tot), round(100 * b / tot, 1)])

if __name__ == "__main__":
    print("gravado: resultados/eletrificacao_mix_vendas.csv, resultados/eletrificacao_frota_bev.csv")
