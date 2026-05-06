# Procurement Metadata

## Continuation Procurement

Use `is_continuation_procurement` to mark whether a structured procurement record belongs to a continuation procurement cycle.

Default:

```text
false
```

Mark as `true` only when the source explicitly indicates continuation procurement, for example:

```text
接续采购
续约采购
期满接续
协议期满后接续
带量采购接续
续采
```

Do not infer continuation status from year, province, or price alone. If the source does not say it is continuation procurement, keep `is_continuation_procurement=false`.

The existing imported datasets are currently marked as non-continuation procurement.
