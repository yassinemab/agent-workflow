"""Hidden tests for the dutch-amounts task. Imports happen inside each test, so the
file always loads and its tests can be counted, even when the agent broke an import."""

import unittest
from decimal import Decimal


class DutchAmounts(unittest.TestCase):
    def test_decimal_comma(self) -> None:
        from billing.invoice import parse_amount

        self.assertEqual(parse_amount("1,5"), Decimal("1.5"))

    def test_thousands_dot_and_decimal_comma(self) -> None:
        from billing.invoice import parse_amount

        self.assertEqual(parse_amount("1.234,56"), Decimal("1234.56"))

    def test_whole_number(self) -> None:
        from billing.invoice import parse_amount

        self.assertEqual(parse_amount("10"), Decimal("10"))

    def test_cents(self) -> None:
        from billing.invoice import parse_amount

        self.assertEqual(parse_amount("0,05"), Decimal("0.05"))

    def test_total_of_a_dutch_price(self) -> None:
        from billing.invoice import invoice_total

        self.assertEqual(invoice_total([("1,5", 2)]), Decimal("3"))
