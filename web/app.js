const state = {
  fileName: "",
  data: null,
  audit: null,
  cleaned: null,
  pipelineYaml: "",
};

const els = {
  modeButtons: document.querySelectorAll(".mode-button"),
  pipelineView: document.querySelector("#pipelineView"),
  iqgeoView: document.querySelector("#iqgeoView"),
  dbtestsView: document.querySelector("#dbtestsView"),
  howtoView: document.querySelector("#howtoView"),
  inspectView: document.querySelector("#inspectView"),
  fileInput: document.querySelector("#fileInput"),
  loadExample: document.querySelector("#loadExample"),
  datasetName: document.querySelector("#datasetName"),
  datasetMeta: document.querySelector("#datasetMeta"),
  featureCount: document.querySelector("#featureCount"),
  issueCount: document.querySelector("#issueCount"),
  fixableCount: document.querySelector("#fixableCount"),
  reviewCount: document.querySelector("#reviewCount"),
  issueList: document.querySelector("#issueList"),
  ruleList: document.querySelector("#ruleList"),
  issueTemplate: document.querySelector("#issueTemplate"),
  severityFilter: document.querySelector("#severityFilter"),
  idColumn: document.querySelector("#idColumn"),
  requiredColumns: document.querySelector("#requiredColumns"),
  targetCrs: document.querySelector("#targetCrs"),
  reanalyze: document.querySelector("#reanalyze"),
  downloadAudit: document.querySelector("#downloadAudit"),
  downloadCleaned: document.querySelector("#downloadCleaned"),
  copyClaudePrompt: document.querySelector("#copyClaudePrompt"),
  mapCanvas: document.querySelector("#mapCanvas"),
  boundsLabel: document.querySelector("#boundsLabel"),
  pipelineName: document.querySelector("#pipelineName"),
  pipelineMode: document.querySelector("#pipelineMode"),
  postgisTable: document.querySelector("#postgisTable"),
  postgisGeometry: document.querySelector("#postgisGeometry"),
  pipelineIdColumn: document.querySelector("#pipelineIdColumn"),
  pipelineTargetCrs: document.querySelector("#pipelineTargetCrs"),
  pipelineRequiredColumns: document.querySelector("#pipelineRequiredColumns"),
  pipelineTrimColumns: document.querySelector("#pipelineTrimColumns"),
  auditTable: document.querySelector("#auditTable"),
  reviewThreshold: document.querySelector("#reviewThreshold"),
  oracleStageTable: document.querySelector("#oracleStageTable"),
  oracleTargetTable: document.querySelector("#oracleTargetTable"),
  oracleSourceTable: document.querySelector("#oracleSourceTable"),
  oracleKeyColumns: document.querySelector("#oracleKeyColumns"),
  oracleColumns: document.querySelector("#oracleColumns"),
  sourceEngine: document.querySelector("#sourceEngine"),
  outputSink: document.querySelector("#outputSink"),
  pipelineRunMode: document.querySelector("#pipelineRunMode"),
  validationGate: document.querySelector("#validationGate"),
  configStatus: document.querySelector("#configStatus"),
  yamlOutput: document.querySelector("#yamlOutput"),
  downloadYaml: document.querySelector("#downloadYaml"),
  copyYaml: document.querySelector("#copyYaml"),
  copyCommands: document.querySelector("#copyCommands"),
  installCommand: document.querySelector("#installCommand"),
  dryRunCommand: document.querySelector("#dryRunCommand"),
  executeCommand: document.querySelector("#executeCommand"),
  gateList: document.querySelector("#gateList"),
  gcommSourceTable: document.querySelector("#gcommSourceTable"),
  iqgeoTargetTable: document.querySelector("#iqgeoTargetTable"),
  iqgeoStageTable: document.querySelector("#iqgeoStageTable"),
  iqgeoCleanTable: document.querySelector("#iqgeoCleanTable"),
  iqgeoRejectTable: document.querySelector("#iqgeoRejectTable"),
  iqgeoRedundantTable: document.querySelector("#iqgeoRedundantTable"),
  iqgeoRequiredFields: document.querySelector("#iqgeoRequiredFields"),
  iqgeoKeyFields: document.querySelector("#iqgeoKeyFields"),
  iqgeoAssetTypes: document.querySelector("#iqgeoAssetTypes"),
  iqgeoStatuses: document.querySelector("#iqgeoStatuses"),
  iqgeoRedundantStatuses: document.querySelector("#iqgeoRedundantStatuses"),
  iqgeoGeometryTypes: document.querySelector("#iqgeoGeometryTypes"),
  iqgeoSrid: document.querySelector("#iqgeoSrid"),
  iqgeoFailureAction: document.querySelector("#iqgeoFailureAction"),
  iqgeoParentRules: document.querySelector("#iqgeoParentRules"),
  iqgeoRulesOutput: document.querySelector("#iqgeoRulesOutput"),
  downloadIqgeoRules: document.querySelector("#downloadIqgeoRules"),
  copyIqgeoRules: document.querySelector("#copyIqgeoRules"),
  iqgeoRuleCards: document.querySelector("#iqgeoRuleCards"),
  gcommDsnEnv: document.querySelector("#gcommDsnEnv"),
  iqgeoDsnEnv: document.querySelector("#iqgeoDsnEnv"),
  gcommUserEnv: document.querySelector("#gcommUserEnv"),
  iqgeoUserEnv: document.querySelector("#iqgeoUserEnv"),
  dbTestGcommTable: document.querySelector("#dbTestGcommTable"),
  dbTestIqgeoTable: document.querySelector("#dbTestIqgeoTable"),
  dbTestGeometryColumn: document.querySelector("#dbTestGeometryColumn"),
  dbTestIdColumn: document.querySelector("#dbTestIdColumn"),
  dbCheckCount: document.querySelector("#dbCheckCount"),
  dbTestsOutput: document.querySelector("#dbTestsOutput"),
  downloadDbTests: document.querySelector("#downloadDbTests"),
  copyDbTests: document.querySelector("#copyDbTests"),
  dbTestCards: document.querySelector("#dbTestCards"),
};

