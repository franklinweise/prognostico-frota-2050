"""
MODELO DE FROTA POR SAFRA v3.0 - Demanda brasileira de etanol sob eletrificacao
Artigo "Do excedente a fundicao de moleculas" | FATEC Pompeia

Reproduz, a partir de um unico script, todos os numeros do artigo que dependem
do modelo: Tabelas 2, 3 e 4, Figuras 1, 2 e 3 e os valores citados no texto
(Resumo, secoes 2.2, 2.3, 3.1 e 4).

Execucao:  python modelo_frota_etanol_v3.py
Saidas:    resultados/*.csv, resultados/resultados_v3.json, figuras/fig_0*.png

MUDANCAS EM RELACAO A v2.0 (8_white_paper_v2.0/modelo_demanda_etanol_v2.py)
  1. Trajetorias de emplacamento BEV passam a ser as descritas na secao 2.2 do
     artigo (logisticas com duracao e assintota declaradas), ancoradas
     explicitamente no valor observado de julho de 2026 (9,7%). O ano de
     inflexao deixa de ser parametro: e consequencia da ancoragem.
  2. Hibridos plugaveis (PHEV) e hibridos (HEV/HEV flex) modelados
     explicitamente em todas as trajetorias, ancorados na composicao observada
     de julho de 2026 (ABVE).
  3. Frota: a trajetoria e uma funcao declarada e substituivel (bloco FROTA),
     com fonte para o ano-base (Sindipecas 2026). As vendas sao calibradas ano a
     ano para que o estoque reproduza EXATAMENTE a frota-alvo (na v2 a frota
     so era atingida em regime estacionario).
  4. Sucateamento: Weibull k = 3,5, lambda = 18,9 (vida media 17,0 anos, como
     declarado no texto). A v2 usava lambda = 17, k = 2,2 (vida media 15,1 anos).
  5. Balanco de oferta e demanda (Tabelas 3 e 4) calculado no mesmo script,
     com ciclo leve 2025 = 33,0 bi L e E32 = 0,9 bi L, como no texto.
"""
from __future__ import annotations
import csv, json, math, os
import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
DIR_RES = os.path.join(AQUI, "resultados")
DIR_FIG = os.path.join(AQUI, "figuras")

# ================================================================ HORIZONTE
Y0, Y1 = 2025, 2060
YRS = np.arange(Y0, Y1 + 1)
T = len(YRS)
AGES = np.arange(0, 51)
MARCOS = [2030, 2035, 2040, 2045, 2050]

# ==================================================================== FROTA
# Ano-base: Sindipecas, Relatorio da Frota Circulante 2026 (ref. 2025):
#   automoveis 39,5 M + comerciais leves 6,6 M = 46,1 M veiculos leves.
#   Crescimento 2024->2025: automoveis +1,2%, comerciais leves +3,4%
#   (conjunto de leves ~ +1,5% a.a.).
# ATENCAO: comerciais leves incluem picapes a diesel, que nao consomem etanol.
F0 = 46.1e6

def frota_composta(y, g=0.0145):
    """Crescimento composto constante. g = 1,45% a.a. -> 66,0 M em 2050."""
    return F0 * (1 + g) ** (y - Y0)

def frota_logistica(y, fmax=66.0e6, k=0.045):
    """Logistica da v1.5/v2: 66 M e a SATURACAO; em 2050 da 57,8 M."""
    return fmax / (1 + ((fmax - F0) / F0) * math.exp(-k * (y - Y0)))

def frota_constante(y):
    """Frota congelada: isola o efeito da eletrificacao (indice de intensidade)."""
    return F0

FROTAS = {"composta": frota_composta, "logistica": frota_logistica,
          "constante": frota_constante}
FROTA_PADRAO = "composta"          # e a hipotese descrita no texto (46 -> 66 M)

