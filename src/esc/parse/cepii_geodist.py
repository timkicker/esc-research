"""cepii dist_cepii -> interim dyad_static

the zip holds one xls from 2004 and its codes show their age (see RENAME and
PROXY below). filtered down to contest countries because 50176 world pairs
only slow every later join
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pandas as pd

from esc import config, io
from esc.parse import enforce

RAW_ID = "cepii_geodist"
MEMBER = "dist_cepii.xls"
DUMMIES = ("contig", "comlang_off", "comlang_ethno", "colony", "comcol", "smctry")
KEEP = ("iso_o", "iso_d", "dist", "distw", *DUMMIES)

# romania is still the pre-2002 code here
RENAME = {"ROM": "ROU"}
# in 2004 yugoslavia was serbia and montenegro so all three reference belgrade
PROXY = {"SCG": "YUG", "SRB": "YUG"}


def parse() -> list[Path]:
    archive = config.RAW / RAW_ID / "dist_cepii.zip"
    if not archive.exists():
        raise FileNotFoundError(f"{archive} is missing, run `make data` first")

    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
        if MEMBER not in names:
            raise ValueError(f"{archive} does not hold {MEMBER}, it has {names}")
        with zf.open(MEMBER) as fh:
            df = pd.read_excel(fh, usecols=list(KEEP))

    for column in ("iso_o", "iso_d"):
        df[column] = df[column].replace(RENAME)
    for ours, theirs in PROXY.items():
        borrowed = df[(df["iso_o"] == theirs) | (df["iso_d"] == theirs)].copy()
        borrowed["iso_o"] = borrowed["iso_o"].replace({theirs: ours})
        borrowed["iso_d"] = borrowed["iso_d"].replace({theirs: ours})
        df = pd.concat([df, borrowed], ignore_index=True)

    wanted = set(io.read_parquet("country_map", "interim")["iso3"])
    before = len(df)
    df = df[df["iso_o"].isin(wanted) & df["iso_d"].isin(wanted)].copy()
    df = df[df["iso_o"] != df["iso_d"]]

    for column in DUMMIES:
        df[column] = df[column].astype("Int8").astype("boolean")
    for column in ("dist", "distw"):
        df[column] = pd.to_numeric(df[column]).astype("float64")
    for column in ("iso_o", "iso_d"):
        df[column] = df[column].astype("string")

    out = enforce(df, "dyad_static")
    covered = set(out["iso_o"]) | set(out["iso_d"])
    missing = sorted(wanted - covered)
    print(
        f"[parse.cepii_geodist] dyad_static: {before} world pairs -> {len(out)} "
        f"contest pairs, {len(covered)} countries covered"
    )
    if missing:
        print(f"[parse.cepii_geodist] no cepii row for {missing}")
    return [io.write_parquet(out, "dyad_static", "interim")]
