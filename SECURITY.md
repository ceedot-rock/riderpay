# Security Policy

RiderPay moves money (in sandbox). A bug that lets the agent pay more than
policy allows, that lets a tampered receipt verify, or that introduces any
real-money path is a security issue, not a normal bug.

## Reporting a vulnerability

Please do not open a public issue for security problems.

- Use GitHub's private vulnerability reporting on this repository
  (Security tab, "Report a vulnerability"), **or**
- Email corey@slidphilabs.com with the subject line `RiderPay security`

Include the affected file or endpoint, steps or inputs to reproduce, and what
you expected versus what happened.

You can expect an acknowledgement within 3 business days. We will keep you
updated while we investigate and credit you unless you prefer to stay
anonymous.

## In scope

- Policy bypass: any instruction or credential that gets the agent to pay more
  than `SpendingPolicy` allows
- Credential verification weaknesses (the ES256 JWT verify once the stub is
  replaced)
- Receipt forgery: a tampered receipt that still verifies
- Any path that could touch real money (the sandbox pin must hold)

## Out of scope

- The PayPal sandbox itself
- Social engineering, spam, or denial-of-service against hosted demos
