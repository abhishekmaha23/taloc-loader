def df_to_list(df):
    cols = df.columns

    return [dict(zip(cols, item)) for item in df.values.tolist()]
