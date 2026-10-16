import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from collector import (
    SerpApiAuthError,
    build_observation,
    classify_serpapi_error,
    build_search_query,
    merge_observations,
    collect,
    parse_brl,
    parse_shipping,
    select_store_result,
)


class CollectorTests(unittest.TestCase):
    def test_parse_brl_handles_brazilian_price(self):
        self.assertEqual(parse_brl("R$ 4.599,90"), 4599.90)
        self.assertEqual(parse_brl("1.200,00"), 1200.00)

    def test_parse_shipping_handles_free_and_paid_shipping(self):
        self.assertEqual(parse_shipping("Frete grátis"), 0.0)
        self.assertEqual(parse_shipping("Entrega por R$ 24,90"), 24.90)
        self.assertIsNone(parse_shipping("Consulte o frete"))

    def test_select_store_result_requires_matching_store(self):
        results = [
            {"source": "Outra loja", "price": "R$ 10,00", "link": "https://outra.example/p"},
            {"source": "KaBuM!", "price": "R$ 20,00", "link": "https://www.kabum.com.br/p"},
        ]
        chosen = select_store_result(results, "kabum")
        self.assertEqual(chosen["source"], "KaBuM!")

    def test_search_query_avoids_site_operator_for_shopping(self):
        query = build_search_query("Monitor Gamer LG UltraGear 34G600A", "fastshop")
        self.assertNotIn("site:", query)
        self.assertIn("Fast Shop", query)

    def test_serpapi_no_results_is_not_authentication_error(self):
        self.assertEqual(classify_serpapi_error("Google hasn't returned any results for this query."), "no_results")

    def test_serpapi_invalid_key_is_authentication_error(self):
        self.assertEqual(classify_serpapi_error("Invalid API key"), "auth")

    def test_serpapi_authentication_error_is_propagated(self):
        with patch("collector.serpapi_search", side_effect=SerpApiAuthError("invalid key")):
            with self.assertRaises(SerpApiAuthError):
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
