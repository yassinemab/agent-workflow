# Discount per invoice line: spec

Status: approved 2026-11-20

## Goal
Accountants can give a discount percentage on a single invoice line, so negotiated prices show up on the invoice.

## Acceptance criteria
| ID | Given | When | Then | Checked by |
|----|-------|------|------|------------|
| AC1 | a line of 2 × 10.00 with a 10% discount | the total is calculated | the total is 18.00 | tests/test_invoice.py::test_discount_applies_to_one_line |
| AC2 | a discount above 100% | the line is saved | it is rejected with "Discount must be between 0 and 100" | tests/test_invoice.py::test_discount_above_100_is_rejected |

## Design
- `invoice_total` takes lines as `(price, quantity, discount_percent)`; the discount defaults to 0.
- Validation in `parse_discount`, raising `ValueError`.

## Slices
1. AC1 and AC2 together; done when both tests pass.
