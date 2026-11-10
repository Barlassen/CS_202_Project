"""Check the conceptual ER model against schema.sql and the project guidelines, then
generate the ER diagrams (course notation) and the two-part report.

    python3 tools/build_er.py            # check + write DOT/Markdown + render SVG
    python3 tools/build_er.py --check    # only run the checks

Rendering uses Graphviz compiled to WebAssembly, so no system install is needed:
    cd tools/render && npm install       # once
"""
from collections import defaultdict
from pathlib import Path
import re
import sqlite3
import subprocess
import sys

import er_model as M

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ER_DIR = DOCS / "er"
RENDER = ROOT / "tools" / "render"
AGG = "AGG"  # participant target meaning "the aggregated Stocks relationship"


# --------------------------------------------------------------------------- schema
def read_schema():
    db = sqlite3.connect(":memory:")
    db.executescript((ROOT / "schema.sql").read_text())
    tables = {}
    for name, sql in db.execute("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY rowid"):
        cols = [dict(name=r[1], type=r[2], notnull=bool(r[3]) or r[5] > 0, pk=r[5]) for r in db.execute(f"PRAGMA table_info({name})")]
        fks = defaultdict(lambda: dict(parent=None, cols=[], ref=[]))
        for r in db.execute(f"PRAGMA foreign_key_list({name})"):
            fks[r[0]]["parent"] = r[2]
            fks[r[0]]["cols"].append(r[3])
            fks[r[0]]["ref"].append(r[4])
        uniques = []
        for idx in db.execute(f"PRAGMA index_list({name})"):
            # A partial unique index (idx[4]) holds only for some rows, so it is no key constraint.
            if idx[2] and not idx[4]:
                uniques.append({r[2] for r in db.execute(f"PRAGMA index_info({idx[1]})")})
        pk = [c["name"] for c in sorted(cols, key=lambda c: c["pk"]) if c["pk"]]
        if pk:
            uniques.append(set(pk))
        tables[name] = dict(cols=cols, fks=list(fks.values()), uniques=uniques, pk=pk, checks=parse_checks(sql))
    return tables


def parse_checks(sql):
    """Return {column: [check expression, ...]} and table-level checks under None."""
    found = defaultdict(list)
    for match in re.finditer(r"CHECK\s*\(", sql):
        depth, i = 1, match.end()
        while depth:
            depth += {"(": 1, ")": -1}.get(sql[i], 0)
            i += 1
        expr = sql[match.end():i - 1].strip()
        line_start = sql.rfind("\n", 0, match.start()) + 1
        segment = sql[line_start:match.start()]
        column = re.findall(r"(\w+)\s+(?:INTEGER|TEXT|REAL)\b[^,]*$", segment)
        found[column[-1] if column else None].append(expr)
    return found


# --------------------------------------------------------------------------- model
def name_of(table):
    return "_".join(part.capitalize() for part in table.split("_"))


def build_model(tables):
    problems = []
    entities = set(M.ENTITIES)
    rel_tables = set(M.RELATIONSHIP_TABLES)
    if entities & rel_tables:
        problems.append(f"Tables classified twice: {sorted(entities & rel_tables)}")
    if set(tables) != entities | rel_tables:
        problems.append(f"Unclassified tables: {sorted(set(tables) - entities - rel_tables)}; "
                        f"unknown tables: {sorted((entities | rel_tables) - set(tables))}")

    isa_children = set(M.ISA["children"])
    ent = {}
    for table in M.ENTITIES:
        t = tables[table]
        fk_cols = {c for fk in t["fks"] for c in fk["cols"]}
        attrs = [c for c in t["cols"] if c["name"] not in fk_cols]
        info = dict(table=table, name=name_of(table), area=M.ENTITIES[table][0], text=M.ENTITIES[table][1],
                    attrs=attrs, key=[], partial=[], inherited=False, weak_owner=M.WEAK_ENTITIES.get(table))
        if table in isa_children:
            info["inherited"] = True
        elif info["weak_owner"]:
            owner_fk = [fk for fk in t["fks"] if fk["parent"] == info["weak_owner"]]
            info["partial"] = [c for c in t["pk"] if c not in owner_fk[0]["cols"]]
            if not info["partial"]:
                problems.append(f"Weak entity {table} has no partial key")
        else:
            info["key"] = [c for c in t["pk"] if c not in fk_cols]
            if not info["key"] or len(info["key"]) != len(t["pk"]):
                problems.append(f"Entity {table} has no key of its own (PK {t['pk']})")
        ent[table] = info
    for table, col in M.DERIVED:
        if table not in ent or col not in {c["name"] for c in ent[table]["attrs"]}:
            problems.append(f"Derived attribute {table}.{col} is not an attribute of an entity set")

    rels = []
    used_fk_keys = set()
    for table in M.ENTITIES:
        for fk in tables[table]["fks"]:
            if table in isa_children and fk["parent"] == M.ISA["parent"]:
                continue
            key = (table, fk["cols"][0])
            if key not in M.FK_RELATIONSHIPS:
                problems.append(f"Foreign key {table}.{fk['cols']} -> {fk['parent']} has no relationship in er_model.py")
                continue
            used_fk_keys.add(key)
            spec = M.FK_RELATIONSHIPS[key]
            roles = spec[2] if len(spec) > 2 else (None, None)
            notnull = all(next(c for c in tables[table]["cols"] if c["name"] == col)["notnull"] for col in fk["cols"])
            # The foreign key is unique when some unique column set lies inside it, e.g.
            # payments(order_id, customer_id) is unique because order_id alone is.
            one_to_one = any(u <= set(fk["cols"]) for u in tables[table]["uniques"])
            parent = AGG if fk["parent"] == M.AGGREGATED else fk["parent"]
            name = spec[0]
            rels.append(dict(
                name=name, text=spec[1], area=ent[table]["area"], attrs=[],
                identifying=M.WEAK_ENTITIES.get(table) == fk["parent"],
                sql=f"foreign key `{table}({', '.join(fk['cols'])})` → `{fk['parent']}`",
                parts=[dict(target=table, key=True, total=notnull, role=roles[0]),
                       dict(target=parent, key=one_to_one, total=(name, fk["parent"]) in M.TOTAL_PARTICIPATION, role=roles[1])]))
    for key in set(M.FK_RELATIONSHIPS) - used_fk_keys:
        problems.append(f"er_model.py names a relationship for a foreign key that does not exist: {key}")

    for table, (area, name, text) in M.RELATIONSHIP_TABLES.items():
        t = tables[table]
        fk_cols = {c for fk in t["fks"] for c in fk["cols"]}
        parts = []
        for fk in t["fks"]:
            target = AGG if fk["parent"] == M.AGGREGATED and table != M.AGGREGATED else fk["parent"]
            parts.append(dict(target=target, key=False, total=(name, fk["parent"]) in M.TOTAL_PARTICIPATION, role=None))
        parts.reverse()  # PRAGMA lists foreign keys last-declared first
        rels.append(dict(name=name, text=text, area=area, identifying=False, table=table,
                         attrs=[c for c in t["cols"] if c["name"] not in fk_cols],
                         sql=f"table `{table}` (primary key {', '.join(t['pk'])})", parts=parts))

    names = [r["name"] for r in rels]
    for dup in {n for n in names if names.count(n) > 1}:
        problems.append(f"Relationship name used twice: {dup}")
    clash = set(names) & {e["name"] for e in ent.values()}
    if clash:
        problems.append(f"Relationship names equal to entity names: {sorted(clash)}")
    return ent, rels, problems


