const fs = require("fs");
const path = require("path");

const TOOL_ROOT = __dirname;
const REPO_ROOT = path.resolve(TOOL_ROOT, "..", "..");
const DEFAULT_CLIENT_ROOT = path.join(REPO_ROOT, "client", "EVE", "tq");
const DEFAULT_OUTPUT_PATH = path.join(TOOL_ROOT, "runtime", "catalog.json");

function parseArgs(argv) {
  const options = {
    clientRoot: process.env.ELYSIAN_JESSICA_EVE_CLIENT || DEFAULT_CLIENT_ROOT,
    outputPath: process.env.ELYSIAN_JESSICA_CATALOG_PATH || DEFAULT_OUTPUT_PATH,
  };
  for (let index = 2; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--client-root" && argv[index + 1]) {
      options.clientRoot = argv[index + 1];
      index += 1;
    } else if (arg === "--output" && argv[index + 1]) {
      options.outputPath = argv[index + 1];
      index += 1;
    } else if (arg === "--help" || arg === "-h") {
      console.log("usage: node build_standalone_catalog.js [--client-root <EVE tq path>] [--output <catalog.json>]");
      process.exit(0);
    }
  }
  options.clientRoot = path.resolve(options.clientRoot);
  options.outputPath = path.resolve(options.outputPath);
  return options;
}

function normalizeSlash(value) {
  return String(value || "").replace(/\\/g, "/");
}

function readJson(filePath, fallback = null) {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch (error) {
    return fallback;
  }
}

function readJsonl(filePath) {
  if (!filePath || !fs.existsSync(filePath)) {
    return [];
  }
  const rows = [];
  for (const line of fs.readFileSync(filePath, "utf8").split(/\r?\n/)) {
    if (!line.trim()) {
      continue;
    }
    rows.push(JSON.parse(line));
  }
  return rows;
}

function safeStat(filePath) {
  try {
    return fs.statSync(filePath);
  } catch (error) {
    return null;
  }
}

function walkForFile(root, filename, found = []) {
  if (!root || !fs.existsSync(root)) {
    return found;
  }
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    const filePath = path.join(root, entry.name);
    if (entry.isDirectory()) {
      walkForFile(filePath, filename, found);
    } else if (entry.name.toLowerCase() === filename.toLowerCase()) {
      found.push(filePath);
    }
  }
  return found;
}

function findLatestClientSdeExport() {
  const exportsRoot = path.join(REPO_ROOT, "tools", "ClientSDE", "exports");
  if (!fs.existsSync(exportsRoot)) {
    return null;
  }
  return fs.readdirSync(exportsRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => path.join(exportsRoot, entry.name))
    .sort((left, right) => {
      const leftStat = safeStat(left);
      const rightStat = safeStat(right);
      return (rightStat ? rightStat.mtimeMs : 0) - (leftStat ? leftStat.mtimeMs : 0);
    })[0] || null;
}

function findFirst(root, filename) {
  return walkForFile(root, filename)[0] || null;
}

function loadResIndex(clientRoot = DEFAULT_CLIENT_ROOT) {
  const indexPath = path.join(clientRoot, "resfileindex.txt");
  const byResPath = new Map();
  if (!fs.existsSync(indexPath)) {
    return { indexPath, byResPath, count: 0 };
  }
  for (const line of fs.readFileSync(indexPath, "utf8").split(/\r?\n/)) {
    if (!line.trim()) {
      continue;
    }
    const [rawResPath, relativePath, hash, sizeRaw, compressedSizeRaw] = line.split(",");
    if (!rawResPath || !relativePath) {
      continue;
    }
    const resPath = normalizeSlash(rawResPath);
    byResPath.set(resPath.toLowerCase(), {
      resPath,
      relativePath: normalizeSlash(relativePath),
      hash,
      sizeBytes: Number(sizeRaw) || 0,
      compressedSizeBytes: Number(compressedSizeRaw) || 0,
    });
  }
  return { indexPath, byResPath, count: byResPath.size };
}

function normalizeGraphicRow(row) {
  return {
    graphicID: Number(row && row._key) || 0,
    sofHullName: row && row.sofHullName || null,
    sofFactionName: row && row.sofFactionName || null,
    sofRaceName: row && row.sofRaceName || null,
    sofLayout: row && row.sofLayout || null,
    sofMaterialSetID: row && row.sofMaterialSetID || null,
    graphicFile: row && row.graphicFile || null,
    explosionBucketID: Number(row && row.explosionBucketID) || null,
  };
}

