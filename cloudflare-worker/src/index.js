const json = (data, status = 200) => new Response(JSON.stringify(data), {
  status,
  headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
});

const allowedStores = new Set(["fastshop", "magalu", "mercadolivre", "lg", "kabum", "amazon"]);

function normalizeRecord(record) {
  if (!record || typeof record !== "object") throw new Error("record must be an object");
  const required = ["id", "itemId", "itemName", "store", "collectedAt"];
  for (const field of required) if (!record[field]) throw new Error(`missing field: ${field}`);
  if (!allowedStores.has(record.store)) throw new Error(`unsupported store: ${record.store}`);
  if (typeof record.id !== "string" || record.id.length > 128 || record.id.includes("#")) throw new Error("invalid id");
  return {
    id: record.id,
    itemId: String(record.itemId),
    itemName: String(record.itemName),
    store: record.store,
    price: record.price == null ? null : Number(record.price),
    shipping: record.shipping == null ? null : Number(record.shipping),
    total: record.total == null ? null : Number(record.total),
    collectedAt: String(record.collectedAt),
    url: record.url == null ? null : String(record.url),
    seller: record.seller == null ? null : String(record.seller),
    availability: record.availability == null ? null : String(record.availability),
    confidence: record.confidence == null ? null : String(record.confidence),
    notes: record.notes == null ? null : String(record.notes),
  };
}

async function ingest(request, env) {
  const auth = request.headers.get("authorization") || "";
  if (!env.INGEST_TOKEN || auth !== `Bearer ${env.INGEST_TOKEN}`) return json({ error: "unauthorized" }, 401);
  const body = await request.json();
  if (body.collection !== "observations" || !Array.isArray(body.records) || body.records.length > 200) {
    return json({ error: "expected collection=observations and up to 200 records" }, 400);
  }
  const records = body.records.map(normalizeRecord);
  const statements = records.map((r) => env.DB.prepare(`
    INSERT OR IGNORE INTO observations
      (id, item_id, item_name, store, price, shipping, total, collected_at, url, seller, availability, confidence, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).bind(r.id, r.itemId, r.itemName, r.store, r.price, r.shipping, r.total, r.collectedAt, r.url, r.seller, r.availability, r.confidence, r.notes));
  if (statements.length) await env.DB.batch(statements);
  return json({ accepted: records.length, collection: "observations" });
}

async function api(request, env, url) {
  if (request.method === "GET" && url.pathname === "/api/items") {
    const result = await env.DB.prepare("SELECT id, name, category, target, shipping_cep AS shippingCep FROM items ORDER BY name").all();
    return json({ items: result.results });
  }
  if (request.method === "GET" && url.pathname === "/api/observations") {
    const result = await env.DB.prepare("SELECT * FROM observations ORDER BY collected_at DESC LIMIT 5000").all();
    return json({ observations: result.results });
  }
  if (request.method === "POST" && url.pathname === "/api/observations") return ingest(request, env);
  return json({ error: "not found" }, 404);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname.startsWith("/api/")) {
      try { return await api(request, env, url); }
      catch (error) { return json({ error: error.message || "internal error" }, 400); }
    }
    return env.ASSETS.fetch(request);
  },
};