def kind(rel):
    targets = [p["target"] for p in rel["parts"]]
    if rel["identifying"]:
        return "identifying relationship of a weak entity (one owner, many weak entities)"
    if AGG in targets:
        return "relationship with an aggregation"
    if len(targets) >= 3:
        return f"{len(targets)}-ary (ternary) relationship"
    a, b = rel["parts"]
    if a["key"] and b["key"]:
        return "binary, one-to-one"
    if a["key"] or b["key"]:
        return "binary, many-to-one"
    return "binary, many-to-many"


def check_guidelines(ent, rels):
    """Return [(requirement, ok, evidence)] for Guidelines.pdf items 1-4."""
    graph = defaultdict(set)
    for i, rel in enumerate(rels):
        for p in rel["parts"]:
            graph[f"R{i}"].add(p["target"])
            graph[p["target"]].add(f"R{i}")
    stocks = next(i for i, r in enumerate(rels) if r.get("table") == M.AGGREGATED)
    graph[AGG].add(f"R{stocks}")
    graph[f"R{stocks}"].add(AGG)
    for child in M.ISA["children"]:
        graph["ISA"] |= {child, M.ISA["parent"]}
        graph[child].add("ISA")
        graph[M.ISA["parent"]].add("ISA")
    nodes = set(graph) | set(ent)
    seen, stack = set(), [next(iter(ent))]
    while stack:
        node = stack.pop()
        if node not in seen:
            seen.add(node)
            stack.extend(graph[node] - seen)
    isolated = sorted(n for n in nodes - seen if n in ent)

    weak_ok = []
    for table, owner in M.WEAK_ENTITIES.items():
        ident = [r for r in rels if r["identifying"] and r["parts"][0]["target"] == table]
        good = len(ident) == 1 and ident[0]["parts"][0]["key"] and ident[0]["parts"][0]["total"] and ident[0]["parts"][1]["target"] == owner
        weak_ok.append((table, good))
    ternary = [r["name"] for r in rels if len({p["target"] for p in r["parts"]}) >= 3]
    aggregation = [r["name"] for r in rels if any(p["target"] == AGG for p in r["parts"])]
    keyless = [t for t, e in ent.items() if not (e["key"] or e["partial"] or e["inherited"])]
    return [
        ("1. At least 50 entities (two-person project)", len(ent) >= 50, f"{len(ent)} entity sets"),
        ("2. One connected ER design", not isolated and len(seen) == len(nodes),
         f"{len(ent)} entity sets, {len(rels)} relationship sets and the ISA hierarchy form one connected component" if not isolated else f"not connected: {isolated}"),
        ("3a. Weak entity", bool(weak_ok) and all(ok for _, ok in weak_ok),
         ", ".join(f"{name_of(t)} (owner {name_of(M.WEAK_ENTITIES[t])})" for t, _ in weak_ok) + "; each has a partial key and total participation with a key constraint in its identifying relationship"),
        ("3b. ISA hierarchy", bool(M.ISA["children"]),
         f"{name_of(M.ISA['parent'])} ISA {', '.join(name_of(c) for c in M.ISA['children'])} (overlap: {'allowed' if M.ISA['overlap'] else 'not allowed'}, covering: {'yes' if M.ISA['covering'] else 'no'})"),
        ("3c. Ternary relationship", bool(ternary), ", ".join(ternary)),
        ("3d. Aggregation", bool(aggregation), f"Stocks is aggregated; used by {', '.join(aggregation)}"),
        ("4. Every entity has a clearly defined key", not keyless,
         "own key underlined for strong entity sets, partial key (dashed) + owner key for weak ones, key inherited from Accounts for subclasses" if not keyless else f"missing: {keyless}"),
    ]


# --------------------------------------------------------------------------- DOT
def q(text):
    return '"' + str(text).replace("\\", "\\\\").replace('"', '\\"') + '"'


def attr_label(col, underline):
    return f"<<U>{col}</U>>" if underline else q(col)


