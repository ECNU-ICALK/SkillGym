const fs = require("fs");
const path = require("path");
const { parse } = require("csv-parse/sync");
const { parseTimeToSeconds, secondsToTime } = require("../../shared");

function readCsv(filePath) {
  return parse(fs.readFileSync(filePath, "utf-8"), {
    columns: true,
    skip_empty_lines: true,
  });
}

function normalizeText(value) {
  return String(value || "").trim().toLowerCase();
}

function buildDataset(dataRoot) {
  const agency = readCsv(path.join(dataRoot, "agency.txt"))[0];
  const routes = readCsv(path.join(dataRoot, "routes.txt"));
  const stops = readCsv(path.join(dataRoot, "stops.txt"));
  const trips = readCsv(path.join(dataRoot, "trips.txt"));
  const stopTimes = readCsv(path.join(dataRoot, "stop_times.txt"));
  const calendars = readCsv(path.join(dataRoot, "calendar.txt"));
  const calendarDates = readCsv(path.join(dataRoot, "calendar_dates.txt"));

  const routeById = new Map(routes.map((route) => [route.route_id, route]));
  const stopById = new Map(stops.map((stop) => [stop.stop_id, stop]));
  const tripsById = new Map(trips.map((trip) => [trip.trip_id, trip]));
  const stopTimesByTripId = new Map();
  const childStopsByParentId = new Map();
  const logicalStops = [];
  const logicalStopById = new Map();
  const calendarByServiceId = new Map(calendars.map((row) => [row.service_id, row]));
  const calendarDateAdjustments = new Map();

  for (const stop of stops) {
    const parentId = stop.parent_station || null;
    if (parentId) {
      const existing = childStopsByParentId.get(parentId) || [];
      existing.push(stop.stop_id);
      childStopsByParentId.set(parentId, existing);
      continue;
    }
    const logical = {
      stop_id: stop.stop_id,
      stop_name: stop.stop_name,
      location_type: stop.location_type || "0",
      child_stop_ids: [],
    };
    logicalStops.push(logical);
    logicalStopById.set(logical.stop_id, logical);
  }

  for (const [parentId, children] of childStopsByParentId.entries()) {
    const logical = logicalStopById.get(parentId);
    if (logical) {
      logical.child_stop_ids = [...children].sort();
    }
  }

  for (const row of stopTimes) {
    const existing = stopTimesByTripId.get(row.trip_id) || [];
    existing.push(row);
    stopTimesByTripId.set(row.trip_id, existing);
  }

  for (const [tripId, rows] of stopTimesByTripId.entries()) {
    rows.sort((left, right) => Number(left.stop_sequence) - Number(right.stop_sequence));
    stopTimesByTripId.set(tripId, rows);
  }

  for (const row of calendarDates) {
    const dateEntries = calendarDateAdjustments.get(row.date) || new Map();
    dateEntries.set(row.service_id, row.exception_type);
    calendarDateAdjustments.set(row.date, dateEntries);
  }

  return {
    agency,
    routeById,
    stopById,
    trips,
    tripsById,
    stopTimesByTripId,
    logicalStops,
    logicalStopById,
    childStopsByParentId,
    calendarByServiceId,
    calendarDateAdjustments,
  };
}

function serviceIdsForDate(dataset, serviceDate) {
  const dateDigits = serviceDate.replaceAll("-", "");
  const weekday = new Date(`${serviceDate}T12:00:00Z`).getUTCDay();
  const flagByWeekday = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"];
  const active = new Set();

  for (const [serviceId, calendar] of dataset.calendarByServiceId.entries()) {
    if (dateDigits < calendar.start_date || dateDigits > calendar.end_date) {
      continue;
    }
    if (calendar[flagByWeekday[weekday]] === "1") {
      active.add(serviceId);
    }
  }

  const adjustments = dataset.calendarDateAdjustments.get(dateDigits);
  if (adjustments) {
    for (const [serviceId, exceptionType] of adjustments.entries()) {
      if (exceptionType === "1") {
        active.add(serviceId);
      }
      if (exceptionType === "2") {
        active.delete(serviceId);
      }
    }
  }

  return active;
}

function findLogicalStop(dataset, stopId) {
  if (dataset.logicalStopById.has(stopId)) {
    return dataset.logicalStopById.get(stopId);
  }
  const childStop = dataset.stopById.get(stopId);
  if (childStop && childStop.parent_station) {
    return dataset.logicalStopById.get(childStop.parent_station);
  }
  return null;
}

