---
title: "Mini-project canvas: Predicting Jury and Televote Scores at the Eurovision Song Contest"
subtitle: "Anna-Ilona Nikolaeva, Yauheni Zviazdou, Tim Kicker · Workshop 2 · revised version, October 2026"
---

## Motivation

Our target group are the delegations that send an entry and people who follow Eurovision forecasts and betting odds. Both want to know before the final how a song will do. Both also see the jury and the public disagree every year. We give them a forecast for the jury ranking and for the public ranking separately, made only from what is known the day before the final. Just as important, we tell them how far such a forecast can be trusted.

## Data collection

Results and every single vote up to 2023 come from the Eurovision Song Contest dataset by Spijkervet (Zenodo, CC BY 4.0), the years 2024 to 2026 from the data file behind the results pages of eurovisionworld.com. Distance, shared border, shared language and colonial ties between two countries come from CEPII GeoDist. Google Trends gives the search interest for every entry in every voting country in the 30 days before the final, on web search and on YouTube. A language model labels each song's lyrics for mood, theme and repetition. We leave out YouTube view counts and the semi-final result, because both already contain what happened at or after the final. All downloads are stored with source, date, licence and checksum.

## Preprocessing

We predict the points every voting country gives every finalist (separately for jury and public) and add them up to a ranking. So one row is one voter and one finalist in one final, which gives 19,774 rows for the ten finals from 2016 to 2026 (2020 was cancelled). Rows with zero points stay in, since only ten countries score per vote. Country names are mapped onto three-letter codes, because the sources spell them differently. Inputs we compute ourselves are the mean points between the two countries in earlier finals, the running order scaled from first to last and the two Trends values.

## Exploratory data analysis

Jury and public points per entry only loosely agree (Spearman correlation 0.43 over 257 entries), so we forecast them separately. Sixty percent of all rows are zero. Of the rows with a Trends value, 53 percent are zero on both web and YouTube, which means below the Trends threshold and not zero interest.

## Visualisations

Jury points against public points for every entry, with the entries far from the diagonal labelled. The forecast error of our models next to the error of a random ranking, for jury and public. How often entries with a given predicted chance of winning actually won.

## Learning task

Supervised regression. The target is the number of points one country gives one finalist, with jury and public as two separate targets. The predicted points are summed per entry to a predicted ranking for each final and simulated into a chance of winning. Inputs are the relationship between the two countries (distance, border, language, colonial ties, past points), the Google Trends interest in the voting country, the lyric labels and the running order.

## Learning approach

We compare ridge regression, gradient boosting (our main model) and a random forest. Every final is held out once and the model learns from the other nine, because votes within one final depend on each other. We score the ranking with the mean rank error and Spearman's correlation. A random order serves as the baseline, drawn 1000 times per final. The best model, with country pair data and search interest, is on average 5.56 places off for the public and 6.40 for the juries, against 8.43 and 8.51 for a random order. That is clearly better than chance but still rough. The lyrics and the running order made the forecast worse. The chances of winning were unreliable, since only one of the eight entries given more than 50 percent actually won the public vote. A weak result is still a result. It tells our target group how little can be known the day before the final.

## Communication of results

A blog post for fans and anyone following the betting, with the three charts above. It shows how well jury and public results can be predicted, which inputs help and why a single winning chance should be taken with care. All numbers are in places and percent, without model terms. The spotlight presentation uses the same charts.

## Data privacy and ethical considerations

The data are public contest results per country, so no consent is needed. The only people in the data are the artists, who are public figures. Google Trends values are already aggregated by Google. Since the forecast is rough, the blog post must not read like betting advice. The lyric labels may be less accurate for songs that are not in English. Russia and Belarus are missing in later years and the public vote from the rest of the world has no country behind it.

## Added value

The closest published study we found, Adamska and Reiss (2025), predicts the combined place in the final. We predict the jury and the public ranking separately and show how much of each can be known in advance. Putting the error of the forecast next to the error of chance tells a reader how much a forecast is worth.
