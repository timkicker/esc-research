"""finished tables as csv for people and as small json files for the site

uv run esc export, writes data/export/csv/ and data/export/site/
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from esc import config, io
from esc.models.explain import MIN_MEETINGS

EXPORT = config.EXPORT
VOTE_CODE = {"jury": "j", "televote": "t"}
SHARES = ["entry_only", "pair_only", "overlap", "noise"]
HEADLINE_MODEL = "ridge"


def votes(features: pd.DataFrame) -> dict:
    """every award with points, the zeros are implied"""
    given = features[
        features["vote_type"].isin(VOTE_CODE) & (features["points"] > 0)
    ].sort_values(
        ["year", "vote_type", "from_iso3", "points"],
        ascending=[True, True, True, False],
    )
    rows = [
        [int(r.year), VOTE_CODE[r.vote_type], r.from_iso3, r.to_iso3, int(r.points)]
        for r in given.itertuples()
    ]
    return {"columns": ["year", "type", "from", "to", "points"], "rows": rows}


def entries(features: pd.DataFrame, table: pd.DataFrame) -> dict:
    """one row per final entry with the jury and the televote total"""
    halves = (
        features[features["vote_type"].isin(VOTE_CODE)]
        .groupby(["year", "to_iso3", "vote_type"])["points"]
        .sum()
        .unstack("vote_type")
        .fillna(0)
        .astype(int)
        .reset_index()
        .rename(columns={"to_iso3": "country_iso3"})
    )
    finals = table[
        (table["round"] == "final") & (table["year"] >= halves["year"].min())
    ]
    merged = finals.merge(halves, on=["year", "country_iso3"], how="inner")
    merged = merged.sort_values(["year", "place"])
    rows = [
        [
            int(r.year),
            r.country_iso3,
            r.artist,
            r.song,
            int(r.place),
            int(r.running_order),
            int(r.jury),
            int(r.televote),
        ]
        for r in merged.itertuples()
    ]
    columns = ["year", "country", "artist", "song", "place", "order"]
    return {"columns": [*columns, "jury", "televote"], "rows": rows}


def split(decomposition: pd.DataFrame) -> dict:
    """the headline split per vote type plus its range over the years"""
    out = {}
    headline = decomposition[decomposition["model"] == HEADLINE_MODEL]
    for vote_type, part in headline.groupby("vote_type"):
        pooled = part[part["scope"] == "all"].iloc[0]
        years = part[part["scope"] != "all"]
        out[vote_type] = {
            **{share: round(float(pooled[share]), 4) for share in SHARES},
            "per_year": {
                str(r.scope): {s: round(float(getattr(r, s)), 4) for s in SHARES}
                for r in years.itertuples()
            },
        }
    return {"model": HEADLINE_MODEL, "split": out}


def affinity(pairs: pd.DataFrame) -> dict:
    reliable = pairs[pairs["meetings"] >= MIN_MEETINGS].sort_values(
        ["vote_type", "excess"], ascending=[True, False]
    )
    rows = [
        [
            VOTE_CODE[r.vote_type],
            r.from_iso3,
            r.to_iso3,
            round(float(r.excess), 2),
            round(float(r.points), 2),
            int(r.meetings),
        ]
        for r in reliable.itertuples()
    ]
    columns = ["type", "from", "to", "excess", "points", "meetings"]
    return {"min_meetings": MIN_MEETINGS, "columns": columns, "rows": rows}


def meta(features: pd.DataFrame, names: pd.DataFrame) -> dict:
    used = sorted(set(features["from_iso3"]) | set(features["to_iso3"]))
    lookup = dict(zip(names["iso3"], names["name"], strict=True))
    missing = [c for c in used if c not in lookup]
    if missing:
        raise ValueError(f"no display name for {missing}, add them to country_names")
    return {
        "years": sorted(int(y) for y in features["year"].unique()),
        "countries": {c: lookup[c] for c in used},
        "vote_types": {code: name for name, code in VOTE_CODE.items()},
    }


def _write_json(name: str, payload: dict) -> Path:
    path = EXPORT / "site" / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    path.write_text(text, encoding="utf-8")
    return path


def _write_csv(name: str, frame: pd.DataFrame) -> Path:
    path = EXPORT / "csv" / f"{name}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")
    return path


def main() -> list[Path]:
    features = io.read_parquet("features", "processed")
    table = io.read_parquet("entries", "processed")
    decomposition = io.read_parquet("decomposition", "processed")
    pairs = io.read_parquet("pair_affinity", "processed")
    names = io.read_parquet("country_names", "interim")

    written = [
        _write_json("meta", meta(features, names)),
        _write_json("votes", votes(features)),
        _write_json("entries", entries(features, table)),
        _write_json("split", split(decomposition)),
        _write_json("affinity", affinity(pairs)),
        _write_csv("pairs", features),
        _write_csv("entries", table),
        _write_csv("decomposition", decomposition),
        _write_csv("pair_affinity", pairs),
    ]
    for path in written:
        size = path.stat().st_size / 1024
        print(f"[export] {path.relative_to(config.ROOT).as_posix()}: {size:.0f} KB")
    return written


if __name__ == "__main__":
    main()
