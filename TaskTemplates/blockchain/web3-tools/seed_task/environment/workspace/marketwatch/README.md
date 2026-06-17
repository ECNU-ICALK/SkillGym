# Marketwatch Workspace

This workspace is the project surface for the market surveillance delivery task.

Expected entrypoint:

- `python3 /app/workspace/marketwatch/build_surveillance.py`

The final implementation should read the task manifest, collect the authoritative market set from the local service, normalize the required daily bars, and write the requested delivery files under `/app/output/surveillance`.

