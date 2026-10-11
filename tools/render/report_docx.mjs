// Builds docs/MarketLab_Project_Description.docx from docs/er/model.json and the PNG diagrams.
// Run python3 tools/build_er.py first (it writes both). Usage: node tools/render/report_docx.mjs
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  AlignmentType, BorderStyle, Document, Footer, HeadingLevel, ImageRun, LevelFormat, Packer, PageBreak,
  PageNumber, PageOrientation, Paragraph, ShadingType, Table, TableCell, TableRow, TextRun, UnderlineType,
  WidthType, ExternalHyperlink,
} from "docx";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const ER = join(ROOT, "docs", "er");
const OUT = join(ROOT, "docs", "MarketLab_Project_Description.docx");
const M = JSON.parse(readFileSync(join(ER, "model.json"), "utf8"));
const REPO = "https://github.com/Barlassen/CS_202_Project";

// A4 with 2 cm margins.
const PAGE = { width: 11906, height: 16838 };
const MARGIN = { top: 1134, bottom: 1134, left: 1134, right: 1134 };
const BODY_W = PAGE.width - MARGIN.left - MARGIN.right; // 9638 DXA
const LAND_W = PAGE.height - MARGIN.left - MARGIN.right; // 14570 DXA
const LAND_H = PAGE.width - MARGIN.top - MARGIN.bottom;
const FONT = "Calibri";
const INK = "1F2933";
const MUTED = "52606D";
const ACCENT = "2F4A6D";
const GRID = "BCC5CF";

// ------------------------------------------------------------------ text helpers
const run = (text, o = {}) => new TextRun({ text, font: FONT, ...o });
const para = (children, o = {}) =>
  new Paragraph({ spacing: { after: 120, line: 276 }, ...o, children: typeof children === "string" ? [run(children)] : children });
const heading = (text, level) => new Paragraph({ heading: level, children: [run(text)] });
const bullet = (children) => new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 }, children: typeof children === "string" ? [run(children)] : children });
const code = (text) => run(text, { font: "Consolas", size: 19 });
const key = (text) => run(text, { underline: { type: UnderlineType.SINGLE } });
const partialKey = (text) => run(text, { underline: { type: UnderlineType.DASH } });

let figureNo = 0;
let tableNo = 0;

function pngSize(file) {
  const b = readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20), data: b };
}

function figure(name, caption, maxW, maxH, label) {
  const { w, h, data } = pngSize(join(ER, `${name}.png`));
  const maxWpx = (maxW / 1440) * 96;
  const maxHpx = (maxH / 1440) * 96;
  const s = Math.min(maxWpx / w, maxHpx / h);
  figureNo += 1;
  label = label ?? `Figure ${figureNo}. `;
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 60 }, keepNext: true,
      children: [new ImageRun({ type: "png", data, transformation: { width: Math.round(w * s), height: Math.round(h * s) } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
      children: [run(label, { bold: true, size: 18, color: MUTED }), run(caption, { size: 18, color: MUTED })] }),
  ];
}

function tableCaption(text) {
  tableNo += 1;
  return new Paragraph({ spacing: { before: 120, after: 60 }, keepNext: true,
    children: [run(`Table ${tableNo}. `, { bold: true, size: 18, color: MUTED }), run(text, { size: 18, color: MUTED })] });
}

const border = { style: BorderStyle.SINGLE, size: 4, color: GRID };
const borders = { top: border, bottom: border, left: border, right: border };

function cell(content, width, o = {}) {
  const paras = (Array.isArray(content) ? content : [content]).map((c) =>
    c instanceof Paragraph ? c : new Paragraph({ spacing: { after: 20 }, children: Array.isArray(c) ? c : [typeof c === "string" ? run(c, { size: 18 }) : c] }));
  return new TableCell({
    borders, width: { size: width, type: WidthType.DXA }, margins: { top: 50, bottom: 50, left: 90, right: 90 },
    shading: o.fill ? { fill: o.fill, type: ShadingType.CLEAR, color: "auto" } : undefined, children: paras,
  });
}

function table(widths, header, rows) {
  const total = widths.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: total, type: WidthType.DXA }, columnWidths: widths,
    rows: [
      new TableRow({ tableHeader: true, cantSplit: true,
        children: header.map((h, i) => cell([[run(h, { bold: true, size: 18, color: "FFFFFF" })]], widths[i], { fill: ACCENT })) }),
      ...rows.map((r, n) => new TableRow({ cantSplit: true,
        children: r.map((c, i) => cell(c, widths[i], { fill: n % 2 ? "F4F6F8" : undefined })) })),
    ],
  });
}

