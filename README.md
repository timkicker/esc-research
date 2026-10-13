# esc-research

Eurovision votes from 2016 to 2026 as a table of country pairs. We want to know how much of a vote is the song and how much is the relationship between the two countries. We also check if the answer is different for the jury and the televote.

The rules for working on the code, the schema and the traps we already ran into are in `README.md`. Read that first if you want to add something.

## Setup

All you need is [uv](https://docs.astral.sh/uv/). It installs Python 3.12 and every package by itself on the first run.

Clone the repo first and run everything below inside the `esc-research` folder:

```
git clone https://github.com/timkicker/esc-research.git
cd esc-research
```

On Windows in PowerShell:

```
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
copy .env.example .env
notepad .env
```

If PowerShell can't find `uv` afterwards, close it and open a new window.

On Linux or Mac:

```
curl -LsSf https://astral.sh/uv/install.sh | sh
cp .env.example .env
```

Then put your email into `CONTACT_EMAIL` in `.env`. Only the download needs it because it goes into every request and some sites block requests that don't say who is asking.

## Usage

Everything runs through one command, on every system the same way:

```
uv run esc all        # download, build and fit, the whole thing
uv run esc data       # download and scrape -> data/raw
uv run esc parse      # -> data/interim
uv run esc build      # -> data/processed
uv run esc model      # fit on all years but one and test on that one
uv run esc test
uv run esc lint
uv run esc clean      # delete data/interim
uv run esc clean-all  # delete everything downloaded or built
```

`uv run esc` without anything lists the commands. On Linux and Mac `make all`, `make data` and so on do the same. Each step also runs on its own and nothing needs a browser.

The finished tables are parquet files in `data/processed/` and `features.parquet` is the full one. If you want a csv, `pandas.read_parquet` and `to_csv` is enough.

## What is in the table

There is one row for every country that gives points to another country in a final, separately for jury and televote. That is 19800 rows over ten contests. Older contests are parsed too, but we only use them for the history between two countries since the jury and televote points were not published separately before 2016.

`uv run esc model` writes three more tables to `data/processed/`. `model_summary` has the forecast scores for every model and every set of inputs. `decomposition` splits the points into the part the entry explains by itself, the part the relationship between the two countries explains and the rest, separately for jury and televote. `pair_affinity` says for every pair of countries how many points one gave the other on average beyond what the entry earned. On disk it is sorted by country, so sort it by `excess` if you want a ranking.

## Layout

```
src/esc/config.py     paths, User-Agent
src/esc/io.py         parquet helpers, cached http client
src/esc/cli.py        the esc command\nsrc/esc/pipeline.py   runs the stages
src/esc/fetch/        one module per source, the only place with network access
src/esc/parse/        raw -> typed interim tables
src/esc/build/        joins and features -> processed
src/esc/models/       models, baselines, metrics
data/raw|interim|processed
data/manual/          csvs we maintain by hand
```

Only `data/manual/` is in git. `sources.yml` is in git too but a run never changes it. Every download writes its date and checksums to `data/raw/provenance.yml` and warns if a file is not the one we used for our results.

## Sources

`sources.yml` has the urls, licenses and checksums.

- Spijkervet, J. (2023). Spijkervet/eurovision-dataset: 2023. Zenodo. https://doi.org/10.5281/zenodo.10088892. Results, votes and lyrics up to 2023. The GitHub repo has no license file, the Zenodo record of this release says CC BY 4.0.
- eurovisionworld.com for 2024 to 2026, where the dataset stops. The results page loads all its points from a small script file with json in it, so we download that file directly and keep it on disk. robots.txt allows it.
- Mayer & Zignago (2011). Notes on CEPII's distances measures: The GeoDist database. CEPII WP 2011-25. Etalab 2.0. Distance, shared border and shared language for every pair.
- [ezvezdov/eurovision-dataset](https://github.com/ezvezdov/eurovision-dataset) is the repo of our teammate (GPL-3.0). From there we take what an llm read out of the lyrics, the song language and Google Trends for every entry in every voting country. We only read its data files at a fixed commit and use none of its code.
- Wikidata (CC0 1.0) for the age and sex of the artists. The module for it is not written yet.
- The tables in `data/manual/` are ours, CC0 1.0.

Some things we left out on purpose. YouTube views can't be used because the API only gives today's count and not the one from before the final. Published work gets only 1 to 8 percent of the variance out of audio features and Spotify closed its audio API in 2024 anyway. The terms of Spotify and TMDB don't allow machine learning at all. `sources.yml` lists all of them under `excluded:` with the reason.

## Gotchas

- Nothing is joined on country names. Everything goes through `data/manual/country_map.csv`, which maps 108 labels (spelled out names and lowercase iso2) onto iso3.
- There was no contest in 2020.
- In 1956 every country sent two songs. It is the only year where `year-iso3` is not unique.
- CEPII is from 2004, so Romania is still `ROM` there and Serbia and Montenegro are under `YUG`.
- The receiver effect (how many points everyone else gave the same song) explains a result but can't predict one, see rule 10 in `README.md`.
