import io
import json
import unittest
from datetime import datetime, timezone
from urllib.error import HTTPError
from unittest.mock import patch

from collector import (
    CATALOG,
    SerperAuthError,
    SerperQuotaError,
    build_observation,
    build_search_query,
    merge_observations,
    collect,
    select_store_results,
    parse_brl,
    parse_shipping,
    select_store_result,
    serper_search,
)


class CollectorTests(unittest.TestCase):
    def test_parse_brl_handles_brazilian_price(self):
        self.assertEqual(parse_brl("R$ 4.599,90"), 4599.90)
        self.assertEqual(parse_brl("1.200,00"), 1200.00)

    def test_parse_shipping_handles_free_and_paid_shipping(self):
        self.assertEqual(parse_shipping("Frete grátis"), 0.0)
        self.assertEqual(parse_shipping("Entrega por R$ 24,90"), 24.90)
        self.assertIsNone(parse_shipping("Consulte o frete"))

    def test_select_store_results_matches_display_names_with_punctuation(self):
        results = [{"source": "Fast Shop", "price": "R$ 10,00", "link": ""}]
        self.assertIn("fastshop", select_store_results(results))

    def test_select_store_result_requires_matching_store(self):
        results = [
            {"source": "Outra loja", "price": "R$ 10,00", "link": "https://outra.example/p"},
            {"source": "KaBuM!", "price": "R$ 20,00", "link": "https://www.kabum.com.br/p"},
        ]
        chosen = select_store_result(results, "kabum")
        self.assertEqual(chosen["source"], "KaBuM!")

    def test_search_query_uses_exact_monitor_term_without_store_repetition(self):
        monitor = CATALOG[0]
        self.assertEqual(monitor["search"], "Monitor Gamer LG UltraGear Curvo 34G600A-B")
        query = build_search_query(monitor)
        self.assertEqual(query, "Monitor Gamer LG UltraGear Curvo 34G600A-B preço")
        self.assertNotIn("site:", query)

    def test_select_store_results_classifies_one_shopping_response(self):
        results = [
            {"source": "Amazon.com.br", "price": "R$ 10,00", "link": "https://amazon.com.br/p"},
            {"source": "KaBuM!", "price": "R$ 20,00", "link": "https://kabum.com.br/p"},
        ]
        selected = select_store_results(results)
        self.assertEqual(set(selected), {"amazon", "kabum"})

    def test_serper_search_posts_to_shopping_with_api_key_header(self):
        from collector import serper_search
        payload = {"shopping": [{"title": "SSD 1TB", "source": "Amazon.com.br", "price": "R$ 799,90", "link": "https://amazon.com.br/p"}]}
        response = io.BytesIO(json.dumps(payload).encode("utf-8"))
        with patch("collector.urlopen", return_value=response) as mocked:
            results = serper_search("test-key-not-real", "SSD 1TB preço")
        request = mocked.call_args.args[0]
        self.assertEqual(request.full_url, "https://google.serper.dev/shopping")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("X-api-key"), "test-key-not-real")
        self.assertEqual(json.loads(request.data)["q"], "SSD 1TB preço")
        self.assertEqual(results[0]["source"], "Amazon.com.br")

    def test_serper_401_maps_to_auth_error(self):
        from collector import serper_search
        error = HTTPError("https://google.serper.dev/shopping", 401, "Unauthorized", {}, io.BytesIO())
        with patch("collector.urlopen", side_effect=error):
            with self.assertRaises(SerperAuthError):
                serper_search("bad-key", "SSD 1TB")

    def test_serper_429_maps_to_quota_error(self):
        from collector import SerperQuotaError, serper_search
        error = HTTPError("https://google.serper.dev/shopping", 429, "Too Many Requests", {}, io.BytesIO())
        with patch("collector.urlopen", side_effect=error):
            with self.assertRaises(SerperQuotaError):
                serper_search("test-key-not-real", "SSD 1TB")

    def test_parse_serper_shopping_response_fields(self):
        from collector import normalize_serper_shopping_response
        payload = {"shopping": [{"title": "SSD 1TB", "source": "Amazon.com.br", "price": "R$ 799,90", "link": "https://amazon.com.br/p", "delivery": "Frete grátis"}]}
        self.assertEqual(normalize_serper_shopping_response(payload)[0]["price"], "R$ 799,90")

    def test_collect_queries_once_per_item(self):
        result = {"source": "Amazon.com.br", "price": "R$ 10,00", "link": "https://amazon.com.br/p"}
        with patch("collector.serper_search", return_value=[result]) as search:
            observations = collect("key", datetime(2026, 10, 16, tzinfo=timezone.utc))
        self.assertEqual(search.call_count, len(CATALOG))
        self.assertEqual(len(observations), len(CATALOG))

    def test_serper_invalid_key_is_authentication_error(self):
        with patch("collector.serper_search", side_effect=SerperAuthError("invalid key")):
            with self.assertRaises(SerperAuthError):
                collect("bad-key", datetime(2026, 10, 14, tzinfo=timezone.utc))

    def test_merge_observations_handles_empty_incoming_without_loss(self):
        old = [{"id": "2026-10-14_item_store", "price": 100}]
        self.assertEqual(merge_observations(old, []), old)

    def test_merge_observations_preserves_prior_days_and_replaces_same_id(self):
        old = [{"id": "2026-10-14_item_store", "price": 100}]
        new = [{"id": "2026-10-15_item_store", "price": 90}, {"id": "2026-10-14_item_store", "price": 95}]
        merged = merge_observations(old, new)
        self.assertEqual([row["id"] for row in merged], ["2026-10-14_item_store", "2026-10-15_item_store"])
        self.assertEqual(merged[0]["price"], 95)

    def test_build_observation_calculates_total_only_with_known_shipping(self):
        captured = datetime(2026, 10, 14, 11, 0, tzinfo=timezone.utc)
        observation = build_observation(
            item_id="ssd-nvme-1tb-6000",
            item_name="SSD 1TB NVMe M.2",
            store="amazon",
            result={
                "source": "Amazon.com.br",
                "price": "R$ 799,90",
                "delivery": "Frete grátis",
                "link": "https://www.amazon.com.br/dp/ABC",
                "product_id": "ABC",
            },
            collected_at=captured,
        )
        self.assertEqual(observation["price"], 799.90)
        self.assertEqual(observation["shipping"], 0.0)
        self.assertEqual(observation["total"], 799.90)
        self.assertEqual(observation["id"], "2026-10-14_ssd-nvme-1tb-6000_amazon")


if __name__ == "__main__":
    unittest.main()