const exampleData = {
  type: "FeatureCollection",
  name: "sample-parcels",
  crs: { type: "name", properties: { name: "EPSG:3857" } },
  features: [
    {
      type: "Feature",
      properties: { parcel_id: "P-001", owner_name: "  A Khan ", land_use: "res" },
      geometry: {
        type: "Polygon",
        coordinates: [[[-0.14, 51.5], [-0.12, 51.5], [-0.12, 51.52], [-0.14, 51.52]]],
      },
    },
    {
      type: "Feature",
      properties: { parcel_id: "P-001", owner_name: "M Smith", land_use: "commercial use" },
      geometry: {
        type: "Point",
        coordinates: [-0.11, 51.51],
      },
    },
    {
      type: "Feature",
      properties: { parcel_id: "P-003", owner_name: "", land_use: "park" },
      geometry: null,
    },
    {
      type: "Feature",
      properties: { parcel_id: "P-004", owner_name: "N Patel", land_use: "comm" },
      geometry: {
        type: "Point",
        coordinates: [392000, 6820000],
      },
    },
  ],
};

const categoryMaps = {
  land_use: {
    res: "residential",
    "residential use": "residential",
    comm: "commercial",
    "commercial use": "commercial",
  },
};

els.modeButtons.forEach((button) => {
  button.addEventListener("click", () => setView(button.dataset.view));
});

document.querySelectorAll("#pipelineView input, #pipelineView select").forEach((input) => {
  input.addEventListener("input", renderPipeline);
  input.addEventListener("change", renderPipeline);
});

document.querySelectorAll("#iqgeoView input, #iqgeoView select").forEach((input) => {
  input.addEventListener("input", renderIqgeoRules);
  input.addEventListener("change", renderIqgeoRules);
});

document.querySelectorAll("#dbtestsView input").forEach((input) => {
  input.addEventListener("input", renderDbTests);
  input.addEventListener("change", renderDbTests);
});

els.downloadYaml.addEventListener("click", () =>
  downloadText("oracle-output.yaml", state.pipelineYaml, "application/x-yaml"),
);
els.copyYaml.addEventListener("click", async () => {
  await copyText(state.pipelineYaml);
  flashButton(els.copyYaml, "Copied");
});
els.copyCommands.addEventListener("click", async () => {
  await copyText(
    [
      els.installCommand.textContent,
      els.dryRunCommand.textContent,
      els.executeCommand.textContent,
    ].join("\n"),
  );
  flashButton(els.copyCommands, "Copied");
});
els.downloadIqgeoRules.addEventListener("click", () =>
  downloadText("iqgeo-rules.yaml", els.iqgeoRulesOutput.value, "application/x-yaml"),
);
els.copyIqgeoRules.addEventListener("click", async () => {
  await copyText(els.iqgeoRulesOutput.value);
  flashButton(els.copyIqgeoRules, "Copied");
});
els.downloadDbTests.addEventListener("click", () =>
  downloadText("oracle-db-tests.sql", els.dbTestsOutput.value, "text/plain"),
);
els.copyDbTests.addEventListener("click", async () => {
  await copyText(els.dbTestsOutput.value);
  flashButton(els.copyDbTests, "Copied");
});

els.fileInput.addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  const text = await file.text();
  try {
    loadDataset(file.name, JSON.parse(text));
  } catch (error) {
    showError(`Could not parse ${file.name}: ${error.message}`);
  }
});

els.loadExample.addEventListener("click", () => {
  loadDataset("example-parcels.geojson", exampleData);
});

els.reanalyze.addEventListener("click", () => {
  if (state.data) analyzeAndRender();
});

els.severityFilter.addEventListener("change", renderIssues);
els.downloadAudit.addEventListener("click", () => downloadJson("audit.json", state.audit));
els.downloadCleaned.addEventListener("click", () =>
  downloadJson(cleanedFileName(), state.cleaned),
);
els.copyClaudePrompt.addEventListener("click", async () => {
  if (!state.audit) return;
  await copyText(buildClaudePrompt(state.audit));
  els.copyClaudePrompt.textContent = "Copied";
  window.setTimeout(() => {
    els.copyClaudePrompt.textContent = "Copy Claude prompt";
  }, 1200);
});

renderPipeline();
renderIqgeoRules();
renderDbTests();
drawEmptyMap();

function setView(view) {
  const showPipeline = view === "pipeline";
  const showIqgeo = view === "iqgeo";
  const showDbtests = view === "dbtests";
  const showHowto = view === "howto";
  els.pipelineView.classList.toggle("hidden", !showPipeline);
  els.iqgeoView.classList.toggle("hidden", !showIqgeo);
  els.dbtestsView.classList.toggle("hidden", !showDbtests);
  els.howtoView.classList.toggle("hidden", !showHowto);
  els.inspectView.classList.toggle(
    "hidden",
    showPipeline || showIqgeo || showDbtests || showHowto,
  );
  els.modeButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.view === view);
  });
}

