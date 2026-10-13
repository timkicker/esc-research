"""finished tables as csv for people and as small json files for the site

uv run esc export, writes data/export/csv/ and data/export/site/
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd

from esc import config, io
from esc.models.explain import MIN_MEETINGS

EXPORT = config.EXPORT
SITE_DATA = config.ROOT / "site" / "data"
VOTE_CODE = {"jury": "j", "televote": "t"}
SHARES = ["entry_only", "pair_only", "overlap", "noise"]
HEADLINE_MODEL = "ridge"
# fixed before any result in the canvas of 1 october, so it is not picked on test years
FORECAST_MODEL = "boosting"
FORECAST_LABELS = {
    "pair": "country pair",
    "pair+lyrics": "country pair + lyrics",
    "pair+order": "country pair + running order",
    "pair+attention": "country pair + search interest",
    "pair+attention+order": "country pair + search interest + running order",
}


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


SPLIT_LABELS = {
    "entry_only": "the entry itself",
    "pair_only": "the two countries",
    "overlap": "both together",
    "noise": "nothing we can explain",
}


def _records(payload: dict) -> list[dict]:
    return [dict(zip(payload["columns"], r, strict=True)) for r in payload["rows"]]


def latex_tables(payloads: dict, names: dict, named: int = 5, top: int = 8) -> dict:
    """small tables that pgfplots reads for the slides and the report"""
    split_rows = [
        {
            "y": i,
            "label": SPLIT_LABELS[share],
            "jury": round(payloads["split"]["split"]["jury"][share] * 100, 1),
            "public": round(payloads["split"]["split"]["televote"][share] * 100, 1),
        }
        for i, share in enumerate(SHARES)
    ]
    entry_rows = _records(payloads["entries"])
    scatter = pd.DataFrame(entry_rows)[["jury", "televote"]]
    by_gap = sorted(entry_rows, key=lambda r: r["televote"] - r["jury"])
    far = by_gap[: named - named // 2 - 1] + by_gap[-(named // 2 + 1) :]
    outliers = pd.DataFrame(
        {
            "jury": [r["jury"] for r in far],
            "televote": [r["televote"] for r in far],
            "label": [f"{names[r['country']]} {r['year']}" for r in far],
        }
    )
    public = [r for r in _records(payloads["affinity"]) if r["type"] == "t"][:top]
    favourites = pd.DataFrame(
        {
            "y": range(len(public)),
            "label": [f"{names[r['from']]} $\\to$ {names[r['to']]}" for r in public],
            "excess": [r["excess"] for r in public],
        }
    )
    return {
        "split": pd.DataFrame(split_rows),
        "scatter": scatter,
        "scatter-named": outliers,
        "favourites-public": favourites,
    }


def forecast_table(summary: pd.DataFrame, chance: pd.DataFrame) -> pd.DataFrame:
    """chance and every forecast set of the main model, jury next to televote"""
    by_type = chance.set_index("vote_type")
    rows = [{"label": "chance"}]
    for v in VOTE_CODE:
        rows[0][f"{v}_rank_error"] = round(float(by_type.loc[v, "rank_error"]), 2)
        rows[0][f"{v}_low"] = round(float(by_type.loc[v, "low"]), 2)
        rows[0][f"{v}_high"] = round(float(by_type.loc[v, "high"]), 2)
    main = summary[summary["model"] == FORECAST_MODEL].set_index(
        ["features", "vote_type"]
    )
    for name, label in FORECAST_LABELS.items():
        if (name, "jury") not in main.index:
            continue
        row = {"label": label}
        for v in VOTE_CODE:
            row[f"{v}_rank_error"] = round(float(main.loc[(name, v), "rank_error"]), 2)
            row[f"{v}_spearman"] = round(float(main.loc[(name, v), "spearman"]), 2)
        rows.append(row)
    columns = ["label"] + [
        f"{v}_{k}" for v in VOTE_CODE for k in ("rank_error", "spearman", "low", "high")
    ]
    return pd.DataFrame(rows).reindex(columns=columns)


def favourites(pairs: pd.DataFrame, names: dict, top: int = 5) -> pd.DataFrame:
    """strongest public and jury pairs side by side for the report table

    rounded once from full precision, the site json already rounds to two
    places and a second rounding would turn 9.849 into 9.9
    """
    reliable = pairs[pairs["meetings"] >= MIN_MEETINGS]
    sides = {}
    for vote_type, side in (("televote", "public"), ("jury", "jury")):
        best = reliable[reliable["vote_type"] == vote_type].nlargest(top, "excess")
        # a plain arrow, pgfplotstable cannot typeset math inside a string cell
        sides[f"{side}_label"] = [
            f"{names[a]} \u2192 {names[b]}"
            for a, b in zip(best["from_iso3"], best["to_iso3"], strict=True)
        ]
        sides[f"{side}_meetings"] = [int(m) for m in best["meetings"]]
        sides[f"{side}_excess"] = [round(float(e), 1) for e in best["excess"]]
    return pd.DataFrame(sides)


def _write_latex(name: str, frame: pd.DataFrame) -> Path:
    path = EXPORT / "latex" / f"{name}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")
    return path


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
    summary = io.read_parquet("model_summary", "processed")
    chance = io.read_parquet("chance", "processed")
    calibration = io.read_parquet("calibration", "processed")
    leakcheck = io.read_parquet("leakcheck", "processed")

    payloads = {
        "meta": meta(features, names),
        "votes": votes(features),
        "entries": entries(features, table),
        "split": split(decomposition),
        "affinity": affinity(pairs),
    }
    written = [_write_json(name, payload) for name, payload in payloads.items()]
    # the site folder has to stand on its own, so it carries a copy of its data
    SITE_DATA.mkdir(parents=True, exist_ok=True)
    for path in list(written):
        written.append(Path(shutil.copy2(path, SITE_DATA / path.name)))
    tables = latex_tables(payloads, payloads["meta"]["countries"])
    tables["forecast"] = forecast_table(summary, chance)
    tables["favourites"] = favourites(pairs, payloads["meta"]["countries"])
    written += [_write_latex(name, frame) for name, frame in tables.items()]
    written += [
        _write_csv("pairs", features),
        _write_csv("entries", table),
        _write_csv("decomposition", decomposition),
        _write_csv("pair_affinity", pairs),
        _write_csv("forecast", summary),
        _write_csv("chance", chance),
        _write_csv("calibration", calibration),
        _write_csv("leakcheck", leakcheck),
    ]
    for path in written:
        size = path.stat().st_size / 1024
        print(f"[export] {config.shown(path)}: {size:.0f} KB")
    return written


if __name__ == "__main__":
    main()
