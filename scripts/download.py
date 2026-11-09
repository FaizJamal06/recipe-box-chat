"""Download and unzip the Recipe Box dataset into data/raw/ (idempotent, stdlib only).

Stdlib only so it runs before any `pip install` (Docker build, fresh clone).
Manual fallback: place recipes_raw_nosource_{ar,epi,fn}.json into data/raw/ yourself.
"""
import io
import time
import urllib.request
import zipfile
from pathlib import Path

URL = "https://eightportions.com/recipes_raw.zip"
RAW = Path(__file__).resolve().parent.parent / "data" / "raw"


def main() -> None:
    """Fetch the zip with retries and extract the JSON files flat into data/raw/."""
    if len(list(RAW.glob("*.json"))) >= 3:
        print(f"already present in {RAW}")
        return
    RAW.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, 5):
        try:
            req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (recipe-box-chat)"})
            with urllib.request.urlopen(req, timeout=120) as r:  # default Python UA gets a 403
                blob = r.read()
            break
        except OSError as e:
            print(f"attempt {attempt} failed: {e}")
            if attempt == 4:
                raise
            time.sleep(2 * attempt)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        for info in z.infolist():
            if info.filename.endswith(".json"):  # flatten: ignore any folder in the zip
                (RAW / Path(info.filename).name).write_bytes(z.read(info))
                print("extracted", Path(info.filename).name)


if __name__ == "__main__":
    main()
