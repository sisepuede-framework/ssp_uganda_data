"""
ddl.py
------
Generate Athena DDL (CREATE EXTERNAL TABLE + MSCK REPAIR TABLE) for the run's
CSV outputs, straight from a CSV header.

Why generate it: CSV tables in Athena are *positional* -- every column must be
declared, in order. model_output has ~1678 columns and cb ~21; the header is the
ground truth, so we read it once and emit the DDL. All batch files in a run share
the same column order, so one header is representative.

Partitioning: the data is laid out Hive-style as <table>/region=<x>/.../data.csv,
so we partition by `region`. model_output ALSO has a physical `region` column in
the data; to keep positional alignment we declare it under a different name
(`region_data`) -- the partition column wins for WHERE filters and prunes the scan.

Types: primary_id -> bigint, time_period -> int, everything else -> double
(unreferenced columns are never parsed by the LazySimpleSerDe, so over-declaring
numeric is harmless). The renamed region column is declared string.
"""

PARTITION_COL = "region"
BIGINT_COLS = {"primary_id"}
INT_COLS = {"time_period"}


def _col_type(name: str) -> str:
    if name in BIGINT_COLS:
        return "bigint"
    if name in INT_COLS:
        return "int"
    if name == PARTITION_COL:
        return "string"      # physical region column, declared under a renamed key
    return "double"


def build_create_table_sql(table: str, header: list, location: str) -> str:
    """CREATE EXTERNAL TABLE statement for a CSV table partitioned by region."""
    lines = []
    for col in header:
        # A physical `region` column would clash with the partition column; rename it.
        decl_name = f"{col}_data" if col == PARTITION_COL else col
        lines.append(f"  `{decl_name}` {_col_type(col)}")
    cols_block = ",\n".join(lines)
    return (
        f"CREATE EXTERNAL TABLE IF NOT EXISTS `{table}` (\n"
        f"{cols_block}\n"
        f")\n"
        f"PARTITIONED BY (`{PARTITION_COL}` string)\n"
        f"ROW FORMAT DELIMITED FIELDS TERMINATED BY ','\n"
        f"STORED AS TEXTFILE\n"
        f"LOCATION '{location}'\n"
        f"TBLPROPERTIES ('skip.header.line.count'='1');"
    )


def build_create_database_sql(database: str) -> str:
    return f"CREATE DATABASE IF NOT EXISTS `{database}`;"


def build_repair_table_sql(table: str) -> str:
    """Discover partitions (region=<x>/) so the table can be queried."""
    return f"MSCK REPAIR TABLE `{table}`;"
