# Guideline compliance status (two-person project)

This is a factual checklist against the supplied `Guidelines.pdf` and course announcement. It distinguishes an implemented SQL table from a conceptual ER entity. **The project is a working draft, not a verified final submission.**

| Requirement | Evidence now | Status | What remains |
| --- | --- | --- | --- |
| At least 50 entities | `schema.sql` has 70 tables. `docs/ENTITIES.md` lists their keys and meanings. Excluding 11 clear relationship tables gives 59 entity/subtype candidates under our classification. | **Not verified** | Classify every object in a complete conceptual ER model and check that at least 50 will be accepted as entities. A table count alone does not prove this. |
| One connected ER design | `tools/generate_design_artifacts.py` verifies that the 70-table foreign-key graph has one connected component. | **Relational graph verified; conceptual ER pending** | Draw and check the full conceptual ER graph, including the relationship constructs, as one connected model. |
| Weak entity | `order_lines` has owner `orders`, partial key `line_no`, and full key `(order_id, line_no)`. | **Example modeled** | Mark identifying relationship and participation clearly in the complete ER diagram. |
| ISA | `accounts` specializes into `customers`, `staff`, and `couriers`; subtype primary keys also reference `accounts`. | **Example modeled** | State and draw disjoint/overlap and total/partial constraints; database does not enforce discriminator/subtype consistency yet. |
| Ternary relationship | `stock_positions` stores a Seller × Variant × Warehouse triple and quantity. | **Example modeled** | Show this as a ternary relationship in the complete ER diagram. |
| Aggregation | `stock_reservations` links an order line to the Seller × Variant × Warehouse stock relationship. | **Example modeled** | Show the aggregation boundary and its participation/cardinality in the complete ER diagram. |
| Clear key for every entity | Every SQL table has a declared primary key; `docs/ENTITIES.md` lists the keys. | **Implemented at SQL level** | Transfer keys for the accepted conceptual entities into the complete ER diagram/report. |
| Report part 1: entities | `docs/REPORT.md` and `docs/ENTITIES.md` describe all 70 tables. | **Draft present** | Align the report's entity classification with the final conceptual ER model; relationship tables should not be counted as ordinary entities solely because they have a row. |
| Report part 2: relationships | `docs/REPORT.md`, `docs/RELATIONSHIPS.md`, and `docs/FOREIGN_KEYS.md` explain business relationships and list 102 FKs. | **Draft present** | Review cardinalities, participation, and the complete conceptual relationship set against the final diagram. |
| AI use for two-person group | `Guidelines.pdf` permits it if students check, understand, and verify the output. | **Permitted; student verification ongoing** | Both students must be able to explain and validate the design and implementation. |
| Database-backed web interface (announcement) | `app.py` runs catalog, cart, checkout, fulfillment, delivery, return, refund, and reports against SQLite. | **Core path implemented** | Confirm the assessed interface scope on the course page. |
| Required SQL queries (announcement) | `docs/SQL_QUERIES.md` documents several implemented SQL queries. | **Cannot verify** | The supplied PDF and syllabus do not give the exact required-query list; compare with the course page. |

`docs/er_conceptual.svg` illustrates the four special ER concepts only. `docs/er_full.svg` is a complete **table/FK graph**, not the complete **conceptual ER diagram** required to certify the first two guideline rows. The first clear deliverable gap is therefore a complete, reviewed conceptual ER model.
