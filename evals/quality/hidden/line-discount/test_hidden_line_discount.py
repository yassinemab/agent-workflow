"""Hidden tests for the line-discount task, taken from specs/discount.md. Imports happen
inside each test, so the file always loads and its tests can be counted."""

import unittest
from decimal import Decimal


class LineDiscount(unittest.TestCase):
    def test_discount_applies_to_one_line(self) -> None:
        from billing.invoice import invoice_total

        self.assertEqual(invoice_total([("10", 2, 10)]), Decimal("18.00"))

    def test_lines_without_a_discount_keep_working(self) -> None:
        from billing.invoice import invoice_total

        self.assertEqual(invoice_total([("10", 2)]), Decimal("20"))

    def test_full_discount_gives_zero(self) -> None:
        from billing.invoice import invoice_total

        self.assertEqual(invoice_total([("10", 1, 100)]), Decimal("0"))

    def test_total_is_rounded_to_cents_half_up(self) -> None:
        from billing.invoice import invoice_total

        self.assertEqual(invoice_total([("25", 1, Decimal("99.5"))]), Decimal("0.13"))

    def test_discount_above_100_is_rejected(self) -> None:
        from billing.invoice import invoice_total

        with self.assertRaisesRegex(ValueError, "Discount must be between 0 and 100"):
            invoice_total([("10", 1, 101)])

    def test_parse_discount_rejects_negative_discounts(self) -> None:
        from billing.invoice import parse_discount

        with self.assertRaisesRegex(ValueError, "Discount must be between 0 and 100"):
            parse_discount(-1)
