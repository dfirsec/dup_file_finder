# Duplicate File Finder

![Generic badge](https://img.shields.io/badge/python-3.7-blue.svg)

`dup_file_finder.py`: Search for duplicate files based on extension. Utilizes [fleep](https://github.com/floyernick/fleep-py) to validate the file format.
Outputs the results to either a table txt file, or option for csv file.

```text
usage: dup_file_finder.py [-h] [-c] PATH EXT

Duplicate File Finder

positional arguments:
  PATH        directory path to scan
  EXT         file extension

optional arguments:
  -h, --help  show this help message and exit
  -c, --csv   option to send out to csv file
```

## Requirements

- colorama
- fleep
- prettytable
- requests
- tqdm

## Installation

```text
git clone https://github.com/dfirsec/dup_file_finder.git
cd dup_file_finder
pip install -r requirements.txt
```

## Example runs

Standard run with csv option...

```text
C:\dup_file_finder>python dup_img_finder.py c:\Users txt --csv
⮩ Scanning: c:\Users for 'txt' files
⮩ Processing: 24979 files [00:54, 457.15 files/s]
✔ Unique file hashes: 349 of 956
✔ Duplicate matches written to: C:\dup_file_finder\duplicate_matches.csv
```

Results with possible mismatches...

```text
C:\dup_file_finder>python dup_img_finder.py c:\Users\enduser tiff
⮩ Scanning: c:\Users for 'tiff' files
⮩ Processing: 25226 files [00:05, 4374.17 files/s]
✔ Unique file hashes: 1 of 2
✔ Duplicate matches written to: C:\dup_file_finder\duplicate_matches.txt
=======================================
✘ Possibly invalid 'tiff' file format:
c:\Users\enduser\computers.tiff
c:\Users\enduser\hello.tiff
```
