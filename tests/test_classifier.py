import unittest

from src.classifier import CategoryRule, classify_event, event_text, matches_rule


class ClassifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rules = {
            "studies": CategoryRule(
                name="studies",
                color_id="3",
                include_keywords=["study", "exam"],
                exclude_keywords=[],
            ),
            "travel": CategoryRule(
                name="travel",
                color_id="6",
                include_keywords=["trip", "flight"],
                exclude_keywords=["daytrip"],
            ),
        }

    def test_event_text_uses_summary_description_and_location(self) -> None:
        event = {
            "summary": "Family Trip",
            "description": "Flight tickets booked",
            "location": "Stockholm",
        }
        self.assertEqual(event_text(event), "family trip flight tickets booked stockholm")

    def test_matches_rule_respects_include_and_exclude_keywords(self) -> None:
        rule = self.rules["travel"]
        self.assertTrue(matches_rule(rule, "summer trip with flight"))
        self.assertFalse(matches_rule(rule, "fun daytrip tomorrow"))
        self.assertFalse(matches_rule(rule, "regular calendar event"))

    def test_classify_event_uses_priority_order(self) -> None:
        event = {"summary": "Study trip planning"}
        priority = ["travel", "studies"]
        matched = classify_event(event, self.rules, priority)
        self.assertIsNotNone(matched)
        self.assertEqual(matched.name, "travel")

    def test_classify_event_returns_none_when_no_rule_matches(self) -> None:
        event = {"summary": "Weekly groceries"}
        matched = classify_event(event, self.rules, ["studies", "travel"])
        self.assertIsNone(matched)


if __name__ == "__main__":
    unittest.main()
