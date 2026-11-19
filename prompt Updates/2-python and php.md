# TECHNOLOGY STACK & ENGINEERING STANDARDS

## 1. Objective

The organisation must select, justify, implement and maintain a modern, secure, scalable and production-ready technology stack appropriate for the given problem domain.

The technology stack must be selected based on:

- Business domain and functional requirements.
- Application complexity and expected growth.
- Performance, scalability and availability requirements.
- Data volume, data relationships and processing requirements.
- Integration requirements and external dependencies.
- Security, compliance and regulatory requirements.
- Hosting environment and infrastructure constraints.
- Development and operational complexity.
- Team skills and long-term maintainability.
- Licensing, support lifecycle and total cost of ownership.

Do not select technologies simply because they are popular or familiar. Select the most appropriate technologies for the actual problem.

## 2. Technology Selection Principles

1. Prefer mature, actively maintained and production-proven technologies.
2. Prefer stable releases and supported Long-Term Support (LTS) versions where available.
3. Use the latest stable version compatible with the project's dependencies and deployment environment.
4. Prefer simplicity over unnecessary architectural complexity.
5. Avoid introducing multiple technologies that solve the same problem without a clear reason.
6. Do not introduce microservices, Kubernetes, distributed messaging or complex infrastructure unless justified by requirements.
7. Prefer well-supported frameworks and libraries with strong documentation and communities.
8. Consider developer productivity, testing, security and operational support.
9. Check framework and library compatibility before implementation.
10. Document the reasons for major technology choices.
11. Do not blindly upgrade dependencies or use deprecated frameworks.
12. Re-evaluate technology decisions when requirements materially change.

## 3. Backend Technology Standards

Evaluate the following ecosystems based on the problem domain.

### 3.1 Python

Preferred frameworks and tools:

- FastAPI – modern asynchronous APIs, microservices and AI/ML services.
- Django – full-featured web applications, enterprise systems and applications requiring built-in administration, authentication and ORM.
- Django REST Framework – REST APIs for Django applications.
- Flask – lightweight applications and smaller services.
- Litestar – modern typed APIs and service-oriented applications.
- Pydantic – data validation and settings management.
- SQLAlchemy – relational database ORM and SQL toolkit.
- Alembic – database schema migrations.
- Django ORM – database access for Django applications.
- Celery – distributed background processing.
- Dramatiq or RQ – background job processing.
- Uvicorn – ASGI application server.
- Gunicorn – production process management where appropriate.
- Pytest – testing.
- Poetry or uv – dependency and environment management.
- Ruff – linting and formatting.
- mypy or Pyright – static type checking.

Standards:

- Use Python 3 with a currently supported version.
- Follow PEP 8 and PEP 257.
- Use type hints consistently.
- Use `pyproject.toml` for project configuration.
- Maintain a dependency lock file.
- Separate application, domain, infrastructure and API responsibilities.
- Use dependency injection where it improves maintainability and testability.
- Use Pydantic for validation and structured configuration where appropriate.
- Use environment-based configuration and secure secret management.
- Use structured logging.
- Implement automated tests using Pytest.
- Implement database migrations.
- Use asynchronous programming only when it provides a genuine benefit.
- Include health checks, readiness checks and graceful shutdown handling.

### 3.2 PHP

Evaluate PHP when appropriate for web applications, enterprise portals, APIs, content-driven platforms, e-commerce systems, SaaS applications and business management solutions.

Preferred frameworks and tools:

**Application frameworks**

- Laravel – preferred general-purpose PHP framework for modern web applications, SaaS platforms, business applications and APIs.
- Symfony – enterprise applications, complex business domains, reusable components and long-lived applications requiring architectural flexibility.
- API Platform – API-first applications, REST and GraphQL APIs, particularly with Symfony.
- Slim – lightweight APIs and microservices.
- Laminas – modular enterprise applications and reusable components.
- CodeIgniter – lightweight applications where its simplicity is advantageous.

**PHP ecosystem**

- PHP – currently supported stable release.
- Composer – dependency management and autoloading.
- PHP-FIG standards – PSR recommendations and interoperability.
- PHPStan – static analysis.
- Psalm – static analysis and type checking.
- PHP-CS-Fixer – coding standards and formatting.
- Laravel Pint – Laravel-oriented code formatting.
- Rector – automated refactoring and PHP upgrades.
- PHPUnit – automated testing.
- Pest – expressive PHP testing.
- PHP_CodeSniffer – coding standard enforcement.
- Xdebug – debugging and code coverage.
- Laravel Octane – high-performance Laravel application serving when justified.
- RoadRunner or FrankenPHP – alternative application serving and performance options where appropriate.