function renderPipeline() {
  const config = readPipelineConfig();
  state.pipelineYaml = buildPipelineYaml(config);
  els.yamlOutput.value = state.pipelineYaml;
  els.pipelineRunMode.textContent = config.runMode;
  els.validationGate.textContent = String(config.reviewThreshold);
  els.configStatus.textContent = config.requiredColumns.length
    ? `${config.requiredColumns.length} required columns`
    : "No required columns";
  els.dryRunCommand.textContent =
    "a2a-geo-clean config/oracle-output.yaml --run-mode dry_run";
  els.executeCommand.textContent =
    "a2a-geo-clean config/oracle-output.yaml --run-mode execute";
  renderGates(config);
}

function readPipelineConfig() {
  return {
    projectName: valueOf(els.pipelineName),
    runMode: valueOf(els.pipelineMode),
    postgisTable: valueOf(els.postgisTable),
    geometryColumn: valueOf(els.postgisGeometry),
    idColumn: valueOf(els.pipelineIdColumn),
    targetCrs: valueOf(els.pipelineTargetCrs),
    requiredColumns: csvValues(els.pipelineRequiredColumns),
    trimColumns: csvValues(els.pipelineTrimColumns),
    auditTable: valueOf(els.auditTable),
    reviewThreshold: Number(valueOf(els.reviewThreshold) || 0.85),
    oracleStageTable: valueOf(els.oracleStageTable),
    oracleTargetTable: valueOf(els.oracleTargetTable),
    oracleSourceTable: valueOf(els.oracleSourceTable),
    oracleKeyColumns: csvValues(els.oracleKeyColumns),
    oracleColumns: csvValues(els.oracleColumns),
  };
}

function buildPipelineYaml(config) {
  return [
    "project:",
    `  name: ${yamlScalar(config.projectName)}`,
    `  run_mode: ${yamlScalar(config.runMode)}`,
    "  output_dir: ./runs/postgis-oracle-cleaning",
    "",
    "dataset:",
    "  source: postgis",
    `  table: ${yamlScalar(config.postgisTable)}`,
    `  geometry_column: ${yamlScalar(config.geometryColumn)}`,
    `  id_column: ${yamlScalar(config.idColumn)}`,
    `  target_crs: ${yamlScalar(config.targetCrs)}`,
    ...yamlListBlock("  required_columns:", config.requiredColumns),
    "",
    "rules:",
    ...yamlListBlock("  string_trim_columns:", config.trimColumns),
    "  category_maps:",
    "    land_use:",
    "      res: residential",
    "      residential use: residential",
    "      comm: commercial",
    "      commercial use: commercial",
    "  bounds:",
    "    minx: -180",
    "    miny: -90",
    "    maxx: 180",
    "    maxy: 90",
    "",
    "execution:",
    "  engine: postgis",
    `  audit_table: ${yamlScalar(config.auditTable)}`,
    `  review_confidence_threshold: ${config.reviewThreshold}`,
    "  write_cleaned_dataset: false",
    "",
    "output:",
    "  sink: oracle",
    "  mode: merge",
    `  stage_table: ${yamlScalar(config.oracleStageTable)}`,
    `  target_table: ${yamlScalar(config.oracleTargetTable)}`,
    `  source_table: ${yamlScalar(config.oracleSourceTable)}`,
    ...yamlListBlock("  key_columns:", config.oracleKeyColumns),
    ...yamlListBlock("  columns:", config.oracleColumns),
    "  geometry:",
    `    column: ${yamlScalar(oracleGeometryColumn(config))}`,
    "    source_format: wkt",
    "    srid: 4326",
    "",
  ].join("\n");
}

function renderGates(config) {
  const gates = [
    ["Dry-run first", "Generates PostGIS and Oracle SQL plans before execution."],
    ["Audit table", `Writes rule counts and validation checks to ${config.auditTable}.`],
    ["Review threshold", `Rules below ${config.reviewThreshold} confidence remain visible for review.`],
    ["Oracle merge", `Stages rows in ${config.oracleStageTable} before merging into ${config.oracleTargetTable}.`],
  ];
  els.gateList.textContent = "";
  for (const [title, text] of gates) {
    const item = document.createElement("div");
    item.className = "rule";
    item.innerHTML = "<strong></strong><span></span>";
    item.querySelector("strong").textContent = title;
    item.querySelector("span").textContent = text;
    els.gateList.append(item);
  }
}

function renderIqgeoRules() {
  const config = readIqgeoConfig();
  els.iqgeoRulesOutput.value = buildIqgeoRulesYaml(config);
  renderIqgeoRuleCards(config);
}

function readIqgeoConfig() {
  return {
    gcommSourceTable: valueOf(els.gcommSourceTable),
    iqgeoTargetTable: valueOf(els.iqgeoTargetTable),
    stageTable: valueOf(els.iqgeoStageTable),
    cleanTable: valueOf(els.iqgeoCleanTable),
    rejectTable: valueOf(els.iqgeoRejectTable),
    redundantTable: valueOf(els.iqgeoRedundantTable),
    requiredFields: csvValues(els.iqgeoRequiredFields),
    keyFields: csvValues(els.iqgeoKeyFields),
    assetTypes: csvValues(els.iqgeoAssetTypes),
    statuses: csvValues(els.iqgeoStatuses),
    redundantStatuses: csvValues(els.iqgeoRedundantStatuses),
    geometryTypes: csvValues(els.iqgeoGeometryTypes),
    srid: Number(valueOf(els.iqgeoSrid) || 4326),
    failureAction: valueOf(els.iqgeoFailureAction),
    parentRules: relationshipValues(els.iqgeoParentRules),
  };
}

