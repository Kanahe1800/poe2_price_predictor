import pandas as pd

df = pd.read_csv("Data/poe2_ml_dataset_full.csv")
print(df.head())
print(df['price_currency'].unique())