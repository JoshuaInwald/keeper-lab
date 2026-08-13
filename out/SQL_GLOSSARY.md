# Databases and SQL, defined from scratch

Written for someone fluent in R/tidyverse and new to database vocabulary.
Every term is defined once, then tied to something concrete in this project.

**The single most useful thing to know first:** you already know SQL's logic.
dplyr was designed as a translation of it.

| dplyr | SQL | does |
|---|---|---|
| `select()` | `SELECT` | pick columns |
| `filter()` | `WHERE` | pick rows |
| `mutate()` | `SELECT ... AS` | make a new column |
| `group_by()` | `GROUP BY` | split into groups |
| `summarise()` | aggregate in `SELECT` | collapse groups |
| `arrange()` | `ORDER BY` | sort |
| `left_join()` | `LEFT JOIN` | merge on a key |
| `slice_head(n)` | `LIMIT` | take the top n |
| `filter()` after `group_by` | `HAVING` | filter *groups*, post-aggregation |

The one real difference is **order**. dplyr reads top-to-bottom in the order it
executes. SQL is written `SELECT … FROM … WHERE … GROUP BY … ORDER BY` but
*executes* `FROM → WHERE → GROUP BY → SELECT → ORDER BY`. That mismatch is the
single biggest source of beginner confusion, and knowing it removes most of it.

```sql
SELECT team, AVG(redraft_value) AS mean_value   -- 4th: compute
FROM board                                       -- 1st: get the table
WHERE keep_2027 = TRUE                           -- 2nd: drop rows
GROUP BY team                                    -- 3rd: split
ORDER BY mean_value DESC;                        -- 5th: sort
```

```r
board |>
  filter(keep_2027) |>
  group_by(team) |>
  summarise(mean_value = mean(redraft_value)) |>
  arrange(desc(mean_value))
```

Identical. If you can write the second you can write the first.

---

## 1. The basic furniture

**Database.** A structured collection of data plus software that manages
reading and writing it. Not a file format — a *system*. The distinction matters
because "put it in a database" is a decision about management, not storage.

**Table.** A rectangle of data. Same idea as a data frame: named, typed columns
and any number of rows. In SQL a table has a *fixed schema* declared up front,
which a data frame does not.

**Row / record / tuple.** One observation. All three words mean the same thing;
"row" is fine.

**Column / field / attribute.** One variable. Again, one concept, three words.

**Schema.** Two meanings, both common, which is annoying:
1. The *structure* — what columns a table has and what type each is.
2. A *namespace* — a folder of tables inside a database (`analytics.board`).

Context disambiguates. In this project, meaning (1).

**Type.** What kind of value a column holds: `INTEGER`, `DOUBLE`, `VARCHAR`
(text), `BOOLEAN`, `DATE`, `TIMESTAMP`. A database *enforces* types — you
cannot put "N/A" in an integer column. This is a feature. Half the data bugs in
this project were type confusion that a CSV happily permitted.

**NULL.** Missing. Same as R's `NA`, with the same contagion rule: anything
compared to NULL is NULL, not TRUE or FALSE. So `WHERE x = NULL` never matches
anything — you must write `WHERE x IS NULL`. This trips up everyone once.

**Primary key.** The column (or columns) that uniquely identifies a row. In
your board that is `fg_id` — the FanGraphs player ID. The database will refuse
to insert a duplicate, which is a guarantee a CSV cannot give you. Your
`snapshots` table would need a *composite* primary key: `(fg_id, snapshot_date)`
— one row per player per day.

**Foreign key.** A column that points at another table's primary key. `board.team`
pointing at `teams.name`. The database can then refuse to record a player on a
team that does not exist. This is called *referential integrity*, and it is the
main thing databases give you that data frames do not.

**Index.** A lookup structure — conceptually a sorted copy of one column with
pointers back to the rows. Turns "find every row where `fg_id = 19755`" from
scanning a million rows into a handful of steps. Costs disk space and slows
writes. At your data size, **irrelevant**; at a million rows, the difference
between instant and unusable.

**Constraint.** A rule the database enforces on every write: `NOT NULL`,
`UNIQUE`, `CHECK (salary >= 0)`. This is the database equivalent of the
assertions in `tests/test_invariants.py` — except it runs on every insert
forever, not just when you run pytest.

---

## 2. The language

**SQL** — Structured Query Language, pronounced "sequel" or "ess-cue-ell",
both accepted. Declarative: you describe *what you want*, not how to get it.
The database's **query planner** decides how. That is why SQL can be
dramatically faster than a hand-written loop — the planner reorders your work.

**Query.** A single SQL statement. Usually a read.

