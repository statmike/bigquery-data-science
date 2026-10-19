# Choosing between these and the `AI.*` functions

> **Source:** [`bigquery-ai/reference/cloud-ai-service-models.md#choosing-between-these-and-the-ai-functions`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/cloud-ai-service-models.md#choosing-between-these-and-the-ai-functions)

Every member has a generative alternative — [`AI.GENERATE`](https://github.com/statmike/bigquery-data-science/blob/main/bigquery-ai/reference/general-purpose-functions.md) over an `ObjectRef` reads audio and images directly, and a prompt can translate, score sentiment or extract entities. Each notebook runs both over the same rows so the comparison is measured rather than argued. What the comparisons keep showing:

**Reach for a Cloud AI service model** when the output is a record: a fixed API version, a published per-unit price, a closed vocabulary, and behavior that does not move when a model default does. When the service cannot do something, it says so — an unsupported language, an unsupported feature, an unreadable file all arrive as errors in a status column.

**Reach for an `AI.*` function** when the deliverable is not the service's output: a summary rather than a transcript, your categories rather than the taxonomy's, translate-and-rewrite rather than translate. It will also answer questions the service refuses — and that is the trade, because it answers them the same confident way whether or not it is right, with no status column and no confidence beside the answer. A refusal is information; a fluent guess is not.

**Use both** when the record and the analysis are different artifacts: the service output as the durable, priced, inspectable column, and the generative function over *that column* — where the input is text you can read instead of media you cannot.