function buildDogmaByType(rows) {
  return new Map((rows || []).map((row) => [
    Number(row && row._key) || 0,
    new Map((row && row.dogmaAttributes || []).map((attribute) => [
      Number(attribute && attribute.attributeID) || 0,
      Number(attribute && attribute.value) || 0,
    ])),
  ]));
}

function buildGroupGraphicsByID(rows) {
  return new Map((rows || []).map((row) => [
    Number(row && row._key) || 0,
    (row && row.graphicIDs || []).map(Number).filter((value) => value > 0),
  ]));
}

function buildAnimatedHullTokens(resIndex) {
  const tokens = new Set();
  for (const entry of resIndex.byResPath.values()) {
    const resourcePath = String(entry && entry.resPath || "").toLowerCase();
    if (
      !resourcePath.endsWith(".gr2") ||
      !/(?:^|[/_])(ani|animation|animations)(?:[/_]|$)/.test(resourcePath)
    ) {
      continue;
    }
    const parts = resourcePath.split("/");
    const filename = parts[parts.length - 1] || "";
    const folder = parts.length > 1 ? parts[parts.length - 2] : "";
    for (const candidate of [filename.split("_")[0], folder]) {
      const normalized = candidate.replace(/\.(gr2|black|red)$/i, "").trim();
      if (normalized.length >= 3) {
        tokens.add(normalized);
      }
    }
  }
  return tokens;
}

function classifyAsset(row) {
  const categoryID = Number(row && row.categoryID) || 0;
  const groupName = String(row && row.groupName || "").toLowerCase();
  const name = String(row && (row.name || row.typeName) || "").toLowerCase();
  const blob = `${groupName} ${name}`;
  if (categoryID === 6) return "ship";
  if (blob.includes("stargate") || blob.includes("jump gate") || blob.includes("acceleration gate")) return "gate";
  if (blob.includes("station") || blob.includes("citadel") || blob.includes("engineering complex") || blob.includes("refinery")) return "station";
  if (blob.includes("structure") || blob.includes("starbase") || blob.includes("control tower") || blob.includes("sentry")) return "structure";
  if (blob.includes("drone") || blob.includes("fighter")) return "drone";
  return "object";
}

function buildSofDna(asset) {
  const { hull, faction, race, layout } = asset && asset.sof ? asset.sof : {};
  if (!hull || !faction || !race) {
    return null;
  }
  let dna = `${hull}:${faction}:${race}`;
  const layouts = Array.isArray(layout)
    ? layout.filter(Boolean)
    : (layout ? [layout] : []);
  if (layouts.length > 0) {
    dna += `:layout?${layouts.join(";")}`;
  }
  return dna;
}

function makeAsset(row, graphic, sourceKind, animatedHullTokens) {
  const asset = {
    typeID: Number(row.typeID) || 0,
    name: row.name || row.typeName || `Type ${row.typeID}`,
    groupID: Number(row.groupID) || 0,
    groupName: row.groupName || "Unknown",
    categoryID: Number(row.categoryID) || 0,
    graphicID: Number(row.graphicID) || 0,
    radius: Number(row.radius) || 1,
    published: row.published === true,
    sourceKind,
    assetKind: classifyAsset(row),
    sof: {
      hull: graphic.sofHullName,
      faction: graphic.sofFactionName,
      race: graphic.sofRaceName,
      layout: graphic.sofLayout,
      materialSetID: graphic.sofMaterialSetID,
    },
    explosionBucketID: graphic.explosionBucketID,
    graphicFile: graphic.graphicFile,
  };
  asset.dna = buildSofDna(asset);
  const hullToken = String(asset.sof.hull || "")
    .toLowerCase()
    .replace(/_(t[0-9]+|base).*$/i, "")
    .split("_")[0];
  asset.capabilities = {
    animations:
      asset.assetKind === "gate" ||
      (hullToken.length >= 3 && animatedHullTokens.has(hullToken)),
    explosions: false,
  };
  return asset;
}

