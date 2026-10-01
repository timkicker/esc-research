"""spijkervet release csvs -> interim entries and votes

the two files disagree about how a country is written. contestants.csv spells
the name out, votes.csv uses lowercase iso2. both go through country_map, which
is why parse.manual has to run first

votes.csv is wide, with a jury and a televote column side by side. the interim
schema is long, one row per vote_type, so it gets melted here. where the split
is not reported the row becomes 'combined', never a 'jury' row, otherwise the
build step would compare a combined series against a jury series
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from esc import config, io
from esc.parse import enforce, entry_id

RAW_ID = "eurovision_dataset"

ROUND_MAP = {
    "final": "final",
    "semi-final": "semi1",
    "semi-final-1": "semi1",
    "semi-final-2": "semi2",
}


def _raw(name: str) -> pd.DataFrame:
    path = config.RAW / RAW_ID / name
    if not path.exists():
        raise FileNotFoundError(f"{path} is missing, run `make data` first")
    return pd.read_csv(path, dtype="string", keep_default_na=False, na_values=[""])


def _lookup(kind: str) -> dict[str, str]:
    cmap = io.read_parquet("country_map", "interim")
    rows = cmap[cmap["kind"] == kind]
    return dict(zip(rows["label"], rows["iso3"], strict=True))


def _to_iso3(series: pd.Series, kind: str, what: str) -> pd.Series:
    mapping = _lookup(kind)
    out = series.map(mapping).astype("string")
    missing = sorted(set(series[out.isna() & series.notna()]))
    if missing:
        raise ValueError(
            f"{what}: {len(missing)} label(s) missing from country_map.csv: "
            f"{missing}. add them by hand, do not drop them"
        )
    return out


def parse_entries() -> Path:
    df = _raw("contestants.csv")
    iso3 = _to_iso3(df["to_country"], "name", "contestants.csv")

    def block(round_name: str, order: str, place: str, points: str) -> pd.DataFrame:
        out = pd.DataFrame(
            {
                "year": pd.to_numeric(df["year"]).astype("int16"),
                "country_iso3": iso3,
                "artist": df["performer"],
                "song": df["song"],
                "running_order": pd.to_numeric(df[order]).astype("Int16"),
                "place": pd.to_numeric(df[place]).astype("Int16"),
                "points_total": pd.to_numeric(df[points]).astype("Int32"),
                "round": pd.Series(round_name, index=df.index, dtype="string"),
            }
        )
        # an entry only has a row for a round it actually took part in
        return out[out[["running_order", "place", "points_total"]].notna().any(axis=1)]

    finals = block("final", "running_final", "place_final", "points_final")
    semis = block("semi1", "running_sf", "place_sf", "points_sf")
    semis["round"] = (
        pd.to_numeric(df.loc[semis.index, "sf_num"])
        .map({1: "semi1", 2: "semi2"})
        .fillna("semi1")
        .astype("string")
    )

    out = pd.concat([finals, semis], ignore_index=True)
    out["entry_id"] = entry_id(out["year"], out["country_iso3"]).values
    # in 1956 every country sent two songs, so year-iso3 is not a key that year
    twice = out.duplicated(subset=["entry_id", "round"], keep=False)
    if twice.any():
        rank = out[twice].groupby(["entry_id", "round"]).cumcount() + 1
        out.loc[twice, "entry_id"] = out.loc[twice, "entry_id"] + "-" + rank.astype(str)
        years = sorted(out.loc[twice, "year"].unique())
        print(
            f"[parse.eurovision_dataset] {int(twice.sum())} entries share a "
            f"country and year in {years}, numbered apart"
        )
    # an entry that reached the final qualified, the big five never had to
    reached_final = {
        f"{y}-{c}" for y, c in zip(finals["year"], finals["country_iso3"], strict=True)
    }
    out["qualified"] = pd.Series(
        [
            (eid in reached_final) if r.startswith("semi") else pd.NA
            for eid, r in zip(out["entry_id"], out["round"], strict=True)
        ],
        index=out.index,
        dtype="boolean",
    )
    for column, dtype in (
        ("artist_age", "Int16"),
        ("artist_sex", "string"),
        ("song_language", "string"),
    ):
        out[column] = pd.Series(pd.NA, index=out.index, dtype=dtype)

    out = enforce(out, "entries")
    rounds = out["round"].value_counts().to_dict()
    span = f"{out['year'].min()}-{out['year'].max()}"
    print(
        f"[parse.eurovision_dataset] entries: {len(df)} contestants -> "
        f"{len(out)} rows, {rounds}, years {span}"
    )
    return io.write_parquet(out, "entries", "interim")


def parse_votes() -> Path:
    df = _raw("votes.csv")
    unknown = sorted(set(df["round"].dropna()) - set(ROUND_MAP))
    if unknown:
        raise ValueError(f"votes.csv has unmapped round(s) {unknown}")

    base = pd.DataFrame(
        {
            "year": pd.to_numeric(df["year"]).astype("int16"),
            "round": df["round"].map(ROUND_MAP).astype("string"),
            "from_iso3": _to_iso3(df["from_country"], "iso2", "votes.csv from_country"),
            "to_iso3": _to_iso3(df["to_country"], "iso2", "votes.csv to_country"),
        }
    )
    jury = pd.to_numeric(df["jury_points"])
    tele = pd.to_numeric(df["tele_points"])
    total = pd.to_numeric(df["total_points"])
    split = jury.notna() & tele.notna()

    parts = []
    for name, values, mask in (
        ("jury", jury, split),
        ("televote", tele, split),
        ("combined", total, ~split),
    ):
        part = base[mask].copy()
        part["vote_type"] = pd.Series(name, index=part.index, dtype="string")
        part["points"] = values[mask].astype("Int16")
        parts.append(part)

    out = enforce(pd.concat(parts, ignore_index=True), "votes")

    # the source ships a full matrix including the diagonal, always at zero.
    # no contest rule lets a country vote for itself, so a non-zero one would
    # mean the from and to columns are swapped
    self_pairs = out["from_iso3"] == out["to_iso3"]
    scored = out[self_pairs & (out["points"] > 0)]
    if len(scored):
        raise ValueError(
            f"{len(scored)} self-votes carry points, from and to look swapped: "
            f"{scored.head(3).to_dict('records')}"
        )
    out = out[~self_pairs].reset_index(drop=True)
    print(f"[parse.eurovision_dataset] dropped {int(self_pairs.sum())} zero self-pairs")

    kinds = out["vote_type"].value_counts().to_dict()
    print(
        f"[parse.eurovision_dataset] votes: {len(df)} wide -> {len(out)} long, "
        f"{kinds}, {int(split.sum())} rows carry a reported split"
    )
    return io.write_parquet(out, "votes", "interim")


def parse() -> list[Path]:
    return [parse_entries(), parse_votes()]
