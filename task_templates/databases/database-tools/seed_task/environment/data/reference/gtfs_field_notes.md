GTFS files shipped in this task

- agency.txt: agency timezone and feed publisher information.
- routes.txt: selected route identities for Blue, Orange, and Red.
- stops.txt: stop-level rows plus parent stations used by the selected trips.
- trips.txt: selected trips whose service IDs are active inside the task analysis window.
- stop_times.txt: ordered stop events for the selected trips.
- calendar.txt: base service calendars for the selected service IDs.
- calendar_dates.txt: added and removed service dates for the selected service IDs.

Operational notes

- `parent_station` should be used to roll child stops up to station-level identities.
- `departure_time` stays on the GTFS service-day clock and may need numeric handling before window filters are applied.
- `route_short_name` is blank for some heavy-rail rows; use the task contract for output expectations.