function classifyWeapon(row, graphic) {
  const groupName = String(row && row.groupName || "");
  const name = String(row && (row.name || row.typeName) || "");
  const graphicFile = String(graphic && graphic.graphicFile || "");
  const blob = `${groupName} ${name} ${graphicFile}`.toLowerCase();
  if (Number(row && row.categoryID) !== 7 || !graphicFile) {
    return null;
  }
  if (groupName.toLowerCase().includes("blueprint")) {
    return null;
  }
  let kind = null;
  let family = null;
  if (blob.includes("missile launcher") || blob.includes("/launcher/")) {
    kind = "launcher";
    family = "missile";
  } else if (blob.includes("energy weapon") || blob.includes("/energy/")) {
    kind = "turret";
    family = "energy";
  } else if (blob.includes("hybrid weapon") || blob.includes("/hybrid/")) {
    kind = "turret";
    family = "hybrid";
  } else if (blob.includes("projectile weapon") || blob.includes("/projectile/")) {
    kind = "turret";
    family = "projectile";
  }
  if (!kind || !/^res:\/dx9\/model\/turret\//i.test(graphicFile)) {
    return null;
  }
  let variant = family;
  if (family === "energy") {
    variant = blob.includes("/pulse/") || blob.includes("pulse")
      ? "Pulse Laser"
      : "Beam Laser";
  } else if (family === "hybrid") {
    variant = blob.includes("/blaster/") || blob.includes("blaster")
      ? "Blaster"
      : "Railgun";
  } else if (family === "projectile") {
    variant = blob.includes("/autocannon/") || blob.includes("autocannon")
      ? "Autocannon"
      : "Artillery";
  } else if (family === "missile") {
    if (blob.includes("rocket")) variant = "Rocket Launcher";
    else if (blob.includes("rapid light")) variant = "Rapid Light Missile";
    else if (blob.includes("rapid heavy")) variant = "Rapid Heavy Missile";
    else if (blob.includes("rapid torpedo")) variant = "Rapid Torpedo";
    else if (blob.includes("heavy assault")) variant = "Heavy Assault Missile";
    else if (blob.includes("heavy missile")) variant = "Heavy Missile";
    else if (blob.includes("light missile")) variant = "Light Missile";
    else if (blob.includes("cruise")) variant = "Cruise Missile";
    else if (blob.includes("torpedo")) variant = "Torpedo";
    else variant = "Missile Launcher";
  }
  let size = "unknown";
  if (/\/(s|small)\//i.test(graphicFile) || /\b(small|light|rocket|rapid light)\b/i.test(blob)) {
    size = "small";
  } else if (/\/(m|medium)\//i.test(graphicFile) || /\b(medium|heavy|rapid heavy)\b/i.test(blob)) {
    size = "medium";
  } else if (/\/(l|large)\//i.test(graphicFile) || /\b(large|cruise|torpedo|mega|tachyon|1400mm|1200mm)\b/i.test(blob)) {
    size = "large";
  } else if (/\/(xl|xlarge)\//i.test(graphicFile) || /\b(xl|capital|doomsday|lance)\b/i.test(blob)) {
    size = "xlarge";
  }
  return { kind, family, variant, size };
}

function buildMissilePreviewByLauncherGroup(
  itemTypes,
  graphicsByID,
  dogmaByType,
  groupGraphicsByID,
  resIndex,
) {
  const launcherAttributeIDs = [137, 602, 603, 2076, 2077, 2078];
  const candidatesByLauncherGroup = new Map();
  for (const row of (itemTypes && itemTypes.types) || []) {
    if (
      !row ||
      Number(row.categoryID) !== 8 ||
      row.published !== true ||
      !row.graphicID
    ) {
      continue;
    }
    const attributes = dogmaByType.get(Number(row.typeID)) || new Map();
    const launcherGroups = launcherAttributeIDs
      .map((attributeID) => Number(attributes.get(attributeID)) || 0)
      .filter((groupID) => groupID > 0);
    if (launcherGroups.length <= 0) {
      continue;
    }
    const impactGraphic = graphicsByID.get(Number(row.graphicID));
    const flightGraphicIDs = groupGraphicsByID.get(Number(row.groupID)) || [];
    const flightGraphic = flightGraphicIDs
      .map((graphicID) => graphicsByID.get(graphicID))
      .find((graphic) => graphic && graphic.graphicFile);
    if (!impactGraphic || !impactGraphic.graphicFile || !flightGraphic) {
      continue;
    }
    const preview = {
      ammoTypeID: Number(row.typeID) || 0,
      ammoName: row.name || row.typeName || `Charge ${row.typeID}`,
      missilePath: resolveClientResourcePath(resIndex, flightGraphic.graphicFile),
      impactPath: resolveClientResourcePath(resIndex, impactGraphic.graphicFile),
      maxVelocity: Number(attributes.get(37)) || 0,
      flightTimeSeconds: Math.max(0.5, (Number(attributes.get(281)) || 3000) / 1000),
    };
    if (!preview.missilePath || !preview.impactPath) {
      continue;
    }
    const name = String(preview.ammoName).toLowerCase();
    const score =
      (name.includes("navy") ? 20 : 0) +
      (name.includes("f.o.f.") ? 30 : 0) +
      (name.includes("rage") || name.includes("javelin") || name.includes("precision") ? 10 : 0) +
      preview.ammoTypeID;
    for (const launcherGroupID of launcherGroups) {
      const current = candidatesByLauncherGroup.get(launcherGroupID);
      if (!current || score < current.score) {
        candidatesByLauncherGroup.set(launcherGroupID, { ...preview, score });
      }
    }
  }
  return new Map([...candidatesByLauncherGroup.entries()].map(([groupID, preview]) => [
    groupID,
    {
      ammoTypeID: preview.ammoTypeID,
      ammoName: preview.ammoName,
      missilePath: preview.missilePath,
      impactPath: preview.impactPath,
      maxVelocity: preview.maxVelocity,
      flightTimeSeconds: preview.flightTimeSeconds,
    },
  ]));
}

