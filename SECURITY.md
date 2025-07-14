# Security Policy

## Supported Versions

| Version | Supported          |
|:--------|:-------------------|
| 1.x     | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do not** open a public GitHub issue.
2. Email the details to **harshpahurkar@gmail.com** with the subject line: `[SECURITY] global-billing-service`.
3. Include steps to reproduce, potential impact, and any suggested fixes.

You can expect an initial response within **48 hours**. We will work with you to understand and address the issue before any public disclosure.

## Security Practices

This project follows these security practices:

- **Environment variables** for all secrets (never committed to source)
- **Stripe webhook signature verification** to validate incoming events
- **API key hashing** using bcrypt (plaintext keys are never stored)
- **SQL injection prevention** via SQLAlchemy ORM parameterized queries
- **CORS configuration** to restrict cross-origin access
- **Non-root Docker user** in production containers
- **Secrets Manager** for production credentials (AWS)
