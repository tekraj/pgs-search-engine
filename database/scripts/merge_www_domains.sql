-- One-off cleanup: `domains` rows registered with a leading "www." (by the ETL, before
-- BronzeRepository learned to strip it). A website is stored without "www.".
--   psql -v ON_ERROR_STOP=1 -U <owner> -d pgs -f scripts/merge_www_domains.sql
-- For each www row: if the bare row exists, everything pointing at the www row moves to it and
-- the www row is deleted; if not, the www row is renamed. Runs in one transaction.
BEGIN;

CREATE TEMP TABLE www_dup ON COMMIT DROP AS
SELECT w.id AS www_id, b.id AS bare_id
FROM domains w JOIN domains b ON b.domain = substr(w.domain, 5)
WHERE w.domain LIKE 'www.%';

UPDATE crawled_documents t SET domain_id = d.bare_id FROM www_dup d WHERE t.domain_id = d.www_id;
UPDATE pages             t SET domain_id = d.bare_id FROM www_dup d WHERE t.domain_id = d.www_id;
UPDATE quarantined_files t SET domain_id = d.bare_id FROM www_dup d WHERE t.domain_id = d.www_id;
UPDATE error_logs        t SET domain_id = d.bare_id FROM www_dup d WHERE t.domain_id = d.www_id;
DELETE FROM domain_stats WHERE domain_id IN (SELECT www_id FROM www_dup);  -- rebuilt by the stats job
DELETE FROM domains WHERE id IN (SELECT www_id FROM www_dup);

UPDATE domains SET domain = substr(domain, 5)
WHERE domain LIKE 'www.%' AND NOT EXISTS (SELECT 1 FROM domains b WHERE b.domain = substr(domains.domain, 5));

SELECT 'merged' AS what, count(*) FROM www_dup
UNION ALL SELECT 'www rows left', count(*) FROM domains WHERE domain LIKE 'www.%';
COMMIT;
