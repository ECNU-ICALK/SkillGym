import express from "express";
import fs from "node:fs";
import path from "node:path";

const app = express();
const port = Number(process.env.CITIBIKE_API_PORT || process.env.PORT || 3001);
const dataDir =
  process.env.CITIBIKE_DATA_DIR ||
  process.env.BIKE_DATA_DIR ||
  "/app/workspace/data";

function readJson(name) {
  return JSON.parse(fs.readFileSync(path.join(dataDir, name), "utf-8"));
}

function stationState(status) {
  if (status.is_installed === 0) {
    return { tone: "critical", label: "Unavailable" };
  }
  if (status.is_renting === 0 || status.is_returning === 0) {
    return { tone: "critical", label: "Limited service" };
  }
  if ((status.num_bikes_available || 0) === 0) {
    return { tone: "warning", label: "No bikes" };
  }
  if ((status.num_docks_available || 0) === 0) {
    return { tone: "warning", label: "No docks" };
  }
  if ((status.num_bikes_available || 0) <= 2) {
    return { tone: "info", label: "Low bikes" };
  }
  return { tone: "available", label: "Available" };
}

function buildAdvisories(station, status) {
  const advisories = [];

  if (status.is_installed === 0 || status.is_renting === 0 || status.is_returning === 0) {
    advisories.push({
      station_id: station.station_id,
      kind: "service_pause",
      severity: "warning",
      title: "Service update",
      message: "This stop has limited rider actions in the current feed."
    });
  }

  if ((status.num_bikes_available || 0) === 0) {
    advisories.push({
      station_id: station.station_id,
      kind: "empty_station",
      severity: "warning",
      title: "No bikes available",
      message: "Commuters may need a nearby pickup alternative."
    });
  }

  if ((status.num_docks_available || 0) === 0) {
    advisories.push({
      station_id: station.station_id,
      kind: "dock_full",
      severity: "info",
      title: "No open docks",
      message: "Return capacity is currently exhausted at this stop."
    });
  }

  return advisories;
}

function buildDataset() {
  const system = readJson("system_information.json");
  const stationInformation = readJson("station_information.json");
  const stationStatus = readJson("station_status.json");
  const favorites = readJson("favorite_stations.json");
  const searchQueries = readJson("search_queries.json");
  const contract = readJson("delivery_contract.json");

  const infoById = new Map(
    stationInformation.data.stations.map((station) => [station.station_id, station])
  );
  const statusById = new Map(
    stationStatus.data.stations.map((station) => [station.station_id, station])
  );

  function buildStation(stationId) {
    const info = infoById.get(stationId);
    const status = statusById.get(stationId);
    if (!info || !status) {
      return null;
    }

    const state = stationState(status);
    return {
      station_id: stationId,
      name: info.name,
      short_name: info.short_name || "",
      capacity: info.capacity || 0,
      bikes_available: status.num_bikes_available || 0,
      docks_available: status.num_docks_available || 0,
      status_tone: state.tone,
      status_label: state.label,
      last_reported: status.last_reported || stationStatus.last_updated,
      lat: info.lat,
      lon: info.lon
    };
  }

  function buildStationPayload(stationId) {
    const station = buildStation(stationId);
    if (!station) {
      return null;
    }
    return {
      station,
      advisories: buildAdvisories(station, statusById.get(stationId))
    };
  }

  const favoritesPayload = favorites.favorite_station_ids
    .map((stationId) => buildStationPayload(stationId))
    .filter(Boolean);

  return {
    system: {
      name: system.data.name,
      operator: system.data.operator,
      timezone: system.data.timezone,
      purchase_url: system.data.purchase_url
    },
    meta: {
      snapshot_id: `citibike-${stationStatus.last_updated}`,
      status_last_updated: stationStatus.last_updated
    },
    contract,
    favorites: {
      stations: favoritesPayload.map((entry) => entry.station)
    },
    advisories: favoritesPayload.flatMap((entry) => entry.advisories),
    search_examples: searchQueries.queries,
    buildStationPayload,
    listStations(query) {
      const normalized = query.trim().toLowerCase();
      return Array.from(infoById.keys())
        .map((stationId) => buildStation(stationId))
        .filter(Boolean)
        .filter((station) => {
          if (!normalized) {
            return true;
          }
          return (
            station.name.toLowerCase().includes(normalized) ||
            station.short_name.toLowerCase().includes(normalized)
          );
        })
        .sort((left, right) => {
          if (left.status_tone !== right.status_tone) {
            return left.status_tone.localeCompare(right.status_tone);
          }
          return left.name.localeCompare(right.name);
        })
        .slice(0, 24);
    }
  };
}

function withDelay(value) {
  return new Promise((resolve) => {
    setTimeout(() => resolve(value), 120);
  });
}

app.use((_req, res, next) => {
  res.setHeader("Cache-Control", "no-store");
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  next();
});

app.get("/health", (_req, res) => {
  res.json({ ok: true });
});

app.get("/api/bootstrap", async (_req, res) => {
  res.json(await withDelay(buildDataset()));
});

app.get("/api/stations", async (req, res) => {
  const dataset = buildDataset();
  const query = String(req.query.q || req.query.query || "");
  res.json(
    await withDelay({
      query,
      meta: dataset.meta,
      items: dataset.listStations(query)
    })
  );
});

app.get("/api/stations/:stationId", async (req, res) => {
  const dataset = buildDataset();
  const payload = dataset.buildStationPayload(req.params.stationId);
  if (!payload) {
    res.status(404).json({ error: "station_not_found" });
    return;
  }

  res.json(
    await withDelay({
      station: payload.station,
      advisories: payload.advisories,
      meta: dataset.meta
    })
  );
});

app.listen(port, () => {
  console.log(`bike-api listening on ${port}`);
});
