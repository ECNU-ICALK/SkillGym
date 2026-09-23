You need to complete the formal delivery of a mobile station dashboard for Citi Bike commuters.

Input data is in:
- `/app/workspace/app/`: the existing mobile web project code, including the home page, station detail page, data access layer, routes, and startup entrypoint
- `/app/workspace/data/system_information.json`
- `/app/workspace/data/station_information.json`
- `/app/workspace/data/station_status.json`
- `/app/workspace/data/favorite_stations.json`
- `/app/workspace/data/search_queries.json`
- `/app/workspace/data/delivery_contract.json`
- `/app/workspace/scripts/`: startup, build, and basic validation scripts
- `/services/citibike-api/`: the startup code for the local API service in the same container; runtime data must follow this service's returned results, and it may be called but must not be modified

Your tasks
1. Complete a station dashboard for mobile commuting scenarios so users can browse favorite stations, search stations, view station details, and see available bikes, available docks, station capacity, and current alerts.
2. Improve the project's delivery quality for continuous mobile usage scenarios. When users encounter network instability during a commute, re-enter the current app, or return to the app from a home screen shortcut, the home page and the main browsing flows must remain usable. If the current content cannot be restored for the moment, users must see a clear offline explanation page.
3. Let users judge how fresh the data shown on the current page is, and provide clear cues about that in the UI.
4. Keep the existing project structure, route entrypoints, and startup flow unchanged, and continue using the data files provided by the task to complete the delivery.

Output:
- Directly modify the existing project code under `/app/workspace/app/`.
- Preserve the existing startup and build entrypoints; validation will continue to start the app using the repo's default flow and run basic checks.
- Write `/app/workspace/artifacts/release-notes.md`

`/app/workspace/artifacts/release-notes.md` must contain the following level-1 headings in this exact order:

- `# Home`
- `# Search`
- `# Station Detail`
- `# Re-entry Behavior`
- `# Quick Access`
- `# Data Freshness`

Requirements:
- `# Home` must explain what core information appears on the home page and how favorite stations are presented.
- `# Search` must explain the matching scope supported by search and how users enter the station detail page.
- `# Station Detail` must explain the minimum required fields and alert information shown on the detail page.
- `# Re-entry Behavior` must explain which pages or content remain accessible after a user re-enters the app, how the page indicates the current state, and what explanation the user sees when the current content cannot be restored.
- `# Quick Access` must explain the entry name and first-screen behavior when the user returns to the app from a home screen shortcut.
- `# Data Freshness` must explain where update times are shown and what data-scope guidance is presented.

Notes:
- You may use only the data files provided under `/app/workspace/data/` to complete the delivery.
- Do not introduce login, remote databases, analytics tracking, push services, or third-party cloud services.
- Do not modify the input data under `/app/workspace/data/`.
- Do not modify the local API service under `/services/citibike-api/`.
- Do not turn the task into a pure offline script, a static screenshot set, or a report-only export.
- Do not remove the home page, search, details, favorite-station browsing, or alert-browsing capabilities to avoid constraints.
- Do not hard-code the result so it only works for a single station ID, a single alert, or a single sample query.
- The input will include out-of-service stations, empty fields, and stations with no additional alerts, and the delivered result must handle all of them.
- Do not require internet access during solve; the final result must be completed entirely from code and local data inside the container.
