"""Daily price collector for the PC-parts radar.

The collector queries SerpAPI's Google Shopping endpoint and emits observations
as JSONL. It deliberately does not invent prices, shipping, availability or URLs.
A persistence endpoint can be configured with ARTIFACT_INGEST_URL; the workflow
sends the JSON payload there when the variable is present.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

STORES = {
    "fastshop": ["fastshop.com.br"],
    "magalu": ["magazineluiza.com.br", "magalu.com"],
    "mercadolivre": ["mercadolivre.com.br", "mercadolivre"],
    "lg": ["lg.com", "lg.com/br"],
    "kabum": ["kabum.com.br"],
    "amazon": ["amazon.com.br"],
}

CATALOG = [
    {"id": "monitor-lg-34g600a", "name": "Monitor Gamer LG UltraGear Curvo 34G600A-B 34\" QuadHD 2K UltraWide 1800R, 160Hz", "target": 1450.0},
    {"id": "suporte-monitor-35", "name": "Suporte de mesa articulado para até 35\"", "target": 190.0},
    {"id": "ryzen-5-7600x", "name": "Ryzen 5 7600X, 6-Core, 12-Threads, 4.7GHz (5.3GHz Turbo)", "target": 1000.0},
    {"id": "radeon-rx-9070xt", "name": "AMD Radeon RX 9070 XT 16GB VRAM", "target": 4500.0},
    {"id": "gigabyte-b650m-gaming-wifi", "name": "Placa-Mãe Gigabyte B650M Gaming WIFI, B650, AMD AM5, M-ATX, DDR5", "target": 609.99},
    {"id": "memoria-ddr5-16gb-5600", "name": "Memória RAM 16GB DDR5 5600MHz", "target": 1200.0},
    {"id": "ssd-nvme-1tb-6000", "name": "SSD 1TB NVMe M.2, leitura 6000 MB/s", "target": 800.0},
    {"id": "fonte-850w-bronze", "name": "Fonte 850W 80 Plus Bronze MSI MAG / Corsair", "target": 325.0},
    {"id": "aircooler-ak400-ag400", "name": "Air Cooler DeepCool AK400 / AG400", "target": 190.0},
    {"id": "gabinete-mid-tower-mesh", "name": "Gabinete Gamer Mid Tower, frente Mesh, 3x Fans ARGB", "target": 140.0},
]


def parse_brl(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace("R$", "").replace(" ", "")
    match = re.search(r"[-+]?\d[\d.]*,\d{2}|[-+]?\d+(?:\.\d+)?", text)
    if not match:
        return None
    number = match.group(0)
    if "," in number:
        number = number.replace(".", "").replace(",", ".")
    try:
        return float(number)
    except ValueError:
        return None


def parse_shipping(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).lower()
    if "grátis" in text or "gratis" in text or "free" in text:
        return 0.0
    return parse_brl(value)


def _host_matches(link: str, domains: list[str]) -> bool:
    link_lower = (link or "").lower()
    return any(domain in link_lower for domain in domains)


def select_store_result(results: list[dict[str, Any]], store: str) -> dict[str, Any] | None:
    """Select the first result whose link or source matches the requested store."""
    domains = STORES.get(store, [store])
    for result in results:
        source = str(result.get("source", ""))
        link = str(result.get("link", ""))
        if _host_matches(link, domains) or any(domain.split(".")[0] in source.lower() for domain in domains):
            return result
    return None


def build_observation(
    *, item_id: str, item_name: str, store: str, result: dict[str, Any], collected_at: datetime
) -> dict[str, Any]:
    price = parse_brl(result.get("price"))
    shipping = parse_shipping(result.get("delivery") or result.get("shipping"))
    total = price + shipping if price is not None and shipping is not None else None
    day = collected_at.astimezone(timezone.utc).date().isoformat()
    return {
        "id": f"{day}_{item_id}_{store}",
        "itemId": item_id,
        "itemName": item_name,
        "store": store,
        "price": price,
        "shipping": shipping,
        "total": total,
        "collectedAt": collected_at.astimezone(timezone.utc).isoformat(),
        "url": result.get("link"),
        "seller": result.get("source"),
        "availability": "available" if price is not None else "unavailable",
        "confidence": "serpapi_google_shopping",
        "notes": "Frete confirmado pela descrição retornada pela SerpAPI." if shipping is not None else "Frete não confirmado; total não calculado.",
    }


def serpapi_search(api_key: str, query: str, location: str = "Brasília, Federal District, Brazil") -> list[dict[str, Any]]:
    params = urlencode({"engine": "google_shopping", "q": query, "location": location, "hl": "pt-br", "gl": "br", "api_key": api_key})
    request = Request(f"https://serpapi.com/search.json?{params}", headers={"User-Agent": "radar-precos-github/1.0"})
    with urlopen(request, timeout=45) as response:
        payload = json.load(response)
    return payload.get("shopping_results", [])


def post_observations(url: str, token: str | None, observations: list[dict[str, Any]]) -> None:
    body = json.dumps({"collection": "observations", "records": observations}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, data=body, headers=headers, method="POST")
    with urlopen(request, timeout=45) as response:
        if response.status >= 300:
            raise RuntimeError(f"ingest endpoint returned HTTP {response.status}")


def collect(api_key: str, collected_at: datetime) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    for item in CATALOG:
        for store in STORES:
            query = f"{item['name']} site:{STORES[store][0]}"
            try:
                results = serpapi_search(api_key, query)
                selected = select_store_result(results, store)
                if selected:
                    observations.append(build_observation(item_id=item["id"], item_name=item["name"], store=store, result=selected, collected_at=collected_at))
                else:
                    print(f"unavailable: {item['id']} / {store}", file=sys.stderr)
            except Exception as exc:
                print(f"error: {item['id']} / {store}: {exc}", file=sys.stderr)
    return observations


def main() -> int:
    api_key = os.environ.get("SERPAPI_API_KEY")
    if not api_key:
        print("SERPAPI_API_KEY is required", file=sys.stderr)
        return 2
    collected_at = datetime.now(timezone.utc)
    observations = collect(api_key, collected_at)
    output = Path(os.environ.get("OUTPUT_JSONL", "observations.jsonl"))
    serialized = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in observations)
    output.write_text(serialized, encoding="utf-8")
    snapshot = Path(os.environ.get("SNAPSHOT_JSON", "data/observations.json"))
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_text(json.dumps({"generatedAt": collected_at.astimezone(timezone.utc).isoformat(), "observations": observations}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ingest_url = os.environ.get("ARTIFACT_INGEST_URL")
    if ingest_url and observations:
        post_observations(ingest_url, os.environ.get("ARTIFACT_INGEST_TOKEN"), observations)
    print(json.dumps({"created": len(observations), "output": str(output), "ingested": bool(ingest_url and observations)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
