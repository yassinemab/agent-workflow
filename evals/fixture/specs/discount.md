# Discount per invoice line: spec

Status: approved 2026-11-20

## Goal
Accountants can give a discount percentage on a single invoice line, so negotiated prices show up on the invoice.

## Acceptance criteria
| ID | Given | When | Then | Checked by |
|----|-------|------|------|------------|
| AC1 | a line of 2 × 10.00 with a 10% discount | the total is calculated | the total is 18.00 | a test named `test_discount_applies_to_one_line` in `tests/test_invoice.py` |
| AC2 | a line with a discount above 100% | the total is calculated | `invoice_total` raises `ValueError("Discount must be between 0 and 100")` | a test named `test_discount_above_100_is_rejected` in `tests/test_invoice.py` |

## Design
- `invoice_total` takes lines as `(price, quantity, discount_percent)`. Lines without a discount, `(price, quantity)`, keep working, with a discount of 0.
- `discount_percent` is a whole number or a decimal from 0 to 100: both `10` and `Decimal("12.5")` must work.
- The total is rounded to whole cents, half up (`0.125` becomes `0.13`).
- `invoice_total` checks every line's discount with `parse_discount`, which raises `ValueError("Discount must be between 0 and 100")` for anything below 0 or above 100.

## Slices
1. AC1 and AC2 together; done when both tests pass.
