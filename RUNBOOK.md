# Jyothisha Insight — Runbook (Windows)

## Requirements
- Python 3.12+ venv in `.venv` (report uses 3.12 f-string syntax); built on 3.14
- MSVC Build Tools ("Desktop development with C++") — pyswisseph is compiled
  from source (no Windows wheels for 3.12+)
- MSYS2 Pango for WeasyPrint: `pacman -S mingw-w64-ucrt-x86_64-pango` (in C:\msys64).
  NOT the 2022 GTK3 runtime (uninstalled): its old HarfBuzz leaves gaps after
  මූ / ්‍ර (--qa shaping probe 2 fails on it), and its DLLs clash with MSYS2's
- `fonts/` with 6 files directly inside: NotoSansSinhala.ttf (v3.000+),
  NotoSansSinhala-Bold.ttf, NotoSans.ttf, NotoSans-Bold.ttf,
  NotoSansSymbols2.ttf, NotoSansMath.ttf
- `ephe/` with sepl_18.se1, semo_18.se1, seas_18.se1 (else Moshier fallback)

## Activate (every new terminal)
```powershell
. .\env.ps1
```
Activates `.venv` and sets WEASYPRINT_DLL_DIRECTORIES.

## Setup from scratch
```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install weasyprint pyswisseph pymupdf tzdata
```

## Selftest (expect ALL PASS)
```powershell
python jyotisha_calc.py --selftest
```

## Report G
```powershell
python jyotisha_report.py --report G --name Test --date 1990-05-15 --time 10:30 --lat 6.93 --lon 79.85 --place Colombo --out test_G.pdf --qa
```

## Report A1
```powershell
python jyotisha_report.py --report A1 --name Test --date 1990-05-15 --time 10:30 --lat 6.93 --lon 79.85 --place Colombo --brand "Jyothisha Insight" --out test_A1.pdf --qa
```

## --qa
Adds a check after the PDF is written: two Sinhala shaping probes, page PNGs
in `<out>_qa/` (e.g. `test_A1_qa/page-01.png`) and font/overflow/blank checks.
Prints `QA: PASS`/`QA: FAIL` on stderr (exit 3 on failure). PowerShell 5.1
shows stderr as red "NativeCommandError" text; that alone is not a failure.

## Astrologer notes
- Keep per-client files in `clients/<client>/notes.json` (git-ignored); pass `--notes clients/<client>/notes.json`
- Keys (Sinhala text): summary, lagna, yogas, dasha, gochara, upcoming, remedies
- See `notes_sample.json` for the format
