"""
run_extracts.py
---------------
Orchestrates the Athena side of the training-data pipeline:

  1. Sniff the CSV headers of model_output / cb in S3 and GENERATE the DDL.
  2. (gated) Create the per-run Glue database + external tables + MSCK REPAIR.
  3. Run the 2 SELECT queries, wait, report bytes scanned, download the result CSVs.

Safety gate -- writing tables to AWS (the Glue catalog) requires an explicit flag:

  python run_extracts.py                 # DRY RUN: print the DDL + queries, write nothing
  python run_extracts.py --apply-ddl     # create db/tables, then run queries + download
  python run_extracts.py --skip-ddl      # tables already exist: run queries + download only

Then run assemble_training_data.py to build the parquet.
"""

import argparse
import os

from config import load_config, QUERIES_DIR
import athena_client as ac
import ddl as ddlgen

# table -> the .sql file whose result we download
QUERIES = {
    "emissions_and_gdp": "emissions_and_gdp.sql",
    "cost_benefit": "cost_benefit.sql",
}
TABLES = ["model_output", "cb"]


def _load_sql(name: str, region: str) -> str:
    with open(os.path.join(QUERIES_DIR, name)) as f:
        return f.read().format(region=region)


def generate_ddl(session, cfg) -> dict:
    """Read headers from S3 and build all DDL statements. No AWS writes."""
    statements = {"create_database": ddlgen.build_create_database_sql(cfg.database)}
    for table in TABLES:
        prefix = f"run_database/{cfg.run_dir_name}/{table}/region={cfg.region}/"
        key = ac.first_data_csv_key(session, cfg.bucket, prefix)
        header = ac.read_csv_header(session, cfg.bucket, key)
        location = cfg.table_location(table)
        statements[f"create_{table}"] = ddlgen.build_create_table_sql(table, header, location)
        statements[f"repair_{table}"] = ddlgen.build_repair_table_sql(table)
        print(f"  {table}: {len(header)} columns  (header from {key})")
    return statements


def apply_ddl(session, cfg, statements: dict) -> None:
    """Execute DDL: create database (no context), then tables + repair (in db)."""
    out = cfg.query_output("_ddl")
    print(f"\nCreating database `{cfg.database}` ...")
    ac.wait_for_query(session, ac.run_query(session, statements["create_database"], out))
    for table in TABLES:
        print(f"Registering table `{table}` + repairing partitions ...")
        ac.wait_for_query(session, ac.run_query(session, statements[f"create_{table}"], out, cfg.database))
        ac.wait_for_query(session, ac.run_query(session, statements[f"repair_{table}"], out, cfg.database))


def run_queries(session, cfg) -> None:
    """Run the SELECT queries and download each result CSV locally."""
    os.makedirs(cfg.query_csv_dir, exist_ok=True)
    for name, sql_file in QUERIES.items():
        sql = _load_sql(sql_file, cfg.region)
        print(f"\nRunning query `{name}` ...")
        qe = ac.wait_for_query(session, ac.run_query(session, sql, cfg.query_output(name), cfg.database))
        uri = ac.result_s3_uri(qe)
        mb = ac.bytes_scanned(qe) / 1e6
        local = os.path.join(cfg.query_csv_dir, f"{name}.csv")
        ac.download_s3_uri(session, uri, local)
        print(f"  scanned {mb:,.1f} MB  (~${mb / 1e6 * 5:.4f})")
        print(f"  result: {uri}")
        print(f"  saved:  {local}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--apply-ddl", action="store_true", help="execute DDL (writes to Glue), then run queries")
    p.add_argument("--skip-ddl", action="store_true", help="skip DDL, run queries only (tables already exist)")
    args = p.parse_args()

    cfg = load_config()
    session = ac.make_session(cfg)
    print(f"Run:      {cfg.run_dir_name}")
    print(f"Region:   {cfg.region}")
    print(f"Database: {cfg.database}")
    print(f"Output:   {cfg.query_output_prefix}\n")

    print("Generating DDL from S3 headers ...")
    statements = generate_ddl(session, cfg)

    if not args.skip_ddl:
        print("\n" + "=" * 78 + "\nDDL TO BE EXECUTED (writes to the Glue catalog)\n" + "=" * 78)
        for stmt in statements.values():
            preview = stmt if len(stmt) < 1500 else stmt[:700] + "\n  ... (truncated) ...\n" + stmt[-200:]
            print("\n" + preview)
        print("=" * 78)

    if not (args.apply_ddl or args.skip_ddl):
        print("\nDRY RUN: nothing written. Re-run with --apply-ddl to register tables "
              "and run the queries, or --skip-ddl if the tables already exist.")
        return

    if args.apply_ddl:
        apply_ddl(session, cfg, statements)

    run_queries(session, cfg)
    print("\nDone. Next: python assemble_training_data.py")


if __name__ == "__main__":
    main()
