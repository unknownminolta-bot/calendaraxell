import unittest

from src.classifier import CategoryRule, classify_event, event_text, matches_rule


class ClassifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rules = {
            "completed_task": CategoryRule(
                name="completed_task",
                color_id="8",
                include_keywords=[
                    "klar",
                    "klart",
                    "färdig",
                    "färdigt",
                    "avklarad",
                    "avklarat",
                    "slutförd",
                    "slutfört",
                    "gjord",
                    "gjort",
                    "fixad",
                    "fixat",
                    "ansökt",
                    "sökt",
                    "inskickad",
                    "inskickat",
                    "bokad",
                    "bokat",
                    "betalad",
                    "betalt",
                    "done",
                    "completed",
                    "complete",
                    "finished",
                    "submitted",
                    "applied",
                    "paid",
                    "booked",
                ],
                exclude_keywords=[
                    "att göra",
                    "todo",
                    "pågående",
                    "under behandling",
                    "väntar",
                    "ska ansöka",
                    "ansökan öppen",
                    "planerar",
                    "planering",
                    "pending",
                    "in progress",
                ],
                all_day_only=True,
            ),
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
            "misc": CategoryRule(
                name="misc",
                color_id="8",
                include_keywords=["car", "vehicle", "passport"],
                exclude_keywords=[],
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

    def test_all_day_only_rule_skips_timed_events(self) -> None:
        event = {
            "summary": "NAIS application ansökt",
            "start": {"dateTime": "2026-04-15T10:00:00+02:00"},
        }
        matched = classify_event(event, self.rules, ["completed_task"])
        self.assertIsNone(matched)

    def test_all_day_only_rule_matches_all_day_events(self) -> None:
        event = {
            "summary": "NAIS application ansökt",
            "start": {"date": "2026-04-15"},
        }
        matched = classify_event(event, self.rules, ["completed_task"])
        self.assertIsNotNone(matched)
        self.assertEqual(matched.name, "completed_task")

    def test_completed_task_matches_swedish_word_anywhere_in_text(self) -> None:
        event = {
            "summary": "NAIS ansökan",
            "description": "Nu är allt inskickat och klart.",
            "start": {"date": "2026-04-15"},
        }
        matched = classify_event(event, self.rules, ["completed_task"])
        self.assertIsNotNone(matched)
        self.assertEqual(matched.name, "completed_task")

    def test_completed_task_matches_english_word_anywhere_in_text(self) -> None:
        event = {
            "summary": "University paperwork",
            "description": "Application submitted yesterday.",
            "location": "Home office",
            "start": {"date": "2026-04-15"},
        }
        matched = classify_event(event, self.rules, ["completed_task"])
        self.assertIsNotNone(matched)
        self.assertEqual(matched.name, "completed_task")

    def test_completed_task_exclude_keyword_blocks_match(self) -> None:
        event = {
            "summary": "NAIS ansökan öppen",
            "description": "Ska ansöka senare idag, fortfarande pending.",
            "start": {"date": "2026-04-15"},
        }
        matched = classify_event(event, self.rules, ["completed_task"])
        self.assertIsNone(matched)

    def test_whole_word_matching_avoids_sokt_in_besokt_false_positive(self) -> None:
        event = {
            "summary": "Besökt tandläkaren",
            "start": {"date": "2026-04-15"},
        }
        matched = classify_event(event, self.rules, ["completed_task"])
        self.assertIsNone(matched)

    def test_whole_word_matching_avoids_klar_in_forklarar_false_positive(self) -> None:
        event = {
            "summary": "Förklarar uppgift",
            "start": {"date": "2026-04-15"},
        }
        matched = classify_event(event, self.rules, ["completed_task"])
        self.assertIsNone(matched)

    def test_completed_task_priority_overrides_studies(self) -> None:
        event = {
            "summary": "Exam application ansökt",
            "start": {"date": "2026-04-15"},
        }
        matched = classify_event(event, self.rules, ["completed_task", "studies"])
        self.assertIsNotNone(matched)
        self.assertEqual(matched.name, "completed_task")

    def test_completed_task_priority_overrides_misc(self) -> None:
        event = {
            "summary": "Passport renewal completed",
            "start": {"date": "2026-04-15"},
        }
        matched = classify_event(event, self.rules, ["completed_task", "misc"])
        self.assertIsNotNone(matched)
        self.assertEqual(matched.name, "completed_task")

    def test_timed_event_with_status_word_keeps_original_category(self) -> None:
        event = {
            "summary": "Study exam klar",
            "start": {"dateTime": "2026-04-15T10:00:00+02:00"},
        }
        matched = classify_event(event, self.rules, ["completed_task", "studies"])
        self.assertIsNotNone(matched)
        self.assertEqual(matched.name, "studies")

    def test_priority_rule_handles_inflected_school_words(self) -> None:
        rules = {
            "preschool": CategoryRule(
                name="preschool",
                color_id="10",
                include_keywords=["förskola", "förskolan"],
                exclude_keywords=[],
            ),
            "time_off": CategoryRule(
                name="time_off",
                color_id="2",
                include_keywords=["ledig"],
                exclude_keywords=[],
            ),
        }
        event = {"summary": "Dante ledig från förskolan", "start": {"date": "2026-06-11"}}
        matched = classify_event(event, rules, ["preschool", "time_off"])
        self.assertIsNotNone(matched)
        self.assertEqual(matched.name, "preschool")


if __name__ == "__main__":
    unittest.main()
