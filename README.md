# Duplicate File Finder

![Generic badge](https://img.shields.io/badge/python-3.8-blue.svg)

This script scans a directory tree and identifies duplicate files with a given file extension. It uses SHA256 hashing to compare the files and outputs the duplicate matches to a CSV file.

File signatures courtesy of fleep @ua-nick.

## Prerequisites

Python 3.8 or higher

## Installation

1. Clone the repository:

```text
git clone https://github.com/dfirsec/dup_file_finder.git
```

2. Navigate to the project directory:

```text
cd dup_file_finder
```

3. Install the dependencies using poetry:

```text
poetry install
```

## Usage

1. Create the virtual environment

```text
poetry shell
```

2. Run using the following commands:

```text
python dup_file_finder.py dirpath ext
```

- `dirpath`: The directory path to scan for duplicate files.
- `ext`: The file extension to scan for.

### Example

```text
python dup_file_finder.py /path/to/directory pdf
```

This will scan the specified directory for PDF files and identify duplicate matches. The results will be saved to a CSV file named duplicate_matches.csv in the results directory.

## Contributing

Contributions are welcome! If you find any issues or have suggestions for improvement, please create an issue or submit a pull request.

## License

This project is licensed under the MIT License.