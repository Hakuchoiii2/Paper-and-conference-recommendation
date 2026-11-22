import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const modules = process.env.CODEX_SPREADSHEET_NODE_MODULES;
const require = createRequire(join(modules, "review-workbook.cjs"));
const { Workbook, SpreadsheetFile } = await import(pathToFileURL(require.resolve("@oai/artifact-tool")));
const output = resolve(process.argv[2] ?? "ground_truth_generation/output");
const queue = (await readFile(join(output, "human_review_queue.jsonl"), "utf8"))
  .trim().split("\n").map(JSON.parse);
const byQuery = Map.groupBy(queue, row => row.query_id);
const workbook = Workbook.create();
const heading = { fill: "#143654", font: { bold: true, color: "#FFFFFF" } };

const guide = workbook.worksheets.add("Guide");
guide.getRange("A1:B6").values = [
  ["Relevance grade", "Meaning"],
  [0, "Unrelated"],
  [1, "Lightly related"],
  [2, "Substantially related"],
  [3, "Highly related and directly useful"],
  ["Blank", "Pending review"],
];
guide.getRange("A1:B1").format = heading;
guide.getRange("A:A").format.columnWidth = 22;
guide.getRange("B:B").format.columnWidth = 52;

const facets = paper => Object.entries(paper.facets)
  .filter(([, text]) => text).map(([name, text]) => `${name}: ${text}`).join("\n");
const describe = paper => [paper.title, paper.abstract, facets(paper)].filter(Boolean).join("\n");
for (const [queryId, rows] of byQuery) {
  const sheet = workbook.worksheets.add(queryId);
  const labels = ["Pair ID", "Candidate ID", "Candidate evidence", "Grade 0–3", "Notes"];
  sheet.getRange("A1:E1").values = [["Query ID", queryId, "Query evidence", "Split", rows[0].split]];
  sheet.getRange("A1:E1").format = heading;
  sheet.getRange("C2").values = [[describe(rows[0].query)]];
  sheet.getRange("C2").format.rowHeight = 150;
  sheet.getRange("A4:E4").values = [labels];
  sheet.getRange("A4:E4").format = heading;
  const last = 4 + rows.length;
  sheet.getRange(`A5:E${last}`).values = rows.map(row => [
    row.pair_id, row.candidate_id, describe(row.candidate), null, null,
  ]);
  sheet.getRange("A:A").format.columnWidth = 24;
  sheet.getRange("B:B").format.columnWidth = 15;
  sheet.getRange("C:C").format.columnWidth = 105;
  sheet.getRange("D:D").format.columnWidth = 12;
  sheet.getRange("E:E").format.columnWidth = 34;
  sheet.getRange(`C2:C${last}`).format.wrapText = true;
  sheet.getRange(`A5:E${last}`).format.rowHeight = 100;
  sheet.getRange(`D5:E${last}`).format.fill = "#EDF6FF";
  sheet.getRange(`D5:D${last}`).dataValidation = {
    rule: { type: "list", values: ["0", "1", "2", "3"] },
  };
  sheet.freezePanes.freezeRows(4);
}
const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(join(output, "human_review_template.xlsx"));
