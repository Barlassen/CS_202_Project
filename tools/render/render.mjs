// Usage: node render.mjs <file.dot>...  -> writes <file.svg> next to each input.
import { instance } from "@viz-js/viz";
import { readFileSync, writeFileSync } from "node:fs";

const viz = await instance();
for (const path of process.argv.slice(2)) {
  const svg = viz.renderString(readFileSync(path, "utf8"), { format: "svg", engine: "dot" });
  writeFileSync(path.replace(/\.dot$/, ".svg"), svg);
  console.log(`rendered ${path}`);
}
