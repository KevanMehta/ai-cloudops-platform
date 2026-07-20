# Security Policy

## Supported Versions

This is a portfolio reference implementation rather than a deployed service. Security fixes are applied only to the latest revision on the default branch; no released version line is currently maintained.

## Reporting a Vulnerability

Do not open a public issue for a suspected vulnerability. Use GitHub's **Report a vulnerability** option on the repository's Security tab. Include the affected component, reproduction steps, impact, and any suggested mitigation. If private vulnerability reporting is not enabled, contact the repository owner through the contact method on their GitHub profile and request a private reporting channel.

Please allow time to confirm the report before public disclosure. Acknowledgement does not imply a specific remediation or release timeline.

## Security Assumptions

- Demo mode is designed for local evaluation with synthetic data. Connected mode performs read-only provider calls with the identity supplied through the AWS or Kubernetes client configuration.
- The API is expected to run on a trusted developer machine or isolated network.
- The bundled database credentials are local defaults, not secrets.
- An OpenAI API key, when configured, is read by the backend from its environment and is not intentionally returned to the frontend.
- Terraform analysis is restricted to `.tf` file names under the configured samples directory.

## Known Limitations

- API endpoints have no authentication or authorization.
- CORS is configurable and defaults to the local frontend origin; it is not an authentication control.
- Terraform checks use an HCL parser but are not a security scanner or policy engine.
- Dependency and container-image updates still require maintainer review even when Dependabot opens a pull request.
- There is no rate limiting, audit log, TLS termination, secret manager, or tenant isolation.
- Provider synchronization runs synchronously and the endpoints have no authorization boundary.
- AWS read permissions may expose organization billing data; use a dedicated least-privilege role and an external ID for third-party cross-account access.
- Mounted AWS and kubeconfig files must be protected by host filesystem permissions.
- Prompt content is derived from stored demo data, but enabling the OpenAI integration sends the assembled operational summary to the configured external API.

Do not expose this application to the public internet without addressing these limitations and completing an independent security review.
