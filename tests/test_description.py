import unittest

from draw_to_life.description import identify_species, parse_description


class DescriptionTests(unittest.TestCase):
    def test_catalog_aliases(self):
        for text, animal in (("little puppy", "dog"), ("happy kitten", "cat"),
                             ("yellow duckling", "duck"), ("pink piglet", "pig"),
                             ("green bunny", "rabbit"), ("teddy bear", "bear")):
            with self.subTest(text=text):
                self.assertEqual(identify_species(text), animal)

    def test_partial_words_and_multiple_animals_are_ambiguous(self):
        for text in ("bearded monster", "cat or dog", "friendly creature"):
            self.assertEqual(identify_species(text), "unknown")

    def test_legacy_description_infers_species(self):
        desc = parse_description('{"creature":"puppy", "eyes":"large eyes"}')
        self.assertEqual(desc.species, "dog")
        self.assertFalse(desc.species_uncertain)
        self.assertTrue(desc.summary)

    def test_explicit_uncertainty_is_respected(self):
        desc = parse_description('{"creature":"dog", "species":"dog", "species_uncertain":true}')
        self.assertEqual(desc.species, "dog")
        self.assertTrue(desc.species_uncertain)

    def test_unknown_species_is_always_uncertain(self):
        desc = parse_description('{"creature":"blob", "species":"unknown", "species_uncertain":false}')
        self.assertTrue(desc.species_uncertain)

    def test_invalid_species_types(self):
        for value in ('[]', '42', '"unicorn"'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_description('{"creature":"dog", "species":' + value + '}')
        with self.assertRaises(ValueError):
            parse_description('{"creature":"dog", "species_uncertain":"false"}')

    def test_missing_creature_and_nonjson(self):
        for text in ('not json', '{}', '{"creature":[]}'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_description(text)


if __name__ == "__main__":
    unittest.main()
