import fs from "node:fs";
import path from "node:path";
import { parse } from "csv-parse/sync";
import express from "express";

const app = express();
const port = Number(process.env.PORT || 3001);
const dataRoot = process.env.ENERGY_DATA_DIR || "/data";

function readText(filename) {
  return fs.readFileSync(path.join(dataRoot, filename), "utf-8");
}

function loadDataset() {
  const energyRows = parse(readText("owid_energy_snapshot.csv"), {
    columns: true,
    skip_empty_lines: true
  });
  const codebook = parse(readText("owid_energy_codebook.csv"), {
    columns: true,
    skip_empty_lines: true
  });
  const countries = JSON.parse(readText("world_bank_countries.json"));

  const latestYear = 2023;
  const previousYear = 2022;
  const countryMetadata = new Map(countries.map((entry) => [entry.id, entry]));
  const byCode = new Map();

  for (const row of energyRows) {
    const bucket = byCode.get(row.iso_code) || {};
    bucket[row.year] = row;
    byCode.set(row.iso_code, bucket);
  }

  const compiled = [...byCode.entries()]
    .map(([isoCode, rows]) => {
      const latest = rows[String(latestYear)];
      const previous = rows[String(previousYear)];
      const metadata = countryMetadata.get(isoCode);
      if (!latest || !previous || !metadata) {
        return null;
      }

      const latestRenewables =
        Number(latest.hydro_share_elec) + Number(latest.solar_share_elec) + Number(latest.wind_share_elec);
      const previousRenewables =
        Number(previous.hydro_share_elec) + Number(previous.solar_share_elec) + Number(previous.wind_share_elec);
      const latestFossil =
        Number(latest.coal_share_elec) + Number(latest.gas_share_elec) + Number(latest.oil_share_elec);
      const latestLowCarbon = latestRenewables + Number(latest.nuclear_share_elec);

      return {
        isoCode,
        name: latest.country,
        region: metadata.region,
        incomeLevel: metadata.incomeLevel,
        year: latestYear,
        population: Number(latest.population),
        generationTwh: Number(latest.electricity_generation),
        demandTwh: Number(latest.electricity_demand),
        renewablesShare: latestRenewables,
        fossilShare: latestFossil,
        lowCarbonShare: latestLowCarbon,
        coalShare: Number(latest.coal_share_elec),
        gasShare: Number(latest.gas_share_elec),
        oilShare: Number(latest.oil_share_elec),
        hydroShare: Number(latest.hydro_share_elec),
        solarShare: Number(latest.solar_share_elec),
        windShare: Number(latest.wind_share_elec),
        nuclearShare: Number(latest.nuclear_share_elec),
        deltaRenewables: latestRenewables - previousRenewables
      };
    })
    .filter(Boolean)
    .sort((left, right) => left.name.localeCompare(right.name));

  const detailsByCode = Object.fromEntries(
    compiled.map((entry) => {
      const dominantRenewableSource = [
        ["Hydro", entry.hydroShare],
        ["Solar", entry.solarShare],
        ["Wind", entry.windShare]
      ].sort((left, right) => right[1] - left[1])[0][0];

      return [
        entry.isoCode,
        {
          isoCode: entry.isoCode,
          name: entry.name,
          region: entry.region,
          incomeLevel: entry.incomeLevel,
          year: entry.year,
          population: entry.population,
          generationTwh: entry.generationTwh,
          demandTwh: entry.demandTwh,
          demandPerCapitaKwh: entry.population ? (entry.demandTwh * 1_000_000_000) / entry.population : 0,
          renewablesShare: entry.renewablesShare,
          lowCarbonShare: entry.lowCarbonShare,
          fossilShare: entry.fossilShare,
          deltaRenewables: entry.deltaRenewables,
          dominantRenewableSource,
          renewableBreakdown: {
            hydro: entry.hydroShare,
            solar: entry.solarShare,
            wind: entry.windShare,
            nuclear: entry.nuclearShare
          }
        }
      ];
    })
  );

  return {
    snapshotId: "owid-energy-workbench-2023-snapshot",
    defaultYear: latestYear,
    regions: [...new Set(compiled.map((entry) => entry.region))].sort(),
    countries: compiled,
    codebook,
    detailsByCode
  };
}

let cache = loadDataset();

app.use((_request, response, next) => {
  response.setHeader("Access-Control-Allow-Origin", "*");
  response.setHeader("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
  response.setHeader("Access-Control-Allow-Headers", "Content-Type");
  if (_request.method === "OPTIONS") {
    response.status(204).end();
    return;
  }
  next();
});

app.get("/health", (_request, response) => {
  response.json({ ok: true, snapshotId: cache.snapshotId });
});

app.get("/api/dashboard", async (_request, response) => {
  await new Promise((resolve) => setTimeout(resolve, 120));
  response.json({
    snapshotId: cache.snapshotId,
    defaultYear: cache.defaultYear,
    regions: cache.regions,
    countries: cache.countries,
    codebook: cache.codebook
  });
});

app.get("/api/countries/:isoCode", async (request, response) => {
  const isoCode = String(request.params.isoCode || "").toUpperCase();
  const detail = cache.detailsByCode[isoCode];
  if (!detail) {
    response.status(404).json({ message: `Unknown country code: ${isoCode}` });
    return;
  }

  const delayByCode = {
    DEU: 420,
    FRA: 90,
    GBR: 180,
    USA: 260,
    CAN: 220
  };
  await new Promise((resolve) => setTimeout(resolve, delayByCode[isoCode] || 160));
  response.json(detail);
});

app.post("/admin/reload", (_request, response) => {
  cache = loadDataset();
  response.json({ ok: true, snapshotId: cache.snapshotId });
});

app.listen(port, () => {
  console.log(`Energy API listening on ${port}`);
});
