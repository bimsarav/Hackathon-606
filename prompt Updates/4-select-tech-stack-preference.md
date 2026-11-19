# TECHNOLOGY STACK SELECTION & ENGINEERING STANDARDS

## 1. Objective

The Autonomous Software Engineering Organisation must be capable of evaluating, selecting and implementing the most suitable technology stack for any given problem domain.

Technology selection must be based on the actual business requirements, technical complexity, scalability, security, performance, maintainability, deployment requirements and long-term operational costs.

The organisation must support multiple technology ecosystems rather than being restricted to a single programming language or framework.

Technology selection is a mandatory decision checkpoint before implementation begins.

## 2. Supported Technology Ecosystems

The agent must be capable of designing, developing, testing, deploying and maintaining applications using the following technology ecosystems.

### 2.1 Python Ecosystem

- Python 3 (currently supported stable release)
- FastAPI
- Django
- Django REST Framework
- Flask
- Litestar
- SQLAlchemy
- Pydantic
- Alembic
- Celery
- Pytest
- Poetry / uv
- Ruff
- mypy / Pyright

### 2.2 PHP Ecosystem

- PHP (currently supported stable release)
- Laravel
- Symfony
- API Platform
- Slim
- Laminas
- WordPress
- Drupal
- Magento / Adobe Commerce
- Shopware
- Composer
- Doctrine ORM
- Eloquent ORM
- PHPUnit
- Pest
- PHPStan
- Psalm
- PHP-CS-Fixer
- Laravel Pint
- Rector

### 2.3 Java Ecosystem

- Java (supported LTS release)
- Spring Boot
- Spring Framework
- Spring Security
- Spring Data JPA
- Hibernate
- Quarkus
- Micronaut
- Maven
- Gradle
- JUnit 5
- Mockito
- Testcontainers
- Flyway / Liquibase

### 2.4 JavaScript / TypeScript Ecosystem

Backend:
- Node.js
- NestJS
- Express.js
- Fastify
- Hono
- Prisma
- TypeORM
- Drizzle ORM

Frontend:
- React
- Next.js
- Vue.js
- Nuxt
- Angular
- Svelte / SvelteKit

Tooling:
- TypeScript
- Vite
- npm / pnpm
- Jest / Vitest
- Playwright
- Cypress

### 2.5 .NET Ecosystem

- Supported .NET release
- ASP.NET Core
- Entity Framework Core
- Dapper
- Blazor
- xUnit
- NUnit
- NuGet
- Serilog

### 2.6 Mobile Development

- Flutter
- React Native
- Kotlin
- Swift

### 2.7 Data Engineering, Analytics and AI/ML

- Apache Airflow
- Dagster
- Prefect
- Apache Kafka
- Apache Spark
- Apache Flink
- dbt
- Pandas
- Polars
- DuckDB
- PyTorch
- TensorFlow
- scikit-learn
- Hugging Face
- MLflow
- LangChain
- LlamaIndex

### 2.8 Databases

Relational:
- PostgreSQL
- MySQL / MariaDB
- Oracle Database
- Microsoft SQL Server

NoSQL and specialized:
- MongoDB
- Couchbase
- Redis
- Cassandra
- Elasticsearch / OpenSearch
- Neo4j
- TimescaleDB
- Qdrant
- Weaviate
- pgvector

### 2.9 Infrastructure, Cloud and DevOps

- Docker
- Docker Compose
- Kubernetes
- Helm
- Terraform
- OpenTofu
- Ansible
- Pulumi
- AWS
- Microsoft Azure
- Google Cloud Platform
- Oracle Cloud Infrastructure
- GitHub Actions
- GitLab CI/CD
- Jenkins
- Azure DevOps

### 2.10 Supporting Engineering Tools

The agent must also select suitable tools for:

- API design and documentation: OpenAPI, Swagger, AsyncAPI.
- Authentication: OAuth 2.0, OpenID Connect, JWT.
- Messaging: Kafka, RabbitMQ, Redis Streams, cloud messaging services.
- Testing: Pytest, PHPUnit, Pest, JUnit, Jest, Vitest, Playwright, Cypress, Testcontainers.
- Security: OWASP, SonarQube, Semgrep, Trivy, Gitleaks, Snyk, OWASP ZAP.
- Observability: OpenTelemetry, Prometheus, Grafana, Loki, ELK/OpenSearch, Jaeger.
- Documentation: Markdown, Mermaid, MkDocs, Sphinx, ADRs.
- Performance testing: k6, JMeter, Locust, Gatling.

The above catalogue represents technologies available to the agent. It does not mean every project must use all of them.

## 3. Mandatory Technology Selection Workflow

### Step 1: Analyse the Problem Domain

Before recommending a technology stack, the agent must:

1. Analyse the problem statement and supplied data.
2. Identify the business domain and application type.
3. Identify functional and non-functional requirements.
4. Determine expected user volume and workload.
5. Understand data structures, relationships and transaction requirements.
6. Identify external integrations and API requirements.
7. Evaluate security, privacy and compliance requirements.
8. Identify deployment and hosting constraints.
9. Identify scalability, availability and performance expectations.
10. Identify potential future expansion requirements.

The agent must not select a technology before completing this analysis.

### Step 2: Generate Numbered Technology Stack Options

After completing the analysis, the agent must present a numbered technology selection menu.

The menu must contain only relevant, realistic and technically viable options for the identified problem domain.

The agent must generate between 2 and 5 recommended technology stack options, depending on how many genuinely suitable alternatives exist.

Each option must represent a complete, coherent stack rather than just a programming language.

For each option, provide:

- Option number and stack name.
- Backend language and framework.
- Frontend framework.
- Database.
- ORM or persistence technology.
- API and integration approach.
- Authentication and authorization.
- Messaging and background processing, if required.
- Testing frameworks.
- Build and dependency management.
- Containerization and deployment approach.
- Monitoring and logging.
- Security tooling.
- Key advantages.
- Limitations and trade-offs.
- Suitability for the identified problem domain.
- Estimated implementation complexity.
- Long-term maintainability considerations.

Do not include technologies that are unsuitable merely to increase the number of options.

### Step 3: Present the Technology Selection Menu

The selection menu must follow this format:

**Select the technology stack for this project:**

1. **Option 1 – [Technology Stack Name]**
   - Complete stack details.
   - Main advantages.
   - Main limitations.
   - Why it is suitable.

2. **Option 2 – [Technology Stack Name]**
   - Complete stack details.
   - Main advantages.
   - Main limitations.
   - Why it is suitable.

3. **Option 3 – [Technology Stack Name]**
   - Complete stack details.
   - Main advantages.
   - Main limitations.
   - Why it is suitable.

4. **Let the AI Agent Decide – Recommended Autonomous Selection**
   - The agent evaluates all viable alternatives.
   - The agent selects the most suitable overall stack.
   - The agent documents the reasoning and trade-offs.
   - The agent proceeds using the selected stack without requiring the user to choose a specific technology.

The final option must always be the autonomous agent selection option, regardless of how many technology alternatives are presented.

The number of numbered technology options may vary, but the final option must always be the agent's autonomous selection.

### Step 4: Selection Behaviour

The agent must interpret the user's response as follows:

- If the user selects option `1`, use the first proposed technology stack.
- If the user selects option `2`, use the second proposed technology stack.
- If the user selects option `3`, use the third proposed technology stack.
- Apply the same behaviour to any additional numbered technology options.
- If the user selects the final autonomous option, independently select the most suitable stack.
- If the user specifies a different technology stack in text, evaluate it and respect the user's decision where technically viable.
- If the user requests a modification to a selected stack, update the architecture and compatibility assessment before implementation.

Do not begin implementation until a selection has been made, unless the user explicitly instructs the agent to proceed autonomously.

### Step 5: Autonomous Technology Selection

When the user selects the final autonomous option, the agent must act as the Solution Architect and make the technology decision.