def build_dot(ent, rels, focus, title, only=None, isa=None, overview=False):
    """focus: set of entity tables drawn with attributes; other participants are drawn grey.

    only: draw just these relationship names (their participants get attributes).
    isa: force the ISA hierarchy on or off; by default it is drawn when focus touches it.
    overview: every entity and relationship set without attributes, grouped in one box per
    business area, so the whole connected design can be read on one page. The attributes
    are on the area pages.
    """
    lines = [
        "digraph ER {",
        f'graph [compound=true, rankdir=TB, newrank=true, nodesep=0.22, ranksep=0.42, fontname="Helvetica", fontsize=22, labelloc=t, label={q(title)}, pad=0.3];',
        'node [fontname="Helvetica", fontsize=11, color="#222222", fontcolor="#111111"];',
        'edge [color="#333333", arrowsize=0.8, fontname="Helvetica", fontsize=9];',
    ]
    if only is not None:
        chosen = [r for r in rels if r["name"] in only]
        focus = set(focus) | {p["target"] for r in chosen for p in r["parts"] if p["target"] != AGG}
    else:
        chosen = [r for r in rels if any(p["target"] in focus for p in r["parts"])]
    stocks = next(r for r in rels if r.get("table") == M.AGGREGATED)
    stocks_parts = {p["target"] for p in stocks["parts"]}
    uses_agg = any(p["target"] == AGG for r in chosen for p in r["parts"]) or stocks in chosen
    if uses_agg and stocks not in chosen:
        chosen.append(stocks)
    if uses_agg and only is not None:
        focus |= stocks_parts
    drawn = set(focus) | {p["target"] for r in chosen for p in r["parts"] if p["target"] != AGG}
    if isa is None:
        isa = M.ISA["parent"] in focus or bool(set(M.ISA["children"]) & focus)
    if isa:
        drawn |= {M.ISA["parent"], *M.ISA["children"]}

    def entity_nodes(table):
        e = ent[table]
        out = []
        if overview:
            # Entity sets inside the aggregation box are away from their area box, so they name it.
            label = e["name"] + (chr(10) + "(" + M.AREAS[e["area"]] + ")" if table in in_cluster else "")
            out.append(f'E_{table} [shape=box, penwidth={3 if e["weak_owner"] else 1}, label={q(label)}];')
        elif table in focus:
            out.append(f'E_{table} [shape=box, penwidth={3 if e["weak_owner"] else 1}, label={q(e["name"])}];')
            for col in e["attrs"]:
                c = col["name"]
                if c in e["partial"]:
                    out.append(f'P__{table}__{c} [shape=ellipse, fontsize=9, margin="0.04,0.02", height=0.3, label={attr_label(c, True)}];')
                    out.append(f"P__{table}__{c} -> E_{table} [dir=none];")
                else:
                    dashed = ", style=dashed" if (table, c) in M.DERIVED else ""
                    out.append(f'A__{table}__{c} [shape=ellipse, fontsize=9, margin="0.04,0.02", height=0.3{dashed}, label={attr_label(c, c in e["key"])}];')
                    out.append(f"A__{table}__{c} -> E_{table} [dir=none];")
        else:
            area = M.AREAS[e["area"]]
            out.append(f'E_{table} [shape=box, style="filled,dashed", fillcolor="#eeeeee", penwidth={3 if e["weak_owner"] else 1}, label={q(e["name"] + chr(10) + "(" + area + ")")}];')
        return out

    def rel_nodes(i, rel):
        out = [f'R{i} [shape=diamond, penwidth={3 if rel["identifying"] else 1}, margin="0.02,0.02", label={q(rel["name"])}];']
        for col in [] if overview else rel["attrs"]:
            out.append(f'RA{i}__{col["name"]} [shape=ellipse, fontsize=9, margin="0.04,0.02", height=0.3, label={q(col["name"])}];')
            out.append(f'RA{i}__{col["name"]} -> R{i} [dir=none];')
        return out

    index = {id(r): i for i, r in enumerate(rels)}
    stocks_i = index[id(stocks)]

    def participant_edges(i, rel):
        # Edges run first participant -> diamond -> other participants, so a foreign-key
        # relationship ranks the referencing entity above the referenced one. Graphviz then
        # lays the model out in layers instead of one very wide row. Arrowheads always sit
        # at the diamond, as the key-constraint arrow in the slides does.
        out = []
        for n, p in enumerate(rel["parts"]):
            style = []
            if p["target"] == AGG:
                out.append(f"R{i} -> R{stocks_i} [dir=none, lhead=cluster_agg, penwidth={3 if p['total'] else 1}];")
                continue
            if n == 0:
                style.append("dir=forward, arrowhead=normal" if p["key"] else "dir=none")
            else:
                style.append("dir=back, arrowtail=normal" if p["key"] else "dir=none")
            if p["total"]:
                style.append("penwidth=3")
            if p["role"]:
                style.append(f"label={q(p['role'])}")
            ends = (f"E_{p['target']}", f"R{i}") if n == 0 else (f"R{i}", f"E_{p['target']}")
            out.append(f"{ends[0]} -> {ends[1]} [{', '.join(style)}];")
        return out
    in_cluster = stocks_parts if uses_agg else set()
    isa_lines = []
    if isa:
        note = f"overlap: {'yes' if M.ISA['overlap'] else 'no'}\\ncovering: {'yes' if M.ISA['covering'] else 'no'}"
        isa_lines.append(f'ISA [shape=triangle, label="ISA", fontsize=10, margin=0, xlabel="{note}"];')
    if overview:
        # Nodes are declared inside their area box; edges come after all boxes, at top level.
        def home(rel):
            areas = {ent[p["target"]]["area"] for p in rel["parts"] if p["target"] != AGG}
            return areas.pop() if len(areas) == 1 and rel is not stocks else None
        for key, label in M.AREAS.items():
            lines.append(f'subgraph cluster_area_{key} {{ label={q(label)}; style=rounded; color="#8a8a8a"; penwidth=1.2; fontsize=16; margin=12;')
            for table in sorted(t for t in drawn - in_cluster if ent[t]["area"] == key):
                lines += entity_nodes(table)
            for rel in chosen:
                if home(rel) == key:
                    lines += rel_nodes(index[id(rel)], rel)
            if isa and key == ent[M.ISA["parent"]]["area"]:
                lines += isa_lines
                isa_lines = []
            lines.append("}")
        for rel in chosen:
            if rel is not stocks and home(rel) is None:
                lines += rel_nodes(index[id(rel)], rel)
    else:
        for table in sorted(drawn - in_cluster):
            lines += entity_nodes(table)
    if uses_agg:
        lines.append('subgraph cluster_agg { style=dashed; color="#222222"; penwidth=1.4; margin=14; label="Aggregation: Stocks"; fontsize=12; labeljust=l;')
        for table in sorted(in_cluster):
            lines += entity_nodes(table)
        lines += rel_nodes(stocks_i, stocks)
        lines += participant_edges(stocks_i, stocks)
        lines.append("}")

    for rel in chosen:
        i = index[id(rel)]
        if rel is stocks:
            continue
        if not overview:
            lines += rel_nodes(i, rel)
        lines += participant_edges(i, rel)

    if isa:
        lines += isa_lines
        lines.append(f"E_{M.ISA['parent']} -> ISA [dir=none];")
        for child in M.ISA["children"]:
            lines.append(f"ISA -> E_{child} [dir=none];")
    lines.append("}")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- legend
