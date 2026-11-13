# Task suites

A suite is a JSON Lines file of fictional support tickets. Each ticket becomes three tasks:
**classify** (category and priority), **extract** (four fields as JSON) and **summarize** (at
most 40 words). The use case, label sets and scoring are decided in
[ADR-0008](../docs/decisions/0008-use-case-support-ticket-triage.md).

| Suite | Tickets | Tasks | Notes |
| --- | --- | --- | --- |
| [support_triage_v1.jsonl](support_triage_v1.jsonl) | 15 | 45 | 3 tickets per category; every priority present |

## Format

One ticket per line:

```json
{"id": "T04",
 "ticket": "Order A-1042 arrived today and the ceramic table lamp is cracked ...",
 "expected": {
   "category": "refund",
   "priority": "high",
   "order_id": "A-1042",
   "customer_name": "Priya Raman",
   "product": ["ceramic table lamp", "table lamp", "lamp"],
   "issue_keywords": ["cracked", "damaged", "broken"],
   "summary_facts": [["A-1042"], ["cracked", "damaged", "broken"], ["refund"]]}}
```

| Key | Meaning |
| --- | --- |
| `category` | One of `billing`, `refund`, `shipping`, `technical`, `account` |
| `priority` | One of `urgent`, `high`, `medium`, `low` |
| `order_id` | The order number as written in the ticket, or `null` |
| `customer_name` | The customer's name as written |
| `product` | Acceptable wordings of the product, or `null` when none is named |
| `issue_keywords` | Words of which at least one must appear in the extracted `issue` |
| `summary_facts` | Facts the summary must contain; each fact lists acceptable wordings |

The prompts that turn a ticket into its three tasks live in
[`suite.py`](../src/local_ai_benchmark/suite.py) and belong to the suite version.

## Rules

- **Fictional only.** Invented names, `example.com` addresses, made-up order numbers. A test
  rejects any other e-mail domain.
- **Self-consistent.** Every expected name, order number and product appears in its ticket; a
  test checks it.
- **Versioned.** Changing a ticket, an expectation or a prompt makes a new file
  (`support_triage_v2.jsonl`), so scores remain comparable within a version.
