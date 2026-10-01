"""rebuild the csv fixtures

python tests/fixtures/generate.py

a made up twelve country world, ten of them score so every voter leaves one
pair on zero, 2015 is combined and 2016 is split
"""

from __future__ import annotations

import csv
from pathlib import Path

HERE = Path(__file__).parent

COUNTRIES = [
    ("Austria", "AUT", "AT", "Q40"),
    ("Sweden", "SWE", "SE", "Q34"),
    ("Greece", "GRC", "EL", "Q41"),
    ("United Kingdom", "GBR", "UK", "Q145"),
    ("Serbia", "SRB", "RS", "Q403"),
    ("Montenegro", "MNE", "ME", "Q236"),
    ("North Macedonia", "MKD", "MK", "Q221"),
    ("Norway", "NOR", "NO", "Q20"),
    ("Finland", "FIN", "FI", "Q33"),
    ("Ireland", "IRL", "IE", "Q27"),
    ("Portugal", "PRT", "PT", "Q45"),
    ("Italy", "ITA", "IT", "Q38"),
]

LADDER = [12, 10, 8, 7, 6, 5, 4, 3, 2, 1]
YEARS = {2015: ["combined"], 2016: ["jury", "televote"]}
ISO3 = [c[1] for c in COUNTRIES]


def write(name: str, header: list[str], rows: list[list]) -> None:
    with (HERE / f"{name}.csv").open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)
    print(f"{name}.csv: {len(rows)} rows")


def main() -> None:
    labels = []
    for name, iso3, _geo, _qid in COUNTRIES:
        labels.append([name, iso3, "name", 1956, ""])
        labels.append([iso3.lower()[:2], iso3, "iso2", 1956, ""])
    write("country_map", ["label", "iso3", "kind", "valid_from", "valid_to"], labels)

    write(
        "voting_regimes",
        ["year", "jury_share", "televote_share", "separately_reported", "row_vote"],
        [
            [2015, 0.5, 0.5, "false", "false"],
            [2016, 0.5, 0.5, "true", "false"],
        ],
    )

    entries = []
    for year in YEARS:
        for place, iso3 in enumerate(ISO3, start=1):
            entries.append(
                [
                    f"{year}-{iso3}",
                    year,
                    iso3,
                    f"artist {iso3}",
                    f"song {iso3} {year}",
                    place,
                    "final",
                    place,
                    100 - place,
                    "true",
                    30 + place,
                    "female" if place % 2 else "male",
                    "english",
                ]
            )
    write(
        "entries",
        [
            "entry_id",
            "year",
            "country_iso3",
            "artist",
            "song",
            "running_order",
            "round",
            "place",
            "points_total",
            "qualified",
            "artist_age",
            "artist_sex",
            "song_language",
        ],
        entries,
    )

    votes = []
    for year, vote_types in YEARS.items():
        for vote_type in vote_types:
            for i, sender in enumerate(ISO3):
                targets = [c for c in ISO3 if c != sender]
                # rotate so not everyone votes the same way
                targets = targets[i:] + targets[:i]
                for points, receiver in zip(LADDER, targets, strict=False):
                    votes.append([year, "final", sender, receiver, vote_type, points])
    write(
        "votes",
        ["year", "round", "from_iso3", "to_iso3", "vote_type", "points"],
        votes,
    )

    static = []
    for i, origin in enumerate(ISO3):
        for j, dest in enumerate(ISO3):
            if origin == dest:
                continue
            gap = abs(i - j)
            static.append(
                [
                    origin,
                    dest,
                    gap * 400.0,
                    gap * 390.0,
                    "true" if gap == 1 else "false",
                    "false",
                    "false",
                    "false",
                    "false",
                    "false",
                ]
            )
    write(
        "dyad_static",
        [
            "iso_o",
            "iso_d",
            "dist",
            "distw",
            "contig",
            "comlang_off",
            "comlang_ethno",
            "colony",
            "comcol",
            "smctry",
        ],
        static,
    )

    write(
        "entries_manual",
        [
            "entry_id",
            "year",
            "country_iso3",
            "artist",
            "song",
            "running_order",
            "round",
            "place",
            "points_total",
            "qualified",
            "artist_age",
            "artist_sex",
            "song_language",
        ],
        [],
    )


if __name__ == "__main__":
    main()
