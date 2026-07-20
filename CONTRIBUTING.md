# Contributing

Contributions that improve correctness, tests, documentation, or maintainability are welcome. Please open an issue before proposing a substantial change so its scope can be agreed without expanding the project unnecessarily.

## Development Setup

The supported full-stack path is Docker Compose:

```bash
cp .env.example .env
docker compose up --build
```

For a local backend process, provide reachable PostgreSQL and Redis instances, install `backend/requirements.txt`, run `python -m app.seed.init_db`, and start `uvicorn app.main:app --reload --port 8000` from `backend/`.

For the frontend:

```bash
cd frontend
npm ci
npm run dev
```

## Before Opening a Pull Request

Run the checks affected by your change:

```bash
cd backend && pytest -v
cd frontend && npm test -- --run && npm audit --audit-level=high && npm run build
```

Keep pull requests focused. Update tests and documentation when behavior changes, disclose whether data or integrations are simulated, and do not add performance or savings claims without a reproducible method and evidence.

Provider tests must mock the SDK boundary and include at least one failure path. Never run automated tests against a contributor's default AWS account or current Kubernetes context.

## Commit and Pull Request Notes

- Use a short, imperative commit subject.
- Explain the problem, the chosen approach, and relevant tradeoffs.
- Include screenshots only for visible interface changes.
- Link the issue when one exists.
- Never commit `.env` files, credentials, customer data, or real cloud account identifiers.

By contributing, you agree that your contribution is licensed under the repository's MIT License.
