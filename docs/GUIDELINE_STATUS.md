# Guideline compliance status (two-person project)

This is a factual checklist against the supplied `Guidelines.pdf` and course announcement. It distinguishes an implemented SQL table from a conceptual ER entity. **The project is a working draft, not a verified final submission.**

| Requirement | Evidence now | Status | What remains |
| --- | --- | --- | --- |
| At least 50 entities | `schema.sql` has 70 tables; [`CONCEPTUAL_ER.md`](CONCEPTUAL_ER.md) explicitly separates 59 entity/subtype candidates from 11 relationship sets. | **59 candidates documented; acceptance not verified** | Check that at least 50 of these meet the instructor's conceptual entity definition. A table count alone does not prove this. |
| One connected ER design | [`er_conceptual_full.svg`](er_conceptual_full.svg) is a single draft with 59 entity candidates and 11 relationship sets; its generator verifies one connected graph. | **Draft diagram connected** | Students and instructor should review the semantic relations and notation. |
| Weak entity | `order_lines` has owner `orders`, partial key `line_no`, full key `(order_id, line_no)`, and a double-border identifying link in the full draft. | **Modeled in full draft** | Review identifying participation and notation with the instructor. |
| ISA | `accounts` specializes into `customers`, `staff`, and `couriers`; the full draft uses an ISA triangle. | **Modeled in full draft** | Decide total/partial participation and enforce discriminator/subtype consistency if required. |
| Ternary relationship | `stock_positions` stores a Seller × Variant × Warehouse triple and quantity; the full draft shows a three-participant diamond. | **Modeled in full draft** | Review cardinality and notation with the instructor. |
| Aggregation | `stock_reservations` links an order line to the Seller × Variant × Warehouse stock relationship; the full draft shows an aggregation box. | **Modeled in full draft** | Review aggregation participation/cardinality with the instructor. |
| Clear key for every entity | Every SQL table has a declared primary key; the full draft labels keys for the 59 candidates. | **Documented** | Confirm keys for the accepted conceptual entities in the final report. |
| Report part 1: entities | `docs/REPORT.md` and `docs/ENTITIES.md` now describe the 59 proposed entity/subtype sets separately from 11 relationship sets. | **Draft aligned with diagram** | Review whether the proposed entities and explanations satisfy the instructor's conceptual criteria. |
| Report part 2: relationships | `docs/REPORT.md`, `docs/RELATIONSHIPS.md`, and `docs/FOREIGN_KEYS.md` explain business relationships and list 102 FKs. | **Draft present** | Review cardinalities, participation, and the complete conceptual relationship set against the final diagram. |
| AI use for two-person group | `Guidelines.pdf` permits it if students check, understand, and verify the output. | **Permitted; student verification ongoing** | Both students must be able to explain and validate the design and implementation. |
| Database-backed web interface (announcement) | `app.py` runs catalog, cart, checkout, fulfillment, delivery, return, refund, and reports against SQLite. | **Core path implemented** | Confirm the assessed interface scope on the course page. |
| Required SQL queries (announcement) | `docs/SQL_QUERIES.md` documents several implemented SQL queries. | **Cannot verify** | The supplied PDF and syllabus do not give the exact required-query list; compare with the course page. |

`docs/er_conceptual.svg` is a small teaching example. `docs/er_full.svg` is a complete **table/FK graph**. The new `docs/er_conceptual_full.svg` is a complete **conceptual ER draft** with explicit entity/relationship classification. Its existence closes the missing-file gap, but does **not** certify the instructor's 50-entity interpretation or final notation. See [`CONCEPTUAL_ER.md`](CONCEPTUAL_ER.md) for the review steps.
