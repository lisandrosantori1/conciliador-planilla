def get_duplicates(df, cols):
    return df[df.duplicated(subset=cols, keep=False)]

def get_unique(df, cols):
    return df.drop_duplicates(subset=cols)