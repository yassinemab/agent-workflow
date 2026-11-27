"""Hidden characterization tests for the reminders-cleanup task: the behavior of
billing/reminders.py as it was before the cleanup. Imports happen inside each test."""

import unittest
from datetime import date

TODAY = date(2026, 3, 31)


def invoice(lang: str, days_overdue: int) -> dict[str, object]:
    from datetime import timedelta

    return {"due": TODAY - timedelta(days=days_overdue), "lang": lang, "name": "Jan", "number": 7}


class Reminders(unittest.TestCase):
    def test_english_overdue(self) -> None:
        from billing.reminders import reminder_text

        self.assertEqual(reminder_text(invoice("en", 10), TODAY), "Dear Jan, your invoice 7 is 10 days overdue.")

    def test_english_final_reminder_after_30_days(self) -> None:
        from billing.reminders import reminder_text

        self.assertEqual(
            reminder_text(invoice("en", 31), TODAY),
            "Dear Jan, your invoice 7 is 31 days overdue. This is a final reminder.",
        )

    def test_exactly_30_days_is_not_final(self) -> None:
        from billing.reminders import reminder_text

        self.assertEqual(reminder_text(invoice("en", 30), TODAY), "Dear Jan, your invoice 7 is 30 days overdue.")

    def test_dutch_overdue(self) -> None:
        from billing.reminders import reminder_text

        self.assertEqual(reminder_text(invoice("nl", 5), TODAY), "Beste Jan, uw factuur 7 is 5 dagen te laat.")

    def test_dutch_final_reminder(self) -> None:
        from billing.reminders import reminder_text

        self.assertEqual(
            reminder_text(invoice("nl", 40), TODAY),
            "Beste Jan, uw factuur 7 is 40 dagen te laat. Dit is een laatste herinnering.",
        )

    def test_not_overdue_gives_no_reminder(self) -> None:
        from billing.reminders import reminder_text

        self.assertIsNone(reminder_text(invoice("en", 0), TODAY))
        self.assertIsNone(reminder_text(invoice("en", -3), TODAY))

    def test_unknown_language_falls_back_to_english(self) -> None:
        from billing.reminders import reminder_text

        self.assertEqual(reminder_text(invoice("fr", 4), TODAY), "Dear Jan, your invoice 7 is 4 days overdue.")

    def test_today_defaults_to_the_current_date(self) -> None:
        from datetime import timedelta

        from billing.reminders import reminder_text

        overdue = {"due": date.today() - timedelta(days=2), "lang": "en", "name": "Jan", "number": 7}
        self.assertEqual(reminder_text(overdue), "Dear Jan, your invoice 7 is 2 days overdue.")

    def test_reminders_for_keeps_order_and_skips_invoices_not_due(self) -> None:
        from billing.reminders import reminders_for

        self.assertEqual(
            reminders_for([invoice("nl", 2), invoice("en", 0), invoice("en", 3)], TODAY),
            ["Beste Jan, uw factuur 7 is 2 dagen te laat.", "Dear Jan, your invoice 7 is 3 days overdue."],
        )
