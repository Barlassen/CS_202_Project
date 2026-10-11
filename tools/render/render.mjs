// Usage: node render.mjs <file.dot>...          -> <file.svg> next to each input
//        node render.mjs --png <file.svg>...    -> <file.png> next to each input (for the Word report)
import { readFileSync, writeFileSync } from "node:fs";

const args = process.argv.slice(2);
if (args[0] === "--png") {
  const { Resvg } = await import("@resvg/resvg-js");
  for (const path of args.slice(1)) {
    const svg = readFileSync(path, "utf8");
    const width = Number(/width="([\d.]+)pt"/.exec(svg)?.[1] ?? 1000);
    // About 200 dpi for normal figures; the very large overview is capped so the file stays small.
    const zoom = Math.min(200 / 72, 9000 / width);
    const png = new Resvg(svg, {
      fitTo: { mode: "zoom", value: zoom },
      background: "white",
      font: { loadSystemFonts: true, defaultFontFamily: "Helvetica", sansSerifFamily: "Arial" },
    }).render().asPng();
    writeFileSync(path.replace(/\.svg$/, ".png"), png);
  }
  console.log(`rasterized ${args.length - 1} SVG files`);
} else {
  const { instance } = await import("@viz-js/viz");
  const viz = await instance();
  // Area and concept figures go on a landscape page of the Word report. Try both layout
  // directions and keep the one that can be printed larger in a 10 x 6.3 inch box.
  const size = (svg) => /width="([\d.]+)pt" height="([\d.]+)pt"/.exec(svg).slice(1).map(Number);
  const fit = (svg) => { const [w, h] = size(svg); return Math.min(720 / w, 450 / h); };
  for (const path of args) {
    const dot = readFileSync(path, "utf8");
    let svg = viz.renderString(dot, { format: "svg", engine: "dot" });
    if (/\/(area|concept)-[^/]*\.dot$/.test(path) && dot.includes("rankdir=TB")) {
      const lr = viz.renderString(dot.replace("rankdir=TB", "rankdir=LR"), { format: "svg", engine: "dot" });
      if (fit(lr) > fit(svg) * 1.1) svg = lr;
    }
    writeFileSync(path.replace(/\.dot$/, ".svg"), svg);
  }
  console.log(`rendered ${args.length} DOT files`);
}
