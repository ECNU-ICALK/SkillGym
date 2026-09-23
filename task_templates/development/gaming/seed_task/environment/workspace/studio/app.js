window.__ATLAS_READY__ = false;

// Implementation hooks you may keep or replace:
// - loadData()
// - buildTrails(zone, seed, params)
// - renderTrails(sketch, geometry, colors)
// - exportSamplePoints(geometry)
// - deriveTypePressure(zone, relations)
// - deriveZoneSignals(zone, summary, pressure)
//
// Delivery constraints worth preserving:
// - Restoring from the same hash URL should also restore the visible seed input and other controls.
// - Avg Level Band should reflect average min level and average max level.
// - Format Avg Level Band as a readable range such as "3.0 to 6.5".
// - Avg BST should be the direct mean base_stat_total for the current zone encounter rows.
// - Keep export.average_level as a single numeric overall mean; show the band in the summary UI.
// - Keep highlighted_species as structured objects in the export payload; do not collapse them to plain strings.
// - Exported sample_points must come from rendered trails, with trail_id/step.
// - Exported x/y coordinates should be normalized to 0-1 canvas space.
// - Export enough ordered points per trail to preserve local bends; do not export only endpoints.
// - density should change both scene trail volume and exported sample volume.
// - Parameter changes should reshape the same seeded zone basis instead of scrambling unrelated randomness.
// - Higher turbulence should increase turning dispersion in exported sample_points under the same seed/zone.
// - Higher focus should pull exported sample_points inward under the same seed/zone.
// - contrast should change rendering only, not exported geometry or summaries.
// - Same seed + same inputs should redraw the same canvas output.