function buildWeaponPreviewCatalog(
  itemTypes,
  graphicsByID,
  dogmaByType,
  groupGraphicsByID,
  resIndex,
) {
  const rows = (itemTypes && itemTypes.types) || [];
  const weapons = [];
  const seenPaths = new Set();
  const missilePreviewByLauncherGroup = buildMissilePreviewByLauncherGroup(
    itemTypes,
    graphicsByID,
    dogmaByType,
    groupGraphicsByID,
    resIndex,
  );
  const launcherGroupAliases = new Map([
    [1673, 508], // Rapid torpedo launchers consume torpedoes.
    [1245, 510], // Rapid heavy launchers consume heavy missiles.
    [511, 509],  // Rapid light launchers consume light missiles.
  ]);
  for (const row of rows) {
    if (row && row.published !== true) {
      continue;
    }
    const graphic = graphicsByID.get(Number(row && row.graphicID) || 0);
    const classification = classifyWeapon(row, graphic);
    if (!classification) {
      continue;
    }
    const resourcePath = resolveClientResourcePath(resIndex, graphic.graphicFile);
    if (!resourcePath) {
      continue;
    }
    const pathKey = resourcePath.toLowerCase();
    if (seenPaths.has(pathKey)) {
      continue;
    }
    seenPaths.add(pathKey);
    const weapon = {
      typeID: Number(row.typeID) || 0,
      name: row.name || row.typeName || `Weapon ${row.typeID}`,
      groupID: Number(row.groupID) || 0,
      groupName: row.groupName || "Weapon",
      graphicID: Number(row.graphicID) || 0,
      resourcePath,
      kind: classification.kind,
      family: classification.family,
      variant: classification.variant,
      size: classification.size,
      sof: {
        hull: graphic.sofHullName || null,
        faction: graphic.sofFactionName || null,
        race: graphic.sofRaceName || null,
      },
    };
    if (classification.kind === "launcher") {
      weapon.missilePreview =
        missilePreviewByLauncherGroup.get(Number(row.groupID)) ||
        missilePreviewByLauncherGroup.get(launcherGroupAliases.get(Number(row.groupID))) ||
        null;
    }
    weapons.push(weapon);
  }
  weapons.sort((left, right) => {
    if (left.kind !== right.kind) return left.kind.localeCompare(right.kind);
    if (left.family !== right.family) return left.family.localeCompare(right.family);
    if (left.size !== right.size) return left.size.localeCompare(right.size);
    return left.name.localeCompare(right.name);
  });
  return weapons;
}

function resolveClientResourcePath(resIndex, filePath) {
  const normalized = normalizeSlash(filePath || "");
  if (!normalized) {
    return null;
  }
  if (resIndex.byResPath.has(normalized.toLowerCase())) {
    return normalized;
  }
  if (/\.red$/i.test(normalized)) {
    const blackPath = normalized.replace(/\.red$/i, ".black");
    if (resIndex.byResPath.has(blackPath.toLowerCase())) {
      return blackPath;
    }
  }
  return normalized;
}

function makeNebulaLabel(resPath) {
  const normalized = normalizeSlash(resPath);
  const parts = normalized.split("/");
  const folder = parts.length >= 2 ? parts[parts.length - 2] : "scene";
  const file = parts[parts.length - 1] || normalized;
  return `${folder}/${file.replace(/\.(dds|black|red)$/i, "")}`;
}

