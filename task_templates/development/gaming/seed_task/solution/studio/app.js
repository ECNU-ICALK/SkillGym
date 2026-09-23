(() => {
  "use strict";

  const CANVAS = {
    width: 1100,
    height: 760,
    margin: 24,
  };

  const state = {
    contract: null,
    zones: [],
    types: [],
    zoneById: {},
    seed: 0,
    zoneId: "",
    preset: "",
    params: {},
    colors: {},
    samplePoints: [],
    highlightedSpecies: [],
    exportPayload: null,
    geometry: null,
    sketch: null,
  };

  const dom = {};

  function mulberry32(seed) {
    let t = seed >>> 0;
    return function next() {
      t += 0x6d2b79f5;
      let value = Math.imul(t ^ (t >>> 15), 1 | t);
      value ^= value + Math.imul(value ^ (value >>> 7), 61 | value);
      return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
    };
  }

  function hashString32(raw) {
    let h = 2166136261;
    for (let i = 0; i < raw.length; i += 1) {
      h ^= raw.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    return h >>> 0;
  }

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function parseHexColor(value, fallback) {
    const raw = String(value || "").trim().toLowerCase();
    return /^#[0-9a-f]{6}$/.test(raw) ? raw : fallback;
  }

  function toTitle(name) {
    return String(name || "")
      .replace(/[-_]/g, " ")
      .replace(/\b\w/g, (m) => m.toUpperCase());
  }

  function typeColor(typeName) {
    const map = {
      grass: "#6f9f68",
      poison: "#9470c1",
      bug: "#88a83f",
      flying: "#6d84d8",
      normal: "#8f8b7c",
      rock: "#a68a5b",
      ground: "#bd9d57",
      water: "#4c8eb9",
      fire: "#d88146",
      electric: "#d6b23d",
      ice: "#80b9c5",
      psychic: "#be6a9a",
      dragon: "#7362b6",
      fairy: "#c896b8",
    };
    return map[typeName] || "#6e7d8f";
  }

  function hexToRgb(hex) {
    const raw = hex.replace("#", "");
    return {
      r: parseInt(raw.slice(0, 2), 16),
      g: parseInt(raw.slice(2, 4), 16),
      b: parseInt(raw.slice(4, 6), 16),
    };
  }

  function blendHex(a, b, t) {
    const left = hexToRgb(a);
    const right = hexToRgb(b);
    const mix = (x, y) => Math.round(x + (y - x) * t);
    const toHex = (value) => value.toString(16).padStart(2, "0");
    return `#${toHex(mix(left.r, right.r))}${toHex(mix(left.g, right.g))}${toHex(mix(left.b, right.b))}`;
  }

  function angleFromMix(a, b, t) {
    const x = Math.cos(a) * (1 - t) + Math.cos(b) * t;
    const y = Math.sin(a) * (1 - t) + Math.sin(b) * t;
    return Math.atan2(y, x);
  }

  function noiseUnit(seed, x, y, step, lane) {
    const raw =
      Math.sin(
        x * 12.9898 +
          y * 78.233 +
          step * 37.719 +
          lane * 17.123 +
          seed * 0.01371,
      ) * 43758.5453;
    return raw - Math.floor(raw);
  }

  function sceneSeed() {
    return hashString32([state.seed, state.zoneId].join("|"));
  }

  function hashScene(seed, zoneId, preset, params) {
    return (
      hashString32(
        [
          seed,
          zoneId,
          preset,
          params.density.toFixed(3),
          params.turbulence.toFixed(3),
          params.focus.toFixed(3),
          params.contrast.toFixed(3),
          state.colors.color1,
          state.colors.color2,
          state.colors.color3,
        ].join("|"),
      )
    ).toString(16);
  }

  function syncHashState() {
    const params = new URLSearchParams();
    params.set("seed", String(state.seed));
    params.set("zone", state.zoneId);
    params.set("preset", state.preset);
    params.set("density", state.params.density.toFixed(2));
    params.set("turbulence", state.params.turbulence.toFixed(2));
    params.set("focus", state.params.focus.toFixed(2));
    params.set("contrast", state.params.contrast.toFixed(2));
    params.set("color1", state.colors.color1);
    params.set("color2", state.colors.color2);
    params.set("color3", state.colors.color3);
    const nextHash = params.toString();
    if (window.location.hash.slice(1) !== nextHash) {
      window.history.replaceState(null, "", `#${nextHash}`);
    }
  }

  function applyHashState() {
    const params = new URLSearchParams(window.location.hash.slice(1));
    if (!params.toString()) return;

    const seed = Number(params.get("seed"));
    if (Number.isFinite(seed)) {
      state.seed = Math.max(1, Math.floor(seed));
    }

    const zoneId = params.get("zone");
    if (zoneId && state.zoneById[zoneId]) {
      state.zoneId = zoneId;
    }

    const preset = params.get("preset");
    if (preset && state.contract.presets[preset]) {
      state.preset = preset;
      applyPreset(preset);
    }

    const specByKey = {
      density: state.contract.required_controls.parameters.find((item) => item.id === "density-control"),
      turbulence: state.contract.required_controls.parameters.find((item) => item.id === "turbulence-control"),
      focus: state.contract.required_controls.parameters.find((item) => item.id === "focus-control"),
      contrast: state.contract.required_controls.parameters.find((item) => item.id === "contrast-control"),
    };

    Object.entries(specByKey).forEach(([key, spec]) => {
      const raw = Number(params.get(key));
      if (!spec || !Number.isFinite(raw)) return;
      state.params[key] = clamp(raw, spec.min, spec.max);
    });

    state.colors = {
      color1: parseHexColor(params.get("color1"), state.colors.color1),
      color2: parseHexColor(params.get("color2"), state.colors.color2),
      color3: parseHexColor(params.get("color3"), state.colors.color3),
    };
  }

  function collectDom() {
    dom.seedDisplay = document.getElementById("seed-display");
    dom.seedInput = document.getElementById("seed-input");
    dom.seedPrev = document.getElementById("seed-prev");
    dom.seedNext = document.getElementById("seed-next");
    dom.seedRandom = document.getElementById("seed-random");
    dom.seedGo = document.getElementById("seed-go");
    dom.zoneSelect = document.getElementById("zone-select");
    dom.presetSurvey = document.getElementById("preset-survey");
    dom.presetBloom = document.getElementById("preset-bloom");
    dom.presetStorm = document.getElementById("preset-storm");
    dom.density = document.getElementById("density-control");
    dom.turbulence = document.getElementById("turbulence-control");
    dom.focus = document.getElementById("focus-control");
    dom.contrast = document.getElementById("contrast-control");
    dom.color1 = document.getElementById("color1");
    dom.color2 = document.getElementById("color2");
    dom.color3 = document.getElementById("color3");
    dom.densityValue = document.getElementById("density-value");
    dom.turbulenceValue = document.getElementById("turbulence-value");
    dom.focusValue = document.getElementById("focus-value");
    dom.contrastValue = document.getElementById("contrast-value");
    dom.color1Value = document.getElementById("color1-value");
    dom.color2Value = document.getElementById("color2-value");
    dom.color3Value = document.getElementById("color3-value");
    dom.regenerate = document.getElementById("regenerate-button");
    dom.reset = document.getElementById("reset-button");
    dom.exportButton = document.getElementById("export-button");
    dom.exportStatus = document.getElementById("export-status");
    dom.exportJson = document.getElementById("export-json");
    dom.routeTitle = document.getElementById("route-title");
    dom.routeSummary = document.getElementById("route-summary");
    dom.metricSpeciesCount = document.getElementById("metric-species-count");
    dom.metricAvgLevel = document.getElementById("metric-avg-level");
    dom.metricAvgBst = document.getElementById("metric-avg-bst");
    dom.metricTypeMix = document.getElementById("metric-type-mix");
    dom.highlightedSpecies = document.getElementById("highlighted-species");
    dom.typeMixBars = document.getElementById("type-mix-bars");
    dom.attackCoverage = document.getElementById("attack-coverage");
    dom.exposureProfile = document.getElementById("exposure-profile");
    dom.zoneSignals = document.getElementById("zone-signals");
    dom.sourceLinks = document.getElementById("source-links");
    dom.canvasContainer = document.getElementById("canvas-container");
    dom.canvasLoading = document.getElementById("canvas-loading");
    dom.presetButtons = [dom.presetSurvey, dom.presetBloom, dom.presetStorm];
  }

  function bindSlider(input, key, valueEl, spec) {
    input.min = String(spec.min);
    input.max = String(spec.max);
    input.step = String(spec.step);
    input.addEventListener("input", () => {
      state.params[key] = Number(input.value);
      valueEl.textContent = state.params[key].toFixed(2);
      drawScene();
    });
  }

  function applyPreset(name) {
    state.preset = name;
    const preset = state.contract.presets[name];
    state.params = {
      density: preset.density,
      turbulence: preset.turbulence,
      focus: preset.focus,
      contrast: preset.contrast,
    };
    syncUiFromState();
  }

  function syncUiFromState() {
    dom.seedDisplay.textContent = String(state.seed);
    dom.seedInput.value = String(state.seed);
    dom.zoneSelect.value = state.zoneId;
    dom.density.value = String(state.params.density);
    dom.turbulence.value = String(state.params.turbulence);
    dom.focus.value = String(state.params.focus);
    dom.contrast.value = String(state.params.contrast);
    dom.color1.value = state.colors.color1;
    dom.color2.value = state.colors.color2;
    dom.color3.value = state.colors.color3;
    dom.densityValue.textContent = state.params.density.toFixed(2);
    dom.turbulenceValue.textContent = state.params.turbulence.toFixed(2);
    dom.focusValue.textContent = state.params.focus.toFixed(2);
    dom.contrastValue.textContent = state.params.contrast.toFixed(2);
    dom.color1Value.textContent = state.colors.color1.toUpperCase();
    dom.color2Value.textContent = state.colors.color2.toUpperCase();
    dom.color3Value.textContent = state.colors.color3.toUpperCase();
    dom.presetButtons.forEach((button) => {
      if (!button) return;
      button.classList.toggle("active", button.dataset.preset === state.preset);
    });
  }

  function computeSummaries(zone) {
    const encounters = zone.encounters;
    const maxChance = Math.max(...encounters.map((row) => row.avg_chance));
    const typedCounter = {};

    const ranked = encounters
      .map((row) => {
        row.types.forEach((typeName) => {
          typedCounter[typeName] = (typedCounter[typeName] || 0) + 1;
        });
        const chanceNorm = row.avg_chance / maxChance;
        const bstNorm = row.base_stat_total / 700;
        const rarityBoost = row.rarity_tier === "core" ? 1.08 : row.rarity_tier === "rare" ? 0.92 : 1;
        const score =
          (0.56 * chanceNorm + 0.44 * bstNorm * (0.5 + state.params.focus * 0.9)) *
          rarityBoost *
          (0.84 + state.params.density * 0.42);
        return { ...row, scene_score: score };
      })
      .sort((a, b) => b.scene_score - a.scene_score || a.dex_number - b.dex_number);

    const highlighted = ranked.slice(
      0,
      Math.max(state.contract.summary_contract.minimum_highlight_cards, 4),
    );
    const avgMin = encounters.reduce((acc, row) => acc + row.min_level, 0) / encounters.length;
    const avgMax = encounters.reduce((acc, row) => acc + row.max_level, 0) / encounters.length;
    const avgBst = encounters.reduce((acc, row) => acc + row.base_stat_total, 0) / encounters.length;
    const totalTypeSamples = Object.values(typedCounter).reduce((sum, count) => sum + count, 0);
    const typeMixRows = Object.entries(typedCounter)
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .slice(0, 3)
      .map(([name, count]) => ({
        type: name,
        share: count / totalTypeSamples,
      }));
    const topTypes = typeMixRows.map((row) => toTitle(row.type));

    return {
      highlighted,
      avgMin,
      avgMax,
      avgBst,
      topTypes,
      typeMixRows,
    };
  }

  function buildPressure(summary) {
    const relationsByType = Object.fromEntries(state.types.map((row) => [row.type_name, row]));
    const coverage = new Map();
    const exposure = new Map();

    summary.typeMixRows.forEach((row) => {
      const relation = relationsByType[row.type] || {};
      (relation.double_damage_to || []).forEach((typeName) => {
        coverage.set(typeName, (coverage.get(typeName) || 0) + row.share);
      });
      (relation.double_damage_from || []).forEach((typeName) => {
        exposure.set(typeName, (exposure.get(typeName) || 0) + row.share);
      });
    });

    const sortRows = (mapping) =>
      Array.from(mapping.entries())
        .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
        .slice(0, 6)
        .map(([type, score]) => ({
          type,
          score,
        }));

    return {
      coverage: sortRows(coverage),
      exposure: sortRows(exposure),
    };
  }

  function renderPressure(summary) {
    const pressure = buildPressure(summary);

    dom.typeMixBars.innerHTML = "";
    summary.typeMixRows.forEach((row) => {
      const item = document.createElement("div");
      item.className = "mix-bar";
      item.innerHTML =
        `<div class="mix-label"><span>${toTitle(row.type)}</span><strong>${Math.round(row.share * 100)}%</strong></div>` +
        `<div class="mix-track"><div class="mix-fill" style="width:${(row.share * 100).toFixed(1)}%;background:${typeColor(row.type)};"></div></div>`;
      dom.typeMixBars.appendChild(item);
    });

    const writeTokenList = (target, rows) => {
      target.innerHTML = "";
      rows.forEach((row) => {
        const item = document.createElement("li");
        item.className = "token-item";
        item.innerHTML =
          `<span>${toTitle(row.type)}</span>` +
          `<span class="token-score">${Math.round(row.score * 100)}%</span>`;
        target.appendChild(item);
      });
    };

    writeTokenList(dom.attackCoverage, pressure.coverage);
    writeTokenList(dom.exposureProfile, pressure.exposure);

    return pressure;
  }

  function buildSignals(zone, summary, pressure) {
    const methods = Array.from(
      new Set([...(zone.methods || []), ...zone.encounters.flatMap((row) => row.methods || [])]),
    ).slice(0, 3);
    const rareCount = zone.encounters.filter((row) => row.rarity_tier === "rare").length;
    const supportCount = zone.encounters.filter((row) => row.rarity_tier === "support").length;
    const leadHighlight = summary.highlighted[0];

    return [
      {
        title: "Zone Density",
        body:
          `${zone.zone_label} carries ${zone.encounters.length} encounter rows ` +
          `from Lv ${summary.avgMin.toFixed(1)} to Lv ${summary.avgMax.toFixed(1)}.`,
        tags: [`${Math.round(summary.avgBst)} BST`, `${toTitle(zone.biome)}`],
      },
      {
        title: "Pressure Lanes",
        body:
          `${pressure.coverage.slice(0, 2).map((row) => toTitle(row.type)).join(" / ")} ` +
          `lead the local attack lanes, while ` +
          `${pressure.exposure.slice(0, 2).map((row) => toTitle(row.type)).join(" / ")} ` +
          `stay highest in the exposure profile.`,
        tags: pressure.coverage.slice(0, 3).map((row) => `${toTitle(row.type)} ${Math.round(row.score * 100)}%`),
      },
      {
        title: "Route Signals",
        body:
          `${rareCount} rare rows and ${supportCount} support rows remain active. ` +
          `${leadHighlight ? `${leadHighlight.display_name} ranks first in the current highlight stack.` : ""}`,
        tags: methods.length ? methods.map((row) => toTitle(row)) : ["Walk"],
      },
    ];
  }

  function renderSignals(signals) {
    dom.zoneSignals.innerHTML = "";
    signals.forEach((signal) => {
      const article = document.createElement("article");
      article.className = "signal-card";
      const tags = signal.tags.map((tag) => `<span class="signal-pill">${tag}</span>`).join("");
      article.innerHTML =
        `<h4>${signal.title}</h4>` +
        `<p>${signal.body}</p>` +
        `<div class="signal-pill-row">${tags}</div>`;
      dom.zoneSignals.appendChild(article);
    });
  }

  function updateDomSummary(zone, summary) {
    dom.routeTitle.textContent = `${zone.zone_label} · ${toTitle(zone.biome)}`;
    dom.routeSummary.textContent =
      `Seed ${state.seed} with ${toTitle(state.preset)} preset. ` +
      `The scene follows local encounter weight, type pressure, and zone accent ${zone.accent}.`;

    dom.metricSpeciesCount.textContent = String(zone.encounters.length);
    dom.metricAvgLevel.textContent = `${summary.avgMin.toFixed(1)} to ${summary.avgMax.toFixed(1)}`;
    dom.metricAvgBst.textContent = `${summary.avgBst.toFixed(1)}`;
    dom.metricTypeMix.textContent = summary.topTypes.join(" / ");

    dom.highlightedSpecies.innerHTML = "";
    summary.highlighted.forEach((row) => {
      const card = document.createElement("article");
      card.className = "species-card";
      card.dataset.speciesId = row.species_name;
      card.innerHTML =
        `<h4>${row.display_name}</h4>` +
        `<p>#${row.dex_number} · ${row.types.map(toTitle).join(" / ")} · BST ${row.base_stat_total}</p>` +
        `<p>Chance ${row.avg_chance.toFixed(2)}% · Lv ${row.min_level}-${row.max_level}</p>`;
      dom.highlightedSpecies.appendChild(card);
    });

    dom.sourceLinks.innerHTML = "";
    const sourceRows = [
      {
        label: `${zone.zone_label} encounter snapshot`,
        url: zone.source_url,
      },
      {
        label: "Kanto Pokedex reference",
        url: "https://pokeapi.co/api/v2/pokedex/2/",
      },
      {
        label: "Type relation reference",
        url: "https://pokeapi.co/api/v2/type/",
      },
    ];
    sourceRows.forEach((row) => {
      const item = document.createElement("li");
      item.innerHTML = `<a href="${row.url}" target="_blank" rel="noopener noreferrer">${row.label}</a>`;
      dom.sourceLinks.appendChild(item);
    });

    const pressure = renderPressure(summary);
    renderSignals(buildSignals(zone, summary, pressure));
  }

  function evenIndexes(length, count) {
    const target = Math.min(length, count);
    const indexes = new Set();
    for (let i = 0; i < target; i += 1) {
      const ratio = target === 1 ? 0 : i / (target - 1);
      indexes.add(Math.round(ratio * (length - 1)));
    }
    return Array.from(indexes).sort((a, b) => a - b);
  }

  function exportSamplePoints(trails) {
    const sorted = [...trails].sort((a, b) => b.weight - a.weight || a.trailId.localeCompare(b.trailId));
    const trailLimit = Math.max(6, Math.min(sorted.length, Math.round(6 + state.params.density * 8)));
    const samplesPerTrail = Math.max(4, Math.round(4 + state.params.density * 2));
    const selected = sorted.slice(0, trailLimit);
    const points = [];

    selected.forEach((trail) => {
      evenIndexes(trail.points.length, samplesPerTrail).forEach((index) => {
        const point = trail.points[index];
        points.push({
          trail_id: trail.trailId,
          step: point.step,
          species_name: trail.speciesName,
          layer: trail.layer,
          x: Number((point.x / CANVAS.width).toFixed(4)),
          y: Number((point.y / CANVAS.height).toFixed(4)),
          radius: Number(trail.radius.toFixed(3)),
          weight: Number(trail.weight.toFixed(3)),
        });
      });
    });

    return points;
  }

  function buildTrails(zone, summary) {
    const maxChance = Math.max(...zone.encounters.map((row) => row.avg_chance));
    const centerX = CANVAS.width * 0.5;
    const centerY = CANVAS.height * 0.5;
    const orbitRadius = Math.min(CANVAS.width, CANVAS.height) * 0.34;
    const seed = sceneSeed();
    const rng = mulberry32(seed);
    const trails = [];

    zone.encounters.forEach((row, index) => {
      const chanceNorm = row.avg_chance / maxChance;
      const baseAngle = (index / zone.encounters.length) * Math.PI * 2 + (rng() - 0.5) * 0.4;
      const rimRadius = orbitRadius * (0.74 - state.params.focus * 0.26 + rng() * 0.08);
      const clusterX = centerX + Math.cos(baseAngle) * rimRadius;
      const clusterY = centerY + Math.sin(baseAngle) * rimRadius;
      const trailCount = Math.max(2, Math.round(1 + chanceNorm * 2 + state.params.density * 4));
      const stepCount = Math.max(10, Math.round(10 + chanceNorm * 8 + state.params.density * 4));
      const typeName = row.types[0] || "normal";

      for (let trailIndex = 0; trailIndex < trailCount; trailIndex += 1) {
        const startAngle = baseAngle + (rng() - 0.5) * 1.6;
        const startSpread = 34 + (1 - state.params.focus) * 160 * (0.4 + rng());
        let x = clusterX + Math.cos(startAngle) * startSpread;
        let y = clusterY + Math.sin(startAngle) * startSpread;
        const targetMix = 0.2 + state.params.focus * 0.72;
        const targetX = clusterX * (1 - targetMix) + centerX * targetMix;
        const targetY = clusterY * (1 - targetMix) + centerY * targetMix;
        const points = [];

        let driftHeading = startAngle;
        const laneSeed = seed + trailIndex * 97 + index * 131;

        for (let step = 0; step < stepCount; step += 1) {
          const scale = 0.006 + state.params.turbulence * 0.02;
          const fieldA = noiseUnit(laneSeed, x * scale, y * scale, step * 0.19, trailIndex);
          const fieldB = noiseUnit(laneSeed ^ 0x9e3779b9, y * scale * 1.7, x * scale * 0.85, step * 0.13, index);
          const turnKick =
            (fieldA - 0.5) * (0.24 + state.params.turbulence * 1.8) +
            (fieldB - 0.5) * (0.18 + state.params.turbulence * 1.5);
          driftHeading += turnKick;
          const attractAngle = Math.atan2(targetY - y, targetX - x);
          const attractWeight = clamp(
            0.72 - state.params.turbulence * 0.38 + state.params.focus * 0.22,
            0.18,
            0.88,
          );
          const heading = angleFromMix(driftHeading, attractAngle, attractWeight);
          const stepSize = 2.4 + chanceNorm * 3.6 + state.params.density * 1.45;

          x += Math.cos(heading) * stepSize + (targetX - x) * (0.015 + state.params.focus * 0.05);
          y += Math.sin(heading) * stepSize + (targetY - y) * (0.015 + state.params.focus * 0.05);
          x = clamp(x, CANVAS.margin, CANVAS.width - CANVAS.margin);
          y = clamp(y, CANVAS.margin, CANVAS.height - CANVAS.margin);
          points.push({ x, y, step });
        }

        trails.push({
          trailId: `${row.species_name}-${index}-${trailIndex}`,
          speciesName: row.species_name,
          displayName: row.display_name,
          layer: row.rarity_tier,
          weight: row.avg_chance,
          radius: 0.55 + chanceNorm * 1.1,
          typeName,
          clusterX,
          clusterY,
          points,
        });
      }
    });

    const samplePoints = exportSamplePoints(trails);
    return {
      trails,
      samplePoints,
      summary,
    };
  }

  function renderGeometry() {
    if (!state.sketch) {
      state.sketch = new window.p5((p) => {
        p.setup = () => {
          const canvas = p.createCanvas(CANVAS.width, CANVAS.height);
          canvas.parent(dom.canvasContainer);
          p.pixelDensity(1);
          p.noLoop();
          if (dom.canvasLoading) {
            dom.canvasLoading.classList.add("is-hidden");
          }
        };

        p.draw = () => {
          const primary = hexToRgb(state.colors.color1);
          const secondary = hexToRgb(state.colors.color2);
          const accent = hexToRgb(state.colors.color3);
          const contrastBoost = 0.45 + state.params.contrast * 1.4;
          p.background(250, 245, 233);
          p.noStroke();
          for (let i = 0; i < 80; i += 1) {
            const blend = i / 79;
            p.fill(
              primary.r + (secondary.r - primary.r) * blend,
              primary.g + (secondary.g - primary.g) * blend,
              primary.b + (secondary.b - primary.b) * blend,
              20 + state.params.contrast * 20,
            );
            p.rect(0, blend * CANVAS.height, CANVAS.width, CANVAS.height / 80 + 1);
          }

          p.fill(primary.r, primary.g, primary.b, 28 + state.params.contrast * 18);
          p.ellipse(CANVAS.width * 0.22, CANVAS.height * 0.22, CANVAS.width * 0.72, CANVAS.height * 0.48);
          p.fill(secondary.r, secondary.g, secondary.b, 26 + state.params.contrast * 18);
          p.ellipse(CANVAS.width * 0.82, CANVAS.height * 0.78, CANVAS.width * 0.82, CANVAS.height * 0.54);

          state.geometry.trails.forEach((trail) => {
            const baseColor = blendHex(typeColor(trail.typeName), state.colors.color1, 0.22);
            const strokeColor = blendHex(baseColor, state.colors.color2, 0.18);
            const rgb = hexToRgb(strokeColor);
            p.noFill();
            p.stroke(rgb.r, rgb.g, rgb.b, 52 + state.params.contrast * 110);
            p.strokeWeight(trail.radius * contrastBoost);
            p.beginShape();
            trail.points.forEach((point) => {
              p.vertex(point.x, point.y);
            });
            p.endShape();

            const glow = hexToRgb(blendHex(typeColor(trail.typeName), state.colors.color3, 0.35));
            const head = trail.points[trail.points.length - 1];
            p.noStroke();
            p.fill(glow.r, glow.g, glow.b, 18 + state.params.contrast * 28);
            p.circle(head.x, head.y, 3 + trail.radius * (3.5 + state.params.contrast * 4));
          });

          p.noFill();
          p.stroke(accent.r, accent.g, accent.b, 95 + state.params.contrast * 80);
          p.strokeWeight(1.1 + state.params.contrast * 1.2);
          p.rect(CANVAS.margin - 8, CANVAS.margin - 8, CANVAS.width - (CANVAS.margin - 8) * 2, CANVAS.height - (CANVAS.margin - 8) * 2, 12);
        };
      });
    }

    state.sketch.redraw();
  }

  function buildExportPayload(zone, summary) {
    const sceneHash = hashScene(state.seed, state.zoneId, state.preset, state.params);
    return {
      scene_id: `atlas-${sceneHash}`,
      seed: state.seed,
      zone_id: zone.zone_id,
      zone_label: zone.zone_label,
      preset: state.preset,
      parameters: {
        density: Number(state.params.density.toFixed(3)),
        turbulence: Number(state.params.turbulence.toFixed(3)),
        focus: Number(state.params.focus.toFixed(3)),
        contrast: Number(state.params.contrast.toFixed(3)),
      },
      colors: {
        color1: state.colors.color1,
        color2: state.colors.color2,
        color3: state.colors.color3,
      },
      highlighted_species: state.highlightedSpecies.map((row) => ({
        species_id: row.species_name,
        species_name: row.species_name,
        display_name: row.display_name,
        dex_number: row.dex_number,
        types: row.types,
        scene_score: Number(row.scene_score.toFixed(4)),
      })),
      type_mix: summary.typeMixRows.map((row) => ({
        type: row.type,
        share: Number(row.share.toFixed(4)),
      })),
      average_level: Number(((summary.avgMin + summary.avgMax) / 2).toFixed(2)),
      average_base_stat_total: Number(summary.avgBst.toFixed(2)),
      sample_points: state.samplePoints,
    };
  }

  function updateExportPreview() {
    if (!state.exportPayload) return;
    dom.exportJson.value = JSON.stringify(state.exportPayload, null, 2);
    dom.exportStatus.textContent =
      `Ready to export ${state.exportPayload.scene_id} with ${state.exportPayload.sample_points.length} sampled trail points.`;
  }

  function drawScene() {
    const zone = state.zoneById[state.zoneId];
    if (!zone) return;

    const summary = computeSummaries(zone);
    state.highlightedSpecies = summary.highlighted;
    updateDomSummary(zone, summary);

    state.geometry = buildTrails(zone, summary);
    state.samplePoints = state.geometry.samplePoints;
    renderGeometry();
    syncHashState();
    state.exportPayload = buildExportPayload(zone, summary);
    updateExportPreview();
  }

  function exportScene() {
    if (!state.exportPayload) return;
    updateExportPreview();
    const blob = new Blob([dom.exportJson.value], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${state.exportPayload.scene_id}.json`;
    link.style.display = "none";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.setTimeout(() => URL.revokeObjectURL(url), 1500);
    dom.exportStatus.textContent =
      `Exported scene ${state.exportPayload.scene_id} with ${state.exportPayload.sample_points.length} sampled trail points.`;
  }

  function bindEvents() {
    const sliderSpecs = state.contract.required_controls.parameters;
    const map = {
      density: sliderSpecs.find((item) => item.id === "density-control"),
      turbulence: sliderSpecs.find((item) => item.id === "turbulence-control"),
      focus: sliderSpecs.find((item) => item.id === "focus-control"),
      contrast: sliderSpecs.find((item) => item.id === "contrast-control"),
    };

    bindSlider(dom.density, "density", dom.densityValue, map.density);
    bindSlider(dom.turbulence, "turbulence", dom.turbulenceValue, map.turbulence);
    bindSlider(dom.focus, "focus", dom.focusValue, map.focus);
    bindSlider(dom.contrast, "contrast", dom.contrastValue, map.contrast);

    [dom.color1, dom.color2, dom.color3].forEach((input, index) => {
      input.addEventListener("input", () => {
        const key = `color${index + 1}`;
        state.colors[key] = input.value.toLowerCase();
        dom[`${key}Value`].textContent = state.colors[key].toUpperCase();
        drawScene();
      });
    });

    dom.zoneSelect.addEventListener("change", () => {
      state.zoneId = dom.zoneSelect.value;
      drawScene();
    });

    dom.seedPrev.addEventListener("click", () => {
      state.seed = Math.max(1, state.seed - 1);
      syncUiFromState();
      drawScene();
    });

    dom.seedNext.addEventListener("click", () => {
      state.seed += 1;
      syncUiFromState();
      drawScene();
    });

    dom.seedRandom.addEventListener("click", () => {
      const r = Math.floor(Math.random() * 999999) + 1;
      state.seed = r;
      syncUiFromState();
      drawScene();
    });

    dom.seedGo.addEventListener("click", () => {
      const next = Number(dom.seedInput.value);
      if (Number.isFinite(next)) {
        state.seed = Math.max(1, Math.floor(next));
        syncUiFromState();
        drawScene();
      }
    });

    dom.presetButtons.forEach((button) => {
      button.addEventListener("click", () => {
        applyPreset(button.dataset.preset);
        drawScene();
      });
    });

    dom.regenerate.addEventListener("click", () => drawScene());
    dom.exportButton.addEventListener("click", exportScene);
    dom.reset.addEventListener("click", () => {
      state.seed = state.contract.default_seed;
      state.zoneId = state.contract.default_zone_id;
      applyPreset(state.contract.default_preset);
      state.colors = Object.fromEntries(
        state.contract.required_controls.colors.map((item) => [item.id, item.default]),
      );
      dom.exportJson.value = "";
      dom.exportStatus.textContent = "Reset complete.";
      syncUiFromState();
      drawScene();
    });
  }

  function populateZones() {
    dom.zoneSelect.innerHTML = "";
    state.zones.forEach((zone) => {
      const opt = document.createElement("option");
      opt.value = zone.zone_id;
      opt.textContent = zone.zone_label;
      dom.zoneSelect.appendChild(opt);
    });
  }

  async function loadData() {
    const [contractRes, zoneRes, typeRes] = await Promise.all([
      fetch("/data/render_contract.json"),
      fetch("/data/encounter_zones.json"),
      fetch("/data/type_relations.json"),
    ]);

    if (!contractRes.ok || !zoneRes.ok || !typeRes.ok) {
      throw new Error("Failed to load atlas input data.");
    }

    state.contract = await contractRes.json();
    const zoneDoc = await zoneRes.json();
    const typeDoc = await typeRes.json();
    state.zones = zoneDoc.zones || [];
    state.types = typeDoc.types || [];
    state.zoneById = Object.fromEntries(state.zones.map((zone) => [zone.zone_id, zone]));
    state.seed = state.contract.default_seed;
    state.zoneId = state.contract.default_zone_id;
    state.preset = state.contract.default_preset;
    const preset = state.contract.presets[state.preset];
    state.params = {
      density: preset.density,
      turbulence: preset.turbulence,
      focus: preset.focus,
      contrast: preset.contrast,
    };
    state.colors = Object.fromEntries(
      state.contract.required_controls.colors.map((item) => [item.id, item.default]),
    );
    applyHashState();
  }

  async function init() {
    window.__ATLAS_READY__ = false;
    collectDom();
    await loadData();
    populateZones();
    bindEvents();
    syncUiFromState();
    drawScene();
    window.__atlasState = state;
    window.__ATLAS_READY__ = true;
  }

  init().catch((error) => {
    console.error(error);
    const title = document.getElementById("route-title");
    if (title) title.textContent = "Failed to load atlas data";
    const summary = document.getElementById("route-summary");
    if (summary) summary.textContent = String(error.message || error);
  });
})();