# ============================================================ SUCATEAMENTO
K_WB, LAM_WB = 3.5, 18.9           # vida media = LAM * Gamma(1 + 1/K) = 17,0 anos
SURV = np.exp(-((AGES / LAM_WB) ** K_WB))
VIDA_MEDIA = LAM_WB * math.gamma(1 + 1 / K_WB)

# ============================================================ INTENSIDADES
# etanol por km relativo ao flex convencional
INTENS = {"ICE": 1.00, "HEV": 0.50, "PHEV": 0.30, "BEV": 0.0}

# ======================================================= EMPLACAMENTOS BEV
# Observado (ABVE, 2026; Fenabrave, 2026): participacao BEV no total de leves
OBS_BEV = [(2026 + 3.0 / 12, 0.067, "1o sem. 2026"),
           (2026 + 5.5 / 12, 0.081, "jun/2026"),
           (2026 + 6.5 / 12, 0.097, "jul/2026")]
T_ANCORA, S_ANCORA = OBS_BEV[-1][0], OBS_BEV[-1][1]

# Secao 2.2: duracao do percurso de 20% a 80% da assintota, e assintota.
# A assintota da rapida (90%) nao esta no texto; vem da Figura 1 publicada.
TRAJETORIAS = {
    "rapida":  {"rotulo": "Rápida (limite superior)", "anos": 3,  "assintota": 0.90},
    "central": {"rotulo": "Central",                  "anos": 7,  "assintota": 0.85},
    "lenta":   {"rotulo": "Lenta (limite inferior)",  "anos": 12, "assintota": 0.75},
}

def logistica_ancorada(assintota, anos, t_anc, s_anc):
    """Logistica com k dado pela duracao 20%->80% da assintota e inflexao
    calculada para passar pelo ponto observado (t_anc, s_anc)."""
    k = math.log(16) / anos
    t_mid = t_anc + math.log(assintota / s_anc - 1) / k
    return k, t_mid

def s_bev(t, assintota, k, t_mid):
    return assintota / (1 + np.exp(-k * (np.asarray(t) - t_mid)))

# ================================================================ HIBRIDOS
# ABVE, julho de 2026, leves: total 265.695; BEV 25.782; PHEV 20.500;
# HEV 4.168 + HEV flex 5.624 = 9.792; MHEV 6.216 (tratado como flex, ganho pequeno).
# Entre as vendas nao-BEV (239.913): hibridos = 30.292 -> 12,6%; PHEV = 68% dos hibridos.
H_ANCORA = 30292 / 239913
H_MAX = 0.50                       # teto de hibridizacao das vendas nao-BEV (hipotese)
H_ANOS = 7                         # duracao 20%->80% do teto (hipotese)
FRAC_PHEV = 20500 / 30292          # mantida constante

K_H, TMID_H = logistica_ancorada(H_MAX, H_ANOS, T_ANCORA, H_ANCORA)

def mix_vendas(nome, h_max=H_MAX):
    """Participacao de cada motorizacao nas vendas de cada safra (c + 0,5)."""
    p = TRAJETORIAS[nome]
    k, t_mid = logistica_ancorada(p["assintota"], p["anos"], T_ANCORA, S_ANCORA)
    tc = YRS + 0.5
    bev = s_bev(tc, p["assintota"], k, t_mid)
    kh, tmh = logistica_ancorada(h_max, H_ANOS, T_ANCORA, H_ANCORA)
    hib = (1 - bev) * s_bev(tc, h_max, kh, tmh)
    return {"BEV": bev, "PHEV": hib * FRAC_PHEV, "HEV": hib * (1 - FRAC_PHEV),
            "ICE": 1 - bev - hib}

def contrafactual_tudo_bev(mix):
    """Secao 2.3: toda venda eletrificada seria BEV puro."""
    return {"ICE": mix["ICE"], "HEV": np.zeros(T), "PHEV": np.zeros(T),
            "BEV": mix["BEV"] + mix["HEV"] + mix["PHEV"]}

