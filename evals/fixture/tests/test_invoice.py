from billing.invoice import invoice_total


def test_total_of_whole_amounts():
    assert invoice_total([("10", 2)]) == 20
