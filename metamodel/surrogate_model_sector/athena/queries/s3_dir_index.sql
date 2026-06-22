-- s3_dir_index.sql
-- ---------------------------------------------------------------------------
-- Map each primary_id to the S3 batch file that holds its rows, using Athena's
-- "$path" pseudo-column (the source file of each row). Parsed downstream into
-- backend/s3_model_input_index.json as primary_id -> batch_n.
--
-- model_input_<n> and model_output_<n> share the same batching (verified), so
-- this single index serves the chatbot's model_input AND model_output lookups.
--
-- Each primary_id lives in exactly one batch file, so GROUP BY collapses the
-- 56 time-period rows per scenario to one (primary_id, path) pair.
-- ---------------------------------------------------------------------------
SELECT primary_id, "$path" AS path
FROM model_output
WHERE region = '{region}'
GROUP BY primary_id, "$path";
