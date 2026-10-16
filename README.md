# Prognóstico de frota e vendas de veículos no Brasil, 2025–2050

Código, dados e resultados do prognóstico de frota e vendas de automóveis, comerciais leves e motocicletas no
Brasil até 2050, com a eletrificação das vendas e da frota de leves em três trajetórias.

## Como rodar

Requer Python 3.10 ou superior.

```bash
pip install -r requirements.txt
./rodar_tudo.sh
```

Os scripts devem ser executados a partir da pasta raiz do repositório (o `rodar_tudo.sh` já faz isso), porque leem
`dados/` e gravam em `resultados/` por caminho relativo. A execução completa leva poucos segundos e reproduz
exatamente os arquivos de `resultados/`.

## Procedimento

O modelo é dirigido pelo estoque: primeiro se projeta quantos veículos haverá em circulação; as vendas são o que
falta para chegar a essa frota depois do sucateamento.

### 1. Frota = população adulta × taxa de motorização

- **População:** habitantes com 18 anos ou mais, projeção do IBGE (2024).
- **Taxa de motorização:** veículos por mil adultos, em função do PIB per capita real, entre dois limites:
  - **Limite superior (leves):** curva de Gompertz com ajuste parcial (Dargay, Gately e Sommer, 2007), calibrada
    em 2000–2025: saturação M = 500, α = 12,9, β = 2,42, ajuste anual θ = 0,17 (elasticidade-renda ≈ 1,4).
    Reancorada para que 2025 seja ponto de equilíbrio.
  - **Limite inferior (leves):** elasticidade-renda observada em 2015–2025 (0,08).
  - **Motocicletas:** elasticidades de 2015–2025 (0,11, inferior) e de 2021–2025 (0,89, superior).
- **Renda:** PIB per capita real cresce 1,0%, 1,5% ou 2,0% ao ano a partir de 2026.
- **Estimativa central:** PIB per capita +1,5% a.a. e média dos dois limites; as vendas são recalculadas a partir
  da frota central.

### 2. Sucateamento

Curva de sobrevivência por idade S(a) = exp(−h·a − (a/λ)^k), calibrada nas vendas da Anfavea desde 1957 e na
estrutura etária da frota do Sindipeças:

| Segmento | h | λ | k | Vida média |
|---|---|---|---|---|
| Automóveis | 0,0149 | 23,4 | 16,9 | ~19 anos |
| Comerciais leves | 0,0117 | 19,1 | 7,6 | ~16 anos |
| Motocicletas | — | — | — | ~10,4 anos |

### 3. Vendas

Vendas do ano = (frota-alvo − sobreviventes das safras anteriores) / S(0). Vendas futuras divididas entre
automóveis e comerciais leves na proporção de 2025 (78,3% / 21,7%); diesel mantido em 9,9% das vendas de leves.

### 4. Eletrificação (leves)

Participação dos elétricos a bateria (BEV) nas vendas não diesel segue uma logística ancorada no observado em
julho de 2026 (ABVE), em três trajetórias:

| Trajetória | Duração de 20% a 80% da assíntota | Assíntota |
|---|---|---|
| Rápida | 3 anos | 90% |
| Central | 7 anos | 85% |
| Lenta | 12 anos | 75% |

Híbridos ocupam uma fração das vendas não BEV: 12,6% em julho de 2026, subindo logisticamente até 50%
(7 anos de 20% a 80% do teto); 68% deles são plugáveis (PHEV) e 32% híbridos-flex (HEV). Híbridos leves (MHEV)
são contados como flex. Veículos vendidos até 2025 entram na frota como flex ou diesel.

## Scripts e resultados

| Script | O que faz | Resultado |
|---|---|---|
| `calibrar_por_safra.py` | Curvas de sucateamento de automóveis e comerciais leves | `calibracao_por_safra.json` |
| `motorizacao.py` | Motorização de leves e renda, 2000–2025; ajuste da Gompertz | — (`historico_2000_2025.csv` é derivado dos dados) |
| `projecao_2050.py` | Frota e vendas de leves: 2 limites × 3 cenários de PIB × 3 trajetórias | `projecao_2050.csv` |
| `motos_calibrar.py`, `motos_projecao.py` | Motocicletas: calibração e projeção | `motos_2050.csv` |
| `cenario_central.py` | Estimativa central de frota e vendas (leves e motos) | `cenario_central.csv` |
| `frota_segmentos.py` | Frota por segmento, 2010–2050 | `frota_segmentos_2010_2050.csv` |
| `eletrificacao_series.py` | Mix de vendas por motorização e BEV + PHEV nas vendas | `eletrificacao_mix_vendas.csv`, `eletrificacao_frota_bev.csv` |
| `frota_motorizacao.py` | Frota de leves por motorização (BEV, PHEV, HEV, flex, diesel) | `frota_motorizacao_2025_2050.csv` |
| `teste_2026.py` | Compara a projeção de 2026 com a da Anfavea | (saída no terminal) |
| `rodar_v3_recalibrado.py`, `rodar_v3_sem_diesel.py`, `modelo_frota_etanol_v3.py` | Bibliotecas: sobrevivência por segmento, separação do diesel, trajetórias de eletrificação | — |

O modelo vem de um trabalho sobre demanda de etanol ([etanol-frota-2050](https://github.com/franklinweise/etanol-frota-2050));
por isso alguns arquivos de resultado trazem também colunas de consumo de etanol, que não fazem parte deste prognóstico.

## Dados

| Arquivo | Conteúdo | Fonte |
|---|---|---|
| `anfavea_autos_cl_1957_2025.csv` | Emplacamentos anuais de automóveis e comerciais leves | Anfavea |
| `anfavea_leves_combustivel.csv` | Emplacamentos de leves por combustível, 2017–2025 | Anfavea |
| `frota_sindipecas_2010_2025.csv` | Frota circulante e idade média por segmento | Abipeças/Sindipeças, Relatório da Frota Circulante |
| `motos_vendas_abraciclo.csv` | Vendas anuais de motocicletas desde 1975 | Abraciclo |
| `pop18_ibge_2024.csv` | População com 18 anos ou mais, 2000–2070 | IBGE, Projeções da População (2024) |
| `pib_per_capita_ibge.csv` | Variação real anual do PIB per capita, 2000–2025 | IBGE |

## Licença

Código sob licença MIT (ver `LICENSE`). Resultados e dados derivados sob CC BY 4.0. As séries originais pertencem às
respectivas fontes, citadas acima.