// ------------------------------------------------------------------ model helpers
const entities = M.entities;
const rels = M.relationships;
const byArea = (list, area) => list.filter((x) => x.area === area);

function keyRuns(e) {
  if (e.inherited) return [key("account_id"), run(` (inherited from ${M.isa.parent})`, { size: 18, color: MUTED })];
  if (e.partial.length) {
    return [partialKey(e.partial.join(", ")), run(" (partial) + ", { size: 18, color: MUTED }), key(e.owner_key.join(", ")),
      run(` of ${e.owner}`, { size: 18, color: MUTED })];
  }
  return [key(e.key.join(", "))];
}

function attrRuns(e) {
  const list = e.attrs.filter((a) => !e.key.includes(a.name) && !e.partial.includes(a.name));
  if (!list.length) return [run("—", { size: 18, color: MUTED })];
  const out = [];
  list.forEach((a, i) => {
    out.push(run(a.name, { size: 18 }));
    const tags = [];
    if (a.unique) tags.push("unique");
    if (!a.required) tags.push("optional");
    if (tags.length) out.push(run(` (${tags.join(", ")})`, { size: 16, color: MUTED }));
    if (i < list.length - 1) out.push(run(", ", { size: 18 }));
  });
  return out;
}

function phrase(p) {
  if (p.key && p.total) return "exactly one";
  if (p.key) return "at most one";
  if (p.total) return "at least one";
  return "any number";
}

const KIND = {
  "binary, one-to-one": "one-to-one",
  "binary, many-to-one": "many-to-one",
  "binary, many-to-many": "many-to-many",
  "3-ary (ternary) relationship": "ternary",
  "relationship with an aggregation": "uses the aggregation",
  "identifying relationship of a weak entity (one owner, many weak entities)": "identifying (weak entity)",
};

// ------------------------------------------------------------------ content
const nEnt = entities.length;
const nRel = rels.length;
const weak = entities.filter((e) => e.owner);
const stocks = rels.find((r) => r.name === "Stocks");
const aggUsers = rels.filter((r) => r.parts.some((p) => p.aggregation));
const check = (prefix) => M.checks.find((c) => c.requirement.startsWith(prefix));

const titleBlock = [
  new Paragraph({ spacing: { after: 40 }, children: [run("MarketLab", { size: 52, bold: true, color: ACCENT })] }),
  new Paragraph({ spacing: { after: 60 }, children: [run("Multi-Vendor Marketplace and Order Fulfilment System", { size: 28, color: INK })] }),
  new Paragraph({ spacing: { after: 240 }, border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: ACCENT, space: 6 } },
    children: [run("Project Description · Entity–Relationship Design · CS 202 Database Systems, Fall 2026–27", { size: 20, color: MUTED })] }),
  table([2600, 4038, 3000], ["Team member", "Full name", "Student ID"], [
    ["Student 1", [run("[ENTER FULL NAME]", { size: 18, highlight: "yellow" })], [run("[ENTER STUDENT ID]", { size: 18, highlight: "yellow" })]],
    ["Student 2", [run("[ENTER FULL NAME]", { size: 18, highlight: "yellow" })], [run("[ENTER STUDENT ID]", { size: 18, highlight: "yellow" })]],
  ]),
  para("", { spacing: { after: 120 } }),
];

const overview = [
  heading("1. Overview", HeadingLevel.HEADING_1),
  para("MarketLab is the database behind an online marketplace where many independent sellers offer their goods side by side. "
    + "Products are described once in a shared catalogue; each seller then publishes its own priced listing for a specific variant of a product. "
    + "Sellers keep stock in shared fulfilment warehouses, buy from their own suppliers, and are paid out by the marketplace after commission."),
  para("A single customer order can therefore involve several sellers and several warehouses. At checkout, stock is reserved from the exact seller–variant–warehouse "
    + "position that will ship it, and the order is split into one fulfilment per seller and warehouse. Each fulfilment is packed, handed to a carrier service and "
    + "delivered by a courier, either to the customer's address or to a pickup point. After delivery the customer can return items, which are inspected before any refund."),
  para([run("Example. ", { bold: true }), run("A customer buys two headphones from Nova Teknoloji (stocked in Istanbul) and a notebook set from Ev & Yaşam (stocked in Ankara). "
    + "This is one order with two order lines, two stock reservations and two fulfilments, each with its own package and shipment. "
    + "If one headphone arrives damaged, the return refers to the original order line, so the refund uses the price paid at checkout.")]),
  para(`The design contains ${nEnt} entity sets and ${nRel} relationship sets, plus one ISA hierarchy, and they form a single connected ER diagram (Figure A1 in Appendix A). `
    + `It is implemented as ${M.tables} relational tables; the schema and a working web prototype are in the project repository.`),
];