**Database and persistence**

- Doctrine ORM – enterprise-oriented persistence, particularly with Symfony.
- Eloquent ORM – Laravel applications.
- Doctrine DBAL – database abstraction.
- Laravel migrations or Doctrine Migrations – schema management.
- PostgreSQL and MySQL/MariaDB – common relational database options.
- Redis – caching, queues and transient data where appropriate.

**PHP application standards**

- Use a currently supported PHP version.
- Follow PSR-12 and applicable PHP-FIG standards.
- Use strict typing where appropriate (`declare(strict_types=1)`).
- Use Composer for dependency management.
- Maintain `composer.lock` for reproducible builds.
- Use namespaces, interfaces, dependency injection and clear separation of concerns.
- Prefer framework-supported security, validation, routing and database mechanisms.
- Avoid business logic inside controllers.
- Separate domain logic from framework-specific infrastructure where appropriate.
- Use database migrations rather than manual production schema changes.
- Validate and sanitize external input.
- Use prepared statements and parameterized queries.
- Implement authentication, authorization and policy-based access control.
- Use secure password hashing and session management.
- Protect against CSRF, XSS, SQL injection, SSRF and insecure file uploads.
- Use queues for long-running background tasks where appropriate.
- Implement structured logging and centralized error handling.
- Use PHPUnit or Pest for automated testing.
- Enforce static analysis using PHPStan or Psalm.
- Use PHP-CS-Fixer, Pint or equivalent formatting tools.
- Provide production-ready configuration, health checks and deployment instructions.

**PHP framework selection guidance**

- Choose Laravel for rapid development of modern business applications, SaaS products, portals and APIs.
- Choose Symfony for complex enterprise applications, reusable components and highly customized architectures.
- Choose API Platform for API-first solutions where its capabilities provide a clear advantage.
- Choose Slim or another lightweight framework for small, focused services.
- Consider WordPress when the primary requirement is a content management platform or publishing website.
- Consider Magento/Adobe Commerce or Shopware for domain-specific e-commerce requirements.
- Do not introduce a CMS or e-commerce framework into a general business application without justification.

### 3.3 Java

Preferred frameworks and tools:

- Java – supported LTS release.
- Spring Boot – enterprise applications, APIs and microservices.
- Spring Framework – dependency injection and application infrastructure.
- Spring Security – authentication and authorization.
- Spring Data JPA – persistence abstraction.
- Hibernate – ORM.
- Spring Cloud – distributed system capabilities when justified.
- Quarkus – cloud-native Java applications.
- Micronaut – lightweight services and serverless applications.
- Maven or Gradle – build and dependency management.
- JUnit 5 – testing.
- Mockito – mocking.
- Testcontainers – integration testing.
- Flyway or Liquibase – database migrations.
- SLF4J and Logback – logging.

### 3.4 JavaScript and TypeScript Backend

Preferred frameworks and tools:

- Node.js – supported LTS release.
- TypeScript – preferred for larger and maintainable applications.
- NestJS – structured enterprise applications and APIs.
- Express.js – lightweight APIs.
- Fastify – high-performance APIs.
- Hono – lightweight services and edge runtimes where appropriate.
- Prisma or TypeORM – database access.
- Zod – runtime validation.
- Jest or Vitest – testing.
- npm, pnpm or Yarn – dependency management.

### 3.5 .NET

Preferred frameworks and tools:

- Supported .NET release.
- ASP.NET Core – web applications and APIs.
- Entity Framework Core – ORM.
- Dapper – lightweight data access.
- xUnit or NUnit – testing.
- NuGet – dependency management.
- Serilog – structured logging.

## 4. Frontend Engineering Standards

Preferred technologies:

- TypeScript – preferred for medium and large applications.
- React – modern component-based applications.
- Next.js – React applications requiring server rendering, routing or full-stack capabilities.
- Vue.js – component-based applications.
- Nuxt – Vue-based full-stack applications.
- Angular – structured enterprise frontend applications where its conventions are beneficial.
- Vite – frontend development and build tooling.
- Tailwind CSS – utility-first styling.
- Material UI – React component library.
- shadcn/ui – customizable component system.
- Ant Design – enterprise-oriented UI components.
- TanStack Query – server state management.
- Redux Toolkit – complex global state management.
- Zustand – lightweight state management.
- React Hook Form – form management.
- Zod – frontend validation.
- Playwright – end-to-end testing.
- Vitest or Jest – unit testing.