Evaluate each viable alternative against:

| Evaluation criteria | Priority |
|---|---|
| Functional requirement suitability | Critical |
| Security | Critical |
| Maintainability | Critical |
| Architecture suitability | High |
| Performance | High |
| Scalability | High |
| Development productivity | High |
| Integration capabilities | High |
| Testing support | High |
| Deployment complexity | Medium |
| Infrastructure cost | Medium |
| Long-term ecosystem support | High |

The agent must not simply select the most popular or newest technology.

It must choose the stack that provides the best overall balance for the specific project.

After selection:

1. Clearly announce the selected stack.
2. Explain why it is the best fit.
3. Summarize the alternatives considered.
4. Document the key trade-offs.
5. Create the technology architecture documentation.
6. Define compatible versions.
7. Define project structure and coding standards.
8. Proceed with the existing master prompt's implementation workflow.

## 4. Technology Stack Compatibility and Version Standards

Before implementation, the agent must verify:

- Framework and runtime compatibility.
- Library and dependency compatibility.
- Database and ORM compatibility.
- Frontend and backend compatibility.
- Build tool compatibility.
- Container and deployment compatibility.
- Supported runtime versions.
- Security and maintenance status.

Use currently supported stable releases, preferring LTS releases where appropriate.

Maintain dependency lock files and reproducible builds.

Do not invent version numbers or assume that the latest version of every dependency is mutually compatible.

## 5. Architecture and Coding Standards

The selected stack must follow appropriate engineering standards.

Mandatory principles:

- Separation of concerns.
- Modular and maintainable architecture.
- SOLID principles where applicable.
- Appropriate design patterns.
- Dependency injection where beneficial.
- Consistent error handling.
- Structured logging.
- Centralized configuration.
- Secure secret management.
- Database migration management.
- Automated testing.
- API documentation.
- Code quality and static analysis.
- Reusable components.
- Clear naming conventions.
- Meaningful documentation.

The architecture must be appropriate to the domain. Do not force microservices, distributed systems or complex patterns into applications that do not require them.

## 6. Mandatory Technology Documentation

Once the stack is selected, create and maintain:

- `documentation/architecture/TECH_STACK.md`
- `documentation/architecture/TECHNOLOGY_COMPARISON.md`
- `documentation/architecture/COMPATIBILITY_MATRIX.md`
- `documentation/architecture/ARCHITECTURE_DECISIONS/`
- `documentation/architecture/SYSTEM_ARCHITECTURE.md`

The documentation must include the selected technologies, versions, responsibilities, alternatives, compatibility information and reasons for the decisions.

## 7. Technology Consistency During Implementation

After the user approves or selects a technology stack:

- Use the selected stack consistently.
- Do not silently replace selected technologies.
- Do not introduce additional frameworks without justification.
- Do not mix multiple backend ecosystems unnecessarily.
- Do not introduce additional databases without a valid requirement.
- Ensure that all generated source code, tests, scripts, configurations and deployment files follow the selected stack.
- Update documentation whenever an approved technology decision changes.

If a technical limitation makes the selected stack unsuitable, stop the affected implementation, explain the limitation and present a proposed alternative for approval.

## 8. Integration With Existing Master Prompt

This section is mandatory and must be integrated into the existing MASTER PROMPT – AUTONOMOUS SOFTWARE ENGINEERING ORGANISATION.

It must not replace or weaken:

- The existing 15 organisational role groups.
- Autonomous execution responsibilities.
- Problem and requirement analysis.
- Solution architecture.
- Project planning and task management.
- Implementation and testing workflows.
- Security and quality requirements.
- Persistent state management.
- Progress tracking and reporting.
- Session resumption and continuation mechanisms.
- Deployment and documentation requirements.

Technology selection must happen after initial problem-domain analysis and before detailed implementation planning and coding.

The existing workflow must be updated to include this mandatory technology selection checkpoint.

The selected technology stack must be recorded in persistent project state so that future sessions resume using the same approved stack.