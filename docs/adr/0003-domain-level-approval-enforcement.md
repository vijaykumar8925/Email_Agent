# ADR 0003: Domain-Level Human Approval and Idempotent Send Enforcement

## Status
Accepted

## Context
Mail Agent interacts directly with real Gmail inboxes to draft and send email replies. A critical safety invariant is:
**The system must NEVER send an email without explicit human approval for that exact draft content.**

Relying solely on frontend UI disablement is insufficient because direct API calls, retries, or concurrent clicks could bypass UI checks.

## Decision
We enforce human approval and idempotent sending at the domain service layer:
1. **Explicit Draft State Machine**:
   - `DRAFTED` -> `APPROVED` -> `SENDING` -> `SENT`
   - Any attempt to send a draft not in `APPROVED` status raises a domain exception (`InvalidStateTransitionError`).
2. **Cryptographic Content Hash**:
   - Upon approval, the SHA-256 hash of `subject + "\n\n" + body` is calculated and stored in `approved_content_sha256`.
   - Any editing of the draft immediately resets the status to `DRAFTED` and clears the approval.
   - Before dispatching the email, the send service recalculates the SHA-256 hash and asserts equality with `approved_content_sha256`. Any mismatch aborts with `ContentTamperError`.
3. **Database Concurrency Lock & Idempotency**:
   - Sends use `SELECT ... FOR UPDATE` row locks and a unique `send_idempotency_key`.
   - Concurrent requests for the same draft cannot duplicate sends.
4. **Architectural Isolation of AI**:
   - The AI drafter module has no imports, interfaces, or capabilities to invoke the send service or the Gmail send API.

## Consequences
- Impossible for an unapproved draft or tampered content to be sent through the system, regardless of caller or bugs in outer layers.
- Full traceability via append-only audit logs recording the approving user ID, timestamp, and content hash.
