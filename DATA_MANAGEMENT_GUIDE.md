# AISL Data Version Control

## Overview

This repository manages the **code and metadata** for downloading and processing YouTube videos for the OpenDV dataset.

## What's Version Controlled

✅ **Code**: `download_videos.py` - Script to download and trim videos  
✅ **Metadata**: `OpenDV-YouTube - OpenDV-YouTube.csv` - Video URLs and timestamps  
✅ **Configuration**: Cookie files excluded, data directory ignored  

❌ **NOT tracked**: Video files in `D:\raw` (~150GB+)

## Why Not Track Video Files?

The video files are:
- **Large** (~150GB+ total)
- **Reproducible** - Can be re-downloaded using the CSV + script
- **Storage-intensive** - Would require cloud storage or large cache

Instead, we version control the **recipe** (CSV + script) to recreate the data.

## Data Location

- **Videos**: `D:\raw` (local D: drive, not version controlled)
- **Source CSV**: `OpenDV-YouTube - OpenDV-YouTube.csv`
- **Download Script**: `download_videos.py`

## Reproducibility

Anyone can recreate the exact dataset by:

```bash
# Clone the repository
git clone https://github.com/Fusili23/AISL_DataVersionControl.git
cd AISL_DataVersionControl

# Add your YouTube cookies (for authentication)
# cookies.txt, cookies2.txt, cookies3.txt

# Run the download script
python download_videos.py
```

This will download all videos to `D:\raw` using the CSV metadata.

## Workflow

1. **Update CSV** with new video entries
2. **Run script** to download new videos to `D:\raw`
3. **Commit** only the CSV and script changes
4. **Push** to GitHub

```bash
git add "OpenDV-YouTube - OpenDV-YouTube.csv" download_videos.py
git commit -m "Added videos 104-110"
git push
```

## File Structure

```
AISL_DataVersionControl/
├── download_videos.py          # Download script
├── OpenDV-YouTube - ....csv    # Video metadata
├── DATA_MANAGEMENT_GUIDE.md    # This file
├── .gitignore                  # Excludes cookies and /raw
├── cookies*.txt                # (ignored) YouTube auth
└── raw/ → D:\raw               # (ignored) Video files
```

## Notes

- Cookie files (`cookies*.txt`) are **excluded** from version control for security
- The `raw/` directory is a junction to `D:\raw` but is **ignored** by Git
- DVC is installed but not actively used for this workflow
