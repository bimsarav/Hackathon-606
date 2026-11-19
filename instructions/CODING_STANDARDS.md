# Coding Standards
- Java: package by feature (`<base>.<service>.<feature>`); layers controller → service → repository; DTOs (Java records) at the API boundary, never JPA entities; constructor injection; no field injection.
- Validation with Jakarta Bean Validation on every request DTO; business rule violations raise typed exceptions mapped centrally (`@RestControllerAdvice`) to problem+json.
- No business logic in controllers or Kafka listeners; they delegate to services.
- Logging via SLF4J with structured fields; never log secrets, tokens or personal free text.
- Format and lint: Spotless (google-java-format) for Java; ESLint + Prettier for TypeScript. CI fails on violations.
- React: function components and hooks, typed props, no `dangerouslySetInnerHTML`, accessible components (labels, roles, keyboard support).
- Tests sit next to the module (`src/test/java`), named `<Class>Test` (unit) and `<Class>IT` (integration).
