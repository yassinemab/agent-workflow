import unittest

from billing.invoice import invoice_total


class InvoiceTotal(unittest.TestCase):
    def test_total_of_whole_amounts(self) -> None:
        self.assertEqual(invoice_total([("10", 2)]), 20)
