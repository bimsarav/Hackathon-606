-- directory-service demo seed: organisation, users (demo password), roles (mapped by name), teams, services.
-- Every seeded user gets the demo password "Demo-Passw0rd1" (bcrypt, generated here). DEMO ONLY.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
\set pw '\'Demo-Passw0rd1\''
SELECT format('INSERT INTO companies (company_id, name, code) VALUES (%s, %L, %L);', company_id, name, code) FROM esmp.companies ORDER BY 1;
SELECT format('INSERT INTO offices (office_id, company_id, name, city, country, timezone) VALUES (%s, %s, %L, %L, %L, %L);',
              office_id, company_id, name, city, country, timezone) FROM esmp.offices ORDER BY 1;
SELECT format('INSERT INTO departments (department_id, company_id, name, cost_centre) VALUES (%s, %s, %L, %L);',
              department_id, company_id, name, cost_centre) FROM esmp.departments ORDER BY 1;
WITH h AS (SELECT crypt(:pw, gen_salt('bf', 12)) AS hash)
SELECT format('INSERT INTO users (user_id, company_id, employee_no, first_name, last_name, email, office_id, department_id, employment_status, password_hash, created_at) VALUES (%s, %s, %L, %L, %L, %L, %s, %s, %L, %L, %L);',
              u.user_id, coalesce(o.company_id, d.company_id, 1), u.employee_no, u.first_name, u.last_name, u.email,
              coalesce(u.office_id::text, 'NULL'), coalesce(u.department_id::text, 'NULL'), u.employment_status, h.hash, u.created_at)
FROM esmp.users u CROSS JOIN h LEFT JOIN esmp.offices o USING (office_id) LEFT JOIN esmp.departments d USING (department_id) ORDER BY 1;
-- Managers are set after all users exist (self-reference)
SELECT format('UPDATE users SET manager_id = %s WHERE user_id = %s;', manager_id, user_id) FROM esmp.users WHERE manager_id IS NOT NULL ORDER BY user_id;
SELECT format('INSERT INTO user_roles (user_id, role_id) SELECT %s, role_id FROM roles WHERE role_name = %L;', ur.user_id, r.role_name)
FROM esmp.user_roles ur JOIN esmp.roles r USING (role_id) ORDER BY 1;
SELECT format('INSERT INTO teams (team_id, company_id, name, support_level, manager_user_id, is_active) VALUES (%s, 1, %L, %s, %s, %L);',
              team_id, name, support_level, coalesce(manager_user_id::text, 'NULL'), is_active) FROM esmp.teams ORDER BY 1;
SELECT format('INSERT INTO team_members (team_id, user_id, joined_at) VALUES (%s, %s, %L);', team_id, user_id, joined_at)
FROM esmp.team_members ORDER BY team_id, user_id;
SELECT format('INSERT INTO service_categories (category_id, name) VALUES (%s, %L);', category_id, name) FROM esmp.service_categories ORDER BY 1;
SELECT format('INSERT INTO services (service_id, company_id, category_id, name, description, owning_team_id, is_active) VALUES (%s, 1, %s, %L, %L, %s, %L);',
              service_id, coalesce(category_id::text, 'NULL'), name, description, coalesce(owning_team_id::text, 'NULL'), is_active)
FROM esmp.services ORDER BY 1;
SELECT format('SELECT setval(pg_get_serial_sequence(%L, %L), (SELECT max(%I) FROM %I));', t, c, c, t)
FROM (VALUES ('companies','company_id'),('offices','office_id'),('departments','department_id'),('users','user_id'),
             ('teams','team_id'),('service_categories','category_id'),('services','service_id')) v(t, c);
