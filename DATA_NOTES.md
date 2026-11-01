# Data notes

## Source

Divvy trip data, published by Motivate International Inc. under the Divvy data license agreement.
Index page: the Divvy tripdata download page (divvy-tripdata S3 index).

## Files used

The twelve most recent complete months at download time (Friday, October 30, 2026):

- 202510-divvy-tripdata.zip
- 202511-divvy-tripdata.zip
- 202512-divvy-tripdata.zip
- 202601-divvy-tripdata.zip
- 202602-divvy-tripdata.zip
- 202603-divvy-tripdata.zip
- 202604-divvy-tripdata.zip
- 202605-divvy-tripdata.zip
- 202606-divvy-tripdata.zip
- 202607-divvy-tripdata.zip
- 202608-divvy-tripdata.zip
- 202609-divvy-tripdata.zip

About 237 MB of zips in total. September 2026 was the newest file on the index at download time, no October 2026 file had been posted yet.

## Reproduce

1. Download the twelve zips above from the Divvy tripdata index.
2. Unzip them and keep the twelve monthly CSVs together in one folder, still as separate files. That folder stays raw and untouched.
3. Run: python clean_cyclistic.py --input-dir path/to/that/folder
   The script writes cyclistic_cleaned.csv, cleaning_log.txt, and summary_by_group.csv into its output folder.
4. Load cyclistic_cleaned.csv into Power BI for the dashboard. Cleaning steps and every judgment call are logged in section 3 of the README and in cleaning_log.txt.

## Privacy

The data carries no personally identifiable information. Per the case study, payment and purchase data is not part of this set, so rides cannot be connected to individual riders or home addresses.
