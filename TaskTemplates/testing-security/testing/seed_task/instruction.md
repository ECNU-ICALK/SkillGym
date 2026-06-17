You need to complete browser-side visual stability validation coverage for the Airport Ops Console.

Input data is in:
- `environment/data/airports.csv`: airport master snapshot with airport identifiers, names, locations, and status fields.
- `environment/data/countries.csv`: country lookup used by filters and airport metadata.
- `environment/data/regions.csv`: region lookup used by grouping and location labels.
- `environment/data/runways.csv`: runway snapshot used for runway counts and minimum runway length summaries.

Your task:
1. Complete the missing browser validation coverage so the console can be checked repeatedly for first visible paint theme behavior, measurable load-time stability across the opening view and lower working area, one airport detail check, and the filtered compare-and-export airport operating flow.
2. Keep the existing application code, existing selectors, input data, and existing run entry unchanged.

Output:
- New or updated browser test files
- Any supporting files required by those tests in the same test area
- The delivered test suite must run through the repository's existing test command
- Do not rely on external accounts, external online services, or precomputed answer files

Notes:
- Scope the work to first visible paint theme behavior, measurable visible stability across the opening view and lower working area, one airport detail check, and the shipped compare-and-export interaction
- The theme coverage must be able to catch a saved-theme mismatch or a temporary light cover during the first animation frames, not only after the page settles
- The stability coverage must include a measurable check while delayed summary and lower-area content resolve, not only an end-state visibility check
- Use the repository's existing test command and server wiring; do not start a parallel server process or an alternate server bootstrap from inside the delivered tests
- Do not modify application source code
- Do not modify the input data files
- Do not introduce manual interaction steps