**Clauses**, in the order they execute:

- `FROM` — which table(s)
- `JOIN` — attach another table on a key
- `WHERE` — drop rows
- `GROUP BY` — split into groups
- `HAVING` — drop *groups* (after aggregation)
- `SELECT` — choose and compute columns
- `ORDER BY` — sort
- `LIMIT` — take the first n

**Aggregate function.** Collapses many rows to one: `COUNT`, `SUM`, `AVG`,
`MIN`, `MAX`, `MEDIAN`, `STDDEV`. Same as `summarise()`.

**JOIN.** Merging two tables on a key. The four you need:

| join | keeps |
|---|---|
| `INNER JOIN` | rows matching in both |
| `LEFT JOIN` | all left rows, NULLs where no match |
| `RIGHT JOIN` | mirror image; rarely used |
| `FULL OUTER JOIN` | everything from both |

Identical semantics to dplyr's `inner_join`, `left_join`, etc. The classic bug
is the same too: if the key is not unique on both sides you get a **fan-out** —
more rows than you started with. Your `PA_x`/`PA_y` collision was the merge
version of this in pandas.

**CTE** — Common Table Expression, written `WITH name AS (...)`. A named
intermediate result. This is the direct equivalent of assigning a variable
mid-pipeline in R, and it is the main tool for keeping SQL readable:

```sql
WITH keepers AS (
  SELECT * FROM board WHERE keep_2027
)
SELECT team, SUM(keeper_cost) FROM keepers GROUP BY team;
```

**Subquery.** A query nested inside another. CTEs do the same job and read far
better. Prefer CTEs.

**Window function.** Computes across a set of rows *without collapsing them* —
running totals, ranks, lags. This is `group_by() |> mutate()` in dplyr, and it
is the single most useful advanced SQL feature for analytics:

```sql
SELECT name, redraft_value,
       RANK() OVER (PARTITION BY team ORDER BY redraft_value DESC) AS rank_on_team
FROM board;
```

Relevant to you: your roto scoring **is** a window function — rank within a
category, across teams. If you ever move the standings calculation to SQL,
`RANK() OVER` is how.

**View.** A saved query that behaves like a table. Not stored — re-runs each
time. Good for "the query I always start from."

**Materialized view.** A view whose results *are* stored, refreshed on demand.
Faster to read, can be stale. Your `out/*.csv` files are, conceptually,
materialized views of the model.

**DDL vs DML.** Data *Definition* Language (`CREATE TABLE`, `ALTER`, `DROP`) —
changes structure. Data *Manipulation* Language (`SELECT`, `INSERT`, `UPDATE`,
`DELETE`) — changes or reads content. Jargon you will see in docs; not deep.

**Upsert.** Insert if new, update if it already exists. Written
`INSERT ... ON CONFLICT ... DO UPDATE`. Exactly what a nightly snapshot job
needs so re-running it twice in one day does not duplicate rows.

**Transaction.** A group of statements that all succeed or all fail. If your
snapshot job dies halfway through, a transaction means you get the old state,
not a half-written one.

**ACID.** The four guarantees a serious transactional database makes:
**A**tomicity (all-or-nothing), **C**onsistency (constraints always hold),
**I**solation (concurrent users don't see each other's half-done work),
**D**urability (committed means survives a power cut). You will see this
acronym constantly. For a one-person analytics project it is mostly irrelevant.

---

## 3. Kinds of database, and which you want

**OLTP** — Online *Transaction* Processing. Optimised for many small
reads/writes: a bank, a web app, a shopping cart. **Postgres**, **MySQL**.

**OLAP** — Online *Analytical* Processing. Optimised for scanning lots of rows
and aggregating: dashboards, research, exactly what you do. **DuckDB**,
BigQuery, Snowflake, Redshift.

The distinction drives everything else:

**Row-store vs column-store.** A row-store keeps a row's values physically
together — fast for "give me everything about player 19755." A **column-store**
keeps each column together — fast for "average `redraft_value` across a million
rows," because it reads only that one column off disk and skips the rest.
Analytics is almost always column-shaped. **DuckDB is a column-store. This is
why it is the right tool for you.**

**Embedded vs client-server.** A **client-server** database (Postgres, MySQL)
is a separate program running in the background that your code connects to over
a network port, with a username and password. An **embedded** database is a
library that runs *inside* your program — no server, no port, no password, no
process to keep alive.

**SQLite** is the famous embedded transactional database — it is inside every
phone you own. **DuckDB is SQLite's analytical counterpart**, and that one
sentence is the best description of it. `pip install duckdb`, and the database
is a single file you can email.