Standards:

- Use reusable components.
- Maintain consistent design systems.
- Follow responsive design principles.
- Implement accessibility using WCAG guidance.
- Separate presentation, business logic and data access.
- Implement loading, empty, error and success states.
- Use secure authentication and session handling.
- Avoid unnecessary client-side complexity.
- Maintain consistent API contracts with the backend.

## 5. Mobile Engineering Standards

Evaluate:

- Flutter – cross-platform applications.
- React Native – cross-platform applications.
- Kotlin – native Android applications.
- Swift – native iOS applications.

Select native or cross-platform development based on performance, device capabilities, user experience and business requirements.

## 6. Database and Data Persistence Standards

### Relational databases

Evaluate:

- PostgreSQL – preferred general-purpose relational database.
- MySQL or MariaDB – web and transactional applications.
- Microsoft SQL Server – Microsoft-oriented enterprise environments.
- Oracle Database – enterprise environments with existing Oracle dependencies or specific requirements.

### NoSQL and specialized databases

Evaluate:

- MongoDB – document-oriented data.
- Couchbase – distributed document and key-value workloads.
- Redis – caching, queues and fast transient data.
- Cassandra – high-volume distributed write workloads.
- Elasticsearch or OpenSearch – search and log analytics.
- Neo4j – graph-oriented domains.
- TimescaleDB – time-series workloads.
- pgvector, Qdrant or Weaviate – vector search and retrieval applications.

### Database engineering standards

- Select the database based on data relationships, consistency, query patterns and scale.
- Prefer relational databases for transactional business systems with complex relationships.
- Define primary keys, foreign keys, constraints and indexes.
- Normalize transactional data where appropriate.
- Avoid unnecessary denormalization.
- Define transaction boundaries and isolation requirements.
- Use connection pooling.
- Use migrations for schema changes.
- Plan backup, recovery and retention.
- Define indexing and query optimization strategies.
- Avoid storing sensitive information unnecessarily.
- Document data ownership, retention and deletion policies.

## 7. Data Engineering and Analytics

Evaluate:

**Data ingestion and orchestration**

- Apache Airflow.
- Dagster.
- Prefect.
- Apache Kafka.
- Apache NiFi.
- Debezium.

**Processing**

- Apache Spark.
- Apache Flink.
- Pandas.
- Polars.
- DuckDB.

**Transformation and modeling**

- dbt.
- SQL-based transformation pipelines.
- Data quality validation frameworks.

**Data platforms**

- Snowflake.
- Google BigQuery.
- Amazon Redshift.
- Databricks.
- PostgreSQL for smaller analytical workloads.

**BI and reporting**

- Power BI.
- Tableau.
- Apache Superset.
- Metabase.
- Grafana.

Choose technologies based on data volume, latency, governance, processing requirements and reporting needs.

## 8. AI, Machine Learning and Intelligent Applications

Evaluate:

- Python as the primary AI/ML development ecosystem.
- PyTorch.
- TensorFlow/Keras.
- scikit-learn.
- Hugging Face.
- XGBoost.
- MLflow.
- LangChain or LlamaIndex where justified.
- pgvector, Qdrant or Weaviate for vector retrieval.
- FastAPI for model-serving APIs.
- KServe or BentoML for model deployment where appropriate.

Standards:

- Define the actual business problem before selecting an AI solution.
- Prefer conventional deterministic solutions when they are sufficient.
- Evaluate data availability and quality.
- Establish model evaluation criteria.
- Address privacy, security, bias and explainability.
- Version datasets, models and configurations.
- Monitor model quality and drift.
- Avoid introducing LLMs or vector databases without a clear use case.

## 9. API and Integration Standards

Preferred technologies and standards:

- REST APIs using OpenAPI.
- GraphQL when flexible data querying is justified.
- gRPC for suitable service-to-service communication.
- OAuth 2.0 and OpenID Connect.
- JWT where appropriate.
- Webhooks for event notifications.
- AsyncAPI for event-driven API documentation.
- JSON as the default API payload format unless another format is justified.