function buildIqgeoRulesYaml(config) {
  return [
    "project:",
    "  name: gcomm-to-iqgeo-validation",
    "  run_mode: dry_run",
    "",
    "dataset:",
    "  source: oracle",
    `  table: ${yamlScalar(config.gcommSourceTable)}`,
    "  target_system: iqgeo",
    "",
    "oracle_pipeline:",
    `  source_table: ${yamlScalar(config.gcommSourceTable)}`,
    `  stage_table: ${yamlScalar(config.stageTable)}`,
    `  clean_table: ${yamlScalar(config.cleanTable)}`,
    `  reject_table: ${yamlScalar(config.rejectTable)}`,
    `  redundant_table: ${yamlScalar(config.redundantTable)}`,
    `  target_table: ${yamlScalar(config.iqgeoTargetTable)}`,
    "",
    "validation:",
    `  default_failure_action: ${yamlScalar(config.failureAction)}`,
    ...yamlListBlock("  required_fields:", config.requiredFields),
    ...yamlListBlock("  key_fields:", config.keyFields),
    ...yamlListBlock("  allowed_asset_types:", config.assetTypes),
    ...yamlListBlock("  allowed_statuses:", config.statuses),
    ...yamlListBlock("  redundant_statuses:", config.redundantStatuses),
    "  geometry:",
    `    srid: ${config.srid}`,
    ...yamlListBlock("    allowed_types:", config.geometryTypes),
    "    reject_null_geometry: true",
    "    reject_invalid_geometry: true",
    "    reject_zero_length_lines: true",
    "  relationships:",
    ...relationshipYaml(config.parentRules),
    "",
    "classification:",
    "  approved: import_to_iqgeo",
    "  fixed: import_with_audit",
    "  rejected: block_import",
    "  quarantined: hold_for_repair",
    "  redundant: archive_only",
    "  needs_review: human_decision",
    "",
    "audit:",
    "  write_validation_errors: true",
    "  write_import_audit: true",
    "  include_redundant_records: true",
    "",
  ].join("\n");
}

function renderIqgeoRuleCards(config) {
  const cards = [
    ["Schema", `${config.requiredFields.length} required fields and ${config.keyFields.length} key fields.`],
    ["Geometry", `${config.geometryTypes.join(", ") || "No"} geometries allowed at SRID ${config.srid}.`],
    ["Domain values", `${config.assetTypes.length} asset types and ${config.statuses.length} statuses allowed.`],
    ["Redundant data", `${config.redundantStatuses.join(", ") || "No"} statuses are separated from import.`],
    ["Relationships", `${config.parentRules.length} parent/reference checks configured.`],
  ];
  els.iqgeoRuleCards.textContent = "";
  for (const [title, text] of cards) {
    const item = document.createElement("div");
    item.className = "rule";
    item.innerHTML = "<strong></strong><span></span>";
    item.querySelector("strong").textContent = title;
    item.querySelector("span").textContent = text;
    els.iqgeoRuleCards.append(item);
  }
}

function renderDbTests() {
  const config = readDbTestConfig();
  const checks = buildDbTestCards(config);
  els.dbCheckCount.textContent = String(checks.length);
  els.dbTestsOutput.value = buildDbTestPack(config);
  els.dbTestCards.textContent = "";
  for (const [title, text] of checks) {
    const item = document.createElement("div");
    item.className = "rule";
    item.innerHTML = "<strong></strong><span></span>";
    item.querySelector("strong").textContent = title;
    item.querySelector("span").textContent = text;
    els.dbTestCards.append(item);
  }
}

function readDbTestConfig() {
  return {
    gcommDsnEnv: valueOf(els.gcommDsnEnv),
    iqgeoDsnEnv: valueOf(els.iqgeoDsnEnv),
    gcommUserEnv: valueOf(els.gcommUserEnv),
    iqgeoUserEnv: valueOf(els.iqgeoUserEnv),
    gcommTable: valueOf(els.dbTestGcommTable),
    iqgeoTable: valueOf(els.dbTestIqgeoTable),
    geometryColumn: valueOf(els.dbTestGeometryColumn),
    idColumn: valueOf(els.dbTestIdColumn),
  };
}

function buildDbTestCards(config) {
  return [
    ["Gcomm connection", `Connect with ${config.gcommDsnEnv} and ${config.gcommUserEnv}.`],
    ["IQGEO connection", `Connect with ${config.iqgeoDsnEnv} and ${config.iqgeoUserEnv}.`],
    ["Source table", `Confirm ${config.gcommTable} exists and is readable.`],
    ["Target table", `Confirm ${config.iqgeoTable} exists and is readable.`],
    ["Required columns", `Check ${config.idColumn} and ${config.geometryColumn}.`],
    ["Geometry quality", "Count null, invalid, and zero-length geometries."],
    ["Duplicate IDs", `Count duplicate ${config.idColumn} values in Gcomm.`],
    ["Import risk", "Measure source rows that need reject/quarantine handling."],
  ];
}

