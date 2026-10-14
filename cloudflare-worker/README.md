# Worker + D1 do Precos-Hardware

Este pacote hospeda o dashboard e recebe as observações do GitHub Actions. O banco D1 guarda o catálogo e o histórico.

## Configuração única na Cloudflare

Na pasta `cloudflare-worker`, execute em um terminal com Wrangler autenticado:

```powershell
npx wrangler d1 create precos-hardware
```

Copie o `database_id` retornado para `wrangler.toml`, substituindo `REPLACE_AFTER_D1_CREATE`.

Aplique o schema:

```powershell
npx wrangler d1 execute precos-hardware --remote --file=schema.sql
```

Crie o token de ingestão sem colocá-lo no código:

```powershell
npx wrangler secret put INGEST_TOKEN
```

Depois publique:

```powershell
npx wrangler deploy
```

O dashboard ficará na URL exibida pelo Wrangler, normalmente `https://precos-hardware.<subdominio>.workers.dev`.

## Secrets no GitHub

No repositório, em **Settings → Secrets and variables → Actions**, cadastre:

- `CLOUDFLARE_API_TOKEN`: token com Workers Scripts Edit e D1 Edit.
- `CLOUDFLARE_ACCOUNT_ID`: identificador da conta Cloudflare.
- `CLOUDFLARE_D1_DATABASE_ID`: o `database_id` criado acima.
- `CLOUDFLARE_WORKER_URL`: URL pública do Worker, sem `/api/observations`.
- `CLOUDFLARE_INGEST_TOKEN`: exatamente o mesmo valor usado em `wrangler secret put INGEST_TOKEN`.
- `SERPAPI_API_KEY`: chave da SerpAPI.

O token de ingestão deve ser longo e aleatório. Nunca o commite no repositório.

## Endpoints

- `GET /api/items`: catálogo.
- `GET /api/observations`: histórico.
- `POST /api/observations`: recebe `{ "collection": "observations", "records": [...] }` com `Authorization: Bearer <token>`.
