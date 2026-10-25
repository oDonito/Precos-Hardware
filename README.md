# Precos-Hardware

Coletor diário de preços do radar de hardware para Fast Shop, Magalu, Mercado Livre, LG, KaBuM! e Amazon.

## Configuração no GitHub

1. Em **Settings → Secrets and variables → Actions**, crie o secret `SERPER_API_KEY` com sua chave do Serper. O valor da chave deve ficar somente no secret; não o grave no repositório nem o envie em mensagens.
2. Opcionalmente, configure `ARTIFACT_INGEST_URL` e `ARTIFACT_INGEST_TOKEN` para enviar as observações a um endpoint de ingestão autorizado. A chave Serper é privada e deve ser criada somente no secret `SERPER_API_KEY`.
3. Em **Actions**, execute **Coletar preços do radar → Run workflow** para testar.
4. Depois, o workflow executa diariamente às 08:00 no horário de Brasília (cron: 11:00 UTC).

Sem `ARTIFACT_INGEST_URL`, os resultados ficam disponíveis como `observations.jsonl` no artefato do próprio workflow. O endpoint de ingestão é necessário para sincronizar o histórico no dashboard hospedado.

## Limitações

- O Serper retorna resultados de pesquisa do Google Shopping; o coletor faz uma consulta consolidada por componente e classifica os resultados por loja e domínio. Preço, estoque, vendedor e frete podem variar.
- O frete só é somado quando a resposta informa frete grátis ou um valor identificável. Caso contrário, `total` fica nulo.
- A pesquisa não inventa valores quando uma loja não é encontrada.
- O cálculo exato do frete para o CEP 71592-074 depende da loja, do vendedor e, em alguns casos, de uma etapa autenticada de checkout.

## Estrutura

- `collector.py`: pesquisa, parsing, seleção da loja e geração das observações.
- `tests/test_collector.py`: testes unitários.
- `.github/workflows/collect-prices.yml`: agendamento diário e execução manual.