function buildDbTestPack(config) {
  const source = sqlQualifiedName(config.gcommTable);
  const target = sqlQualifiedName(config.iqgeoTable);
  const geom = sqlIdentifier(config.geometryColumn);
  const id = sqlIdentifier(config.idColumn);
  return [
    "-- Oracle database pre-flight test pack",
    "-- Run from the backend runner. Do not paste passwords into the browser.",
    "",
    "-- Required environment variables:",
    `-- export ${config.gcommDsnEnv}="gcomm-host:1521/service"`,
    `-- export ${config.gcommUserEnv}="gcomm_user"`,
    `-- export GCOMM_ORACLE_PASSWORD="***"`,
    `-- export ${config.iqgeoDsnEnv}="iqgeo-host:1521/service"`,
    `-- export ${config.iqgeoUserEnv}="iqgeo_user"`,
    `-- export IQGEO_ORACLE_PASSWORD="***"`,
    "",
    "-- Python smoke test:",
    "python -m a2a_geo_cleaning.cli config/iqgeo-rules.yaml --run-mode dry_run",
    "",
    "-- 1. Source table row count",
    `SELECT COUNT(*) AS source_rows FROM ${source};`,
    "",
    "-- 2. Target table row count",
    `SELECT COUNT(*) AS target_rows FROM ${target};`,
    "",
    "-- 3. Source ID and geometry null checks",
    "SELECT",
    `  SUM(CASE WHEN ${id} IS NULL THEN 1 ELSE 0 END) AS null_ids,`,
    `  SUM(CASE WHEN ${geom} IS NULL THEN 1 ELSE 0 END) AS null_geometries`,
    `FROM ${source};`,
    "",
    "-- 4. Duplicate source IDs",
    `SELECT ${id}, COUNT(*) AS duplicate_count`,
    `FROM ${source}`,
    `WHERE ${id} IS NOT NULL`,
    `GROUP BY ${id}`,
    "HAVING COUNT(*) > 1",
    "FETCH FIRST 50 ROWS ONLY;",
    "",
    "-- 5. Oracle Spatial geometry validity",
    "SELECT validation_result, COUNT(*) AS feature_count",
    "FROM (",
    `  SELECT SDO_GEOM.VALIDATE_GEOMETRY_WITH_CONTEXT(${geom}, 0.005) AS validation_result`,
    `  FROM ${source}`,
    `  WHERE ${geom} IS NOT NULL`,
    ")",
    "GROUP BY validation_result",
    "ORDER BY feature_count DESC;",
    "",
    "-- 6. Geometry SRID distribution",
    `SELECT ${geom}.SDO_SRID AS srid, COUNT(*) AS feature_count`,
    `FROM ${source}`,
    `WHERE ${geom} IS NOT NULL`,
    `GROUP BY ${geom}.SDO_SRID`,
    "ORDER BY feature_count DESC;",
    "",
    "-- 7. Redundant/status values to classify before IQGEO import",
    "SELECT STATUS, COUNT(*) AS row_count",
    `FROM ${source}`,
    "GROUP BY STATUS",
    "ORDER BY row_count DESC;",
    "",
    "-- 8. Source IDs that already exist in IQGEO target",
    `SELECT COUNT(*) AS ids_already_in_iqgeo`,
    `FROM ${source} s`,
    `JOIN ${target} t ON t.${id} = s.${id};`,
    "",
  ].join("\n");
}

function loadDataset(fileName, data) {
  if (data.type !== "FeatureCollection" || !Array.isArray(data.features)) {
    throw new Error("Only GeoJSON FeatureCollection files are supported in the browser dashboard.");
  }
  state.fileName = fileName;
  state.data = data;
  els.reanalyze.disabled = false;
  analyzeAndRender();
}

function analyzeAndRender() {
  const config = readConfig();
  const analysis = analyzeGeoJson(state.data, config);
  state.audit = analysis.audit;
  state.cleaned = analysis.cleaned;

  els.datasetName.textContent = state.fileName;
  els.datasetMeta.textContent = `${analysis.geometryTypes.join(", ") || "No geometries"} · ${analysis.propertyColumns.length} property columns`;
  els.featureCount.textContent = String(analysis.featureCount);
  els.issueCount.textContent = String(analysis.issues.length);
  els.fixableCount.textContent = String(analysis.issues.filter((issue) => issue.autoFixable).length);
  els.reviewCount.textContent = String(analysis.issues.filter((issue) => !issue.autoFixable).length);
  els.boundsLabel.textContent = analysis.bounds
    ? analysis.bounds.map((value) => Number(value).toFixed(4)).join(", ")
    : "No bounds";
  els.downloadAudit.disabled = false;
  els.downloadCleaned.disabled = false;
  els.copyClaudePrompt.disabled = false;

  renderIssues();
  renderRules(analysis.rules);
  drawMap(state.data, analysis.bounds);
}

function readConfig() {
  return {
    idColumn: els.idColumn.value.trim(),
    requiredColumns: els.requiredColumns.value
      .split(",")
      .map((column) => column.trim())
      .filter(Boolean),
    targetCrs: els.targetCrs.value.trim() || "EPSG:4326",
    categoryMaps,
  };
}

function analyzeGeoJson(data, config) {
  const issues = [];
  const rules = [];
  const features = data.features;
  const propertyColumns = collectPropertyColumns(features);
  const geometryTypes = [...new Set(features.map((feature) => feature.geometry?.type || "Missing"))];
  const bounds = calculateBounds(features);

  addSchemaIssues(config, propertyColumns, issues, rules);
  addCrsIssues(data, config, issues, rules);
  addGeometryIssues(features, bounds, issues, rules);
  addAttributeIssues(features, config, issues, rules);

  return {
    featureCount: features.length,
    propertyColumns,
    geometryTypes,
    bounds,
    issues,
    rules,
    cleaned: cleanGeoJson(data, config),
    audit: {
      dataset: {
        fileName: state.fileName,
        featureCount: features.length,
        propertyColumns,
        geometryTypes,
        bounds,
      },
      issues,
      recommendedRules: rules,
      generatedAt: new Date().toISOString(),
    },
  };
}

function addSchemaIssues(config, propertyColumns, issues, rules) {
  for (const column of config.requiredColumns) {
    if (!propertyColumns.includes(column)) {
      issues.push({
        severity: "high",
        title: `Missing required column: ${column}`,
        description: `The configured required field "${column}" is not present in the uploaded properties.`,
        fix: "Add the field before export, map an equivalent source field, or remove it from required columns if it is not needed.",
        affected: "Dataset schema",
        status: "Needs review",
        autoFixable: false,
      });
    }
    rules.push({
      type: "require_column",
      target: column,
      fix: `Verify "${column}" exists before accepting the cleaned dataset.`,
    });
  }
}

