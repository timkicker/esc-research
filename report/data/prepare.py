"""turn the notebook results into small semicolon files for pgfplots, values stay unrounded"""
from pathlib import Path
import pandas as pd

HERE = Path(__file__).parent
RESULTS = HERE.parent.parent / "notebooks" / "results"
FEATURES = HERE.parent.parent / "notebooks" / "features_full.csv"

LABELS = {
    "linear regression": "Linear regression",
    "lasso": "Lasso",
    "random forest": "Forest, all features",
    "random forest, no artist and lyrics": "Forest, no artist or lyrics",
    "gradient boosting, no artist and lyrics": "Boosting, no artist or lyrics",
}

models = pd.read_csv(RESULTS / "models.csv")
models = models[models["model"].isin(LABELS)].copy()
models["order"] = models["model"].map(list(LABELS).index)
models = models.sort_values("order")
models["label"] = models["model"].map(LABELS)
models["y"] = range(len(models) - 1, -1, -1)
models["chosen"] = models["chosen"].astype(int)
cols = ["y", "label", "chosen", "val_r2", "val_rank_error", "test_r2", "test_rank_error",
        "winner_2024", "winner_2025", "winner_2026"]
models[cols].to_csv(HERE / "models.csv", sep=";", index=False)

chance = pd.read_csv(RESULTS / "chance.csv")
chance.to_csv(HERE / "chance.csv", sep=";", index=False)

# the middle of the field is what a random order gives the winner on average
field = pd.read_csv(FEATURES, usecols=["year", "to_iso3"], low_memory=False).drop_duplicates()
middle = (field.groupby("year").size() + 1) / 2
yearly = pd.read_csv(RESULTS / "yearly.csv")
yearly["middle"] = yearly["year"].map(middle)
yearly["x"] = range(len(yearly))
yearly = yearly.rename(columns={"rank error": "rank_error", "winner predicted": "winner"})
yearly.assign(partcode=yearly["part"].map({"train": 0, "validation": 1, "test": 2}))[["x", "year", "part", "partcode", "winner", "middle", "rank_error", "chance"]].to_csv(HERE / "yearly.csv", sep=";", index=False)

ablation = pd.read_csv(RESULTS / "ablation.csv")
names = {
    "nothing (all features)": "all features",
    "age and sex": "without age and sex",
    "Google searches": "without Google searches",
    "lyrics": "without lyrics",
    "running order": "without running order",
    "past points between the countries": "without past points",
}
ablation["label"] = ablation["left out"].map(names)
rest = ablation[ablation["left out"] != "nothing (all features)"].sort_values("val rank error", ascending=False)
base = ablation[ablation["left out"] == "nothing (all features)"]["val rank error"].iloc[0]
rest = rest.assign(y=range(len(rest)), base=base)
rest.rename(columns={"val rank error": "rank_error", "val R2": "r2"})[["y", "label", "rank_error", "r2", "base"]] \
    .to_csv(HERE / "ablation.csv", sep=";", index=False)
print(models[cols].to_string(index=False))
print(yearly.to_string(index=False))
print(rest.to_string(index=False), base)