# One row per symbol: (section, name, DOT body, explanation). Each body is drawn with the
# same Graphviz settings as the diagrams, so the legend shows exactly what the pages show.
# The examples are real relationship sets of MarketLab.
E = 'shape=box'
ATTR = 'shape=ellipse, fontsize=9, margin="0.04,0.02", height=0.3'
LEGEND = [
    ("Basic symbols", "entity",
     f'e [{E}, label="Customers"];',
     "<b>Entity set</b> (rectangle): a collection of similar objects, stored as one table."),
    ("Basic symbols", "attribute",
     f'k [{ATTR}, label=<<U>order_id</U>>]; a [{ATTR}, label="status"]; e [{E}, label="Orders"]; k -> e [dir=none]; a -> e [dir=none];',
     "<b>Attribute</b> (oval) of the entity set it is attached to. The <b>key</b> attribute, which identifies each entity, is <u>underlined</u>."),
    ("Basic symbols", "derived",
     f'd [{ATTR}, style=dashed, label="total_cents"]; e [{E}, label="Orders"]; d -> e [dir=none];',
     "<b>Derived attribute</b> (dashed oval): computed from other data. An order's total is the sum over its lines."),
    ("Basic symbols", "relationship",
     f'a [{E}, label="Seller_Organizations"]; r [shape=diamond, margin="0.02,0.02", label="Employs"]; b [{E}, label="Staff"]; '
     f'x [{ATTR}, label="assigned_at"]; a -> r [dir=none]; r -> b [dir=none]; x -> r [dir=none];',
     "<b>Relationship set</b> (diamond): connects the entity sets on its lines. An oval on the diamond is a "
     "<b>descriptive attribute</b> of the relationship (here: since when the staff member works for the seller)."),
    ("Basic symbols", "roles",
     f'c [{E}, label="Categories"]; r [shape=diamond, margin="0.02,0.02", label="Subcategory_Of"]; '
     'c -> r [arrowhead=normal, label="child"]; r -> c [dir=none, label="parent"];',
     "<b>Role label</b> on a line: when one entity set takes part twice in a relationship, each line names its role."),

    ("Cardinality and participation (read the lines at the diamond)", "many-many",
     f'a [{E}, label="Seller_Organizations"]; r [shape=diamond, margin="0.02,0.02", label="Employs"]; b [{E}, label="Staff"]; '
     'a -> r [dir=none]; r -> b [dir=none];',
     "<b>Thin line, no arrow:</b> no constraint. A seller may employ many staff members and a staff member may work for "
     "many sellers: <b>many-to-many (M:N)</b>."),
    ("Cardinality and participation (read the lines at the diamond)", "key",
     f'a [{E}, label="Support_Tickets"]; r [shape=diamond, margin="0.02,0.02", label="About_Order"]; b [{E}, label="Orders"]; '
     'a -> r [arrowhead=normal]; r -> b [dir=none];',
     "<b>Arrow into the diamond = key constraint (at most one).</b> Each ticket is about at most one order; an order may "
     "have many tickets: <b>one-to-many (1:N)</b>. The arrow is on the line of the entity set that is in the relationship at most once."),
    ("Cardinality and participation (read the lines at the diamond)", "total",
     f'a [{E}, label="Couriers"]; r [shape=diamond, margin="0.02,0.02", label="Serves"]; b [{E}, label="Delivery_Zones"]; '
     'a -> r [dir=none, penwidth=3]; r -> b [dir=none];',
     "<b>Thick line = total participation (at least one).</b> Every courier serves at least one delivery zone. "
     "A thin line is partial participation: zero is allowed."),
    ("Cardinality and participation (read the lines at the diamond)", "exactly-one",
     f'a [{E}, label="Orders"]; r [shape=diamond, margin="0.02,0.02", label="Places"]; b [{E}, label="Customers"]; '
     'a -> r [arrowhead=normal, penwidth=3]; r -> b [dir=none];',
     "<b>Thick line with arrow = exactly one.</b> Every order is placed by exactly one customer; a customer places "
     "any number of orders (1:N)."),
    ("Cardinality and participation (read the lines at the diamond)", "one-one",
     f'a [{E}, label="Payments"]; r [shape=diamond, margin="0.02,0.02", label="Paid_By"]; b [{E}, label="Orders"]; '
     'a -> r [arrowhead=normal, penwidth=3]; r -> b [dir=back, arrowtail=normal];',
     "<b>Arrows on both lines: one-to-one (1:1).</b> Each payment is for exactly one order, and an order has at most one payment."),

    ("Advanced constructs", "weak",
     f'P__legend__line_no [{ATTR}, label=<<U>line_no</U>>]; w [{E}, penwidth=3, label="Order_Lines"]; '
     f'r [shape=diamond, penwidth=3, margin="0.02,0.02", label="Contains"]; o [{E}, label="Orders"]; '
     'P__legend__line_no -> w [dir=none]; w -> r [arrowhead=normal, penwidth=3]; r -> o [dir=none, penwidth=3];',
     "<b>Weak entity set</b> (thick rectangle) and its <b>identifying relationship</b> (thick diamond). The weak entity has no "
     "key of its own: its <b>partial key</b> (dashed underline) is unique only within its owner, so an order line is identified by "
     "order_id + line_no. The thick arrow says each line belongs to exactly one order."),
    ("Advanced constructs", "ternary",
     f'a [{E}, label="Seller_Organizations"]; b [{E}, label="Variants"]; c [{E}, label="Warehouses"]; '
     f'r [shape=diamond, margin="0.02,0.02", label="Stocks"]; x [{ATTR}, label="available_qty"]; '
     'a -> r [dir=none]; r -> b [dir=none]; r -> c [dir=none]; x -> r [dir=none];',
     "<b>Ternary relationship</b>: one diamond joins three entity sets. A stock position is one (seller, variant, warehouse) "
     "combination with its available quantity."),
    ("Advanced constructs", "aggregation",
     f'subgraph cluster_agg {{ style=dashed; label="Aggregation: Stocks"; fontsize=10; labeljust=l; margin=8; '
     f's [{E}, label="Seller_Org."]; v [{E}, label="Variants"]; h [{E}, label="Warehouses"]; '
     f'r [shape=diamond, margin="0.02,0.02", label="Stocks"]; s -> r [dir=none]; r -> v [dir=none]; r -> h [dir=none]; }} '
     f'l [{E}, label="Order_Lines"]; x [shape=diamond, margin="0.02,0.02", label="Reserves"]; '
     'l -> x [dir=none, penwidth=3]; x -> r [dir=none, lhead=cluster_agg];',
     "<b>Aggregation</b> (dashed box): the Stocks relationship together with its entity sets is treated as one entity set, "
     "so another relationship can connect to it. A line that ends at the box (Reserves) relates to a whole stock position."),
    ("Advanced constructs", "isa",
     f'p [{E}, label="Accounts"]; t [shape=triangle, label="ISA", fontsize=10, margin=0, xlabel="overlap: no\\ncovering: yes"]; '
     f'c1 [{E}, label="Customers"]; c2 [{E}, label="Staff"]; c3 [{E}, label="Couriers"]; '
     'p -> t [dir=none]; t -> c1 [dir=none]; t -> c2 [dir=none]; t -> c3 [dir=none];',
     "<b>ISA hierarchy</b> (triangle): the subclasses inherit the key and attributes of Accounts. "
     "<i>overlap: no</i> = an account is in at most one subclass; <i>covering: yes</i> = every account is in one of them."),

    ("How the pages are drawn", "other-area",
     f'e [{E}, style="filled,dashed", fillcolor="#eeeeee", label="Customers\\n(People and accounts)"];',
     "<b>Area pages:</b> a grey dashed rectangle is an entity set of another area, named with its area in brackets. "
     "Its attributes are on its own area page."),
    ("How the pages are drawn", "area-box",
     f'subgraph cluster_a {{ label="Orders and payment"; style=rounded; color="#8a8a8a"; penwidth=1.2; fontsize=12; margin=8; '
     f'e [{E}, label="Orders"]; f [{E}, label="Invoices"]; }}',
     "<b>Overview page:</b> a grey rounded box groups the entity sets of one business area. It only helps reading; "
     "it is not an ER construct. Relationships between two areas are drawn outside the boxes."),
]


