# Objects

What this product's things are, what they're called, which states they move through and which rules they obey. Define
uses these names and states in acceptance criteria and UI copy; Review checks each rule like a must-never-break line.
Code spans hold state names only, each declared on its object's States line; write every other name as plain text.

## Objects

### Invoice
A request for payment sent to one Customer.
- UI name: Invoice, Invoices
- Code: Invoice (table invoices)
- Belongs to: Customer (one)
- Has: Line item (many)
- States: `draft` → `sent` → `paid`; `sent` → `void`
- Actions: send (draft), record payment (sent), void (sent)
- Shown as: InvoiceRow (list), InvoiceCard (summary), /invoices/:id (detail)

## Rules

- **DR-001** An Invoice in `paid` never changes its total.

## Avoid

- Bill, Receipt → Invoice