const checklist = [
  heading("2. How the design meets the guidelines", HeadingLevel.HEADING_1),
  tableCaption("Project guidelines and where each one is satisfied."),
  table([3000, 6638], ["Guideline", "In this design"], [
    ["At least 50 entities (two-person project)", `${nEnt} entity sets, defined one by one in Part 1 (Section 5). Relationship sets are not counted, even where they have their own table.`],
    ["One connected ER design", `All ${nEnt} entity sets are linked through the ${nRel} relationship sets and the ISA hierarchy; no entity or group is isolated. The complete diagram is Figure A1.`],
    ["Weak entity", `${weak.map((e) => e.name).join(", ")} (Section 4.1).`],
    ["ISA hierarchy", `${M.isa.parent} ISA ${M.isa.children.join(", ")}; overlap not allowed, covering holds (Section 4.2).`],
    ["Ternary relationship", "Stocks between Seller_Organizations, Variants and Warehouses (Section 4.3)."],
    ["Aggregation", `Stocks is aggregated and used by ${aggUsers.map((r) => r.name).join(" and ")} (Section 4.4).`],
    ["A clear key for every entity", "Given in the Key column of Part 1: an own key for strong entity sets, partial key plus owner key for weak ones, and the inherited key for ISA subclasses."],
    ["Report in two parts", "Part 1 – Entities (Section 5) and Part 2 – Relationships (Section 6)."],
  ]),
];

const notation = [
  heading("3. Notation", HeadingLevel.HEADING_1),
  para("The diagrams use the notation of the course slides (Ramakrishnan & Gehrke, Chapter 2). Entity sets are rectangles and their attributes are ovals; "
    + "the key attribute is underlined. Relationship sets are diamonds, and descriptive attributes of a relationship hang from its diamond. "
    + "Foreign keys are not drawn as attributes: a reference to another entity is a relationship, and the foreign key only appears when the design is mapped to tables."),
  ...figure("legend", "Symbols used in all diagrams.", BODY_W, 6200),
  para("Part 2 states the constraints of every relationship in words. The words correspond to the symbols as follows:"),
  tableCaption("Constraint wording used in Part 2."),
  table([2200, 4238, 3200], ["Wording", "Meaning for each entity of that set", "Symbol"], [
    ["exactly one", "takes part in exactly one relationship (key constraint and total participation)", "bold arrow into the diamond"],
    ["at most one", "takes part in zero or one relationship (key constraint)", "thin arrow into the diamond"],
    ["at least one", "takes part in one or more relationships (total participation)", "bold line"],
    ["any number", "no constraint", "thin line"],
  ]),
];

const owner = (e) => entities.find((x) => x.name === e.owner);
const constructs = [
  heading("4. Required ER constructs", HeadingLevel.HEADING_1),
  heading("4.1 Weak entities", HeadingLevel.HEADING_2),
  para("A weak entity has no key of its own. It is identified by its owner's key together with a partial key, and it exists only as part of its owner. "
    + "Following the slides, each weak entity set takes part in its identifying relationship with a key constraint and total participation (bold arrow), and the owner can have many weak entities."),
  ...weak.map((e) => bullet([run(`${e.name}: `, { bold: true }), run(`owner ${e.owner}, partial key `), partialKey(e.partial.join(", ")),
    run(`, full key (${owner(e).key.join(", ")}, ${e.partial.join(", ")}). `), run(e.text)])),
  ...figure("concept-weak", "Two of the weak entity sets with their identifying relationships.", BODY_W, 5200),
  heading("4.2 ISA hierarchy", HeadingLevel.HEADING_2),
  para(`${M.isa.parent} is specialised into ${M.isa.children.join(", ")}. The subclasses inherit the attributes of an account and its key, and each adds its own attributes `
    + "and its own relationships: only customers place orders, only staff members work in departments, and only couriers drive vehicles and attempt deliveries."),
  bullet([run("Overlap: not allowed. ", { bold: true }), run("An account has exactly one role. The database rejects a subclass row whose account has a different role.")]),
  bullet([run("Covering: yes. ", { bold: true }), run("The role is mandatory, so every account belongs to one of the three subclasses.")]),
  ...figure("concept-isa", "ISA hierarchy of accounts.", BODY_W, 4600),
  heading("4.3 Ternary relationship", HeadingLevel.HEADING_2),
  para(`${stocks.name} relates Seller_Organizations, Variants and Warehouses and carries the available quantity and the reorder point. `
    + "The quantity belongs to the combination of all three. Three binary relationships (seller sells variant, seller uses warehouse, warehouse holds variant) "
    + "would not say how many units of a particular seller's variant lie in a particular warehouse, which is the same argument the slides make with the Contracts example."),
  heading("4.4 Aggregation", HeadingLevel.HEADING_2),
  para("Stocks is enclosed together with its three entity sets in a dashed box, so that the relationship can itself take part in other relationships. Two relationships connect to the box:"),
  ...aggUsers.map((r) => bullet([run(`${r.name}: `, { bold: true }), run(r.text)])),
  para("We chose aggregation over a larger n-ary relationship because a reservation or a batch must refer to a stock position that already exists, because Reserves has its own attribute (quantity), "
    + "and because the constraints differ: a batch belongs to exactly one stock position, whereas an order line may be served from several."),
  ...figure("concept-aggregation", "Stocks as a ternary relationship, aggregated and used by Batch_Of and Reserves.", BODY_W, 5600),
];