function addCrsIssues(data, config, issues, rules) {
  const sourceCrs = data.crs?.properties?.name || "unknown";
  if (sourceCrs === "unknown") {
    issues.push({
      severity: "medium",
      title: "CRS is missing",
      description: "The GeoJSON does not declare a coordinate reference system.",
      fix: `Confirm the source CRS, then assign or reproject to ${config.targetCrs} in the backend workflow.`,
      affected: "Dataset CRS",
      status: "Needs review",
      autoFixable: false,
    });
  } else if (sourceCrs !== config.targetCrs) {
    issues.push({
      severity: "medium",
      title: `CRS differs from target ${config.targetCrs}`,
      description: `The file declares ${sourceCrs}, while the workflow target is ${config.targetCrs}.`,
      fix: `Run the CRS normalization rule to reproject geometries to ${config.targetCrs}.`,
      affected: "Dataset CRS",
      status: "Auto-fix in backend",
      autoFixable: true,
    });
  }
  rules.push({
    type: "normalize_crs",
    target: "geometry",
    fix: `Normalize output CRS to ${config.targetCrs}.`,
  });
}

function addGeometryIssues(features, bounds, issues, rules) {
  let emptyCount = 0;
  let unclosedRings = 0;
  let invalidCoordinates = 0;
  const worldBounds = bounds && (bounds[0] < -180 || bounds[1] < -90 || bounds[2] > 180 || bounds[3] > 90);

  for (const feature of features) {
    if (!feature.geometry) {
      emptyCount += 1;
      continue;
    }
    if (!coordinatesAreFinite(feature.geometry.coordinates)) {
      invalidCoordinates += 1;
    }
    if (feature.geometry.type === "Polygon") {
      unclosedRings += countUnclosedRings(feature.geometry.coordinates);
    }
    if (feature.geometry.type === "MultiPolygon") {
      for (const polygon of feature.geometry.coordinates) {
        unclosedRings += countUnclosedRings(polygon);
      }
    }
  }

  if (emptyCount) {
    issues.push({
      severity: "high",
      title: "Empty or missing geometries",
      description: `${emptyCount} feature${plural(emptyCount)} cannot be used for spatial joins, validation, or map display.`,
      fix: "Drop empty geometries or recover them from the source system before running topology checks.",
      affected: `${emptyCount} feature${plural(emptyCount)}`,
      status: "Auto-fix available",
      autoFixable: true,
    });
  }
  if (unclosedRings) {
    issues.push({
      severity: "high",
      title: "Polygon rings are not closed",
      description: `${unclosedRings} polygon ring${plural(unclosedRings)} do not repeat the first coordinate at the end.`,
      fix: "Close rings deterministically, then run make-valid geometry repair.",
      affected: `${unclosedRings} ring${plural(unclosedRings)}`,
      status: "Auto-fix available",
      autoFixable: true,
    });
  }
  if (invalidCoordinates) {
    issues.push({
      severity: "high",
      title: "Invalid coordinate values",
      description: `${invalidCoordinates} feature${plural(invalidCoordinates)} contain non-numeric or infinite coordinates.`,
      fix: "Remove or repair those coordinates from the source data before geometry validation.",
      affected: `${invalidCoordinates} feature${plural(invalidCoordinates)}`,
      status: "Needs review",
      autoFixable: false,
    });
  }
  if (worldBounds) {
    issues.push({
      severity: "medium",
      title: "Coordinates fall outside longitude/latitude bounds",
      description: "The dataset has coordinates outside -180..180 longitude or -90..90 latitude.",
      fix: "Check whether the source CRS is projected. Reproject before treating coordinates as EPSG:4326.",
      affected: "Dataset bounds",
      status: "Needs review",
      autoFixable: false,
    });
  }

  rules.push(
    {
      type: "drop_empty_geometry",
      target: "geometry",
      fix: "Remove features with null or empty geometry.",
    },
    {
      type: "make_valid",
      target: "geometry",
      fix: "Repair invalid geometry with Shapely/GeoPandas in the backend workflow.",
    },
    {
      type: "check_bounds",
      target: "geometry",
      fix: "Verify coordinates stay inside configured bounds.",
    },
  );
}

