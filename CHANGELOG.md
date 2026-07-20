# Changelog

Notable repository changes are documented here. This project does not currently publish versioned releases; entries remain under `Unreleased` until that changes.

## Unreleased

### Added

- Added explicit demo, connected, and offline operating modes.
- Added AWS Cost Explorer ingestion, STS AssumeRole, Budgets summary, and CloudWatch billing reads.
- Added live Kubernetes Deployment and StatefulSet inventory with restart aggregation.
- Added provider status and synchronization endpoints.
- Added mocked AWS and Kubernetes tests plus API integration and Terraform failure tests.
- Added request IDs and route-level Prometheus metrics.

### Changed

- Upgraded Vitest to the patched 3.2 release line.
- Split React and charting dependencies into separate frontend build chunks.
- Set the pytest-asyncio fixture loop scope explicitly.
- Added frontend dependency auditing and build verification to CI.
- Replaced regex Terraform inspection with HCL parsing and constrained file resolution.
- Removed unsupported monetary savings estimates from generated recommendations.

### Documentation

- Clarified the demo-data boundary, heuristic savings estimates, and optional OpenAI usage.
- Documented architecture decisions, tradeoffs, testing scope, security assumptions, and contribution expectations.
- Added issue and pull request templates plus automated dependency-update configuration.