# ==================================================================== NUCLEO
def calibrar_vendas(frota_fn):
    """Legado (safras <= 2025): vendas constantes em regime estacionario, todo
    flex. A partir de 2026, vendas(t) = frota(t) - sobreviventes das safras
    anteriores, de modo que o estoque reproduz exatamente a frota-alvo."""
    v_leg = F0 / SURV.sum()
    vendas = np.zeros(T)
    vendas[0] = v_leg                                  # safra 2025 (legado)
    for ti in range(1, T):
        sobrev = 0.0
        for a in AGES[1:]:
            c = ti - a
            sobrev += (vendas[c] if c >= 0 else v_leg) * SURV[a]
        vendas[ti] = frota_fn(int(YRS[ti])) - sobrev
    return v_leg, vendas

def rodar(mix, frota="composta"):
    """Indice de demanda de etanol do ciclo leve (2025 = 1,00) e frota por ano."""
    v_leg, vendas = calibrar_vendas(FROTAS[frota])
    inten = sum(mix[m] * INTENS[m] for m in INTENS)
    inten[0] = 1.0                                     # safra 2025 e legado flex
    eth, estoque = np.zeros(T), np.zeros(T)
    for ti in range(T):
        for a in AGES:
            c = ti - a
            if c < 0:
                eth[ti] += v_leg * SURV[a]
                estoque[ti] += v_leg * SURV[a]
            else:
                eth[ti] += vendas[c] * SURV[a] * inten[c]
                estoque[ti] += vendas[c] * SURV[a]
    return eth / eth[0], estoque, vendas

def em(arr, ano):
    return float(arr[int(ano) - Y0])

# ================================================================== BALANCO
LEVE_2025 = 33.0                   # bi L, ciclo leve (anidro + hidratado)
E32 = 0.9                          # bi L/ano (MME, 2026); vigente desde ago/2026
E35_ADIC = 0.45 * 3                # 3 pontos adicionais, 0,45 bi L por ponto
CANA, CANA_MIX60 = 27.3, 22.0      # bi L; mix de 60% para acucar
MILHO_0, MILHO_MAX, MILHO_FREIO, MILHO_ANO = 10.0, 20.0, 15.0, 2032
EXPORT_ADIC = 8.0

def milho(t, teto=MILHO_MAX):
    return MILHO_0 + (teto - MILHO_0) * min(1.0, (t - Y0) / (MILHO_ANO - Y0))

def outros(t):
    return float(np.interp(t, [2025, 2030, 2035, 2040], [3.0, 3.5, 4.0, 4.5]))

def e32(t):
    return 0.0 if t < 2026 else (E32 * 5 / 12 if t == 2026 else E32)

def rampa_mix(t):
    """Na Figura 3 o mix de 60% entra linearmente entre 2027 e 2031."""
    return float(np.clip((t - 2027) / 4, 0, 1))

def ciclo_leve(idx, t, e35=False):
    return LEVE_2025 * em(idx, t) + e32(t) + (E35_ADIC if e35 else 0.0)

def excedente(idx, t, milho_teto=MILHO_MAX, cana=CANA, e35=False, export=0.0):
    oferta = cana + milho(t, milho_teto)
    return oferta - ciclo_leve(idx, t, e35) - outros(t) - export