function addAttributeIssues(features, config, issues, rules) {
  const idValues = new Map();
  let duplicateRows = 0;
  const trimCounts = new Map();
  const categoryCounts = new Map();

  features.forEach((feature) => {
    const properties = feature.properties || {};
    const id = properties[config.idColumn];
    if (id !== undefined && id !== null && id !== "") {
      const count = idValues.get(id) || 0;
      idValues.set(id, count + 1);
      if (count === 1) duplicateRows += 2;
      if (count > 1) duplicateRows += 1;
    }

    for (const [column, value] of Object.entries(properties)) {
      if (typeof value === "string" && value !== value.trim()) {
        trimCounts.set(column, (trimCounts.get(column) || 0) + 1);
      }
    }

    for (const [column, mapping] of Object.entries(config.categoryMaps)) {
      const raw = properties[column];
      const key = typeof raw === "string" ? raw.trim().toLowerCase() : raw;
      if (Object.prototype.hasOwnProperty.call(mapping, key)) {
        categoryCounts.set(column, (categoryCounts.get(column) || 0) + 1);
      }
    }
  });

  if (duplicateRows) {
    issues.push({
      severity: "medium",
      title: `Duplicate ${config.idColumn} values`,
      description: `${duplicateRows} feature${plural(duplicateRows)} share an identifier value.`,
      fix: "Review duplicates, choose a canonical record, merge attributes where needed, or assign stable unique IDs.",
      affected: `${duplicateRows} feature${plural(duplicateRows)}`,
      status: "Needs review",
      autoFixable: false,
    });
  }

  for (const [column, count] of trimCounts.entries()) {
    issues.push({
      severity: "low",
      title: `Whitespace in ${column}`,
      description: `${count} value${plural(count)} have leading or trailing whitespace.`,
      fix: `Apply the trim_string rule to "${column}".`,
      affected: `${count} value${plural(count)}`,
      status: "Auto-fix available",
      autoFixable: true,
    });
    rules.push({
      type: "trim_string",
      target: column,
      fix: `Trim leading and trailing whitespace in "${column}".`,
    });
  }

  for (const [column, count] of categoryCounts.entries()) {
    issues.push({
      severity: "low",
      title: `Known category variants in ${column}`,
      description: `${count} value${plural(count)} match configured category aliases.`,
      fix: `Apply the normalize_category rule to standardize "${column}".`,
      affected: `${count} value${plural(count)}`,
      status: "Auto-fix available",
      autoFixable: true,
    });
    rules.push({
      type: "normalize_category",
      target: column,
      fix: `Map configured aliases in "${column}" to canonical labels.`,
    });
  }

  rules.push({
    type: "flag_duplicates",
    target: config.idColumn,
    fix: `Flag repeated "${config.idColumn}" values for manual review.`,
  });
}

function cleanGeoJson(data, config) {
  const cleaned = structuredClone(data);
  cleaned.features = cleaned.features
    .filter((feature) => feature.geometry)
    .map((feature) => {
      const next = structuredClone(feature);
      const properties = next.properties || {};
      for (const [column, value] of Object.entries(properties)) {
        if (typeof value === "string") {
          properties[column] = value.trim();
        }
      }
      for (const [column, mapping] of Object.entries(config.categoryMaps)) {
        const raw = properties[column];
        const key = typeof raw === "string" ? raw.trim().toLowerCase() : raw;
        if (Object.prototype.hasOwnProperty.call(mapping, key)) {
          properties[column] = mapping[key];
        }
      }
      if (next.geometry?.type === "Polygon") {
        next.geometry.coordinates = closePolygon(next.geometry.coordinates);
      }
      if (next.geometry?.type === "MultiPolygon") {
        next.geometry.coordinates = next.geometry.coordinates.map(closePolygon);
      }
      return next;
    });
  return cleaned;
}

function collectPropertyColumns(features) {
  const columns = new Set();
  for (const feature of features) {
    Object.keys(feature.properties || {}).forEach((column) => columns.add(column));
  }
  return [...columns].sort();
}

function calculateBounds(features) {
  const points = [];
  for (const feature of features) {
    if (feature.geometry) collectPoints(feature.geometry.coordinates, points);
  }
  if (!points.length) return null;
  return points.reduce(
    (bounds, point) => [
      Math.min(bounds[0], point[0]),
      Math.min(bounds[1], point[1]),
      Math.max(bounds[2], point[0]),
      Math.max(bounds[3], point[1]),
    ],
    [Infinity, Infinity, -Infinity, -Infinity],
  );
}

function collectPoints(value, points) {
  if (!Array.isArray(value)) return;
  if (typeof value[0] === "number" && typeof value[1] === "number") {
    if (Number.isFinite(value[0]) && Number.isFinite(value[1])) points.push(value);
    return;
  }
  value.forEach((child) => collectPoints(child, points));
}

function coordinatesAreFinite(value) {
  if (!Array.isArray(value)) return false;
  if (typeof value[0] === "number" || typeof value[1] === "number") {
    return Number.isFinite(value[0]) && Number.isFinite(value[1]);
  }
  return value.every(coordinatesAreFinite);
}

function countUnclosedRings(rings) {
  return rings.filter((ring) => ring.length > 0 && !samePoint(ring[0], ring[ring.length - 1])).length;
}

function closePolygon(rings) {
  return rings.map((ring) => {
    if (!ring.length || samePoint(ring[0], ring[ring.length - 1])) return ring;
    return [...ring, [...ring[0]]];
  });
}

function samePoint(a, b) {
  return Array.isArray(a) && Array.isArray(b) && a[0] === b[0] && a[1] === b[1];
}

function renderIssues() {
  const issues = state.audit?.issues || [];
  const severity = els.severityFilter.value;
  const filtered = severity === "all" ? issues : issues.filter((issue) => issue.severity === severity);
  els.issueList.textContent = "";

  if (!filtered.length) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = issues.length ? "No issues match this filter." : "No issues found.";
    els.issueList.append(empty);
    return;
  }

  for (const issue of filtered) {
    const fragment = els.issueTemplate.content.cloneNode(true);
    fragment.querySelector(".severity").classList.add(issue.severity);
    fragment.querySelector("h4").textContent = issue.title;
    fragment.querySelector(".description").textContent = issue.description;
    fragment.querySelector(".fix").textContent = `Fix: ${issue.fix}`;
    fragment.querySelector(".affected").textContent = issue.affected;
    fragment.querySelector(".status").textContent = issue.status;
    els.issueList.append(fragment);
  }
}

function renderRules(rules) {
  els.ruleList.textContent = "";
  if (!rules.length) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "No rules proposed.";
    els.ruleList.append(empty);
    return;
  }
  for (const rule of rules) {
    const item = document.createElement("div");
    item.className = "rule";
    item.innerHTML = `<strong></strong><span></span>`;
    item.querySelector("strong").textContent = `${rule.type} · ${rule.target}`;
    item.querySelector("span").textContent = rule.fix;
    els.ruleList.append(item);
  }
}

