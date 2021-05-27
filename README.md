# Summary

The app is run by customer. It collects sustainability-related data (starting with air travel) for a University.

It combines this data with emissions, department statistics, employee demographics, airport info.
The result is a json file which can be loaded into a web-based front-end.

# Steps

The data loading and combination steps are (with University being the user):

- read all flight segments ("segment" is synonymous with "leg"). Source: University
- add emission data to the segments. Source: External data provider (atmosfair)
- add HR data (demographics of travelers, and per department FTE statistics). Source: University
- anonymize the whole dataset (k-anonymization)
- output 2 versions of data, 1 identifiable xls for University internal archive, 1
  de-identified json for use in web front-end

# Program flow

The program flow is as such:

First, a user adds files containing the data to the provided folder structure.
The user additionally needs to register those files in the config.yml file.
(TODO: Can we simplify this? See config.yml for details)

Then, the user runs the program which combines all available data.
In the end, the program prompts for all data that still has to be provided, or needs to be fixed.

Multiple runs of the program are expected.
For example, on the first run with new flight segment data, associated GHG emissions will not be available yet for the new segments and first need to be requested by an external service (atmosfair).

Note that the program does not terminate when finding missing or wrong data.
Instead, it sends the full list of open issues to the user after each run, to avoid a bad user experience of discovering a new issue only when a previous issue is fixed.

# Program focus areas (requirements)

The program is written to handle 4 general requirements:

1. Loading and combining flight segment data from multiple sources with different data formatting

(Note that some of the bad data quality from some sources has since been ameliorated by manual data cleaning on customer side, so it is not a high complexity task.)

2. Combining all legs with employee information to find out traveler demographics.

One of the flight leg data sources does not contain University employee ids, but only traveler names.
For this a matching algorithm, supported by user review, matches traveler names to employees.
Non-matches are considered externals.

3. Incremental emissions query.

The situation is as follows:

3.1 Data issues at the University (wrong flight details, employee id, etc.) occur frequently, and when they occur, the user should be able to fix them in the original files and not have to somehow incrementally keep track of what was added, removed or changed since last time.
Therefore the program has to be run with cumulative data for the involved data over all years.

3.2 The external emission service is a relatively expensive service. Once a request involving flight leg definitions has been answered with a response listing GHG emissions for that leg, further requests containing the same leg definition should be avoided. This calls for incremental calling of the emission data service.

The approach the software takes is to create a normalized cache of flight leg definitions that are enriched with emission data from the external service.
All legs from a cumulative data load are first checked against that cache, and only definitions that are not found are filled into a new request.

4. Anonymization (TODO)

Because of the sparse data problem, anonymization is not trivial and a k-anonymization algorithm needs to be implemented

# Running the application

Either run the VS code debug config. Note this does not map volumes and no output files will persist across runs.

Or

```
docker compose up
```

The VS code debug config is useful for debugging.
The vscode debugger does not map directories, because

[Launching directly using the normal launch configuration does not use Docker Compose.](https://code.visualstudio.com/docs/containers/docker-compose)

=> If output files are needed, run `docker-compose up`.

When running `docker compose up`, up-to-date python code is mapped automatically, otherwise, in some cases, watch out for docker image caching issues.
