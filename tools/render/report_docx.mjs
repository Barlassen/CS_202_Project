// Builds docs/MarketLab_Project_Description.docx from docs/er/model.json.
// Run python3 tools/build_er.py first. Usage: node tools/render/report_docx.mjs
// The report follows item 5 of Guidelines.pdf: a short introduction, then
// Part 1 (every entity) and Part 2 (every relationship). The ER diagram is a separate file.
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  AlignmentType, BorderStyle, Document, Footer, HeadingLevel, LevelFormat, Packer, PageBreak,
  PageNumber, Paragraph, ShadingType, Table, TableCell, TableRow, TextRun, UnderlineType, WidthType,
} from "docx";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const OUT = join(ROOT, "docs", "MarketLab_Project_Description.docx");
const M = JSON.parse(readFileSync(join(ROOT, "docs", "er", "model.json"), "utf8"));
export const DIAGRAM_FILE = "MarketLab_ER_Diagram.pdf";

// A4 with 2 cm margins.
const PAGE = { width: 11906, height: 16838 };
const MARGIN = { top: 1134, bottom: 1134, left: 1134, right: 1134 };
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
const key = (text) => run(text, { underline: { type: UnderlineType.SINGLE } });
const partialKey = (text) => run(text, { underline: { type: UnderlineType.DASH } });

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
  "relationship with an aggregation": "uses the aggregation of Stocks",
  "identifying relationship of a weak entity (one owner, many weak entities)": "identifying (weak entity)",
};

// ------------------------------------------------------------------ content
const nEnt = entities.length;
const nRel = rels.length;

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

const intro = [
  para("MarketLab is an online marketplace on which many independent sellers offer goods side by side. Products are described once in a shared catalogue, "
    + "and each seller publishes its own priced listing for a specific variant. Sellers keep stock in shared warehouses, so one customer order can involve several "
    + "sellers and warehouses: stock is reserved from the exact seller–variant–warehouse position, and the order is split into one fulfilment per seller and warehouse, "
    + "which is shipped with a carrier service and delivered by a courier. Delivered items can be returned and refunded."),
  para(`The design has ${nEnt} entity sets and ${nRel} relationship sets, plus one ISA hierarchy, all connected in a single ER diagram (submitted as ${DIAGRAM_FILE}). `
    + "It includes weak entities, an ISA hierarchy, a ternary relationship and an aggregation. Part 1 defines every entity set and Part 2 every relationship set."),
];

// Part 1
let e_no = 0;
const part1 = [
  heading("Part 1 – Entities", HeadingLevel.HEADING_1),
  para("Entity sets are grouped by business area. For each one we give its meaning, its key and its own attributes. The key is underlined. "
    + "A weak entity is identified by its partial key (dashed underline) together with the key of its owner, and the subclasses of Accounts inherit the Accounts key. "
    + "Attributes that point to another entity are not listed, because such links are relationships (Part 2)."),
];
let sec = 0;
for (const [area, label] of Object.entries(M.areas)) {
  sec += 1;
  const list = byArea(entities, area);
  part1.push(heading(`1.${sec} ${label}`, HeadingLevel.HEADING_2));
  part1.push(table([520, 1900, 3318, 1700, 2200], ["#", "Entity set", "Meaning", "Key", "Attributes"],
    list.map((e) => {
      e_no += 1;
      const nameCell = [[run(e.name, { bold: true, size: 18 })]];
      if (e.owner) nameCell.push([run(`weak, owner ${e.owner}`, { italics: true, size: 16, color: MUTED })]);
      if (e.inherited) nameCell.push([run(`subclass of ${M.isa.parent}`, { italics: true, size: 16, color: MUTED })]);
      return [`E${e_no}`, nameCell, e.why ? [[run(e.text, { size: 18 })], [run(e.why, { size: 16, italics: true, color: MUTED })]] : e.text,
        [keyRuns(e)], [attrRuns(e)]];
    })));
}

// Part 2
let r_no = 0;
const part2 = [
  new Paragraph({ children: [new PageBreak()] }),
  heading("Part 2 – Relationships", HeadingLevel.HEADING_1),
  para("Relationship sets are grouped by the same business areas. For each participating entity set we state in how many relationships of the set each of its entities "
    + "takes part: exactly one (key constraint and total participation), at most one (key constraint), at least one (total participation) or any number. "
    + "Identifying relationships of weak entities, the ternary relationship and the relationships that use the aggregation are marked under the relationship name."),
  heading("2.0 ISA hierarchy", HeadingLevel.HEADING_2),
  para(`${M.isa.parent} ISA ${M.isa.children.join(", ")}. The subclasses inherit the attributes of an account and its key, account_id, and each takes part in its own relationships: `
    + "only customers place orders, only staff members work in departments, and only couriers drive vehicles and attempt deliveries. "
    + "Overlap is not allowed, because every account has exactly one role; covering holds, because the role is mandatory."),
];
sec = 0;
for (const [area, label] of Object.entries(M.areas)) {
  const list = byArea(rels, area);
  if (!list.length) continue;
  sec += 1;
  part2.push(heading(`2.${sec} ${label}`, HeadingLevel.HEADING_2));
  part2.push(table([560, 1900, 2600, 4578], ["#", "Relationship", "Participants", "Meaning"],
    list.map((r) => {
      r_no += 1;
      const nameCell = [[run(r.name, { bold: true, size: 18 })], [run(KIND[r.kind] ?? r.kind, { italics: true, size: 16, color: MUTED })]];
      const partCell = r.parts.map((p) => [run(p.target, { size: 18 }), run(`${p.role ? ` (${p.role})` : ""}: ${phrase(p)}`, { size: 18, color: MUTED })]);
      const meaning = [[run(r.text, { size: 18 })]];
      if (r.attrs.length) meaning.push([run("Attributes: ", { size: 18, bold: true }), run(r.attrs.map((a) => a.name).join(", "), { size: 18 })]);
      for (const rule of r.rules ?? []) meaning.push([run("Consistency: ", { size: 18, bold: true }), run(`${rule}.`, { size: 18 })]);
      return [`R${r_no}`, nameCell, partCell, meaning];
    })));
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
    { properties: portrait, footers: { default: footer }, children: [...titleBlock, ...intro, ...part1, ...part2] },
  ],
});

writeFileSync(OUT, await Packer.toBuffer(doc));
console.log(`wrote ${OUT}: ${nEnt} entities, ${nRel} relationships`);
