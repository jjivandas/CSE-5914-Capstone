# pip install python-dotenv requests pandas

import os
from pathlib import Path
from io import StringIO

import requests
import pandas as pd
from dotenv import load_dotenv, find_dotenv

URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqtraded.txt"
REL_OUT = Path("stockrag/data/raw/nasdaq_raw.csv")

def main():
    # Load .env reliably (walks up directories to find it)
    load_dotenv(find_dotenv(usecwd=True))

    root = os.getenv("ROOT")
    if not root:
        raise RuntimeError(
            "ROOT is not set. Add it to your .env like:\n"
            "ROOT=/absolute/path/to/your/project/root"
        )

    out_path = (Path(root).expanduser() / REL_OUT).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Fetch
    resp = requests.get(URL, timeout=30)
    resp.raise_for_status()
    text = resp.text

    # Parse (pipe-delimited) and drop footer line "File Creation Time: ..."
    df = pd.read_csv(
        StringIO(text),
        sep="|",
        engine="python",   # needed for skipfooter
        skipfooter=1,      # drops the creation-time footer
    )

    # Save
    df.to_csv(out_path, index=False)
    print(f"Saved {len(df):,} rows -> {out_path}")

if __name__ == "__main__":
    main()