# ================================================================ FIGURAS
def figuras(res):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    os.makedirs(DIR_FIG, exist_ok=True)
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "axes.grid.axis": "y", "grid.alpha": .35,
        "grid.linewidth": .6, "savefig.dpi": 200, "savefig.bbox": "tight",
    })
    COR = {"rapida": "#c77a00", "central": "#1b5e20", "lenta": "#7b8b2f"}
    EST = {"rapida": "--", "central": "-", "lenta": "--"}

    # Figura 1 - participacao BEV nos emplacamentos
    fig, ax = plt.subplots(figsize=(6.3, 3.6))
    t = np.linspace(2024, 2045, 400)
    for n, p in TRAJETORIAS.items():
        k, tm = logistica_ancorada(p["assintota"], p["anos"], T_ANCORA, S_ANCORA)
        ax.plot(t, 100 * s_bev(t, p["assintota"], k, tm), color=COR[n], lw=2, label=p["rotulo"])
    ax.scatter([o[0] for o in OBS_BEV], [100 * o[1] for o in OBS_BEV], color="#222",
               s=16, zorder=5, label="Observado (ABVE/Fenabrave)")
    ax.set(xlim=(2024, 2045), ylim=(0, 100), ylabel="% dos emplacamentos de leves")
    ax.set_xticks(range(2024, 2046, 3))
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    fig.savefig(os.path.join(DIR_FIG, "fig_01_emplacamentos_bev_v3.png")); plt.close(fig)

    # Figura 2 - indice de demanda
    fig, ax = plt.subplots(figsize=(6.3, 3.6))
    sel = YRS <= 2050
    ax.fill_between(YRS[sel], 100 * res["rapida"]["idx"][sel], 100 * res["lenta"]["idx"][sel],
                    color="#1b5e20", alpha=.12, lw=0, label="Corredor de incerteza")
    for n in ("rapida", "central", "lenta"):
        ax.plot(YRS[sel], 100 * res[n]["idx"][sel], EST[n], color=COR[n], lw=2,
                label=TRAJETORIAS[n]["rotulo"].split(" (")[0])
    ax.set(xlim=(2025, 2050), ylim=(0, 110), ylabel="Índice (2025 = 100)")
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    fig.savefig(os.path.join(DIR_FIG, "fig_02_demanda_indice_v3.png")); plt.close(fig)

    # Figura 3 - balanco
    fig, ax = plt.subplots(figsize=(6.3, 3.8))
    anos = [int(a) for a in YRS if a <= 2050]
    of = [CANA + milho(a) for a in anos]
    of_am = [CANA - (CANA - CANA_MIX60) * rampa_mix(a) + milho(a, MILHO_FREIO) for a in anos]
    dem = {n: [ciclo_leve(res[n]["idx"], a) + outros(a) for a in anos] for n in res}
    ax.plot(anos, of, color="#222", lw=2.5, label="Oferta (cana 27,3 + milho 10→20)")
    ax.plot(anos, of_am, ":", color="#222", lw=1.3,
            label="Oferta com amortecedores (mix 60% açúcar; milho 15)")
    ax.fill_between(anos, dem["lenta"], of, color="#1b5e20", alpha=.15, lw=0,
                    label="Excedente (trajetória lenta)")
    ax.fill_between(anos, dem["rapida"], dem["lenta"], color="#c77a00", alpha=.15, lw=0,
                    label="Excedente adicional (trajetória rápida)")
    for n in ("rapida", "lenta"):
        ax.plot(anos, dem[n], "--", color=COR[n], lw=1.8)
    ax.plot(anos, dem["central"], color=COR["central"], lw=2.2,
            label="Demanda total, trajetória central")
    ax.set(xlim=(2025, 2050), ylim=(0, 52), ylabel="Bilhões de litros por ano")
    ax.legend(frameon=False, fontsize=8, loc="lower left")
    fig.savefig(os.path.join(DIR_FIG, "fig_03_balanco_v3.png")); plt.close(fig)

