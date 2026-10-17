"""turn the notebook results into small semicolon files for pgfplots, values stay unrounded"""
from pathlib import Path
import pandas as pd

HERE = Path(__file__).parent
RESULTS = HERE.parent.parent / "notebooks" / "results"

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
models["chosen"] = models["chosen"].astype(int)
cols = ["label", "chosen", "val_r2", "test_r2", "test_rank_error",
        "val_2021", "val_2022", "val_2023", "test_2024", "test_2025", "test_2026"]
models[cols].to_csv(HERE / "models.csv", sep=";", index=False)

pd.read_csv(RESULTS / "chance.csv").to_csv(HERE / "chance.csv", sep=";", index=False)

yearly = pd.read_csv(RESULTS / "yearly.csv")
yearly = yearly.rename(columns={"winner predicted at": "winner", "real winner": "country"})
yearly["partcode"] = yearly["set"].map({"train": 0, "validation": 1, "test": 2})
yearly["x"] = range(len(yearly))
yearly[["x", "year", "country", "set", "partcode", "winner", "chance"]].to_csv(HERE / "yearly.csv", sep=";", index=False)

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
base = ablation.loc[ablation["left out"] == "nothing (all features)", "mean place"].iloc[0]
rest = ablation[ablation["left out"] != "nothing (all features)"].sort_values("mean place", ascending=False)
rest = rest.assign(y=range(len(rest)), base=base)
rest.rename(columns={"mean place": "place"})[["y", "label", "place", "2021", "2022", "2023", "base"]] \
    .to_csv(HERE / "ablation.csv", sep=";", index=False)
print(models[cols].to_string(index=False))
print(yearly.to_string(index=False))
print(rest.to_string(index=False))