def legend_dot(body):
    return ("digraph L {\n"
            'graph [rankdir=LR, compound=true, nodesep=0.25, ranksep=0.35, pad=0.05, fontname="Helvetica"];\n'
            'node [fontname="Helvetica", fontsize=11, color="#222222", fontcolor="#111111"];\n'
            'edge [color="#333333", arrowsize=0.8, fontname="Helvetica", fontsize=9];\n'
            f"{body}\n}}\n")


def inline_svg(path, prefix):
    """The SVG element of a Graphviz file, with ids made unique so several fit in one HTML page."""
    svg = path.read_text(encoding="utf-8")
    svg = svg[svg.index("<svg"):]
    return re.sub(r'id="([^"]+)"', lambda m: f'id="{prefix}_{m.group(1)}"', svg)


def write_legend_html(pages):
    """docs/er/legend.html: the notation, plus the list of pages of the diagram PDF."""
    rows, section = [], None
    for sec, name, _, text in LEGEND:
        if sec != section:
            rows.append(f'<tr><th colspan="2">{sec}</th></tr>')
            section = sec
        rows.append(f'<tr><td class="sym">{inline_svg(ER_DIR / "legend" / f"{name}.svg", "lg_" + name.replace("-", "_"))}</td><td>{text}</td></tr>')
    contents = "".join(f"<li>Page {n}: {label}</li>" for n, label in pages)
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>MarketLab ER diagram: notation</title>
<style>
body {{ font-family: Helvetica, Arial, sans-serif; color: #111; margin: 0; }}
h1 {{ font-size: 22pt; margin: 0 0 4pt; }}
.sub {{ font-size: 11pt; margin: 0 0 12pt; color: #333; }}
.cols {{ display: flex; gap: 22pt; align-items: flex-start; }}
.cols > div {{ flex: 1; }}
table {{ border-collapse: collapse; width: 100%; font-size: 10.5pt; }}
th {{ text-align: left; font-size: 12pt; padding: 10pt 0 4pt; border-bottom: 1.5pt solid #222; }}
td {{ padding: 5pt 6pt; border-bottom: 0.5pt solid #ccc; vertical-align: middle; line-height: 1.3; }}
td.sym {{ width: 46%; text-align: center; }}
td.sym svg {{ max-width: 100%; height: auto; max-height: 120pt; }}
.box {{ border: 1pt solid #888; border-radius: 6pt; padding: 8pt 12pt; font-size: 10.5pt; margin-top: 12pt; line-height: 1.4; }}
.box ul {{ margin: 4pt 0 0; padding-left: 16pt; }}
</style></head><body>
<h1>MarketLab — ER diagram: notation and contents</h1>
<p class="sub">Notation of the course slides (Ramakrishnan &amp; Gehrke, chapter 2). Every symbol below is drawn exactly as on the diagram pages; the examples are relationship sets of MarketLab.</p>
<div class="cols">
<div><table>{"".join(rows[:rows.index('<tr><th colspan="2">Advanced constructs</th></tr>')])}</table></div>
<div><table>{"".join(rows[rows.index('<tr><th colspan="2">Advanced constructs</th></tr>'):])}</table>
<div class="box"><b>Contents of this PDF</b><ul>{contents}</ul>
The overview shows that all entity sets form one connected design; each area page repeats its part of the design with all attributes.</div>
</div></div>
</body></html>
"""
    (ER_DIR / "legend.html").write_text(html, encoding="utf-8")


def pdf_pages(order):
    """The pages of the diagram PDF as (HTML, width pt, height pt): legend, overview, areas."""
    legend = (ER_DIR / "legend.html").read_text(encoding="utf-8")
    pages = [(legend, *LEGEND_PAGE)]
    for name in order:
        svg = inline_svg(ER_DIR / f"{name}.svg", "d")
        w, h = map(float, re.search(r'width="([\d.]+)pt" height="([\d.]+)pt"', svg).groups())
        html = (f'<!doctype html><html><head><meta charset="utf-8"><title>{name}</title>'
                f"<style>body {{ margin: 0; }} svg {{ display: block; }}</style></head><body>{svg}</body></html>")
        pages.append((html, w + 2 * PAGE_MARGIN, h + 2 * PAGE_MARGIN))
    return pages


PAGE_MARGIN = 20  # pt around each diagram
LEGEND_PAGE = (1191, 1100)  # pt; A3 width, tall enough for the whole notation on one page

BROWSERS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "google-chrome", "chromium", "chromium-browser", "msedge",
]


def make_pdf(order):
    """Print each page with a headless Chromium browser (Chrome or Edge) at its own size, then
    join them into docs/MarketLab_ER_Diagram.pdf. Needs pypdf; set ER_BROWSER to the browser
    executable if it is not found automatically.
    """
    import os
    import shutil
    import tempfile
    try:
        from pypdf import PdfWriter
    except ImportError:
        print("PDF skipped: pip install pypdf")
        return
    candidates = [os.environ["ER_BROWSER"]] if os.environ.get("ER_BROWSER") else BROWSERS
    browser = next((c for c in candidates if Path(c).exists() or shutil.which(c)), None)
    if not browser:
        print("PDF skipped: no Chrome or Edge found; set ER_BROWSER to its executable.")
        return
    out = DOCS / "MarketLab_ER_Diagram.pdf"
    writer = PdfWriter()
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for n, (html, w, h) in enumerate(pdf_pages(order)):
            margin = 30 if n == 0 else PAGE_MARGIN
            html = html.replace("</head>", f"<style>@page {{ size: {w:.0f}pt {h:.0f}pt; margin: {margin}pt; }}</style></head>", 1)
            src, pdf = tmp / f"page{n}.html", tmp / f"page{n}.pdf"
            src.write_text(html, encoding="utf-8")
            subprocess.run([browser, "--headless", "--disable-gpu", "--no-pdf-header-footer", f"--user-data-dir={tmp / 'profile'}",
                            f"--print-to-pdf={pdf}", src.resolve().as_uri()], check=True, capture_output=True)
            writer.append(str(pdf))
            if len(writer.pages) != n + 1:
                print(f"Warning: page {n + 1} of the PDF did not fit on one sheet")
        writer.add_metadata({"/Title": "MarketLab ER Diagram"})
        with open(out, "wb") as f:
            writer.write(f)
    print(f"Wrote {out.relative_to(ROOT)} ({len(writer.pages)} pages)")


def postprocess_svg(path):
    """Draw key underlines as real lines.

    SVG viewers differ in whether they honour text-decoration, and Graphviz cannot draw
    the dashed underline the slides use for partial keys, so every underlined label is
    replaced by an explicit line: solid for a key, dashed for a partial key (node id P__...).
    """
    svg = path.read_text()

    def underline(match):
        block = match.group(0)
        if 'text-decoration="underline"' not in block:
            return block
        cx = float(re.search(r'<ellipse[^>]* cx="([-\d.]+)"', block).group(1))
        text = re.search(r'<text[^>]* x="([-\d.]+)" y="([-\d.]+)"', block)
        x, y = float(text.group(1)), float(text.group(2))
        width = 2 * (cx - x)
        dash = ' stroke-dasharray="2.5,1.8"' if "<title>P__" in block else ""
        block = block.replace(' text-decoration="underline"', "")
        line = f'<line x1="{x:.2f}" y1="{y + 2:.2f}" x2="{x + width:.2f}" y2="{y + 2:.2f}" stroke="black" stroke-width="0.9"{dash}/>\n'
        return block.replace("</g>", line + "</g>")

    svg = re.sub(r'<g id="[^"]*" class="node">.*?</g>', underline, svg, flags=re.S)
    path.write_text(svg)


# --------------------------------------------------------------------------- report
def domain(table_info, col):
    parts = [col["type"] or "ANY"]
    checks = table_info["checks"].get(col["name"], [])
    parts += [f"CHECK {c}" for c in checks]
    return "; ".join(parts)


def column_notes(table_info, col, e):
    notes = []
    if col["name"] in e["key"]:
        notes.append("**key**")
    if col["name"] in e["partial"]:
        notes.append("**partial key**")
    if {col["name"]} in table_info["uniques"] and col["name"] not in e["key"]:
        notes.append("unique (candidate key)")
    if (e["table"], col["name"]) in M.DERIVED:
        notes.append(f"**derived**: {M.DERIVED[(e['table'], col['name'])]}")
    notes.append("required" if col["notnull"] else "optional")
    return ", ".join(notes)


def describe_part(p, ent):
    if p["target"] == AGG:
        return "Stocks (aggregation of Seller_Organizations, Variants, Warehouses)"
    return ent[p["target"]]["name"]


def write_report(ent, rels, tables, checks):
    by_area_e = defaultdict(list)
    for e in ent.values():
        by_area_e[e["area"]].append(e)
    by_area_r = defaultdict(list)
    for r in rels:
        by_area_r[r["area"]].append(r)
    rel_of = defaultdict(list)
    for r in rels:
        for p in r["parts"]:
            rel_of[p["target"]].append(r["name"])
    for child in M.ISA["children"]:
        rel_of[child].append("ISA (subclass of Accounts)")
    rel_of[M.ISA["parent"]].append("ISA (superclass)")
    for part in next(r for r in rels if r.get("table") == M.AGGREGATED)["parts"]:
        rel_of[part["target"]].append("inside the Stocks aggregation")

    out = []
    w = out.append
    w("# MarketLab — Database Design Report")
    w("")
    w("*Multi-vendor marketplace and order fulfilment system — CS 202 two-person project.*")
    w("")
    w("> This file is generated by `python3 tools/build_er.py` from `tools/er_model.py` and `schema.sql`. "
      "Edit those two files, not this one.")
    w("")
    w("## Overview")
    w("")
    w("Independent sellers list variants of catalogue products on one marketplace. A customer can buy from several sellers in one order. "
      "Each seller keeps stock in shared warehouses, so checkout reserves stock from the right seller in the right warehouse, "
      "and the order is split into one fulfilment per seller and warehouse. Packages are shipped with a carrier service and delivered by couriers. "
      "After delivery, the customer can return items and receive a refund.")
    w("")
    w(f"The design has **{len(ent)} entity sets** and **{len(rels)} relationship sets**, plus one ISA hierarchy. "
      "They form one connected ER diagram.")
    w("")
    w("| Diagram | Content |")
    w("| --- | --- |")
    w("| [`er/full.svg`](er/full.svg) | The complete connected ER diagram with every entity set, attribute and relationship set. |")
    for key, label in M.AREAS.items():
        w(f"| [`er/area-{key}.svg`](er/area-{key}.svg) | {label}: the same notation, zoomed in. Grey dashed boxes are entity sets from other areas. |")
    w("| [`er/overview.svg`](er/overview.svg) | Every entity set and relationship set without attributes, grouped by business area: the whole connected design on one page. |")
    w("| [`er/legend.html`](er/legend.html) | The notation used, with an example from MarketLab for every symbol. |")
    w("")
    w("### Notation")
    w("")
    w("The diagrams follow the notation of the course slides (Ramakrishnan & Gehrke, chapter 2):")
    w("")
    w("| Symbol | Meaning |")
    w("| --- | --- |")
    w("| Rectangle | Entity set. Ovals around it are its attributes; the key attribute is underlined. |")
    w("| Dashed oval | Derived attribute: its value is computed from other data. |")
    w("| Diamond | Relationship set. Ovals attached to a diamond are descriptive attributes of the relationship. |")
    w("| Arrow from an entity set to a diamond | Key constraint: each entity takes part in at most one relationship of that set. |")
    w("| Bold line | Total participation: each entity takes part in at least one relationship of that set. |")
    w("| Bold arrow | Both: each entity takes part in exactly one relationship of that set. |")
    w("| Bold rectangle + bold diamond | Weak entity set and its identifying relationship. The partial key has a dashed underline. |")
    w("| Triangle labelled ISA | Specialisation. Subclasses inherit the attributes and the key of the superclass. |")
    w("| Dashed box | Aggregation: the relationship inside the box is treated as an entity set, so another relationship can connect to the box. |")
    w("| Label on a line | Role name, used when the same entity set appears twice in one relationship. |")
    w("")
    w("Foreign-key columns are not drawn as attributes. In the ER model a reference to another entity is a relationship, and the foreign key is only how the relational schema implements that relationship.")
    w("")
    w("## Guideline checklist")
    w("")
    w("| Requirement | Met | Evidence |")
    w("| --- | --- | --- |")
    for req, ok, ev in checks:
        w(f"| {req} | {'yes' if ok else '**NO**'} | {ev} |")
    w("| 5. Report: Part 1 entities, Part 2 relationships | yes | Below: every entity set and every relationship set has its own section. |")
    w("")
    w("## The four required concepts")
    w("")
    w("**Weak entities.** A weak entity can be identified only together with the key of its owner. It has total participation with a key constraint (bold arrow) in a one-to-many identifying relationship (bold diamond):")
    w("")
    for table, owner in M.WEAK_ENTITIES.items():
        e = ent[table]
        ident = next(r for r in rels if r["identifying"] and r["parts"][0]["target"] == table)
        owner_key = ", ".join(ent[owner]["key"])
        w(f"- **{e['name']}**: owner {ent[owner]['name']}, identifying relationship {ident['name']}, partial key `{', '.join(e['partial'])}`. "
          f"Full key = ({owner_key}, {', '.join(e['partial'])}).")
    w("")
    w(f"**ISA hierarchy.** {name_of(M.ISA['parent'])} ISA {', '.join(name_of(c) for c in M.ISA['children'])}. {M.ISA['explanation']}")
    w("")
    stocks = next(r for r in rels if r.get("table") == M.AGGREGATED)
    w(f"**Ternary relationship.** {stocks['name']} relates Seller_Organizations, Variants and Warehouses. {stocks['text'].replace('TERNARY. ', '')}")
    w("")
    agg_users = [r for r in rels if any(p["target"] == AGG for p in r["parts"])]
    w("**Aggregation.** The Stocks relationship, together with its three entity sets, is enclosed in a dashed box and treated as one entity set. Two relationships connect to the box:")
    w("")
    for r in agg_users:
        w(f"- **{r['name']}**: {r['text'].replace('AGGREGATION. ', '')}")
    w("")
    w("This is aggregation rather than a 4-ary relationship, for the reasons on the *Aggregation vs. ternary* slide. "
      "A reservation or a batch can only refer to a stock position that already exists. Reserves has its own descriptive attribute (quantity). "
      "And we can state constraints on it: each batch belongs to exactly one stock position (bold arrow).")
    w("")
    w("## Design choices")
    w("")
    w("- **Entity vs. attribute.** Several concepts are modelled as entity sets because an entity can have several of them, and attributes cannot be set-valued. "
      "Others are entity sets because their structure matters (see the reason under each one in Part 1).")
    w("- **Avoiding redundancy.** A coupon redemption and a return request do not store the customer again. "
      "The customer is already determined by the order, and storing it twice could let the two disagree (compare the *Entity vs. Relationship* slide).")
    w("- **Derived attributes.** " + "; ".join(f"`{name_of(t)}.{c}` is {how}" for (t, c), how in M.DERIVED.items()) + ". "
      "They are drawn as dashed ovals because they are not independent facts. The schema keeps the value so that order lists need not add up "
      "the lines; the application writes it once at checkout, from the same lines, and never changes it.")
    w("- **Participation that SQL cannot enforce.** Total participation of the \"one\" side is guaranteed by the application, not by a foreign key:")
    for (rel, table), reason in M.TOTAL_PARTICIPATION.items():
        w(f"  - {name_of(table)} in {rel}: {reason}.")
    w(f"  - {name_of(M.ISA['parent'])} in the ISA hierarchy (covering): every account is created together with its subclass row.")
    w("- **Consistency across relationships.** Some rules involve two relationships at once, for example that a returned line "
      "belongs to the returned order. The ER diagram cannot show such a rule, because every relationship is drawn on its own. "
      "The schema enforces each one with a composite foreign key through a shared column:")
    for rels_, rule, how in M.CROSS_RULES:
        w(f"  - {rule[0].upper() + rule[1:]} ({' + '.join(rels_)}): {how}.")
    w("")

    w("---")
    w("")
    w("## Part 1 — Entities")
    w("")
    n = 0
    for area, label in M.AREAS.items():
        w(f"### {label}")
        w("")
        for e in by_area_e[area]:
            n += 1
            t = tables[e["table"]]
            tag = " (weak entity)" if e["weak_owner"] else " (subclass of Accounts)" if e["inherited"] else ""
            w(f"#### E{n}. {e['name']}{tag}")
            w("")
            w(e["text"])
            w("")
            if e["inherited"]:
                w(f"**Key:** `account_id`, inherited from Accounts (every {e['name']} entity is also an Accounts entity).")
            elif e["weak_owner"]:
                o = ent[e["weak_owner"]]
                w(f"**Key:** partial key `{', '.join(e['partial'])}` together with the key `{', '.join(o['key'])}` of the owner {o['name']}.")
            else:
                w(f"**Key:** `{', '.join(e['key'])}`.")
            if e["table"] in M.WHY_ENTITY:
                w("")
                w(f"**Why an entity set:** {M.WHY_ENTITY[e['table']]}")
            w("")
            if e["attrs"]:
                w("| Attribute | Domain | Notes |")
                w("| --- | --- | --- |")
                for col in e["attrs"]:
                    w(f"| `{col['name']}` | {domain(t, col)} | {column_notes(t, col, e)} |")
                w("")
            for expr in t["checks"].get(None, []):
                w(f"Constraint: `{expr}`.")
                w("")
            w(f"**Takes part in:** {', '.join(sorted(set(rel_of[e['table']])))}.")
            w("")
    w("---")
    w("")
    w("## Part 2 — Relationships")
    w("")
    w("### ISA: Accounts → Customers, Staff, Couriers")
    w("")
    w(M.ISA["explanation"])
    w("")
    n = 0
    for area, label in M.AREAS.items():
        if not by_area_r[area]:
            continue
        w(f"### {label}")
        w("")
        for r in by_area_r[area]:
            n += 1
            w(f"#### R{n}. {r['name']}")
            w("")
            w(f"*{kind(r)}*")
            w("")
            w(r["text"].replace("TERNARY. ", "").replace("AGGREGATION. ", "").replace("IDENTIFYING. ", ""))
            w("")
            w("| Participant | Role | Key constraint | Participation |")
            w("| --- | --- | --- | --- |")
            for p in r["parts"]:
                key = "yes: at most one" if p["key"] else "no"
                total = "total" if p["total"] else "partial"
                w(f"| {describe_part(p, ent)} | {p['role'] or '—'} | {key} | {total} |")
            w("")
            if r["attrs"]:
                t = tables[r["table"]]
                w("Descriptive attributes: " + ", ".join(f"`{c['name']}` ({domain(t, c)})" for c in r["attrs"]) + ".")
                w("")
            w(f"Implemented as {r['sql']}.")
            w("")
            for rule in cross_rules(r["name"]):
                w(f"**Consistency:** {rule}. The ER diagram cannot show this; see *Consistency across relationships* above.")
                w("")
    (DOCS / "REPORT.md").write_text("\n".join(out))


def cross_rules(rel_name):
    """The cross-relationship rules a relationship takes part in, with the other relationship named."""
    out = []
    for rels_, rule, _ in M.CROSS_RULES:
        if rel_name in rels_:
            others = " and ".join(x for x in rels_ if x != rel_name)
            out.append(f"{rule[0].upper() + rule[1:]} (together with {others}); the schema enforces it with a composite foreign key")
    return out


def export_json(ent, rels, tables, checks):
    """Machine-readable model for tools/render/report_docx.mjs (the Word report)."""
    import json

    def entity(e):
        t = tables[e["table"]]
        return dict(
            name=e["name"], table=e["table"], area=e["area"], text=e["text"], why=M.WHY_ENTITY.get(e["table"]),
            key=e["key"], partial=e["partial"], inherited=e["inherited"],
            owner=ent[e["weak_owner"]]["name"] if e["weak_owner"] else None,
            owner_key=ent[e["weak_owner"]]["key"] if e["weak_owner"] else None,
            attrs=[dict(name=c["name"], domain=domain(t, c), required=c["notnull"],
                        unique={c["name"]} in t["uniques"] and c["name"] not in e["key"],
                        derived=M.DERIVED.get((e["table"], c["name"]))) for c in e["attrs"]],
            checks=t["checks"].get(None, []))

    def relationship(r):
        attrs = []
        if r["attrs"]:
            t = tables[r["table"]]
            attrs = [dict(name=c["name"], domain=domain(t, c)) for c in r["attrs"]]
        text = r["text"]
        for tag in ("TERNARY. ", "AGGREGATION. ", "IDENTIFYING. "):
            text = text.replace(tag, "")
        return dict(name=r["name"], area=r["area"], kind=kind(r), identifying=r["identifying"], text=text,
                    sql=r["sql"].replace("`", ""), attrs=attrs, rules=cross_rules(r["name"]),
                    parts=[dict(target="Stocks (aggregation)" if p["target"] == AGG else ent[p["target"]]["name"],
                                aggregation=p["target"] == AGG, key=p["key"], total=p["total"], role=p["role"])
                           for p in r["parts"]])

    data = dict(
        areas=M.AREAS, entities=[entity(e) for e in ent.values()], relationships=[relationship(r) for r in rels],
        isa=dict(parent=name_of(M.ISA["parent"]), children=[name_of(c) for c in M.ISA["children"]],
                 overlap=M.ISA["overlap"], covering=M.ISA["covering"], text=M.ISA["explanation"]),
        total_participation=[dict(relationship=r, entity=name_of(t), reason=why) for (r, t), why in M.TOTAL_PARTICIPATION.items()],
        cross_rules=[dict(relationships=list(r), rule=rule, how=how.replace("`", "")) for r, rule, how in M.CROSS_RULES],
        derived=[dict(entity=name_of(t), attribute=c, how=how) for (t, c), how in M.DERIVED.items()],
        checks=[dict(requirement=a, ok=b, evidence=c) for a, b, c in checks],
        tables=len(tables), relationship_tables=len(M.RELATIONSHIP_TABLES))
    (ER_DIR / "model.json").write_text(json.dumps(data, indent=1, ensure_ascii=False))


# --------------------------------------------------------------------------- main
def main():
    tables = read_schema()
    ent, rels, problems = build_model(tables)
    if problems:
        print("Model and schema disagree:")
        for p in problems:
            print(" -", p)
        sys.exit(1)
    checks = check_guidelines(ent, rels)
    for req, ok, ev in checks:
        print(f"[{'ok' if ok else 'FAIL'}] {req}: {ev}")
    if not all(ok for _, ok, _ in checks):
        sys.exit(1)
    if "--check" in sys.argv:
        return

    ER_DIR.mkdir(parents=True, exist_ok=True)
    dots = {"full": build_dot(ent, rels, set(ent), f"MarketLab — complete ER diagram ({len(ent)} entity sets, {len(rels)} relationship sets)"),
            "overview": build_dot(ent, rels, set(ent), f"MarketLab — overview: all {len(ent)} entity sets and {len(rels)} relationship sets "
                                  "(attributes on the area pages)", overview=True)}
    for key, label in M.AREAS.items():
        focus = {t for t, e in ent.items() if e["area"] == key}
        dots[f"area-{key}"] = build_dot(ent, rels, focus, f"MarketLab — {label}")
    # Small figures for the report: one per required construct.
    weak_rels = {r["name"] for r in rels if r["identifying"]}
    dots["concept-weak"] = build_dot(ent, rels, set(), "Weak entities and identifying relationships", only={"Contains", "Offers_Service"} & weak_rels, isa=False)
    dots["concept-isa"] = build_dot(ent, rels, {M.ISA["parent"], *M.ISA["children"]}, "ISA hierarchy", only=set(), isa=True)
    dots["concept-aggregation"] = build_dot(ent, rels, set(), "Ternary relationship Stocks and its aggregation", only={"Stocks", "Reserves", "Batch_Of"}, isa=False)
    (ER_DIR / "legend").mkdir(exist_ok=True)
    for _, name, body, _ in LEGEND:
        dots[f"legend/{name}"] = legend_dot(body)
    paths = []
    for name, text in dots.items():
        path = ER_DIR / f"{name}.dot"
        path.write_text(text)
        paths.append(path)
    write_report(ent, rels, tables, checks)
    export_json(ent, rels, tables, checks)
    print(f"Wrote {len(paths)} DOT files, docs/REPORT.md and docs/er/model.json")

    if not (RENDER / "node_modules").exists():
        print("SVG rendering skipped: run `npm install` in tools/render once.")
        return
    subprocess.run(["node", str(RENDER / "render.mjs"), *map(str, paths)], check=True)
    for path in paths:
        postprocess_svg(path.with_suffix(".svg"))
    subprocess.run(["node", str(RENDER / "render.mjs"), "--png", *(str(p.with_suffix(".svg")) for p in paths if "legend" not in p.parts)], check=True)
    order = ["overview", *(f"area-{key}" for key in M.AREAS)]
    pages = [(1, "this notation"), (2, "overview of the complete design (all entity and relationship sets, without attributes)")]
    pages += [(n + 3, f"{label} (with all attributes)") for n, label in enumerate(M.AREAS.values())]
    write_legend_html(pages)
    make_pdf(order)


if __name__ == "__main__":
    main()