function buildNebulaCatalog(resIndex) {
  const byResPath = resIndex && resIndex.byResPath ? resIndex.byResPath : new Map();
  const rows = [...byResPath.values()];
  const cubeRows = [];
  const sceneRows = [];

  for (const entry of rows) {
    const resPath = normalizeSlash(entry && entry.resPath);
    const lower = resPath.toLowerCase();
    if (!resPath) {
      continue;
    }
    if (
      /^res:\/dx9\/scene\/(universe|abyssal|event)\/.+_cube\.dds$/.test(lower) &&
      !lower.includes("_blur.") &&
      !lower.includes("_refl.")
    ) {
      const reflectPath = resPath.replace(/\.dds$/i, "_refl.dds");
      const blurPath = resPath.replace(/\.dds$/i, "_blur.dds");
      cubeRows.push({
        label: makeNebulaLabel(resPath),
        cubePath: resPath,
        reflectionPath: byResPath.has(reflectPath.toLowerCase()) ? reflectPath : null,
        blurPath: byResPath.has(blurPath.toLowerCase()) ? blurPath : null,
        sizeBytes: Number(entry.sizeBytes) || 0,
      });
    }
    if (
      /^res:\/dx9\/scene\/(universe|abyssal|event)\/.+_cube\.black$/.test(lower) ||
      /^res:\/dx9\/scene\/wormholes\/wormhole_class_.+\.black$/.test(lower) ||
      lower === "res:/dx9/scene/starfield/universe.black" ||
      lower === "res:/dx9/scene/starfield/starfieldnebula.black"
    ) {
      sceneRows.push({
        label: makeNebulaLabel(resPath),
        scenePath: resPath,
        sizeBytes: Number(entry.sizeBytes) || 0,
      });
    }
  }

  cubeRows.sort((left, right) => left.cubePath.localeCompare(right.cubePath));
  sceneRows.sort((left, right) => left.scenePath.localeCompare(right.scenePath));
  return {
    cubeMaps: cubeRows,
    scenes: sceneRows,
  };
}

function resolveExplosionOptions(asset, explosionBucketsByID, explosionIDsByKey, resIndex) {
  const bucketID = Number(asset && asset.explosionBucketID) || 0;
  const bucket = explosionBucketsByID.get(bucketID);
  if (!bucket) {
    return [];
  }
  const races = bucket.racialExplosions && typeof bucket.racialExplosions === "object"
    ? bucket.racialExplosions
    : {};
  const preferredRace = String(asset && asset.sof && asset.sof.race || "").toLowerCase();
  const candidates = [
    ...Object.entries(races)
      .filter(([race]) => String(race).toLowerCase() === preferredRace)
      .flatMap(([, rows]) => Array.isArray(rows) ? rows : []),
    ...Object.entries(races)
      .filter(([race]) => String(race).toLowerCase() === "default")
      .flatMap(([, rows]) => Array.isArray(rows) ? rows : []),
    ...Object.values(races).flatMap((rows) => Array.isArray(rows) ? rows : []),
  ];
  const seen = new Set();
  const options = [];
  for (const candidate of candidates) {
    const explosionID = candidate && candidate.explosionID;
    const explosion = explosionIDsByKey.get(String(explosionID));
    const authoredFilePath = normalizeSlash(explosion && explosion.filePath);
    if (!authoredFilePath || seen.has(authoredFilePath)) {
      continue;
    }
    seen.add(authoredFilePath);
    options.push({
      explosionID,
      filePath: authoredFilePath,
      compiledFilePath: resolveClientResourcePath(resIndex, authoredFilePath),
      childExplosionType: explosion.childExplosionType,
      modelSwitchDelayInMs: explosion.modelSwitchDelayInMs,
      localExplosionCount: candidate.localExplosionCount,
      localScale: candidate.localScale,
      globalScale: candidate.globalScale,
      chanceMultiplier: candidate.chanceMultiplier,
    });
  }
  return options.slice(0, 18);
}

