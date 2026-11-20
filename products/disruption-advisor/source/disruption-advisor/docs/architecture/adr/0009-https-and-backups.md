# ADR-0009: HTTPS with Caddy on an sslip.io hostname; nightly PostgreSQL dumps with a restore test

- **Status:** Accepted (2026-11-21, phase 2 approved by the user)
- **Context:** The MVP runs over plain HTTP on :8888, and PostgreSQL (scenarios, decisions, audit) has no backup. No domain name or off-site storage was supplied. Ports 80 and 443 are open on the server and in the cloud firewall.
- **Decision:**
  - **TLS:** a Caddy 2 container terminates TLS for `92-5-154-198.sslip.io` (the hostname is configurable: `PUBLIC_HOSTNAME`). Caddy obtains and renews certificates automatically (Let's Encrypt, ZeroSSL as fallback), redirects HTTP to HTTPS and adds HSTS. It is enabled through a Compose profile, so a laptop run needs no certificate. `:8888` stays for existing links.
  - **Backups:** a `backup` container runs `pg_dump -Fc` every night at 02:00 UTC into a host folder and keeps 14 days. `scripts/restore-test.sh` restores the newest dump into a throw-away PostgreSQL and compares row counts with the live database.
- **Alternatives considered:**
  - **Certificates through nginx + certbot:** more moving parts (renewal cron, reloads).
  - **Self-signed certificate:** browser warnings; not acceptable for users.
  - **Host cron for backups:** works, but lives outside the Compose project and its restart and logging rules.
- **Consequences:**
  - The demo gets a trusted HTTPS URL without buying a domain. sslip.io is a public service: if it or the certificate authority's rate limit fails, `:8888` still works.
  - Backups protect against data loss on the database, not against loss of the server. Off-site copies are a phase 4 item.
