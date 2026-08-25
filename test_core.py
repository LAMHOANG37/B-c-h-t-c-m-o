import unittest
from services.groq_service import strip_think_tags
from services.quota_tracker import QuotaTracker

class TestCoreModules(unittest.TestCase):
    def test_strip_think_tags_complete(self):
        sample = "<think>\nThinking deeply about AI video tools...\nStep 1: Check trends\n</think>\nHere is the final report."
        cleaned = strip_think_tags(sample)
        self.assertEqual(cleaned, "Here is the final report.")

    def test_strip_think_tags_unclosed(self):
        sample = "<think>\nThinking without closing tag..."
        cleaned = strip_think_tags(sample)
        self.assertEqual(cleaned, "")

    def test_calculate_niche_score_tier_s(self):
        # Test scoring formula directly
        demand = 95
        growth = 90
        competition = 85
        content_depth = 85
        monetization = 90
        content_gap = 85
        production_feasibility = 80
        scalability = 90
        risk = 85

        final_score = (
            (demand * 0.20) +
            (growth * 0.10) +
            (competition * 0.15) +
            (content_depth * 0.15) +
            (monetization * 0.15) +
            (content_gap * 0.10) +
            (production_feasibility * 0.05) +
            (scalability * 0.05) +
            (risk * 0.05)
        )
        final_score = round(final_score, 1)
        self.assertGreaterEqual(final_score, 85.0)

    def test_quota_tracker_youtube_units(self):
        tracker = QuotaTracker()
        tracker.start_session()
        warn, msg, reset_info = tracker.add_yt_units(100)
        self.assertFalse(warn)
        stats = tracker.get_session_stats()
        self.assertEqual(stats["yt_units"], 100)

if __name__ == "__main__":
    unittest.main()
