# Cloud Environment

Discovered on 2026-11-20 with read-only commands over SSH (no changes made). It follows MASTER_PROMPT §13.2. No secrets are stored here.

## Summary
| Item | Value | How verified |
|---|---|---|
| Provider | Oracle Cloud Infrastructure (OCI) | instance metadata service |
| Region / AD | eu-frankfurt-1, AD-1 | instance metadata |
| Shape | VM.Standard.E4.Flex (AMD, x86_64) | metadata, `uname -m` |
| CPU / RAM / swap | 8 vCPU / 62 GiB / 5 GiB | `nproc`, `free -h` |
| Disk | 78 GB root volume, 67 GB free (Docker data on `/`) | `df -h` |
| OS | Oracle Linux Server 10.2, kernel 6.12 UEK | `/etc/os-release` |
| Public IP / private IP | 92.5.154.198 / 172.31.76.23 | supplied; SSH works on the public IP |
| Hostname | hackathon22 | `hostname` |
| Access | SSH as `opc` with a key pair (key kept outside git); passwordless sudo | `sudo -n true` |
| Container runtime | Docker 29.10.0, Compose v5.8.0; service enabled and active at boot; `opc` is in the `docker` group | `docker --version`, `systemctl` |
| Docker storage | overlayfs, cgroup v2, Docker SELinux labelling off (bind mounts work without `:Z`) | `docker info` |
| SELinux (host) | Enforcing | `getenforce` |
| Host firewall | firewalld active; open: 22, 80, 443, 8080, 8888, 5432 (TCP) | `firewall-cmd --list-all` |
| Provider network rules | Supplied: only 22, 80, 443, 8080, 8888, 5432 are reachable from outside | provider notes; to be confirmed during deployment |
| Outbound internet | Docker Hub registry and GitHub reachable | `curl` |
| Time | UTC, NTP synchronised | `timedatectl` |
| Existing workload | none (0 containers, 0 images); system services only (sshd, rpcbind, pmcd/pmlogger) | `docker ps -a`, `ss -tlnp` |
| Domain / DNS | none supplied | — |
| TLS certificates | none supplied | — |
| Container registry, managed DB, object storage, secret manager | none supplied; not needed for this deployment | — |
| CI/CD service | GitHub (repository host); no runner on the server | — |

## Operating constraints (from the provider)
- The server can restart at any time and judges open the demo after the deadline, so every container must restart by itself (`restart: unless-stopped` + `systemctl enable docker`), checked with a reboot test.
- The demo link uses one of the open ports, for example `http://92.5.154.198:8080`.

## Fit for esm-hub
- 14 containers (11 Spring Boot JVMs incl. gateway, PostgreSQL, Kafka, Mailpit, nginx web). Measured locally (`docker stats`, idle demo load): about 7.1 GiB in total, so 62 GiB and 8 vCPU leave ample headroom. Risk: the JVM services sit at about 70–85% of their 768 MiB container limit; raise the limit on this server (memory is plentiful) to avoid OOM restarts under load.
- Same CPU architecture as the build machine (x86_64), so locally built and tested images run unchanged.
- PostgreSQL port 5432 is open on the host firewall but **is not published** by the stack (internal network only).