function matchingStopIds(dataset, stopId) {
  const logical = findLogicalStop(dataset, stopId);
  if (!logical) {
    return [];
  }
  return logical.child_stop_ids.length > 0 ? logical.child_stop_ids : [logical.stop_id];
}

function createMtaStaticProvider({ dataRoot }) {
  const dataset = buildDataset(dataRoot);

  return {
    id: "mta_static",
    label: `${dataset.agency.agency_name} Static Subway`,
    kind: "gtfs-static",
    timezone: dataset.agency.agency_timezone,
    searchStops({ query, limit }) {
      const normalized = normalizeText(query);
      const exact = [];
      const fuzzy = [];
      for (const stop of dataset.logicalStops) {
        if (normalizeText(stop.stop_id) === normalized) {
          exact.push(stop);
          continue;
        }
        if (normalizeText(stop.stop_name).includes(normalized)) {
          fuzzy.push(stop);
        }
      }
      return [...exact, ...fuzzy].slice(0, limit);
    },
    getDepartures({ stopId, serviceDate, queryTime, limit }) {
      const logicalStop = findLogicalStop(dataset, stopId);
      if (!logicalStop) {
        return { stop: null, departures: [] };
      }
      const activeServiceIds = serviceIdsForDate(dataset, serviceDate);
      const supportedStopIds = new Set(matchingStopIds(dataset, stopId));
      const querySeconds = parseTimeToSeconds(queryTime);
      const departures = [];

      for (const trip of dataset.trips) {
        if (!activeServiceIds.has(trip.service_id)) {
          continue;
        }
        const stopTimes = dataset.stopTimesByTripId.get(trip.trip_id) || [];
        for (const stopTime of stopTimes) {
          if (!supportedStopIds.has(stopTime.stop_id)) {
            continue;
          }
          const departureSeconds = parseTimeToSeconds(stopTime.departure_time);
          if (departureSeconds < querySeconds) {
            continue;
          }
          const route = dataset.routeById.get(trip.route_id);
          departures.push({
            trip_id: trip.trip_id,
            route_id: trip.route_id,
            route_short_name: route.route_short_name,
            route_long_name: route.route_long_name,
            service_id: trip.service_id,
            direction_id: trip.direction_id,
            stop_id: stopTime.stop_id,
            parent_stop_id: logicalStop.stop_id,
            departure_time: stopTime.departure_time,
            headsign: trip.trip_headsign,
          });
        }
      }

      departures.sort((left, right) => {
        if (left.departure_time !== right.departure_time) {
          return left.departure_time.localeCompare(right.departure_time);
        }
        if (left.route_id !== right.route_id) {
          return left.route_id.localeCompare(right.route_id);
        }
        return left.trip_id.localeCompare(right.trip_id);
      });

      return {
        stop: logicalStop,
        departures: departures.slice(0, limit),
      };
    },
    getServiceWindow({ routeId, serviceDate }) {
      const activeServiceIds = serviceIdsForDate(dataset, serviceDate);
      const route = dataset.routeById.get(routeId);
      const departures = [];
      const parentStops = new Set();
      const directionIds = new Set();
      let tripCount = 0;

      for (const trip of dataset.trips) {
        if (trip.route_id !== routeId || !activeServiceIds.has(trip.service_id)) {
          continue;
        }
        tripCount += 1;
        directionIds.add(trip.direction_id);
        const stopTimes = dataset.stopTimesByTripId.get(trip.trip_id) || [];
        for (const stopTime of stopTimes) {
          departures.push(parseTimeToSeconds(stopTime.departure_time));
          const stop = dataset.stopById.get(stopTime.stop_id);
          const parentId = stop && stop.parent_station ? stop.parent_station : stopTime.stop_id;
          parentStops.add(parentId);
        }
      }

      return {
        route: {
          route_id: route.route_id,
          route_short_name: route.route_short_name,
          route_long_name: route.route_long_name,
        },
        service_window: {
          first_departure: departures.length ? secondsToTime(Math.min(...departures)) : null,
          last_departure: departures.length ? secondsToTime(Math.max(...departures)) : null,
          trip_count: tripCount,
          stop_count: parentStops.size,
          direction_count: directionIds.size,
        },
      };
    },
  };
}

module.exports = {
  createMtaStaticProvider,
};