function drawEmptyMap() {
  const ctx = els.mapCanvas.getContext("2d");
  ctx.clearRect(0, 0, els.mapCanvas.width, els.mapCanvas.height);
  ctx.fillStyle = "#eef2e7";
  ctx.fillRect(0, 0, els.mapCanvas.width, els.mapCanvas.height);
  ctx.fillStyle = "#687069";
  ctx.font = "18px sans-serif";
  ctx.fillText("Upload GeoJSON to preview features", 32, 52);
}

function drawMap(data, bounds) {
  if (!bounds) {
    drawEmptyMap();
    return;
  }
  const canvas = els.mapCanvas;
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  const padding = 28;
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#eef2e7";
  ctx.fillRect(0, 0, width, height);
  ctx.strokeStyle = "#d0d9cc";
  ctx.lineWidth = 1;
  for (let x = 0; x < width; x += 48) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
    ctx.stroke();
  }
  for (let y = 0; y < height; y += 48) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }

  const project = ([x, y]) => {
    const xRange = bounds[2] - bounds[0] || 1;
    const yRange = bounds[3] - bounds[1] || 1;
    return [
      padding + ((x - bounds[0]) / xRange) * (width - padding * 2),
      height - padding - ((y - bounds[1]) / yRange) * (height - padding * 2),
    ];
  };

  for (const feature of data.features) {
    if (!feature.geometry) continue;
    drawGeometry(ctx, feature.geometry, project);
  }
}

function drawGeometry(ctx, geometry, project) {
  ctx.strokeStyle = "#26735b";
  ctx.fillStyle = "rgba(38, 115, 91, 0.18)";
  ctx.lineWidth = 2;
  if (geometry.type === "Point") {
    const [x, y] = project(geometry.coordinates);
    ctx.beginPath();
    ctx.arc(x, y, 4, 0, Math.PI * 2);
    ctx.fillStyle = "#315f8a";
    ctx.fill();
    return;
  }
  if (geometry.type === "LineString") {
    drawLine(ctx, geometry.coordinates, project, false);
  }
  if (geometry.type === "Polygon") {
    geometry.coordinates.forEach((ring) => drawLine(ctx, ring, project, true));
  }
  if (geometry.type === "MultiPolygon") {
    geometry.coordinates.forEach((polygon) =>
      polygon.forEach((ring) => drawLine(ctx, ring, project, true)),
    );
  }
}

function drawLine(ctx, coordinates, project, fill) {
  if (!coordinates.length) return;
  ctx.beginPath();
  coordinates.forEach((point, index) => {
    const [x, y] = project(point);
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  if (fill) ctx.fill();
  ctx.stroke();
}

function downloadJson(fileName, payload) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: "application/json",
  });
  triggerDownload(fileName, blob);
}

function downloadText(fileName, payload, type) {
  triggerDownload(fileName, new Blob([payload], { type }));
}

function triggerDownload(fileName, blob) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  link.click();
  URL.revokeObjectURL(url);
}

function buildClaudePrompt(audit) {
  return [
    "You are reviewing a geospatial data cleaning audit.",
    "Suggest safe next-stage fixes only. Do not invent data values or directly rewrite geometry coordinates.",
    "Return JSON with recommendations containing issue, recommended_fix, risk, and requires_human_review.",
    "",
    JSON.stringify(audit, null, 2),
  ].join("\n");
}

async function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.top = "-1000px";
  document.body.append(textarea);
  textarea.select();
  document.execCommand("copy");
  textarea.remove();
}

function cleanedFileName() {
  const stem = state.fileName.replace(/\.(geo)?json$/i, "");
  return `${stem}.cleaned.geojson`;
}

function valueOf(element) {
  return element.value.trim();
}

function csvValues(element) {
  return valueOf(element)
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
}

function yamlScalar(value) {
  if (/^[A-Za-z0-9_.:/-]+$/.test(value)) return value;
  return JSON.stringify(value);
}

function yamlListBlock(key, values) {
  if (!values.length) return [`${key} []`];
  const indent = " ".repeat((key.match(/^ */)?.[0].length || 0) + 2);
  return [key, ...values.map((value) => `${indent}- ${yamlScalar(value)}`)];
}

function oracleGeometryColumn(config) {
  return (
    config.oracleColumns.find((column) => column.toUpperCase() === "GEOM") ||
    config.oracleColumns.at(-1) ||
    "GEOM"
  );
}

function relationshipValues(element) {
  return valueOf(element)
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean)
    .map((value) => {
      const [child, parent] = value.split("->").map((part) => part.trim());
      return { child, parent: parent || "" };
    });
}

function relationshipYaml(rules) {
  if (!rules.length) return ["    []"];
  return rules.flatMap((rule) => [
    "    - type: parent_reference",
    `      child: ${yamlScalar(rule.child)}`,
    `      parent: ${yamlScalar(rule.parent)}`,
    "      on_missing: quarantine",
  ]);
}

function sqlQualifiedName(value) {
  return value
    .split(".")
    .map((part) => sqlIdentifier(part.trim()))
    .join(".");
}

function sqlIdentifier(value) {
  const cleaned = value.trim().replace(/^"|"$/g, "");
  if (!cleaned) return '""';
  return `"${cleaned.replaceAll('"', '""').toUpperCase()}"`;
}

function flashButton(button, text) {
  const original = button.textContent;
  button.textContent = text;
  window.setTimeout(() => {
    button.textContent = original;
  }, 1200);
}

function showError(message) {
  els.datasetName.textContent = "Upload failed";
  els.datasetMeta.textContent = message;
}

function plural(count) {
  return count === 1 ? "" : "s";
}
