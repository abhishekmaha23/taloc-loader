#####
# Merge the yearly HR records with bta pax names by name.
#
# We start with a list of BTA pax names and a reference HR name list.
# We match the two, proposing a HR name for each BTA pax name by highest similarity.
# We then let the users confirm or deny the proposed match.
#   Possible answers: Y (is match), NR (no match but expect a match), NN (no match and none expected/guest)
#   Files thus filled will serve as input to future runs.
# With this, we have the following situation for a general run:
# 1. Calculate a similarity list
# 2. Merge existing files for manually marked similarities
# 3. We end up with BTA Pax names in following classifications:
#   I) Trivial similarities matches are considered matches without user interaction
#  II) Similarities of the same name pair, marked Y are considered matches
# III) Similarities of unmarked name pairs are pushed out to a new marking request file
#  IV) Similarities of the same name pair, marked NR are raising an Exception.
#   V) Similarities of the same name pair, marked NN are considered guests and ignored
#
# 4. NOTE: We always compare the classifications pair-wise to account for new information.
# For example, after adding HR records, a BTA Pax name previously matched with "A" and marked NN could still end up
# being matched with new HR record "B", which happens to be correct. So the software must facilitate reviewing
# new matches and marking them differently from the old ones.
#####
from .name_similarity import name_similarity
from .parse_hr import employees, id8_by_fullname, get_org_fte, hr_issues
from .find_hr_matches import find_hr_matches, assign_employee_id8, hr_bta_fill_instructions
from .resolve_demographics import demographics_by_year, merge_demographics
