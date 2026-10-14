import unittest
from datetime import datetime, timezone

from collector import (
    build_observation,
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
