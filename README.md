# esc-research

Eurovision finals from 2008 to 2026 as a table of country pairs: one row for every country that gives points to another country in a final. On top of it we predict how many points each country gives each other country, add them up to a scoreboard and check how well that finds the winner the day before the final. The technical report with the results is in `report/technical-report.pdf`.

The pipeline also splits the votes from 2016 on into jury and televote and asks how much of a vote is the song and how much the relationship between the two countries. That part is in `uv run esc model`.

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
uv run esc data       # download -> data/raw
uv run esc parse      # -> data/interim
uv run esc build      # -> data/processed
uv run esc model      # fit on all years but one and test on that one
uv run esc export     # csv and json for the site and the report
uv run esc test
uv run esc lint
uv run esc clean      # delete data/interim
uv run esc clean-all  # delete everything downloaded or built
```

`uv run esc` without anything lists the commands. On Linux and Mac `make all`, `make data` and so on do the same. Each step also runs on its own and nothing needs a browser.

The finished tables are parquet files in `data/processed/` and `features.parquet` is the full one.

## Notebooks

The prediction of the winner lives in `notebooks/`, next to the pipeline and not inside it.

- `create_static_dataset.ipynb` reads `data/processed/` after `uv run esc build` and writes `features_full.csv`, the pair table with the age and sex of the artists added. The other notebooks read that file, so they run without the pipeline once it exists.
- `prediction.ipynb` predicts the points per pair, sums them per song and judges every model by where it puts the real winner. Training is 2008 to 2019, validation 2021 to 2023 and test 2024 to 2026. Its last cell writes the numbers behind the report figures to `notebooks/results/`.
- `visualisations.ipynb` plots what winners have in common.

The report in `report/` is LaTeX. `report/data/prepare.py` turns `notebooks/results/` into the small tables the figures read, then `latexmk -lualatex technical-report.tex` builds the PDF.

## What is in the table

There is one row for every country that gives points to another country in a final, from 2008 on. From 2016 jury and televote are separate rows (19774 rows over ten contests). Before 2016 the two were never published separately, so 2008 to 2015 has one combined row per pair (8144 rows, `vote_type` is `combined`). The jury and televote models only use 2016 on. Contests before 2008 are parsed too, but only for the history between two countries.

A pair that gave no points keeps a row with 0. Only ten countries score per vote, so dropping the zeros would leave a table of successes only.

`uv run esc model` writes three more tables to `data/processed/`. `model_summary` has the forecast scores for every model and every set of inputs. `decomposition` splits the points into the part the entry explains by itself, the part the relationship between the two countries explains and the rest, separately for jury and televote. `pair_affinity` says for every pair of countries how many points one gave the other on average beyond what the entry earned. On disk it is sorted by country, so sort it by `excess` if you want a ranking.

The tables in `data/interim/` follow one schema, which `esc.parse.SCHEMA` fixes with dtypes:

```
entries(entry_id, year, country_iso3, artist, song, running_order, round,
        place, points_total, qualified, artist_age, artist_sex, song_language)
votes(year, round, from_iso3, to_iso3, vote_type, points)
dyad_static(iso_o, iso_d, dist, distw, contig, comlang_off, comlang_ethno,
            colony, comcol, smctry)
