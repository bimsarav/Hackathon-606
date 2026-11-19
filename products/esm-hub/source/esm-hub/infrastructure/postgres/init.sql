-- One database per service (database-per-service). Runs once on an empty PostgreSQL volume.
-- The application user is the POSTGRES_USER of the container (owner of all databases).
CREATE DATABASE esm_directory;
CREATE DATABASE esm_incident;
CREATE DATABASE esm_request;
CREATE DATABASE esm_change;
CREATE DATABASE esm_asset;
CREATE DATABASE esm_knowledge;
CREATE DATABASE esm_notification;
CREATE DATABASE esm_audit;
CREATE DATABASE esm_reporting;