// Part 1
let e_no = 0;
const part1 = [
  new Paragraph({ children: [new PageBreak()] }),
  heading("5. Part 1 – Entities", HeadingLevel.HEADING_1),
  para("The entity sets are grouped by business area. For each one we give its meaning, its key and its own attributes. "
    + "Attributes that refer to another entity are left out on purpose; those links are the relationships of Part 2. Optional attributes may be empty, and unique attributes are alternative keys."),
];
let sec = 0;
for (const [area, label] of Object.entries(M.areas)) {
  sec += 1;
  const list = byArea(entities, area);
  part1.push(heading(`5.${sec} ${label}`, HeadingLevel.HEADING_2));
  part1.push(tableCaption(`${label}: ${list.length} entity sets (diagram in Appendix A).`));
  part1.push(table([520, 1900, 3318, 1700, 2200], ["#", "Entity set", "Meaning", "Key", "Attributes"],
    list.map((e) => {
      e_no += 1;
      e.no = e_no;
      const nameCell = [[run(e.name, { bold: true, size: 18 })]];
      if (e.owner) nameCell.push([run(`weak, owner ${e.owner}`, { italics: true, size: 16, color: MUTED })]);
      if (e.inherited) nameCell.push([run(`subclass of ${M.isa.parent}`, { italics: true, size: 16, color: MUTED })]);
      return [`E${e_no}`, nameCell, e.text, [keyRuns(e).map((r) => r)], [attrRuns(e)]];
    })));
  const notes = list.filter((e) => e.why);
  if (notes.length) {
    part1.push(para([run("Why these are entity sets and not attributes", { bold: true, size: 20 })], { spacing: { before: 160, after: 60 } }));
    notes.forEach((e) => part1.push(bullet([run(`${e.name}: `, { bold: true }), run(e.why)])));
  }
}

// Part 2
let r_no = 0;
const part2 = [
  new Paragraph({ children: [new PageBreak()] }),
  heading("6. Part 2 – Relationships", HeadingLevel.HEADING_1),
  para("Each relationship set is listed under the business area it belongs to. The participants column gives, for every participating entity set, "
    + "how many relationships of this set each of its entities takes part in, using the wording of Table 2. Role names are given where one entity set appears twice."),
  heading("6.0 ISA", HeadingLevel.HEADING_2),
  para(`${M.isa.parent} ISA ${M.isa.children.join(", ")}. ${M.isa.text}`),
];
sec = 0;
for (const [area, label] of Object.entries(M.areas)) {
  const list = byArea(rels, area);
  if (!list.length) continue;
  sec += 1;
  part2.push(heading(`6.${sec} ${label}`, HeadingLevel.HEADING_2));
  part2.push(tableCaption(`${label}: ${list.length} relationship sets.`));
  part2.push(table([560, 1900, 2600, 4578], ["#", "Relationship", "Participants", "Meaning"],
    list.map((r) => {
      r_no += 1;
      const nameCell = [[run(r.name, { bold: true, size: 18 })], [run(KIND[r.kind] ?? r.kind, { italics: true, size: 16, color: MUTED })]];
      const partCell = r.parts.map((p) => [run(p.target, { size: 18 }), run(`${p.role ? ` (${p.role})` : ""}: ${phrase(p)}`, { size: 18, color: MUTED })]);
      const meaning = [[run(r.text, { size: 18 })]];
      if (r.attrs.length) meaning.push([run("Attributes: ", { size: 18, bold: true }), run(r.attrs.map((a) => a.name).join(", "), { size: 18 })]);
      return [`R${r_no}`, nameCell, partCell, meaning];
    })));
}