# =============================================================== RELATORIO
def gravar_csv(nome, cabec, linhas):
    with open(os.path.join(DIR_RES, nome), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(cabec)
        w.writerows(linhas)

if __name__ == "__main__":
    os.makedirs(DIR_RES, exist_ok=True)
    NOMES = ("rapida", "central", "lenta")
    mixes = {n: mix_vendas(n) for n in NOMES}
    res = {}
    for n in NOMES:
        idx, estoque, vendas = rodar(mixes[n], FROTA_PADRAO)
        res[n] = {"idx": idx, "frota": estoque, "vendas": vendas}

    print("=" * 74)
    print("MODELO DE FROTA POR SAFRA v3.0 - demanda de etanol, ciclo leve")
    print(f"Frota '{FROTA_PADRAO}': {F0/1e6:.1f} M (2025) -> "
          f"{em(res['central']['frota'], 2050)/1e6:.1f} M (2050) | "
          f"Weibull k={K_WB} lambda={LAM_WB} (vida media {VIDA_MEDIA:.1f} anos)")
    print("=" * 74)

    print("\nTRAJETORIAS BEV (ancoradas em jul/2026 = 9,7%)")
    for n, p in TRAJETORIAS.items():
        k, tm = logistica_ancorada(p["assintota"], p["anos"], T_ANCORA, S_ANCORA)
        print(f"  {n:<8} assintota {p['assintota']:.0%}  20->80% em {p['anos']:>2} anos"
              f"  k={k:.3f}  inflexao {tm:.1f}")
    print(f"  hibridos: {H_ANCORA:.1%} das vendas nao-BEV em jul/2026 -> teto {H_MAX:.0%}"
          f" (inflexao {TMID_H:.1f}); PHEV = {FRAC_PHEV:.0%} dos hibridos")

    print("\nTABELA 2 - indice de demanda, 2025 = 100")
    print(f"  {'ano':>5}" + "".join(f"{n:>9}" for n in NOMES))
    for a in MARCOS:
        print(f"  {a:>5}" + "".join(f"{100*em(res[n]['idx'], a):>9.0f}" for n in NOMES))

    print("\nSECAO 2.3 - amortecedor dos hibridos (p.p. de indice preservados vs. tudo BEV)")
    amort = {}
    for n in NOMES:
        cf, _, _ = rodar(contrafactual_tudo_bev(mixes[n]), FROTA_PADRAO)
        amort[n] = {a: 100 * (em(res[n]["idx"], a) - em(cf, a)) for a in MARCOS}
        print(f"  {n:<8}" + "".join(f"  {a}: {amort[n][a]:+5.1f}" for a in (2035, 2040, 2050)))

    print("\nTABELA 3 - balanco, bi L/ano")
    t3 = []
    for a in [2025] + MARCOS[:1] + [2035, 2040, 2050]:
        lv = {n: ciclo_leve(res[n]["idx"], a) for n in NOMES}
        exc = sorted(excedente(res[n]["idx"], a) for n in NOMES)
        t3.append([a, CANA + milho(a), *(lv[n] for n in NOMES), outros(a), exc[0], exc[-1]])
        print(f"  {a}  oferta {t3[-1][1]:5.1f}  leve " + " / ".join(f"{lv[n]:4.1f}" for n in NOMES)
              + f"  outros {outros(a):.1f}  excedente {exc[0]:4.1f} - {exc[-1]:4.1f}")

    print("\nTABELA 4 - sensibilidade do excedente central, bi L/ano")
    ic, il = res["central"]["idx"], res["lenta"]["idx"]
    casos = [
        ("Base (milho 20 bi L; E32; mix 50/50)", lambda t: excedente(ic, t)),
        ("Expansão do milho limitada a 15 bi L", lambda t: excedente(ic, t, MILHO_FREIO)),
        ("Mix de 60% para açúcar (cana 22 bi L)", lambda t: excedente(ic, t, cana=CANA_MIX60)),
        ("Mistura a 35% (E35)", lambda t: excedente(ic, t, e35=True)),
        ("Exportação adicional de 8 bi L", lambda t: excedente(ic, t, export=EXPORT_ADIC)),
        ("Os três amortecedores juntos",
         lambda t: excedente(ic, t, MILHO_FREIO, CANA_MIX60, e35=True)),
        ("Trajetória lenta + milho 15 + mix 60%",
         lambda t: excedente(il, t, MILHO_FREIO, CANA_MIX60)),
    ]
    t4 = [[rot, fn(2035), fn(2040)] for rot, fn in casos]
    for rot, v35, v40 in t4:
        print(f"  {rot:<40} {v35:6.1f} {v40:6.1f}")

    print("\nSENSIBILIDADE A FROTA - Tabela 2 (central) e excedente central 2040")
    for fr in FROTAS:
        idx, est, _ = rodar(mixes["central"], fr)
        print(f"  {fr:<10} frota 2050 {em(est, 2050)/1e6:5.1f} M | indice "
              + " ".join(f"{100*em(idx, a):4.0f}" for a in MARCOS)
              + f" | excedente 2040 {excedente(idx, 2040):5.1f}")

    print("\nSENSIBILIDADE AO TETO DE HIBRIDIZACAO - indice central 2040")
    for h in (0.3, 0.5, 0.7):
        idx, _, _ = rodar(mix_vendas("central", h), FROTA_PADRAO)
        print(f"  H_MAX {h:.0%}: {100*em(idx, 2040):.0f}")

    v26 = em(res["central"]["vendas"], 2026)
    print(f"\nDIAGNOSTICO: vendas implicitas 2026 = {v26/1e6:.2f} M "
          f"(jul/2026 anualizado: {265695*12/1e6:.2f} M); "
          f"sucateamento implicito 2026 = {(v26 - (em(res['central']['frota'], 2026) - F0))/1e6:.2f} M")

    # ---------------------------------------------------------------- saidas
    gravar_csv("tabela2_indice_v3.csv", ["ano", *NOMES],
               [[a, *(round(100 * em(res[n]["idx"], a), 1) for n in NOMES)] for a in MARCOS])
    gravar_csv("tabela3_balanco_v3.csv",
               ["ano", "oferta", "leve_rapida", "leve_central", "leve_lenta", "outros",
                "excedente_min", "excedente_max"], [[round(x, 2) for x in r] for r in t3])
    gravar_csv("tabela4_sensibilidade_v3.csv", ["hipotese", "2035", "2040"],
               [[r[0], round(r[1], 2), round(r[2], 2)] for r in t4])
    gravar_csv("frota_e_vendas_v3.csv",
               ["ano", "frota_M", "vendas_M", *(f"bev_{n}" for n in NOMES),
                *(f"phev_{n}" for n in NOMES), *(f"hev_{n}" for n in NOMES)],
               [[int(a), round(res["central"]["frota"][i] / 1e6, 2),
                 round(res["central"]["vendas"][i] / 1e6, 3),
                 *(round(mixes[n]["BEV"][i], 4) for n in NOMES),
                 *(round(mixes[n]["PHEV"][i], 4) for n in NOMES),
                 *(round(mixes[n]["HEV"][i], 4) for n in NOMES)]
                for i, a in enumerate(YRS) if a <= 2050])
    with open(os.path.join(DIR_RES, "resultados_v3.json"), "w", encoding="utf-8") as f:
        json.dump({
            "versao": "3.0",
            "frota": {"hipotese": FROTA_PADRAO, "2025_M": F0 / 1e6,
                      "2050_M": round(em(res["central"]["frota"], 2050) / 1e6, 2)},
            "weibull": {"k": K_WB, "lambda": LAM_WB, "vida_media": round(VIDA_MEDIA, 2)},
            "intensidades": INTENS,
            "tabela2": {n: {a: round(100 * em(res[n]["idx"], a), 1) for a in MARCOS} for n in NOMES},
            "amortecedor_hibridos_pp": {n: {a: round(v, 1) for a, v in amort[n].items()} for n in NOMES},
            "tabela4": {r[0]: {"2035": round(r[1], 1), "2040": round(r[2], 1)} for r in t4},
        }, f, ensure_ascii=False, indent=2)

    figuras(res)
    print(f"\nResultados em {DIR_RES}\nFiguras em {DIR_FIG}")
