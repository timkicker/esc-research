# esc-research

Eurovision voting data as a directed country-pair panel. How much of a vote is the song, how much is the relationship between the two countries, and did that shift when the voting rules changed.

Conventions, schema and the domain traps are in `README.md`. Read it before adding anything.

## Setup

Python 3.12 and [uv](https://docs.astral.sh/uv/).

```
make install
cp .env.example .env
```

`CONTACT_EMAIL` in `.env` is required. Wikimedia rejects requests that don't identify the sender and `esc.config` won't import without it.

## Usage

```
make data     # download -> data/raw
make parse    # -> data/interim
make build    # -> data/processed
make all
make test
make lint
```

`make clean-interim` and `make clean-all` to start over. Every target runs standalone.

## Layout

```
src/esc/config.py     paths, User-Agent
src/esc/io.py         parquet helpers, cached http client
src/esc/pipeline.py   stage runners behind the make targets
src/esc/fetch/        one module per source, network only here
src/esc/parse/        raw -> typed interim tables
src/esc/build/        joins and features -> processed
data/raw|interim|processed
data/manual/          hand-maintained csvs
```

Only `data/manual/` is committed. `sources.yml` is committed too and the fetch step writes `retrieved_at` and `sha256` back into it, so a diff there after a run is expected.

## Sources

Urls, licenses and checksums in `sources.yml`.

- Spijkervet, J. (2020). The Eurovision Song Contest Dataset v1.0. Zenodo. https://doi.org/10.5281/zenodo.4036457 (no license file, authors ask to be cited)
- Burgoyne, Spijkervet & Baker (2023). Measuring the Eurovision Song Contest: A Living Dataset for Real-World MIR. ISMIR 2023. https://archives.ismir.net/ismir2023/paper/000097.pdf (MIT)
- Mayer & Zignago (2011). Notes on CEPII's distances measures: The GeoDist database. CEPII WP 2011-25. (Etalab 2.0)
- Eurostat `migr_pop1ctz` (EC reuse policy, Decision 2011/833/EU)
- Wikidata (CC0 1.0), Wikimedia REST pageviews (CC0 1.0)
- Bailey, Strezhnev & Voeten (2017), UNGA ideal points. https://doi.org/10.7910/DVN/LEJUQZ (CC0 1.0)

Spotify and TMDB aren't used, their terms forbid ML applications. Listed under `excluded:` in `sources.yml`.
