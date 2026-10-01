"""cepii dist_cepii -> interim dyad_static

the zip holds one dist_cepii.xls from 2004, no stata file, so this needs xlrd.
codes are already iso3 and the column names already match the interim schema,
so the mapping is the identity. what does need work is the dummies, they arrive
as 0/1 integers and have to become nullable booleans

the file is filtered down to the countries that actually appear in the contest.
50176 world pairs are not useful here and make every later join slower

the file is from 2004 and its codes show it. romania is ROM, the pre-2002 code.
serbia and montenegro is YUG, because in 2004 that is what yugoslavia had become.
we rename ROM and we copy the YUG rows onto SCG and SRB, which is defensible
because all three reference belgrade. montenegro, monaco and the rest of the
world vote have no row at all and stay missing, the join leaves them NA
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

RENAME = {"ROM": "ROU"}
# our code -> the cepii code we borrow it from, see the module docstring
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