Standards:

- Define API versioning.
- Maintain consistent error responses.
- Validate all external input.
- Apply authentication and authorization.
- Define pagination, filtering and sorting conventions.
- Implement rate limiting where appropriate.
- Document APIs.
- Ensure backward compatibility where required.
- Define timeout, retry and idempotency behavior.

## 10. Messaging and Background Processing

Evaluate:

- Apache Kafka.
- RabbitMQ.
- Redis Streams.
- AWS SQS/SNS.
- Azure Service Bus.
- Google Cloud Pub/Sub.

Use messaging when asynchronous processing, event-driven integration or decoupling is required.

Implement:

- Retry policies.
- Dead-letter queues.
- Idempotent consumers.
- Event schema versioning.
- Message correlation identifiers.
- Outbox pattern where transactional event publishing is required.
- Monitoring and failure recovery.

Do not introduce a message broker for simple synchronous workflows without justification.

## 11. DevOps, Infrastructure and Cloud

### Containerization and orchestration

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

### CI/CD

- GitHub Actions.
- GitLab CI/CD.
- Jenkins.
- Azure DevOps.

### Standards

- Maintain reproducible build processes.
- Automate tests and quality checks.
- Separate development, testing, staging and production environments.
- Externalize configuration and secrets.
- Use immutable deployment artifacts where practical.
- Implement rollback strategies.
- Apply least-privilege access.
- Document deployment and recovery procedures.
- Avoid cloud-provider-specific dependencies unless justified.

## 12. Security Engineering Standards

Follow:

- OWASP Top 10.
- OWASP API Security Top 10.
- OWASP ASVS.
- Secure Software Development Lifecycle principles.

Evaluate:

- SonarQube.
- Semgrep.
- Bandit.
- PHPStan and Psalm.
- Ruff.
- Trivy.
- Checkov.
- Gitleaks.
- OWASP ZAP.
- Snyk.

Implement:

- Authentication and authorization.
- Role-based or attribute-based access control as appropriate.
- Secure secret management.
- Input validation and output encoding.
- Encryption in transit and at rest where required.
- Dependency and container vulnerability scanning.
- Audit logging.
- Security headers.
- Rate limiting and abuse protection.
- Secure file handling.
- Data privacy and retention controls.

Security must be considered during architecture, implementation, testing and deployment.

## 13. Quality Engineering and Testing

Select tools based on the chosen technology stack.

| Area | Preferred tools |
|---|---|
| Python unit/integration tests | Pytest |
| PHP unit/integration tests | PHPUnit, Pest |
| Java tests | JUnit 5, Mockito |
| JavaScript/TypeScript tests | Vitest, Jest |
| .NET tests | xUnit, NUnit |
| API testing | Postman, Newman, REST Assured |
| Browser testing | Playwright, Cypress |
| Database integration | Testcontainers |
| Performance testing | k6, JMeter, Locust, Gatling |
| Code coverage | Coverage.py, JaCoCo, PHPUnit coverage |
| Static analysis | SonarQube, PHPStan, Psalm, mypy, Ruff |

Mandatory testing considerations:

- Unit testing.
- Integration testing.
- API testing.
- End-to-end testing.
- Regression testing.
- Security testing.
- Performance testing where required.
- Database migration testing.
- Failure and recovery testing.

Do not consider an implementation complete merely because it compiles or starts successfully.

## 14. Observability and Operational Tooling

Evaluate:

- OpenTelemetry.
- Prometheus.
- Grafana.
- Loki.
- ELK Stack or OpenSearch.
- Jaeger or Grafana Tempo.
- Python structlog or standard logging.
- PHP Monolog.
- Java SLF4J and Logback.
- Serilog for .NET.

Implement:

- Structured application logs.
- Centralized error reporting.
- Metrics.
- Distributed tracing where appropriate.
- Health and readiness endpoints.
- Correlation and request identifiers.
- Monitoring and alerting.
- Operational dashboards.

Avoid logging passwords, tokens, credentials or sensitive personal information.

## 15. Documentation and Architecture Standards

Use:

- Markdown.
- Mermaid diagrams.
- OpenAPI.
- AsyncAPI.
- MkDocs.
- Sphinx.
- Javadoc.
- Architecture Decision Records (ADRs).

Maintain:

- System architecture.
- Technology stack documentation.
- Architecture decision records.
- Database schema and ERD.
- API documentation.
- Deployment architecture.
- Security architecture.
- Developer setup instructions.
- Operational runbooks.

## 16. Mandatory Technology Selection Process

Before implementing the solution, the organisation MUST:

1. Analyse the problem domain and business requirements.
2. Identify application types and system boundaries.
3. Identify functional and non-functional requirements.
4. Determine the expected data model and data volume.
5. Identify integration and communication requirements.
6. Identify hosting and deployment constraints.
7. Evaluate appropriate backend frameworks.
8. Evaluate appropriate frontend and mobile technologies.
9. Select database and persistence technologies.
10. Select testing, security and observability tools.
11. Check compatibility between selected technologies.
12. Compare viable alternatives.
13. Document the final selection and reasons.
14. Obtain approval where the existing project workflow requires it.

Create and maintain these files:

- `documentation/architecture/TECH_STACK.md`
- `documentation/architecture/TECHNOLOGY_COMPARISON.md`
- `documentation/architecture/COMPATIBILITY_MATRIX.md`
- `documentation/architecture/ARCHITECTURE_DECISIONS/`

The compatibility matrix must include:

- Technology and framework name.
- Selected version.
- Supported runtime version.
- Dependency compatibility.
- Database compatibility.
- Build and deployment requirements.
- Support lifecycle.
- Known limitations.

## 17. Technology Selection Rules Based on Problem Domain

The organisation must not automatically select the same stack for every project.

Examples:

| Problem domain | Technologies to evaluate |
|---|---|
| Enterprise business management system | Java Spring Boot, .NET, Laravel, Symfony, Django |
| SaaS platform | Laravel, Symfony, Django, FastAPI, Spring Boot, NestJS |
| API-first platform | FastAPI, Django REST Framework, Symfony/API Platform, Spring Boot, NestJS |
| E-commerce | Laravel, Symfony, Magento/Adobe Commerce, Shopware, Shopify integrations |
| Content management | WordPress, Drupal, Laravel, Symfony |
| AI/ML platform | Python, FastAPI, PyTorch, TensorFlow |
| Data processing platform | Python, Spark, Kafka, Airflow, Dagster |
| Real-time platform | FastAPI, NestJS, Spring Boot, Kafka, WebSockets |
| Financial or transaction-heavy system | Java Spring Boot, .NET, PostgreSQL, Oracle |
| Lightweight internal application | Laravel, Django, FastAPI, ASP.NET Core |
| Mobile-first platform | Flutter or React Native with an appropriate backend |
| Enterprise integration platform | Spring Boot, .NET, Symfony, Kafka, RabbitMQ |

These are evaluation starting points, not mandatory selections.

## 18. Project-Specific Technology Architecture

For every new project:

- Select one primary backend technology unless multiple runtimes are justified.
- Select one primary frontend framework unless multiple applications require different frameworks.
- Select the appropriate database based on the data model.
- Select the minimum required infrastructure components.
- Select testing tools that match the implementation stack.
- Define dependency versions and compatibility.
- Document why alternatives were rejected.
- Keep the architecture consistent across the project.

If different technologies are required for separate components, document their responsibilities and integration contracts.

## 19. Technology Restrictions

The organisation MUST NOT:

- Use deprecated or unsupported frameworks.
- Introduce technologies without a clear business or technical reason.
- Mix frameworks unnecessarily.
- Introduce multiple ORMs without justification.
- Introduce multiple databases without justification.
- Use unstable dependencies in production without explicit approval.
- Hardcode credentials or environment-specific configuration.
- Ignore dependency vulnerabilities.
- Upgrade major versions without compatibility assessment.
- Use outdated tutorials or code examples without verifying compatibility.
- Select microservices solely because they are considered modern.
- Introduce Kubernetes when simpler deployment is sufficient.
- Introduce AI/ML when conventional software logic solves the problem more reliably.

## 20. Technology Stack Review and Maintenance

Throughout the project, the organisation must:

- Verify framework and library support status.
- Review dependency vulnerabilities.
- Monitor security advisories.
- Maintain dependency lock files.
- Evaluate upgrade requirements.
- Avoid unnecessary technology migrations.
- Update architecture documentation when decisions change.
- Record technology changes in Architecture Decision Records.
- Keep the implementation consistent with the approved stack.

The organisation must prioritize production stability, maintainability, security and business value over adopting the newest technology.