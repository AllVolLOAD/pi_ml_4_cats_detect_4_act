# Export Guide (SCP / Laptop / VPS)

This project can be packed into a zip for transfer over SCP. The export script keeps the code and docs by default and can optionally include large data.

## Quick export (recommended)

From the project root:

```powershell
.\export_project.ps1
```

Result:
- `_export/catcam_export_YYYYMMDD_HHMMSS.zip`
- `EXPORT_MANIFEST.txt` inside the zip (records exclusions)

## Export with data and logs

```powershell
.\export_project.ps1 -IncludeData -IncludeLogs
```

## Copy via SCP

Example to another laptop:

```powershell
scp .\_export\catcam_export_YYYYMMDD_HHMMSS.zip user@LAPTOP_IP:/path/on/laptop/
```

Example to VPS:

```powershell
scp .\_export\catcam_export_YYYYMMDD_HHMMSS.zip user@VPS_IP:/opt/catcam/
```

## Unpack on target

```bash
unzip catcam_export_YYYYMMDD_HHMMSS.zip
```

## Notes

- By default, these are excluded: caches (`__pycache__`), `catcam/pc/logs`, and `catcam/data`.
- Use `-IncludeData` if you want to move datasets, checkpoints, and raw videos.
- Use `-IncludeLogs` if you need telemetry/event history.
