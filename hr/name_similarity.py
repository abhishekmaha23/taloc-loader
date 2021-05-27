# https://bergvca.github.io/2017/10/14/super-fast-string-matching.html
# https://github.com/Bergvca/string_grouper
# Approach: Calculate cosine similarities on name bigram based tf-idf.
# Finding: an (anonymized) name of Fäs Fäsreg matches with Faes Faesreg or Fas Fasreg with a similarity below 20%!
# So we need at least some pre-processing for Umlauts.
from string_grouper import match_strings, match_most_similar
import pandas as pd
import unicodedata
import re


umlaut_equivalents = [
    # Keep separators as they letters on each side should not become neightbors in a n-gram
    (r'[,-./]|\s', ' '),
    (r'ae', 'ä'),
    (r'oe', 'ö'),
    (r'ue', 'ü'),
]


def canonicalize_umlauts(string):
    # Need to convert ae => ä first, then normalize ä -> a.
    for match, new in umlaut_equivalents:
        string = re.sub(match, new, string)
    # This not only removes umlauts, but also accents.
    string = ''.join(c for c in unicodedata.normalize(
        'NFD', string) if not unicodedata.category(c) == 'Mn')
    return string

#####
# name_similarity
#
# Params:
# @ref_list: the "reference" list/ground truth.
# In our case these are the HR names.
# @checklist_with_meta: a list with names that are similar to some in ref_list
# The `_with_meta` denotes additional columns in that frame. Those are simply returned with
# the result.
# @check_key: The column name of the names to be checked in the checklist_with_meta df.
#
# General naming convention:
# 'reference': the ground truth
# ' canonical': name string with canonicalized Umlauts.
#####


def name_similarity(ref_list, checklist_with_meta, check_key):
    reference_names_df = pd.DataFrame({'reference': ref_list})
    candidates = pd.DataFrame.copy(checklist_with_meta)
    # candidates.rename(columns={check_key: 'check'}, inplace=True)

    reference_names_df['reference canonical'] = reference_names_df.apply(
        lambda row: canonicalize_umlauts(row['reference']), axis=1)

    candidates['check canonical'] = candidates.apply(
        lambda row: canonicalize_umlauts(row[check_key]), axis=1)

    # any_matches can contain multiple proposed match entries for the same "check" name.
    any_matches = match_strings(reference_names_df['reference canonical'], candidates['check canonical'], ngram_size=2,
                                regex=r'', max_n_matches=100, min_similarity=0.1)

    # Alternative API:
    # matches = match_most_similar(reference_names_df, candidates, ngram_size=2,
    #  regex=r'[,-./]|\s', max_n_matches=3, min_similarity=0.6)

    # Result: left_side is reference_names_df/HR, right_side is candidates/checklist_with_meta
    # Reduce to a single proposed match row for each candidate name to be checked
    single_matches = any_matches.sort_values(by=['right_side', 'similarity'], ascending=False).groupby(
        'right_side', as_index=False).first()
    # Reduce to a single reference proposal per candidate name
    single_matches = single_matches.sort_values(
        by="similarity", ascending=False)
    single_matches = single_matches.rename(
        columns={'left_side': 'reference canonical', 'right_side': 'check canonical'})

    # Rounding similarity
    single_matches['similarity'] = single_matches.apply(
        lambda row: round(row['similarity'], 2), axis=1)

    # Add original bta names back in (the ones not canonicalized)
    single_matches = pd.merge(single_matches, candidates, how='left',
                              on='check canonical', suffixes=(None, '_m'))
    # Add original hr names back in
    single_matches = pd.merge(single_matches, reference_names_df, how='left',
                              on='reference canonical', suffixes=(None, '_m'))

    # candidates = pd.merge(candidates, single_matches, how='left',
    #                       on='check canonical', suffixes=(None, '_m'))

    # TODO: Clean-up, all file actually.
    is_different = single_matches['reference canonical'].str.casefold(
    ) != single_matches['check canonical'].str.casefold()

    similar = single_matches[is_different].drop(
        ['check canonical', 'reference canonical'], axis=1)
    matched = single_matches[~is_different].drop(
        ['check canonical', 'reference canonical'], axis=1)

    return [similar, matched]