const decisions = [
  new Paragraph({ children: [new PageBreak()] }),
  heading("7. Design decisions", HeadingLevel.HEADING_1),
  bullet([run("Entity or attribute. ", { bold: true }), run("Whenever one entity can have several values of something (images, price changes, status changes, tracking scans, messages), "
    + "that thing is an entity set, because an attribute holds a single value. Cities and countries are entity sets because addresses, warehouses, zones, pickup points and tax rates all depend on them and we search by them.")]),
  bullet([run("No redundant links. ", { bold: true }), run("A coupon redemption and a return request do not point to the customer again; the customer follows from the order. Storing it twice would allow the two to disagree.")]),
  bullet([run("Listing between seller and variant. ", { bold: true }), run("The catalogue (products, variants) is shared, while price and availability belong to a seller's listing. Two sellers can therefore offer the same variant at different prices.")]),
  bullet([run("Price kept on the order line. ", { bold: true }), run("Order_Lines stores the unit price at checkout, so later price changes, which are recorded in Price_History, do not alter past orders or refunds.")]),
  bullet([run("Participation that the tables cannot enforce. ", { bold: true }), run("The following total participations are guaranteed by the application rather than by a foreign key:")]),
  ...M.total_participation.map((t) => new Paragraph({ numbering: { reference: "bullets", level: 1 }, spacing: { after: 40 },
    children: [run(`${t.entity} in ${t.relationship}: ${t.reason}.`)] })),
  heading("8. From the ER design to tables", HeadingLevel.HEADING_1),
  para(`Each entity set becomes a table with its key as primary key. A weak entity's table uses the owner's key plus the partial key as a composite primary key, and its identifying relationship is that same foreign key. `
    + `Many-to-many and ternary relationship sets get their own table whose key combines the participants' keys (${M.relationship_tables} such tables, for example stock_positions for Stocks). `
    + "Many-to-one relationships become a foreign key on the \"many\" side, NOT NULL when participation is total. The aggregation is implemented by foreign keys that reference the composite key of stock_positions. "
    + "ISA subclasses share the account key, which is both their primary key and a foreign key to accounts."),
  para([run("Repository: "), new ExternalHyperlink({ link: REPO, children: [run(REPO, { style: "Hyperlink", color: "1F5FAD", underline: {} })] })]),
];

const areaFigures = [
  heading("Appendix A – ER diagrams", HeadingLevel.HEADING_1),
  para("Figure A1 is the complete diagram; it is large and best viewed zoomed in (the repository also holds it as SVG). The figures after it show each business area in the same notation. "
    + "Grey dashed boxes stand for entity sets of another area, drawn without attributes."),
];
let appendixNo = 0;
const figA = (name, caption) => figure(name, caption, LAND_W, LAND_H - 900, `Figure A${++appendixNo}. `);
areaFigures.push(...figA("full", `Complete ER diagram: ${nEnt} entity sets and ${nRel} relationship sets in one connected component.`));
for (const [area, label] of Object.entries(M.areas)) {
  areaFigures.push(new Paragraph({ children: [new PageBreak()] }));
  areaFigures.push(...figA(`area-${area}`, `${label}.`));
}

// ------------------------------------------------------------------ document
const footer = new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 18, color: MUTED })] })] });
const portrait = { page: { size: PAGE, margin: MARGIN } };

const doc = new Document({
  creator: "Meriç Şen",
  lastModifiedBy: "Meriç Şen",
  title: "MarketLab Project Description",
  description: "",
  styles: {
    default: { document: { run: { font: FONT, size: 21, color: INK } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 30, bold: true, color: ACCENT, font: FONT }, paragraph: { spacing: { before: 320, after: 140 }, outlineLevel: 0, keepNext: true } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, color: INK, font: FONT }, paragraph: { spacing: { before: 240, after: 100 }, outlineLevel: 1, keepNext: true } },
    ],
  },
  numbering: { config: [{ reference: "bullets", levels: [
    { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 400, hanging: 260 } } } },
    { level: 1, format: LevelFormat.BULLET, text: "–", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 800, hanging: 260 } } } },
  ] }] },
  sections: [
    { properties: portrait, footers: { default: footer },
      children: [...titleBlock, ...overview, ...checklist, ...notation, ...constructs, ...part1, ...part2, ...decisions] },
    { properties: { page: { size: { ...PAGE, orientation: PageOrientation.LANDSCAPE }, margin: MARGIN } }, footers: { default: footer },
      children: areaFigures },
  ],
});

writeFileSync(OUT, await Packer.toBuffer(doc));
console.log(`wrote ${OUT}: ${nEnt} entities, ${nRel} relationships`);