**Recommendation, restated plainly:** use DuckDB. Postgres would mean running a
server, managing credentials, and backing up something that isn't a file, all
to query 2 MB of baseball data.

---

## 4. File formats you already have

**CSV.** Comma-separated text. Universal, human-readable, and typeless —
everything is a string until something guesses. No compression. Your raw inputs.

**JSON.** Nested key-value text. Good for irregular structures, bad for tables.
What the app payload is serialised as, because a browser speaks it natively.

**Parquet.** Columnar, compressed, **typed**, and self-describing (the schema
travels in the file). ~5× smaller than the equivalent CSV and dramatically
faster to read. Not human-readable — you need a tool. This is the standard
storage format for analytics, and **your snapshots are already in it.**

**The important consequence:** DuckDB reads Parquet directly. There is no
import step, no migration, no `CREATE TABLE`. Your existing files are already a
database as far as DuckDB is concerned:

```sql
SELECT name, MAX(redraft_value) - MIN(redraft_value) AS swing
FROM 'out/snapshots/*/board.parquet'
GROUP BY name
ORDER BY swing DESC
LIMIT 20;
```

That glob pattern reads every snapshot you have ever written. It is the whole
"track value over time" feature, in six lines, with zero setup.

---

## 5. Pipeline vocabulary you'll meet in job descriptions

**ETL / ELT.** Extract, Transform, Load — the pipeline that moves data from
source to warehouse. ELT reverses the last two: load raw, transform inside the
warehouse. ELT is now the norm because storage got cheap. **Your `run_all.py`
is an ETL job**: extract from CSVs, transform via the model, load into `out/`.

**Pipeline / DAG.** A dependency graph of steps. Directed Acyclic Graph — the
arrows point one way and never loop. The diagram in `ARCHITECTURE.md` §3.1 is a
DAG. Tools that run them: Airflow, Dagster, Prefect. You do not need one; a
script is a pipeline with an implicit DAG.

**dbt.** Tool for organising SQL transformations into a dependency graph with
tests and documentation. Ubiquitous in data-team job ads. Only relevant once
your transformations *are* SQL — yours are pandas.

**Data warehouse / lake / lakehouse.** Warehouse = structured, cleaned,
query-ready. Lake = raw files dumped as-is. Lakehouse = querying the lake
directly with warehouse tools. **DuckDB-over-Parquet is a small lakehouse**, and
you would be entitled to describe it that way.

**Normalization.** Splitting data so nothing repeats — team name stored once in
a `teams` table, referenced by ID everywhere else. Prevents contradictions.
**Denormalization** is deliberately duplicating for query speed. OLTP
normalizes; OLAP usually denormalizes. Your board is denormalized and correctly
so.

**Star schema.** The standard analytics layout: one central **fact** table of
measurements (one row per player per snapshot) surrounded by **dimension**
tables of descriptors (players, teams, seasons). If you ever build a real
warehouse for this, that is the shape: `fact_player_value` joined to
`dim_player`, `dim_team`, `dim_date`.

**Partition.** Splitting a table by a column — usually date — so a query for
one day reads one file. Your `out/snapshots/<date>/` directory is partitioning,
done by hand, and DuckDB understands it natively.

**Driver / connection / cursor.** The library that speaks the database's
protocol; an open session; a pointer for stepping through results. With DuckDB
this collapses to two lines and you can mostly forget the vocabulary:

```python
import duckdb
duckdb.sql("SELECT * FROM 'out/snapshots/*/board.parquet' LIMIT 5").df()
```

**ORM** — Object-Relational Mapper. A library that hides SQL behind objects
(SQLAlchemy, Django ORM). Built for web apps, where you fetch one record at a
time. **Actively unhelpful for analytics** — it obscures exactly the set
operations you want.

---

## 6. The five queries worth writing first

If you want the SQL practice, these are the ones that produce answers you
actually want, in rough order of difficulty. All run against your existing
Parquet snapshots with no setup.

1. **Biggest value swings this season** — `GROUP BY` + `MAX - MIN`.
2. **Team surplus over time** — `GROUP BY team, snapshot` then pivot.
3. **Keeper decisions that flipped** — self-join a snapshot to the previous one
   on `fg_id`, compare `keep_2027`. Teaches joins properly.
4. **Free agents who crossed a value threshold** — `WHERE` + `LAG()` window
   function. Teaches windows.
5. **Each team's category strength vs the league** — window function
   partitioned by category. This is your roto scoring, in SQL.

Do those five and you can honestly claim SQL on a CV. Do not migrate the
modelling code into SQL — it would be slower, less readable, and untestable.
