# Hybrid Search *(capability)*

> **Source:** [`bigquery-ai/reference/embedding-generation-and-semantic-search.md#hybrid-search-capability`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/embedding-generation-and-semantic-search.md#hybrid-search-capability)

Hybrid search combines semantic (vector) retrieval with lexical (keyword) matching, so that exact tokens -- SKUs, error codes, model numbers, proper nouns -- can influence the ranking instead of being dissolved into embedding similarity. **BigQuery ships this as a capability of the two existing search functions, not as a separate `HYBRID_SEARCH` function.** There is no `HYBRID_SEARCH` in the SQL surface.

> **Set the expectation correctly before you reach for it.** Hybrid search fuses two *rankings* of the same corpus; it does not union two result sets. How deep a lexical match can reach is decided entirely by `top_k`, through **two independent gates**: BigQuery hands the lexical leg only the top `10 * top_k` rows by semantic rank, and inside that pool a lexical hit is worth a bounded amount of score -- at most `1/62` = `0.0161`. Effective reach is the smaller of the two. At the page sizes most demos use (`top_k` under ~30) the score gate holds reach to ~110 rows and the token only nudges rows the semantic leg already placed near the top. At `top_k` = 64 the pool gate holds it to semantic rank 640, and no exact-token match reaches deeper than that no matter how perfect the match. Sizing `top_k` is part of the design, not an afterthought.

| Route | How to invoke | Lexical columns | Batch? |
|-------|---------------|-----------------|--------|
| `VECTOR_SEARCH` | Single search syntax + `lexical_search_columns` (+ optional `lexical_search_query_value`) | Any set of base table columns you name | No -- single query only |
| `AI.SEARCH` | `mode => 'HYBRID'` | Only `column_to_search` | No -- single query only |

**Neither route requires a vector index.** Both run against an unindexed base table; the index is a speed optimization for the lexical leg, not a prerequisite.

**Two gates, and `top_k` sets both.** A lexically-matched row appears on the result page only if it clears both of these:

```
Gate 1 (candidate pool):   rank_vector <= 10 * top_k
Gate 2 (fusion score):     1/(60 + rank_vector) + 1/(61 + rank_lexical)
                             must beat the row holding the last slot
```

**Effective reach = `min( score_reach(top_k), 10 * top_k )`.** Gate 1 binds for `top_k` >= 51; Gate 2 binds below that. Everything else in this section is a consequence of those two lines.

**Gate 1: the lexical candidate pool is `10 * top_k` rows.** BigQuery hands the lexical (BM25) leg only the top `10 * top_k` rows by semantic rank. A row deeper than that receives **no lexical rank at all** -- BM25 never sees it, however exactly the token matches, and no amount of score can rescue it. This is why a page of 64 reaches semantic rank 640 and stops.

The diagnostic signature of a query whose target sits outside the pool is that the whole result set comes back with `rank_lexical = rank_vector`, so every returned value is exactly `1 - ( 1/(60 + r) + 1/(61 + r) )`. Read the top row: a best `distance` of **`0.967478`** (= `1 - (1/61 + 1/62)`) means *nothing matched*, while **`0.967734`** (= `1 - (1/61 + 1/63)`) means a match fired somewhere and pushed the top semantic row to lexical rank 2. Those two numbers tell you whether to raise `top_k` or fix the token.

**Gate 2 -- scoring: reciprocal rank fusion.** In hybrid mode the returned `distance` column is a fused rank score rather than a geometric distance. Each candidate is ranked separately by the semantic leg and the lexical leg, and the two ranks are combined. Reproduced against live results, the value matches reciprocal rank fusion with **k = 60 on the semantic leg and k = 61 on the lexical leg**, both ranks 1-based:

```
distance = 1 - ( 1/(60 + rank_vector) + 1/(61 + rank_lexical) )
```

**What is measured, and what is inferred.** `VECTOR_SEARCH` returns no rank column, so only one of the two ranks is ever read directly. `rank_vector` comes from a separate semantic-only run over the same rows; the lexical term is whatever remains after subtracting `1/(60 + rank_vector)` from `1 - distance`. What the arithmetic pins is therefore a set of *denominators*, not a pair of constants. Measured on a 30-row corpus, the semantic leg's top row contributes `1/61`, the lexical leg's top row contributes `1/62`, and the remaining lexical denominators run contiguously from there.

Two readings fit identically, because `1/(61 + rank_lexical)` and `1/(60 + (rank_lexical + 1))` are the same number:

| Reading | Semantic leg | Lexical leg |
|---|---|---|
| A -- two constants | k = 60, ranks `1..n` | k = 61, ranks `1..n` |
| B -- one constant, offset ranks | k = 60, ranks `1..n` | k = 60, ranks `2..n+1` |

Nothing observable from outside BigQuery separates them, but **B is the likelier**. k = 60 over 1-based ranks is the canonical RRF of Cormack, Clarke and Buettcher (2009) and the default wherever the constant is exposed -- Elasticsearch and OpenSearch both name it `rank_constant` and default it to 60, and Spanner and AlloyDB write 60 into their documented SQL. A constant of 61 appears in no published implementation. What is measured is that the semantic leg lands on the canonical `1/61` for its own top row -- so this document's rank convention already agrees with BigQuery's on one leg, and the extra `+1` sits on the lexical side specifically.

**Why the lexical leg would start at 2 is a separate question, and it is open.** Reading B says *where* the extra `+1` sits, not *why*. Three mechanisms fit the observations equally well:

- **A deliberate tie-break.** At equal ranks the vector term `1/(60 + r)` exceeds the lexical term `1/(61 + r)`, so the semantic leg wins every tie by a hair. That is what you would implement if hybrid should never reorder a tie against the embedding.
- **A reserved slot.** If position 1 of the lexical list holds something that is not a result -- the query itself, a sentinel, a header row -- then real rows begin at 2 naturally.
- **An off-by-one.** 61 is universal as the rank-1 *denominator*, `1/(60 + 1)`. Transcribing that as the constant, or applying `+1` to an already-1-based rank, produces exactly the observed `1/62` on a top row.

Only the third is a defect, and it is the least charitable of the three. Nothing observable from outside BigQuery distinguishes them, so do not present any one of them as the explanation.

One argument that looks decisive and is not: decoding with k = 60 on both legs yields lexical ranks `2 .. n+1`, and no n-row list hands out rank n+1. That rules out a shared base combined with ordinary 1-based lexical numbering. It does *not* rule out reading B, where `2 .. n+1` is precisely what an offset 1-based ranking looks like. A contiguous block starting at 2 is evidence *for* an offset, not against a shared constant.

The 60/61 form is used throughout this document because it is the shortest expression that reproduces every observed value. Read it as arithmetic that holds, not as two deliberate design decisions.

Three worked examples from that run, each matching a live returned value exactly:

| rank_vector | rank_lexical | Arithmetic | Returned `distance` |
|---|---|---|---|
| 1 | 3 | `1 - (1/61 + 1/64)` | `0.967981557377` |
| 2 | 1 | `1 - (1/62 + 1/62)` | `0.967741935484` |
| 9 | 2 | `1 - (1/69 + 1/63)` | `0.969634230504` |

The middle row is the one that trips people up: `1/62 + 1/62` is a value the measured arithmetic produces -- `1/(60 + 2)` and `1/(61 + 1)` happen to coincide at ranks (2, 1). It is also the `distance` on the `tiger` row of Google's published hybrid example, which decodes to exactly those ranks. Seeing two equal denominators is not evidence of a shared rank base: under either reading above, ranks (2, 1) produce `1/62` twice.

Consequences worth internalizing:

- **The best attainable score is `1 - (1/61 + 1/62)` = `0.9674775251189847`** -- rank 1 in *both* legs. An exact self-match does not return a near-zero "distance". (The oft-quoted `1 - 2/61` = `0.967213` is not attainable: the two denominators can never be equal at rank 1.)
- **Each leg contributes at most ~`1/61` = `0.0164`.** A rank-1 lexical hit is worth `1/62` = `0.0161` and nothing more. That single number is the budget the whole capability operates inside.
- **The lexical leg ranks the entire candidate pool, so no pooled row ever forfeits a term.** True BM25 matches take lexical ranks `1..m`; every remaining pooled row falls back to its *semantic* order behind them. Verified with a `lexical_search_query_value` matching zero rows -- every row still received a lexical term, with `rank_lexical = rank_vector`. Verified again by promoting one row to lexical rank 1: the row formerly at lexical rank 1 moved to 2, and every row below the promoted row was byte-identical. Within the pool there is no "single-list" state and no forfeiture ceiling; every row in the result is scored from both terms. Outside the pool there is no scoring at all -- that is Gate 1, not a forfeited term.
- **Therefore an unmatched row is not penalized, only un-promoted.** It keeps a lexical rank -- its own semantic rank, pushed down one place for each row below it that did match. Where nothing matched at all, that reduces to `1 - ( 1/(60 + r) + 1/(61 + r) )` at semantic rank `r` -- at `r = 10`, `1 - (1/70 + 1/71)` = `0.97163`. A lexical match moves that row to lexical rank 1, replacing its `1/(61 + r)` with `1/62`. That single substitution is the entire mechanism.
- **What limits hybrid is reach, and reach is a function of `top_k` twice over.** For the score gate: a matched row at semantic rank `R` scores `1/(60 + R) + 1/62`, and it has to displace the row holding the last slot, which sits at semantic rank `top_k` and -- pushed down one position by the match -- lexical rank `top_k + 1`, scoring `1/(60 + top_k) + 1/(61 + top_k + 1)`. For the pool gate the bound is simply `10 * top_k`. Taking the `min` of the two gives the deepest semantic rank a lexically-matched row can occupy and still make the page:

  | `top_k` | 2 | 3 | 5 | 10 | 20 | 30 | 40 | 50 | 51 | 64 | 100 | 208 | 300 |
  |---|---|---|---|---|---|---|---|---|---|---|---|---|---|
  | deepest semantic rank retrievable | 3 | 6 | 10 | 23 | 56 | 110 | 212 | 468 | 510 | 640 | 1,000 | 2,080 | 3,000 |
  | binding gate | score | score | score | score | score | score | score | score | pool | pool | pool | pool | pool |

  Below `top_k` = 51 the score gate is the binding one and growth is steeply non-linear -- nearly flat through the page sizes demos typically use, then accelerating. From `top_k` = 51 upward the pool gate takes over and reach becomes exactly linear at `10 * top_k`. There is no page size at which reach becomes unbounded. `top_k` >= `R/10` is therefore a floor for retrieving a row at semantic rank `R`, not a recipe: it is necessary everywhere, but sufficient only once the pool gate is the binding one. Below that crossover the score gate decides and `R/10` falls short -- a target at semantic rank 100 needs `top_k` of 29, not 10, and one at rank 200 needs 40, not 20. Read the real number off the row above.
- **The evidence.** A 500-row corpus: 499 rows about office and desk items, semantically close to the query `"desk accessories for a computer setup"`, plus one target row `ZQX-9999` described as `"bulk compost bin for garden waste and autumn leaf mulching"` -- semantic rank **500 of 500**. Searching with `lexical_search_query_value => 'ZQX-9999'`:

  | `top_k` | 10 | 49 | 50 | 51 | 63 | 64 |
  |---|---|---|---|---|---|---|
  | target returned | no | no | no | **yes** | yes | yes |

  The arithmetic predicts the flip between 50 and 51 to the exact position. The target's returned `distance`, `0.9820852534562212`, is exactly `1 - (1/560 + 1/62)` -- semantic rank 500, lexical rank 1. Here the score gate is the binding one: at `top_k` = 51 the pool is 510 rows, comfortably deeper than the target.

- **The pool gate, isolated.** Repeating the same construction on deeper corpora puts the target beyond any plausible score-gate reach, so the flip lands on `10 * top_k` exactly. Each of these was a sharp prediction made before the query ran; the 500-row probe is listed alongside them as the contrasting case, where the score gate is the binding one:

  | corpus | index | target semantic rank | predicted flip | observed |
  |---|---|---|---|---|
  | 3,000 rows | none | 3,000 | `top_k` = 300 | 299 no match, **300 match** |
  | 1,500 rows | none | 1,500 | `top_k` = 150 | 149 no match, **150 match** |
  | 500 rows | none | 500 | `top_k` = 51 (score gate) | 50 absent, **51 present** |
  | 7,275-row product catalog | `TREE_AH` hybrid, `ACTIVE`, 100% coverage | 2,072 | needs `top_k` >= 208 | `top_k` = 64 returned nothing |

  The three synthetic probe tables are **unindexed** -- at 3,000, 1,500 and 500 rows they sit below BigQuery's 5,000-row `CREATE VECTOR INDEX` floor and are brute-force scanned, so no index existed that could have restricted anything. The product catalog is the opposite case: it carried a fully populated hybrid `TREE_AH` index declaring `lexical_search_columns`, status `ACTIVE` at 100% coverage, when the `top_k` = 64 observation was made. The pool gate behaves identically with and without an index, which makes it both *not* an index artifact and *not* something an index can avoid. At `top_k` = 64 on the catalog the pool was 640 rows and the target at rank 2,072 was never a candidate; the result set carried the zero-match signature (`rank_lexical = rank_vector`, best `distance` `0.967478`).
- **This is why a hybrid demo at `top_k => 3` or `5` returns almost exactly the semantic-only rows:** at those page sizes reach is 6 and 10, deep enough to shuffle the top of the list, never deep enough to pull in something new. That is a property of the page size chosen, not a limit on the capability.
- **Promotion is a swap.** The fused list is a fixed-length page, so a row hybrid adds displaces one semantic-only would have returned. Always measure both the added *and* the dropped set.
- **When the token is all the user typed, use a predicate.** Hybrid *can* retrieve it, but only if `top_k` clears both gates for the target's semantic rank -- a tenth of that rank at the very least, and more than that whenever the score gate binds -- which you do not know in advance, and a fusion score is still a ranking that can be crowded. Use `WHERE sku = @sku` -- a predicate cannot be outranked and has no candidate pool. Hybrid earns its place on queries that carry descriptive words *and* an identifier.
- Scores are bounded in a narrow band near 1 and are **not comparable** to `VECTOR`-mode distances. Do not threshold hybrid scores with a cutoff tuned on cosine or Euclidean distance.
- Because the score depends only on ranks, `distance_type` has no effect in hybrid mode.

**The sizing rule:** hybrid search re-ranks *and* widens, and `top_k` decides how much of each you get -- the widening is real but bounded, never unbounded. At `top_k` up to about 30 the token only nudges rows already near the top -- do not size a page that way and then expect recall. Beyond that, an exact token surfaces a row from about `10 * top_k` deep and no deeper, so for a target you expect at semantic rank `R`, **size `top_k` to at least `R/10`, and above that to whatever the reach table requires** -- the two gates cross at `top_k` = 51, so for anything shallower than a few hundred ranks the score gate is the one that binds and the floor alone will not retrieve the row. If the identifier *is* the query and you need certainty, use a `WHERE` predicate instead.

> This formula is reverse-engineered from observed results, not documented by Google. Treat it as an explanation of the ordering you see, not as a contract -- it can change without notice.

**Vector indexes for hybrid search.** To accelerate the lexical leg, create a vector index that declares the lexical columns:

```sql
CREATE [ OR REPLACE ] VECTOR INDEX [ IF NOT EXISTS ] index_name
ON table_name(column_name)
[STORING(stored_column_name [, ...])]
[PARTITION BY partition_expression]
OPTIONS(index_option_list);
```

```sql
CREATE VECTOR INDEX IF NOT EXISTS my_hybrid_index
ON my_table(embedding)
STORING (product_name)
OPTIONS (index_type = 'TREE_AH', distance_type = 'COSINE',
         lexical_search_columns = ['product_name']);
```

Rules that are easy to get wrong, all confirmed against a live project:
- Every column in `lexical_search_columns` **must also appear in `STORING(...)`**. Omitting the `STORING` clause fails with `Lexical search column x must be in the list of stored columns`.
- A lexical column **may not also be the index key**. Naming the same column in `ON table(x)` and `STORING(x)` fails with `Column x found multiple times`.
- The index key must be an `ARRAY<FLOAT64>` embedding column. **A vector index cannot be created on an autonomous embedding generation column**, because that column is a `STRUCT`. Demonstrating both autonomous embeddings and a vector index in one pipeline therefore requires two tables.
- **Two separate size gates, and they fail differently.** (a) `CREATE VECTOR INDEX` is *rejected outright* below **5,000 rows**: `Total rows 30 is smaller than min allowed 5000 for CREATE VECTOR INDEX query with the IVF index type. Please use VECTOR_SEARCH table-valued function directly to perform the similarity search.` Verified 2026-09-02 on a 30-row table for **both** `IVF` and `TREE_AH` (the message names whichever `index_type` you passed), so this is not an IVF-only constraint. (b) Once created, **population** is asynchronous and does not begin until the base table exceeds roughly **10 MB**; below that the index sits at `coverage_percentage` 0 with `indexUnusedReasons` = `BASE_TABLE_TOO_SMALL` and queries silently fall back to brute force. A demo table must clear *both* bars to show a working index -- which is why the catalog workflow uses a real ~7,275-row public catalog rather than generated data. Note the 5,000-row floor is enforced by the engine but is **not** stated on the vector-index documentation page; only the 10 MB condition is documented.
- `index_type` is `TREE_AH` or `IVF`.
- **`PARTITION BY` must match the base table's partitioning expression exactly.** The clause does not let you pick an arbitrary partitioning for the index. On a table partitioned by `RANGE_BUCKET(id, GENERATE_ARRAY(0, 30000, 5000))`, repeating that same expression validates; naming any other column -- `PARTITION BY category` -- fails with `Invalid Partition By expression`, and so does `PARTITION BY category` against a table that is not partitioned at all.

**Index lifecycle: coverage, drift, and rebuild.** Creating an index is not managing one. Three signals describe an index's health and they move *independently* -- all measured 2026-09-03 against a live 7,275-row `TREE_AH` hybrid index:

| Signal | Where to read it | What it actually means |
|---|---|---|
| `coverage_percentage`, `unindexed_row_count` | `INFORMATION_SCHEMA.VECTOR_INDEXES` | how much of the base table the index currently covers |
| `tfdv_drift` | `VECTOR_INDEX.STATISTICS(TABLE t)` | how far the *vector distribution* has moved since the index was built |
| `last_model_build_time` | `INFORMATION_SCHEMA.VECTOR_INDEXES` | when the TreeAH model itself was last built -- distinct from `last_refresh_time` |

`VECTOR_INDEX.STATISTICS` takes **exactly one argument** and it must be a relation: `VECTOR_INDEX.STATISTICS(TABLE my_table)`. Adding the index name as a second argument fails with `Signature accepts at most 1 argument, found 2 arguments`; passing a string instead of `TABLE t` fails with `argument 1 must be a relation (i.e. table subquery)`. It returns a single column, `tfdv_drift`, which is `null` until the index's first refresh and `"0.0"` at fresh 100% coverage. On a table carrying **no** index it returns **zero rows** rather than an error, and scans 0 bytes -- so it is safe to call unconditionally.

**A negative `tfdv_drift` is a sentinel, not a magnitude.** Two freshly built indexes at 100% coverage reported different things: `"0.0"` from an unpartitioned hybrid index, and `-1.0` from a `PARTITION BY` index with no `lexical_search_columns`. Those two indexes differ in more than one way, so this does not isolate a cause -- partitioning, the absence of lexical columns, and how recently the first refresh completed are all still in play. Read a negative value as *no drift figure available for this index yet* and corroborate with `coverage_percentage` and `last_refresh_time` before acting on it. Partitioned indexes do populate normally otherwise: one on a 19,055-row / ~8.6 MB table reached 100% coverage about seven minutes after `CREATE`.

**Coverage and drift are not the same alarm.** Inserting 11,780 rows whose vectors duplicate ones already indexed (7,275 -> 19,055 rows) dropped `coverage_percentage` from 100 to 38 and set `unindexed_row_count` to 11,780 -- while `tfdv_drift` moved only from `0.0` to `1.97e-5` and `last_model_build_time` did not change at all (held across six 90-second polls). That is the point of having both numbers: a large volume of *new but distributionally identical* rows is a coverage problem, not a drift problem. Coverage recovers on the automatic refresh; drift is what argues for a rebuild.

**`ALTER VECTOR INDEX ... REBUILD` requires a BACKGROUND reservation.** With no reservation on the project the statement is rejected outright:

```
Cannot alter vector index on table my_table because there is no BACKGROUND reservation.
```

The same gate covers search indexes -- `ALTER SEARCH INDEX ... SET OPTIONS (...)` and `ALTER SEARCH INDEX ... ADD COLUMN` return the identical message with `search index` in place of `vector index`. **The check fires before validation, so these statements cannot even be dry-run**: `bq query --dry_run` on any of them returns the reservation error rather than `Query successfully validated`, and it does so even when the named index does not exist. That rules out the usual trick of parse-checking index-maintenance DDL for free. Index *maintenance* runs as background work, and background work needs slots assigned to it, so a project billed purely on demand has nowhere to run it. Exercising these statements requires an Enterprise-edition reservation carrying a `BACKGROUND` job-type assignment; an autoscale reservation with baseline 0 is the cheap shape, since it bills only while the rebuild actually runs. Creating an index, populating it, and querying through it all work with no reservation at all -- only the `ALTER` path is gated. Related: `last_index_alteration_info` stays `null` until an `ALTER` succeeds, and it is a `RECORD`, so `bq query --format=csv` refuses to print it (`Cannot print record field "last_index_alteration_info" in CSV format`) -- use `--format=prettyjson`.

**Search indexes have a 10 GiB floor -- three orders of magnitude above the vector index gates.** `CREATE SEARCH INDEX` *succeeds* on a small table, and then the index never populates. `INFORMATION_SCHEMA.SEARCH_INDEXES` reports `index_status` = `TEMPORARILY DISABLED`, `disable_time` equal to `creation_time`, `coverage_percentage` 0, and this `disable_reason`:

> The base table size is below the threshold of 10737418240 bytes for indexing. The index does not provide noticeable search performance gains when the base table is too small.

10,737,418,240 bytes is exactly 10 GiB -- against the vector index's 5,000-row hard reject and ~10 MB population gate. No teaching-scale table can carry a populated search index, which is why this project creates none and reaches for `lexical_search_columns` on a vector index instead. Note also that the `ddl` column of `SEARCH_INDEXES` is normalized rather than a verbatim echo of what you ran: a statement written with `OPTIONS (analyzer = 'LOG_ANALYZER')` is recorded as `OPTIONS (data_types = ['STRING'])`, with the analyzer surfaced in the separate `analyzer` column.

**Related:** [`VECTOR_SEARCH`](vector_search.md) · [`AI.SEARCH`](aisearch.md) · workflow [`catalog_search`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/workflows/catalog_search)
