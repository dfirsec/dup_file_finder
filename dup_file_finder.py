"""Scans directory tree and returns duplicate entries."""

import argparse
import csv
import hashlib
import json
import sys
from collections.abc import Iterable
from functools import partial
from os import scandir
from pathlib import Path
from textwrap import TextWrapper

from colorama import Fore, init
from rich.console import Console
from rich.table import Table
from tqdm import tqdm
from utils.signature_checker import FileSignatureChecker

# Base directory path
root = Path(__file__).resolve().parent

# Initialize colorama
init()


class UnsupportedExtensionError(Exception):
    """Exception raised when an unsupported file extension is encountered."""

    def __init__(self: "UnsupportedExtensionError") -> None:
        """Return exception message."""
        super().__init__("Use only supported file extensions.")


class DupFinder:
    """Scans directory tree and returns duplicate entries."""

    def __init__(self: "DupFinder") -> None:
        """Initialize class instance variables."""
        self.filesobj = {}
        self.matches = {}
        self.unique = []
        self.mismatch = []
        self.dump_file = root.joinpath("results/duplicate_matches.csv")

        self.found = f"{Fore.GREEN}\u2714{Fore.RESET}"
        self.invalid = f"{Fore.RED}\u2716{Fore.RESET}"
        self.separator = f'{Fore.LIGHTBLUE_EX}{"-" * 70}{Fore.RESET}'

    def file_hash(self: "DupFinder", filepath: str, blocksize: int = 65536) -> str:
        """Returns a SHA256 hash of a file.

        Args:
            filepath (str): Path to file.
            blocksize (int, optional): Block size to read. Defaults to 65536.

        Returns:
            str: SHA256 hash of file.
        """
        hasher = hashlib.sha256()
        with open(filepath, "rb") as file_obj:
            for chunk in iter(partial(file_obj.read, blocksize), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def scantree(self: "DupFinder", basepath: str) -> Iterable[str]:
        """Recursively scans a directory tree.

        Args:
            basepath (str): Base directory path.

        Yields:
            Iterable[str]: Generator object containing file paths.
        """
        with scandir(basepath) as entries:
            for entry in entries:
                try:
                    if not entry.name.startswith(".") and entry.is_dir(follow_symlinks=False):
                        yield from self.scantree(entry.path)
                    else:
                        yield entry.path
                except PermissionError:
                    continue

    def load_known_extensions(self: "DupFinder") -> dict:
        """Loads known file extensions and their signatures from a JSON file.

        Returns:
            dict: Dictionary mapping file extensions to their signatures.
        """
        with open(root.joinpath("utils/file_signatures.json"), encoding="utf-8") as file_obj:
            data = json.load(file_obj)
            return {item["extension"]: item["signature"] for item in data}

    def scan_finder(self: "DupFinder", directory: str, extension: str) -> Iterable[str]:
        """Scans a directory tree for files with a given extension.

        Args:
            directory (str): Directory path to scan.
            extension (str): File extension to scan for.

        Yields:
            Iterable[str]: Generator object containing file paths.
        """
        processing = f"{Fore.CYAN}\u2BA9{Fore.RESET}"

        known = self.load_known_extensions()

        if extension in known:
            print(f"{processing} Scanning: {directory} for '{extension}' files")
            print(f"{processing} Getting file count...", sep=" ", end=" ")

            files = list(self.scantree(directory))
            filecounter = len(files)
            print(f"{filecounter:,} files")

            file_checker = FileSignatureChecker("", extension)
            for filepath in tqdm(
                files,
                total=filecounter,
                desc=f"{processing} Processing",
                ncols=90,
                unit=" files",
            ):
                dirpath = Path(filepath)
                if dirpath.suffix.strip(".") == extension:
                    file_checker.filepath = filepath
                    signature_match = file_checker.check_file()
                    if signature_match:
                        yield filepath
                    else:
                        self.mismatch.append(filepath)
        else:
            self.dump_extensions(list(known.keys()))

    def dump_extensions(self: "DupFinder", known_extensions: list) -> None:
        """Extracts file extensions from file_signatures.json and prints to console.

        Args:
            known_extensions (list): List of known file extensions.
            extension (str): File extension to scan for.
        """
        wrapper = TextWrapper(width=60)
        knownlist = wrapper.wrap(str(known_extensions))
        print("\n".join(knownlist))
        raise UnsupportedExtensionError()

    def file_processor(self: "DupFinder", workingdir: str, extension: str) -> None:
        """Processes files and returns a dictionary of file paths and hashes.

        Args:
            self (DupFinder): Instance of DupFinder class.
            workingdir (str): Directory path to scan.
            extension (str): File extension to scan for.
        """
        for filename in self.scan_finder(workingdir, extension):
            self.filesobj.update({filename: self.file_hash(filename).upper()})

    def find_duplicates(self: "DupFinder") -> None:
        """Finds duplicate files and saves to file.

        Args:
            self (DupFinder): Instance of DupFinder class.
        """
        for files, hashes in self.filesobj.items():
            self.matches.setdefault(hashes, []).append(files)

        with open(self.dump_file, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = ["File", "Hash"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for filehash, files in self.matches.items():
                if len(files) > 1:  # if file has more than 1 hash
                    for file in files:
                        if filehash:
                            writer.writerow({"File": file, "Hash": filehash})
                            self.unique.append(filehash)

    def dump_duplicates(self: "DupFinder") -> None:
        """Prints duplicate files to console and saves to file.

        Args:
            self (DupFinder): Instance of DupFinder class.
        """
        # Create a new table object and set the title
        table = Table(title="Duplicates")

        # Read the CSV file
        with open(self.dump_file) as csvfile:
            csv_reader = csv.reader(csvfile)
            header = next(csv_reader)  # Read the header row
            table.add_column(header[0], style="cyan", no_wrap=True)  # Add the first column as a header
            table.add_column(header[1], style="magenta")  # Add the second column as a header

            for row in csv_reader:
                table.add_row(*row)

        console = Console()
        console.print(table)

    def duplicate_results(self: "DupFinder", ext: str) -> None:
        """Prints duplicate and mismatch files to console."""
        self.dump_duplicates()  # dump duplicates to console
        print(f"{self.found} Unique file hashes: {len(set(self.unique))} of {len(self.unique)}")
        print(f"{self.found} Duplicate matches written to: {self.dump_file.resolve(strict=True)}")
        if self.mismatch:
            print(f"\nUnable to validate the file signature for the following '{ext}' files:\n{self.separator}")
            for num, filename in enumerate(self.mismatch, start=1):
                print(f"  [{num}] {filename}")


def parse_arguments() -> tuple[str, str]:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Duplicate File Finder")
    parser.add_argument("dirpath", help="directory path to scan")
    parser.add_argument("ext", help="file extension")
    args = parser.parse_args()

    dirpath = args.dirpath
    ext = args.ext

    return dirpath, ext


def main() -> None:
    """Main function."""
    dirpath, ext = parse_arguments()
    dup_finder = DupFinder()

    try:
        dup_finder.file_processor(dirpath, ext)
        dup_finder.find_duplicates()
    except KeyboardInterrupt:
        sys.exit(1)
    except UnsupportedExtensionError as exc:
        print("\n", exc, "\n")
        sys.exit(1)

    # print results if unique duplicates found
    if dup_finder.unique:
        dup_finder.duplicate_results(ext)
    else:
        print("\nNo duplicates found.")


if __name__ == "__main__":
    banner = rf"""{Fore.CYAN}
        ____              _______ __        _______           __
       / __ \__  ______  / ____(_) /__     / ____(_)___  ____/ /__  _____
      / / / / / / / __ \/ /_  / / / _ \   / /_  / / __ \/ __  / _ \/ ___/
     / /_/ / /_/ / /_/ / __/ / / /  __/  / __/ / / / / / /_/ /  __/ /
    /_____/\__,_/ .___/_/   /_/_/\___/  /_/   /_/_/ /_/\__,_/\___/_/
               /_/
    {Fore.RESET}"""

    print(banner)

    # check python version
    if sys.version_info < (3, 8):  # noqa: UP036
        print("Python 3.8 or higher is required.")
        sys.exit(1)

    main()
