# 12. TECHNOLOGY STACK & ENGINEERING STANDARDS

## 12.1 Technology Selection Principles

Act as a Technology Architect and select a modern, production-ready technology stack based on the problem domain, requirements, scalability, maintainability, security and operational complexity.

Use established frameworks, libraries and tools with active community support and long-term viability.

Prefer:
- Mature and widely adopted technologies.
- Stable and supported framework versions.
- Open standards and interoperability.
- Well-maintained libraries.
- Containerisation and automation.
- Cloud portability.
- Developer productivity.
- Minimal operational complexity.

Do not select technologies simply because they are popular.

Do not introduce multiple technologies serving the same purpose without a clear architectural justification.

Document technology decisions and alternatives in architecture decision records (ADRs).

## 12.2 Backend Engineering

Support the following technology ecosystems:

### Python – Preferred for Python-based solutions

- Python 3 (latest stable compatible release).
- FastAPI – Modern asynchronous REST APIs.
- Django – Full-featured web applications and enterprise platforms.
- Django REST Framework – REST API development with Django.
- Flask – Lightweight services where appropriate.
- Pydantic – Data validation and settings management.
- SQLAlchemy – ORM and database interaction.
- Alembic – Database schema migrations.
- Celery – Distributed background processing.
- Dramatiq / RQ – Alternative background task processing.
- Pytest – Automated testing.
- Uvicorn / Gunicorn – Application serving.
- Poetry / uv – Dependency and environment management.
- Ruff – Linting and formatting.
- mypy / Pyright – Static type checking.

Use FastAPI for API-first services unless Django or another framework provides a better fit.

### Java

- Latest suitable LTS Java version.
- Spring Boot.
- Spring Framework.
- Spring Security.
- Spring Data JPA / Hibernate.
- Spring Cloud where justified.
- Maven / Gradle.
- JUnit 5.
- Mockito.
- Testcontainers.
- Flyway / Liquibase.

### Node.js / TypeScript

- Node.js LTS.
- TypeScript.
- NestJS.
- Express.js where appropriate.
- Prisma / TypeORM.
- Jest / Vitest.
- npm / pnpm.

### .NET

- Latest suitable supported .NET version.
- ASP.NET Core.
- Entity Framework Core.
- xUnit / NUnit.
- NuGet.

## 12.3 Frontend Engineering

Preferred technologies:

- TypeScript.
- React.
- Next.js.
- Vue.js / Nuxt where appropriate.
- Angular for enterprise applications where justified.
- Vite.
- Tailwind CSS.
- Material UI.
- shadcn/ui.
- React Query / TanStack Query.
- Redux Toolkit / Zustand where appropriate.
- React Hook Form.
- Zod.
- Playwright.
- Vitest.

Use component-based architecture, reusable UI components, responsive design, accessibility standards and consistent design systems.

Avoid unnecessary frontend state-management libraries.

## 12.4 Mobile Engineering

Support:

- Flutter / Dart.
- React Native / TypeScript.
- Native Android / Kotlin.
- Native iOS / Swift.

Select based on platform requirements, hardware integration, performance and maintainability.

## 12.5 Database Engineering

Select relational or NoSQL databases according to the data model and access patterns.

### Relational databases
- PostgreSQL – Preferred general-purpose relational database.
- MySQL / MariaDB.
- Microsoft SQL Server.
- Oracle Database.

### NoSQL databases
- MongoDB.
- Couchbase.
- Redis.
- Cassandra where justified.

### Data access and migrations
- SQLAlchemy.
- Django ORM.
- Hibernate / JPA.
- Prisma.
- Flyway.
- Liquibase.
- Alembic.

Apply database normalisation where appropriate, indexing, constraints, transactions, migration management and query optimisation.

Do not introduce NoSQL when a relational database adequately satisfies the requirements.

## 12.6 Data Engineering & Analytics

Support:

- Python.
- Apache Airflow.
- Dagster.
- Prefect.
- Apache Kafka.
- Apache Spark.
- dbt.
- Pandas.
- Polars.
- DuckDB.
- Apache Flink where justified.

### Data warehouses and storage
- PostgreSQL.
- Snowflake.
- BigQuery.
- Amazon Redshift.
- Databricks.

### BI and visualisation
- Power BI.
- Apache Superset.
- Metabase.
- Tableau.
- Grafana.

Design reliable data pipelines with validation, lineage, observability, retry mechanisms and idempotency.

Do not introduce a data warehouse or streaming platform without a genuine business requirement.

## 12.7 AI, Machine Learning & Generative AI

Preferred ecosystem:

- Python.
- PyTorch.
- TensorFlow / Keras.
- scikit-learn.
- Hugging Face Transformers.
- XGBoost.
- MLflow.
- LangChain / LlamaIndex where justified.
- Vector databases: pgvector, Qdrant, Weaviate.
- Model serving: FastAPI, KServe, BentoML.

Apply appropriate practices for:
- Model training and evaluation.
- Data preparation.
- Feature engineering.
- Model versioning.
- Model monitoring.
- Model deployment.
- Explainability.
- Responsible AI.
- Data privacy and security.

Use traditional software engineering when AI is unnecessary.

## 12.8 API & Integration Standards

Use established standards:

- REST.
- OpenAPI / Swagger.
- GraphQL when justified.
- gRPC for suitable service-to-service communication.
- OAuth 2.0.
- OpenID Connect.
- JWT where appropriate.
- Webhooks.
- AsyncAPI for event-driven interfaces.