voting_regimes(year, jury_share, televote_share, separately_reported, row_vote)
country_map(label, iso3, kind, valid_from, valid_to)
contest_dates(year, final_date)
trends(year, from_iso3, entry_id, web_interest, youtube_interest, censored)
lyric_features(entry_id, sentiment, repetition_verse, repetition_chorus, theme)
```

`votes` is directed: `from_iso3` gives, `to_iso3` receives. `entry_id` is `year-iso3` and everything about a song joins on it.

## How the voting changed

`data/manual/voting_regimes.csv` is the one place that says what the points measure in a given year:

| years | what the points measure |
|---|---|
| 1956 to 1996 | juries only |
| 1997 | televote tried in five countries |
| 1998 to 2008 | televote, juries only as fallback |
| 2009 to 2015 | jury and televote 50/50, merged per country, the parts not published |
| from 2016 | jury and televote published separately |
| from 2023 | no juries in the semi-finals, a Rest of the World televote added |

So a `jury` row before 2016 would be a mistake. A `combined` series is never compared with a `televote` series without saying so.

## Rules for the code

1. Network access only in `src/esc/fetch/`. Parse, build and model run offline on files on disk.
2. Nothing under `data/raw/` is edited by hand. Corrections go into `data/manual/`.
3. `data/raw`, `data/interim`, `data/processed`, `cache/` and full song lyrics never go into git. `data/manual/` does.
4. Every http response is cached through the client in `io.py`, so a second run with a warm cache never goes online.
5. Wikimedia wants a User-Agent with a contact address, which is why `CONTACT_EMAIL` exists.
6. A new source needs its licence in `sources.yml` before any code is written. Spotify and TMDB forbid machine learning in their terms and stay out.
7. Every downloaded file has a row in `sources.yml` with url, date, checksum, licence and citation.
8. Runs are deterministic: fixed seeds, sorted output, the same parquet bytes on the same input.
9. No YouTube view counts. The API only gives today's count, so an old song would carry every view it got because it won.
10. Nothing measured after the final goes into a forecast. Searches stop the day before. The receiver effect (what everyone else gave the same song) explains a result but can't predict one.
11. Years are split as whole contests and never at random. Anything learned from data, the fill-in median included, is fitted on the training years only.

## Sources

`sources.yml` has the urls, licences and checksums.

- Spijkervet, J. (2023). Spijkervet/eurovision-dataset: 2023. Zenodo. https://doi.org/10.5281/zenodo.10088892. Results, votes and lyrics up to 2023. The GitHub repo has no licence file, the Zenodo record of this release says CC BY 4.0.
- eurovisionworld.com for 2024 to 2026, where the dataset stops. The results page loads all its points from a small script file with json in it, so we download that file directly and keep it on disk. robots.txt allows it.
- Mayer & Zignago (2011). Notes on CEPII's distances measures: The GeoDist database. CEPII WP 2011-25. Etalab 2.0. Distance, shared border and shared language for every pair.
- [ezvezdov/eurovision-dataset](https://github.com/ezvezdov/eurovision-dataset) is the repo of our teammate (GPL-3.0). From there we take the lyric labels, the song language and Google Trends for every entry in every voting country. We only read its data files at a fixed commit and use none of its code.
- Wikidata (CC0 1.0) for the age and sex of the artists since 1956. Bands and duos stay empty. The age also stays empty when Wikidata knows the birth date only to the year.
- The tables in `data/manual/` are ours, CC0 1.0.

Some things we left out on purpose. YouTube views can't be used for the reason in rule 9. Published work gets only 1 to 8 percent of the variance out of audio features and Spotify closed its audio API in 2024 anyway. `sources.yml` lists everything we left out under `excluded:` with the reason.

## Gotchas

- Nothing is joined on country names. Everything goes through `data/manual/country_map.csv`, which maps 108 labels (spelled out names and lowercase iso2) onto iso3. `wld` is the Rest of the World televote and not a country.
- There was no contest in 2020.
- In 1956 every country sent two songs. It is the only year where `year-iso3` is not unique.
- CEPII is from 2004, so Romania is still `ROM` there and Serbia and Montenegro are under `YUG`.
- Google Trends gives a share and not a volume. Several terms in one query split the scale between them, so every song is queried on its own.
- Features that are the same for every voter of one song (lyrics, running order, age) let trees learn the training songs by heart. They made the jury and televote models worse, which is why `models/explain.py` uses ridge as the headline and boosting with large leaves only as a check.
- In the prediction notebook the Rest of the World televote has no jury next to it. It is halved like every other vote, otherwise it would count twice.