function buildCatalog(options = {}) {
  const clientRoot = options.clientRoot || DEFAULT_CLIENT_ROOT;
  const latestExport = findLatestClientSdeExport();
  const graphicIDsPath = findFirst(latestExport, "graphicids.jsonl");
  const explosionIDsPath = findFirst(latestExport, "explosionids.jsonl");
  const explosionBucketIDsPath = findFirst(latestExport, "explosionbucketids.jsonl");
  const itemTypesPath = path.join(REPO_ROOT, "server", "src", "newDatabase", "data", "itemTypes", "data.json");
  const shipTypesPath = path.join(REPO_ROOT, "server", "src", "newDatabase", "data", "shipTypes", "data.json");
  const itemTypes = readJson(itemTypesPath, {});
  const shipTypes = readJson(shipTypesPath, {});
  const graphics = readJsonl(graphicIDsPath).map(normalizeGraphicRow);
  const graphicsByID = new Map(graphics.map((row) => [row.graphicID, row]));
  const explosionIDsByKey = new Map(readJsonl(explosionIDsPath).map((row) => [String(row._key), row]));
  const explosionBucketsByID = new Map(readJsonl(explosionBucketIDsPath).map((row) => [Number(row._key), row]));
  const typeDogmaPath = findFirst(latestExport, "typedogma.jsonl");
  const groupGraphicsPath = findFirst(latestExport, "groupgraphics.jsonl");
  const dogmaByType = buildDogmaByType(readJsonl(typeDogmaPath));
  const groupGraphicsByID = buildGroupGraphicsByID(readJsonl(groupGraphicsPath));
  const resIndex = loadResIndex(clientRoot);
  const animatedHullTokens = buildAnimatedHullTokens(resIndex);
  const weaponPreview = buildWeaponPreviewCatalog(
    itemTypes,
    graphicsByID,
    dogmaByType,
    groupGraphicsByID,
    resIndex,
  );
  const rows = [
    ...((shipTypes && shipTypes.ships) || []).map((row) => ({ row, source: "shipTypes" })),
    ...((itemTypes && itemTypes.types) || []).map((row) => ({ row, source: "itemTypes" })),
  ];
  const seenTypeIDs = new Set();
  const assets = [];
  for (const { row, source } of rows) {
    const typeID = Number(row && row.typeID) || 0;
    if (!typeID || seenTypeIDs.has(typeID)) {
      continue;
    }
    seenTypeIDs.add(typeID);
    const graphicID = Number(row.graphicID) || 0;
    const graphic = graphicsByID.get(graphicID);
    if (!graphic) {
      continue;
    }
    const asset = makeAsset(row, graphic, source, animatedHullTokens);
    if (!asset.dna) {
      continue;
    }
    asset.explosions = resolveExplosionOptions(asset, explosionBucketsByID, explosionIDsByKey, resIndex);
    asset.capabilities.explosions = asset.explosions.length > 0;
    assets.push(asset);
  }
  assets.sort((left, right) => {
    if (left.categoryID === 6 && right.categoryID !== 6) return -1;
    if (right.categoryID === 6 && left.categoryID !== 6) return 1;
    return left.name.localeCompare(right.name);
  });
  const nebulas = buildNebulaCatalog(resIndex);
  return {
    generatedAt: new Date().toISOString(),
    format: "elysian-jessica-standalone-catalog-v3",
    selectedTypeID: 587,
    sources: {
      graphicIDsPath,
      explosionIDsPath,
      explosionBucketIDsPath,
      itemTypesPath,
      shipTypesPath,
      typeDogmaPath,
      groupGraphicsPath,
      resIndexPath: resIndex.indexPath,
    },
    stats: {
      assets: assets.length,
      ships: assets.filter((entry) => entry.categoryID === 6).length,
      objects: assets.filter((entry) => entry.categoryID !== 6).length,
      explosionReady: assets.filter((entry) => entry.explosions.length > 0).length,
      resIndexEntries: resIndex.count,
      nebulaCubeMaps: nebulas.cubeMaps.length,
      nebulaScenes: nebulas.scenes.length,
      weaponPreviewWeapons: weaponPreview.length,
    },
    nebulas,
    weaponPreview: {
      weapons: weaponPreview,
    },
    assets,
  };
}

const options = parseArgs(process.argv);
const catalog = buildCatalog(options);
fs.mkdirSync(path.dirname(options.outputPath), { recursive: true });
fs.writeFileSync(options.outputPath, `${JSON.stringify(catalog, null, 2)}\n`);
console.log(`Wrote ${options.outputPath}`);
console.log(`Assets: ${catalog.stats.assets}, ships: ${catalog.stats.ships}, explosion-ready: ${catalog.stats.explosionReady}`);
console.log(`Nebulas: ${catalog.stats.nebulaCubeMaps} cube maps, ${catalog.stats.nebulaScenes} scene presets`);
console.log(`Weapon previews: ${catalog.stats.weaponPreviewWeapons}`);
