import pandas as pd


def to_excel(df, filename, **kwargs):
    writer = pd.ExcelWriter(filename, engine='xlsxwriter')

    sheet_name = kwargs['sheet_name'] if 'sheet_name' in kwargs else 'Sheet1'

    # send df to writer
    df.to_excel(writer, sheet_name=sheet_name, **kwargs)

    # pull worksheet object
    worksheet = writer.sheets[sheet_name]

    # loop through all columns
    for idx, col in enumerate(df):
        series = df[col]
        max_len = max((
            # len of largest item
            series.astype(str).map(len).max(),
            # len of column name/header
            len(str(series.name))
        # adding a little extra space
        )) + 1

        # set column width
        worksheet.set_column(idx, idx, max_len)
    writer.save()
