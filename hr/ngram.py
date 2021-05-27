import re


def n_grams(string, ignore_case=True, ngram_size=3, replacements=[(r'[,-./]|\s', '')], **kwargs):
    """
    :param string: string to create ngrams from
    :return: list of ngrams
    """
    print(ngram_size)
    if ignore_case and string is not None:
        string = string.lower()  # lowercase to ignore all case
    for match, new in replacements:
        string = re.sub(match, new, string)
    n_grams = zip(*[string[i:] for i in range(ngram_size)])
    return [''.join(n_gram) for n_gram in n_grams]
