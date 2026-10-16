#!/usr/bin/env bash
# Reproduz o prognostico de frota e vendas a partir da pasta raiz do repositorio.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p resultados
python3 modelo/calibrar_por_safra.py      # curvas de sucateamento de automoveis e comerciais leves
python3 modelo/motorizacao.py             # motorizacao de leves e renda, 2000-2025 (Gompertz)
python3 modelo/projecao_2050.py           # frota e vendas de leves: 2 limites x 3 cenarios de PIB x 3 trajetorias
python3 modelo/motos_projecao.py          # motocicletas
python3 modelo/cenario_central.py         # estimativa central: PIB per capita 1,5% a.a., media dos limites
python3 modelo/frota_segmentos.py         # frota por segmento 2010-2050
python3 modelo/eletrificacao_series.py    # mix de vendas por motorizacao e BEV na frota
python3 modelo/frota_motorizacao.py       # frota por motorizacao (BEV, PHEV, HEV, flex, diesel)
python3 modelo/teste_2026.py              # teste com a projecao da Anfavea para 2026
echo "Concluido. Resultados em resultados/."
