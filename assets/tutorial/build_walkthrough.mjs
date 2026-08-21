import { spawnSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const root = process.cwd();
const outDir = resolve(root, "assets/tutorial");
const segmentDir = resolve(outDir, "segments");
mkdirSync(segmentDir, { recursive: true });

const slides = [
  {
    file: "00-intro.mp3",
    title: "GeoFlow IQ Studio",
    body: "Gcomm Oracle to IQGEO Oracle cleansing workflow",
  },
  {
    file: "01-worker.mp3",
    title: "1. Connect the Worker",
    body: "Run GeoFlow worker near Oracle\\NKeep credentials and heavy processing off the browser",
  },
  {
    file: "02-profile.mp3",
    title: "2. Profile Gcomm Oracle",
    body: "Check row counts, duplicate IDs, null geometries,\\Nstatus values, SRIDs, and invalid Oracle Spatial geometry",
  },
  {
    file: "03-rules.mp3",
    title: "3. Define IQGEO Rules",
    body: "Required fields, statuses, parent references,\\Ngeometry rules, and field mappings become repeatable SQL checks",
  },
  {
    file: "04-association.mp3",
    title: "4. Telecom Association Logic",
    body: "Nearest duct is not enough\\NPrefer parallel alignment and flag perpendicular matches",
  },
  {
    file: "05-dry-run.mp3",
    title: "5. Submit Dry Run",
    body: "Generate checkpoints, progress, SQL plans,\\Nand the audit trail before any write happens",
  },
  {
    file: "06-split.mp3",
    title: "6. Split the Records",
    body: "Clean rows move forward\\NReject, quarantine, and redundant rows stay auditable",
  },
  {
    file: "07-approve.mp3",
    title: "7. Approve Execute",
    body: "Execute jobs wait for operator approval\\NOnly reviewed runs can merge into IQGEO",
  },
  {
    file: "08-merge.mp3",
    title: "8. Merge Trusted Rows",
    body: "Batch windows merge approved clean rows into IQGEO Oracle\\NAI-assisted, rule-executed, human-approved cleansing",
  },
];

function durationSeconds(path) {
  const result = spawnSync("ffprobe", [
    "-v",
    "error",
    "-show_entries",
    "format=duration",
    "-of",
    "default=nw=1:nk=1",
    path,
  ]);
  const stdout = result.stdout?.toString().trim();
  if (stdout) {
    return Number(stdout);
  }
  if (result.error) {
    throw result.error;
  }
  throw new Error(result.stderr?.toString() || `Unable to read duration for ${path}`);
}

function assTime(seconds) {
  const cs = Math.round(seconds * 100);
  const h = Math.floor(cs / 360000);
  const m = Math.floor((cs % 360000) / 6000);
  const s = Math.floor((cs % 6000) / 100);
  const c = cs % 100;
  return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}.${String(c).padStart(2, "0")}`;
}

const concatList = slides
  .map((slide) => `file '${resolve(segmentDir, slide.file).replaceAll("'", "'\\''")}'`)
  .join("\n");
writeFileSync(resolve(segmentDir, "concat.txt"), `${concatList}\n`);

let cursor = 0;
const events = [];
for (const slide of slides) {
  const start = cursor;
  const end = cursor + durationSeconds(resolve(segmentDir, slide.file));
  events.push(`Dialogue: 0,${assTime(start)},${assTime(end)},Title,,0,0,0,,${slide.title}`);
  events.push(`Dialogue: 0,${assTime(start)},${assTime(end)},Body,,0,0,0,,${slide.body}`);
  cursor = end;
}
events.push(
  `Dialogue: 0,${assTime(0)},${assTime(cursor)},Accent,,0,0,0,,Tech Mahindra-inspired walkthrough | No Oracle credentials in browser`,
);

const ass = `[Script Info]
Title: GeoFlow IQ Studio Walkthrough
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Title,Liberation Sans,72,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,2,0,8,90,90,70,1
Style: Body,Liberation Sans,46,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,5,130,130,120,1
Style: Accent,Liberation Sans,44,&H00FFFFFF,&H000000FF,&H001917D7,&H00000000,1,0,0,0,100,100,0,0,1,3,0,2,110,110,90,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
${events.join("\n")}
`;

writeFileSync(resolve(outDir, "geoflow-walkthrough-synced.ass"), ass);
writeFileSync(resolve(outDir, "geoflow-walkthrough-duration.txt"), `${cursor.toFixed(2)}\n`);

console.log(`Prepared synced walkthrough timing for ${slides.length} segments (${cursor.toFixed(2)}s).`);