Implement API versioning, validation, authentication, authorisation, rate limiting, idempotency and consistent error responses.

## 12.9 Messaging & Event-Driven Architecture

Supported technologies:

- Apache Kafka.
- RabbitMQ.
- Redis Streams.
- AWS SQS / SNS.
- Azure Service Bus.
- Google Pub/Sub.

Apply:
- Event-driven design.
- Outbox pattern.
- Retry and dead-letter handling.
- Idempotent consumers.
- Event schema versioning.
- Observability and tracing.

Select messaging infrastructure according to actual delivery, ordering, throughput and reliability requirements.

## 12.10 DevOps, Cloud & Infrastructure

### Containerisation
- Docker.
- Docker Compose.
- Kubernetes.
- Helm.

### Infrastructure as Code
- Terraform.
- OpenTofu.
- Ansible.
- Pulumi.

### Cloud platforms
- AWS.
- Microsoft Azure.
- Google Cloud Platform.
- Oracle Cloud Infrastructure.

Select cloud services according to requirements, cost, availability and organisational constraints.

### CI/CD
- GitHub Actions.
- GitLab CI/CD.
- Jenkins.
- Azure DevOps.

### Git and source management
- Git.
- GitHub.
- GitLab.
- Bitbucket.

## 12.11 Security Engineering

Apply OWASP standards and security best practices.

Use:
- OWASP ASVS.
- OWASP Top 10.
- OWASP API Security Top 10.
- SAST and DAST.
- Dependency vulnerability scanning.
- Container image scanning.
- Secret scanning.
- Software composition analysis.
- SBOM generation.

Supported tools:
- SonarQube.
- Semgrep.
- Bandit.
- Ruff security-compatible checks.
- Trivy.
- Checkov.
- Gitleaks.
- OWASP ZAP.
- Snyk where available.

Never expose credentials, tokens, passwords or private keys in source code or logs.

## 12.12 Quality Engineering

Use appropriate automated testing tools.

### Backend
- Pytest.
- JUnit 5.
- Mockito.
- Testcontainers.
- Postman / Newman.
- REST Assured.

### Frontend
- Vitest.
- Jest.
- Playwright.
- Cypress.

### Performance
- k6.
- JMeter.
- Locust.
- Gatling.

### Quality and coverage
- SonarQube.
- Coverage.py.
- JaCoCo.
- ESLint.
- Ruff.
- mypy.

Implement unit, integration, API, contract, end-to-end, performance and security tests according to project risk.

## 12.13 Observability & Logging

Implement centralised, structured logging and monitoring.

Preferred standards and tools:

- Python logging / structlog.
- SLF4J / Logback.
- OpenTelemetry.
- Prometheus.
- Grafana.
- Loki.
- ELK / OpenSearch.
- Jaeger / Tempo.

Every application should provide, where appropriate:

- Structured application logs.
- Correlation and trace IDs.
- Metrics.
- Distributed tracing.
- Health and readiness checks.
- Error monitoring.
- Alerting.
- Audit logging.

Never rely exclusively on console output or temporary conversation history for operational records.

## 12.14 Documentation & Developer Experience

Use:

- Markdown.
- Mermaid diagrams.
- OpenAPI.
- MkDocs.
- Sphinx for Python documentation.
- Javadoc.
- ADRs.
- Architecture diagrams.
- Docker-based development environments.

Every project must include clear setup, configuration, build, test, run and deployment instructions.

## 12.15 Technology Stack Decision Process

Before implementation:

1. Analyse the business and technical requirements.
2. Identify the required application components.
3. Evaluate suitable technologies.
4. Compare alternatives where meaningful.
5. Assess licensing, community support and compatibility.
6. Assess security, scalability and operational costs.
7. Select a consistent technology stack.
8. Document the decisions in `documentation/architecture/TECH_STACK.md`.
9. Record important decisions in `execution/DECISIONS.md`.

Create a technology compatibility matrix covering framework versions, runtime versions, database versions, dependencies and infrastructure.

Use stable, supported releases. Verify current versions and compatibility before locking dependencies.

## 12.16 Technology Stack Restrictions

- Do not use deprecated frameworks or unsupported runtime versions.
- Do not use arbitrary framework versions.
- Do not introduce unnecessary microservices.
- Do not introduce unnecessary databases.
- Do not duplicate functionality across multiple frameworks.
- Do not use AI/ML when conventional programming is sufficient.
- Do not use Kubernetes for small deployments without justification.
- Do not hardcode environment-specific configuration.
- Do not ignore licensing or security considerations.
- Do not upgrade dependencies blindly.

The final technology stack must be justified, documented, reproducible and suitable for production deployment.

## 12.17 Python Engineering Standards

Whenever Python is selected:

- Use a supported stable Python 3 release.
- Use type hints throughout application code.
- Follow PEP 8 and PEP 257.
- Use `pyproject.toml` for project configuration.
- Use a reproducible dependency lock file.
- Separate application, domain, infrastructure and interface layers where appropriate.
- Use dependency injection where beneficial.
- Use Pydantic for external input validation where suitable.
- Use environment-based configuration.
- Use structured logging.
- Use explicit exception handling.
- Implement automated tests with pytest.
- Include database migrations.
- Use asynchronous processing only when beneficial.
- Avoid blocking operations in asynchronous endpoints.
- Use Ruff for linting and formatting.
- Use mypy or Pyright where appropriate.
- Include Docker-based execution.
- Include health checks and production server configuration.
- Provide a README with complete setup and deployment instructions.

A Python project must be maintainable, testable, secure and independently deployable.