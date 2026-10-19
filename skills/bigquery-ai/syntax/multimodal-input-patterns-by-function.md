# Multimodal Input Patterns by Function

> **Source:** [`bigquery-ai/reference/unstructured-data-infrastructure.md#multimodal-input-patterns-by-function`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/unstructured-data-infrastructure.md#multimodal-input-patterns-by-function)

**Every multimodal AI function takes an `ObjectRef`.** What differs between them is only *where the reference goes in the call*: a field of a STRUCT prompt, the second slot of a tuple, a bare positional argument, or a named `content` parameter. There are four shapes, not four pipelines.

Where the `ObjectRef` comes from is an independent choice:

```sql
OBJ.MAKE_REF('gs://bucket/doc.pdf', 'PROJECT.REGION.CONNECTION')  -- inline, no table
ref                                                                -- object table column
```

### Shape 1: STRUCT Prompt (most generation functions + AI.IF)

Replace the STRING prompt with a STRUCT containing text and an array of `ObjectRef`. Works inline — no object table needed.

**Functions:** `AI.GENERATE`, `AI.GENERATE_TEXT`, `AI.GENERATE_TABLE`, `AI.GENERATE_BOOL`, `AI.GENERATE_DOUBLE`, `AI.GENERATE_INT`, `ML.GENERATE_TEXT`, `AI.IF`

```sql
-- Scalar function (AI.GENERATE)
SELECT (AI.GENERATE(
  STRUCT(
    'Summarize this document.' AS prompt,
    [OBJ.MAKE_REF('gs://bucket/doc.pdf', 'PROJECT.REGION.CONNECTION')] AS object_refs
  )
)).result;

-- TVF (AI.GENERATE_TEXT)
SELECT result
FROM AI.GENERATE_TEXT(
  MODEL `project.dataset.model`,
  (SELECT STRUCT(
    'Summarize this document.' AS prompt,
    [OBJ.MAKE_REF('gs://bucket/doc.pdf', 'PROJECT.REGION.CONNECTION')] AS object_refs
  ) AS prompt)
);

-- Managed function (AI.IF)
SELECT AI.IF(
  STRUCT(
    'This document is a financial invoice' AS prompt,
    [OBJ.MAKE_REF('gs://bucket/doc.pdf', 'PROJECT.REGION.CONNECTION')] AS object_refs
  )
) AS is_invoice;
```

> The STRUCT's field *names* are not part of the contract — the function concatenates the fields in the order given, the way `CONCAT` would. `object_refs` is this project's convention because it says what the field holds; `object_ref_runtime` or anything else behaves identically.

### Shape 2: Tuple Syntax (AI.SCORE)

`AI.SCORE` does not accept the STRUCT prompt. Pass a tuple of (scoring text, `ObjectRef`).

**Functions:** `AI.SCORE`

```sql
-- Create an object table first
CREATE EXTERNAL TABLE `project.dataset.docs`
WITH CONNECTION `project.region.connection`
OPTIONS (object_metadata = 'SIMPLE', uris = ['gs://bucket/path/*.pdf']);

-- Score documents using tuple syntax
SELECT
  uri,
  AI.SCORE(
    ('Rate the professionalism of this document on a scale of 0 to 1', ref)
  ) AS professionalism
FROM `project.dataset.docs`;
```

### Shape 3: Direct Argument (AI.CLASSIFY, AI.AGG)

The reference is just an argument — no prompt STRUCT, no tuple. `AI.AGG` wraps it in a one-field `STRUCT` because that is how it takes any input.

**Functions:** `AI.CLASSIFY`, `AI.AGG`

```sql
-- Classify straight off the object table's ref column
SELECT
  uri,
  AI.CLASSIFY(ref, ['invoice', 'receipt', 'contract', 'letter']) AS doc_type
FROM `project.dataset.docs`;

-- AI.AGG wraps the reference in a one-field STRUCT
SELECT AI.AGG(
  STRUCT(ref),
  'Summarize the common themes across these documents.'
) AS themes
FROM `project.dataset.docs`;
```

`EXTERNAL_OBJECT_TRANSFORM(TABLE t, ['SIGNED_URL'])` is not required here — verified live 2026-09-15 against a 10-PDF object table, where the bare `ref` column and the transformed one returned the same classifications.

### Shape 4: `content` Parameter (Embedding and similarity functions)

Embedding and similarity functions take the reference as the content argument rather than in a prompt. Requires a multimodal embedding endpoint (e.g., `multimodalembedding@001`).

**Functions:** `AI.EMBED`, `AI.GENERATE_EMBEDDING`, `ML.GENERATE_EMBEDDING`, `AI.SIMILARITY`

```sql
-- AI.EMBED with inline ObjectRef
SELECT AI.EMBED(
  OBJ.MAKE_REF('gs://bucket/image.jpg', 'PROJECT.REGION.CONNECTION'),
  endpoint => 'multimodalembedding@001',
  connection_id => 'PROJECT.REGION.CONNECTION'
).result AS embedding;

-- AI.SIMILARITY with ObjectRef (returns a FLOAT64 directly, no .result accessor)
SELECT AI.SIMILARITY(
  OBJ.MAKE_REF('gs://bucket/img1.jpg', 'PROJECT.REGION.CONNECTION'),
  OBJ.MAKE_REF('gs://bucket/img2.jpg', 'PROJECT.REGION.CONNECTION'),
  endpoint => 'multimodalembedding@001',
  connection_id => 'PROJECT.REGION.CONNECTION'
) AS similarity;
```

### Shape Summary

| Shape | Functions | Object Table Required? | Input Method |
|-------|-----------|----------------------|--------------|
| STRUCT prompt | AI.GENERATE, AI.GENERATE_TEXT, AI.GENERATE_TABLE, AI.GENERATE_BOOL, AI.GENERATE_DOUBLE, AI.GENERATE_INT, ML.GENERATE_TEXT, AI.IF | No | `STRUCT(text AS prompt, [refs] AS object_refs)` |
| Tuple | AI.SCORE | No (object table is the convenient source) | `('scoring text', ref)` |
| Bare argument | AI.CLASSIFY, AI.AGG | No (object table is the convenient source) | `AI.CLASSIFY(ref, categories)`, `AI.AGG(STRUCT(ref), prompt)` |
| `content` parameter | AI.EMBED, AI.SIMILARITY, AI.GENERATE_EMBEDDING, ML.GENERATE_EMBEDDING | No | Pass the `ObjectRef` as the content argument |
| Object table (document processing) | ML.PROCESS_DOCUMENT | Yes | Object table rows as input to Document AI processor |
| Not supported | VECTOR_SEARCH, AI.SEARCH, AI.FORECAST, AI.DETECT_ANOMALIES, AI.PREDICT, AI.EVALUATE | — | Text/numeric input only |

> **`ObjectRefRuntime` still works everywhere.** Nothing in this section is a breaking change — wrapping a reference in `OBJ.GET_ACCESS_URL` is accepted by every function above. It is simply no longer necessary, and `AI.AGG`'s Known Issues give a reason to prefer the unwrapped form.
