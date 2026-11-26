from decimal import Decimal


def parse_amount(text: str) -> Decimal:
    """Parse an amount typed by a Dutch user, e.g. '1.234,56'."""
    return Decimal(text.replace(",", ""))


def invoice_total(lines: list[tuple[str, int]]) -> Decimal:
    return sum((parse_amount(price) * qty for price, qty in lines), Decimal("0"))
