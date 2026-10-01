# esc-research

Eurovision voting data as a directed country-pair panel. How much of a vote is the song, how much is the relationship between the two countries, and does that split differ between the jury and the televote.

Conventions, schema and the domain traps are in `README.md`. Read it before adding anything.

## Setup

Python 3.12 and [uv](https://docs.astral.sh/uv/).

```
make install
cp .env.example .env
```

`CONTACT_EMAIL` in `.env` is required. Wikidata rejects requests that don't identify the sender and `esc.config` won't import without it.

## Usage

```
make data     # download and scrape -> data/raw
make parse    # -> data/interim
make build    # -> data/processed
make model    # leave-one-year-out fit and evaluation
make all
make test
make lint
```

`make clean-interim` and `make clean-all` to start over. Every target runs standalone. `make data` drives a headless Chrome for one source, see below.

## What is in the panel

19800 directed pair rows, ten contests from 2016 to 2026, finals only, jury and televote as separate rows. Earlier years are parsed too but only feed the pair history, because before 2016 the two halves were never reported apart.

## Layout

```
src/esc/config.py     paths, User-Agent
src/esc/io.py         parquet helpers, cached http client
src/esc/pipeline.py   stage runners behind the make targets
src/esc/fetch/        one module per source, network only here
src/esc/parse/        raw -> typed interim tables
src/esc/build/        joins and features -> processed
src/esc/models/       leave-one-year-out fit, baselines, metrics
data/raw|interim|processed
data/manual/          hand-maintained csvs
```

Only `data/manual/` is committed. `sources.yml` is committed too and the fetch step writes `retrieved_at` and `sha256` back into it, so a diff there after a run is expected.

## Sources

Urls, licenses and checksums in `sources.yml`.

- Spijkervet, J. (2020). The Eurovision Song Contest Dataset v1.0. Zenodo. https://doi.org/10.5281/zenodo.4036457 — results, votes and lyrics up to 2023. No license file, the authors ask to be cited.
- eurovisionworld.com — 2024 onwards, where the release stops. The scoreboard is built by javascript, so this one source needs a browser. robots.txt allows the results pages, we render each page once and keep it on disk.
- Mayer & Zignago (2011). Notes on CEPII's distances measures: The GeoDist database. CEPII WP 2011-25. Etalab 2.0 — distance, shared border, shared language per pair.
- Wikidata (CC0 1.0) — artist birth date and sex.
- Google Trends via pytrends — search interest per entry and per voting country.
- The tables in `data/manual/` are ours, CC0 1.0.

Not used: YouTube view counts, because the API only returns today's count. Audio features, because published work gets 1-8% of the variance out of them and Spotify shut its audio API in 2024. Spotify and TMDB at all, their terms forbid machine learning use. All of them are listed under `excluded:` in `sources.yml` with the reason.

## Gotchas

- nothing joins on country names, everything goes through `data/manual/country_map.csv`, which maps 107 labels from three vocabularies onto iso3
- no contest in 2020
- in 1956 every country sent two songs, the only year where `year-iso3` is not unique
- CEPII is from 2004, Romania is `ROM` there and Serbia and Montenegro sit under `YUG`
- the receiver effect explains a result, it does not forecast one, see rule 10 in `README.md`
