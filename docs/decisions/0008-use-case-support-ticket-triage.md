# ADR-0008: Use case: support-ticket triage

- **Status:** Accepted (owner's choice, 2026-11-13)
- **Date:** 2026-11-13
- **Deciders:** Project owner
- **Issue:** [#18](https://github.com/saicharan-nidiganti/local-ai-benchmark/issues/18)
- **Requirements:** FR-6, FR-9, FR-12

## Context

Speed alone does not say whether a local model is worth running: the comparison needs a
quality score on a task people would actually give it. The privacy argument for running
offline also needs that task to involve data that should not be sent to a hosted API. The
same task later becomes the offline app (FR-12).

## Decision drivers

1. The data is plausibly confidential: names, contact details, order numbers, complaints.
2. Every task can be scored automatically and exactly, without a human or a second model.
3. The tasks exercise the three abilities that matter for small models: following a label
   set, producing valid structured output, and summarizing without losing facts.
4. The suite can be written synthetically, so no real person's data is ever in the repository.

## Options considered

| Option | Pros | Cons |
| --- | --- | --- |
| **Support-ticket triage** | A common enterprise task; customer data makes the privacy case concrete; labels, fields and facts are all scorable | Labels need written rules to be unambiguous |
| Personal email triage | A strong personal-privacy story | "Needs action" is subjective; dates in free text are hard to score |
| Bank transaction categorizing | Exact scoring | Short, formulaic inputs say little about language ability; summarization barely applies |

## Decision

Support-ticket triage, with three tasks per ticket:

| Task | Model output | Scored by |
| --- | --- | --- |
| Classify | JSON: `category` and `priority` | Exact label match, each half the score |
| Extract | JSON: `order_id`, `customer_name`, `product`, `issue` | JSON validity, schema validity, then field accuracy |
| Summarize | Plain text, at most 40 words | Share of required facts present; halved when over the word limit |

Labels:

| Field | Values | Rule |
| --- | --- | --- |
| `category` | `billing`, `refund`, `shipping`, `technical`, `account` | What the customer needs resolved. `billing`: invoices, plans, prices and payment methods going forward. `refund`: money back for an order or charge already paid. `shipping`: delivery status, delays, addresses, lost parcels. `technical`: a product or the app does not work as it should. `account`: sign-in, profile, data and security settings |
| `priority` | `urgent`, `high`, `medium`, `low` | `urgent`: a security problem or a business stopped; `high`: money lost or the product unusable; `medium`: a problem with a workaround or a delay; `low`: a question or feedback |

Every ticket is fictional: invented names, `example.com` addresses, made-up order numbers.
The suite is versioned (`support_triage_v1`); a change to a ticket or an expectation makes a
new version, so scores stay comparable within a version.

## Consequences

### Positive

- Quality, speed and resource use are measured on the same requests.
- The app in Phase 5 is the same three tasks behind one command.

### Negative and risks

- Exact matching under-credits a correct answer phrased differently; field rules (case and
  punctuation ignored, issue scored by keywords) keep this small, and the rules are documented
  with the suite.
- A synthetic suite is cleaner than real tickets; results describe this suite, not every
  support queue.

## Revisit when

- A scorer disagrees with a human reading on more than a few tasks, or the suite stops
  separating the models.
