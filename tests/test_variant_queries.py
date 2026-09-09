import unittest

from backend.api.variant_queries import parse_variant_lookup


class VariantQueryTest(unittest.TestCase):
    def test_valid_query_is_parsed(self) -> None:
        lookup = parse_variant_lookup(
            "gene=BRCA1&hgvs_notation=c.5266dupC"
        )

        self.assertEqual(lookup.gene, "BRCA1")
        self.assertEqual(lookup.hgvs_notation, "c.5266dupC")

    def test_encoded_query_values_are_decoded(self) -> None:
        lookup = parse_variant_lookup(
            "gene=BRCA1&hgvs_notation=c.123%2B1G%3EA"
        )

        self.assertEqual(lookup.hgvs_notation, "c.123+1G>A")

    def test_missing_or_blank_values_are_rejected(self) -> None:
        for query in (
            "",
            "gene=BRCA1",
            "hgvs_notation=c.5266dupC",
            "gene=&hgvs_notation=c.5266dupC",
            "gene=BRCA1&hgvs_notation=",
        ):
            with self.subTest(query=query):
                with self.assertRaises(ValueError):
                    parse_variant_lookup(query)

    def test_repeated_lookup_values_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_variant_lookup("gene=BRCA1&gene=BRCA2&hgvs_notation=c.5266dupC")

    def test_non_string_query_is_rejected(self) -> None:
        with self.assertRaises(TypeError):
            parse_variant_lookup(None)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
