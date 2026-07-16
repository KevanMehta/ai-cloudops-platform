# Security Policy

## Supported Versions

This is a portfolio reference implementation rather than a deployed service. Security fixes are applied only to the latest revision on the default branch; no released version line is currently maintained.

## Reporting a Vulnerability

Do not open a public issue for a suspected vulnerability. Use GitHub's **Report a vulnerability** option on the repository's Security tab. Include the affected component, reproduction steps, impact, and any suggested mitigation. If private vulnerability reporting is not enabled, contact the repository owner through the contact method on their GitHub profile and request a private reporting channel.

Please allow time to confirm the report before public disclosure. Acknowledgement does not imply a specific remediation or release timeline.

## Security Assumptions

- The application is designed for local evaluation with synthetic data.
- The API is expected to run on a trusted developer machine or isolated network.
- The bundled database credentials are local defaults, not secrets.
- An OpenAI API key, when configured, is read by the backend from its environment and is not intentionally returned to the frontend.
- Terraform samples are repository fixtures; the application is not intended to process untrusted infrastructure repositories.

## Known Limitations

- API endpoints have no authentication or authorization.
- CORS currently permits all origins.
- The Terraform endpoint accepts a relative file name and has not been hardened for hostile input.
- Terraform checks use regular expressions and are not a security scanner or policy engine.
- Dependency and container-image updates still require maintainer review even when Dependabot opens a pull request.
- There is no rate limiting, audit log, TLS termination, secret manager, or tenant isolation.
- Prompt content is derived from stored demo data, but enabling the OpenAI integration sends the assembled operational summary to the configured external API.

Do not expose this application to the public internet without addressing these limitations and completing an independent security review.
