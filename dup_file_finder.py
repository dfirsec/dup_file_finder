import argparse
import csv
import hashlib
import json
import sys
from functools import partial
from os import scandir
from pathlib import Path
from textwrap import TextWrapper

import fleep
from colorama import Fore, Style, init
from rich.console import Console
from rich.table import Table
from tqdm import tqdm

# Base directory path
ROOT = Path(__file__).resolve().parent

# Holder for unique hashes and file mismatches
UNIQUE = []
MISMATCH = []

# Unicode Symbols and colors -  ref: http://www.fileformat.info/info/unicode/char/a.htm
init()
PROC = f"{Fore.CYAN}\u2BA9{Fore.RESET}"
FOUND = f"{Fore.GREEN}\u2714{Fore.RESET}"
NOTFOUND = f"{Fore.YELLOW}\u00D8{Fore.RESET}"
INVALID = f"{Fore.RED}\u2716{Fore.RESET}"
SEP = f'{Fore.BLACK}{Style.BRIGHT}{"=" * 40}{Fore.RESET}'


def file_hash(file_path: str, blocksize: int = 65536):
    """
    Reads the file in chunks of 65536 bytes, and updates the hash with each chunk

    :param file_path: The path to the file you want to hash
    :param blocksize: The size of the chunk of data to read from the file at a time, defaults to 65536
    (optional)
    :return: The hash of the file.
    """
    hasher = hashlib.sha256()
    with open(file_path, "rb") as file_obj:
        for chunk in iter(partial(file_obj.read, blocksize), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


class DupFinder:
    """Scans directory tree and returns duplicate entries."""

    def __init__(self, csv_out):
        self.file = {}
        self.matches = {}
        self.csv_out = csv_out
        self.dump_file = None

    def scantree(self, basepath: str):
        """
        Recursively scans a directory and returns a list of all files in that directory.

        :param basepath: The path to the directory you want to scan
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

    def finder(self, directory: str, extension: str):
        """
        Scans a directory for files with a given extension, and if the file has the given extension,
        it yields the filepath.

        :param directory: The directory to scan
        :param extension: The file extension to search for
        """
        with open(ROOT.joinpath("known_exts.json"), encoding="utf-8") as file_obj:
            known = json.load(file_obj)

        if extension in known["extensions"]:
            print(f"{PROC} Scanning: {directory} for '{extension}' files")
            print(f"{PROC} Getting file count...", sep=" ", end=" ")
            filecounter = len(list(self.scantree(directory)))
            print(f"{filecounter:,} files")

            for filepath in tqdm(
                self.scantree(directory),
                total=filecounter,
                desc=f"{PROC} Processing",
                ncols=90,
                unit=" files",
            ):
                _path = Path(filepath)
                if _path.suffix == f".{extension}":
                    try:
                        with open(filepath, "rb") as file_obj:
                            data = fleep.get(file_obj.read(128))
                        if data.extension_matches(extension):
                            yield filepath
                        else:
                            MISMATCH.append(filepath)
                    except FileNotFoundError:
                        continue
        else:
            self.extract_ext(known, extension)

    def extract_ext(self, known: dict, extension: str):
        """
        Takes a dictionary and a string as arguments, and prints a message to the user if the string is
        not in the dictionary.

        :param known: This is the dictionary of known file extensions
        :param extension: The file extension of the file to be converted
        """
        wrapper = TextWrapper(width=60)
        knownlist = wrapper.wrap(str(known["extensions"]))
        print(f"{INVALID}  File extension not a supported: {Fore.LIGHTMAGENTA_EX}{extension}{Fore.RESET}")
        print(f"\nUse only the following:\n{SEP}")
        for ext in knownlist:
            print(ext)
        sys.exit()

    def processor(self, workingdir: str, extension: str):
        """
        Takes a working directory and an extension as arguments, and then it uses the finder function
        to find all files with that extension in the working directory.  Then it uses the file_hash
        function to hash each file and then adds the filename and the hash to the file_dict
        dictionary.

        :param workingdir: The directory to search for files
        :param extension: the file extension you want to search for
        """
        for filename in self.finder(workingdir, extension):
            self.file.update({filename: file_hash(filename).upper()})

    def duplicates(self):
        """
        For each file in the file_dict, append the file to the matches dictionary, using the hash as the
        key.
        """
        for files, hashes in self.file.items():
            self.matches.setdefault(hashes, []).append(files)

        if self.csv_out:
            self.dump_file = ROOT.joinpath("duplicate_matches.csv")
            with open(self.dump_file, "w", newline="", encoding="utf-8") as csvfile:
                fieldnames = ["File", "Hash"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for _hash, files in self.matches.items():
                    if len(files) > 1:  # if file has more than 1 hash
                        for _file in files:
                            if _hash:
                                writer.writerow({"File": _file, "Hash": _hash})
                                UNIQUE.append(_hash)
        else:
            self.dump_duplicates()

    def dump_duplicates(self):
        """
        Takes a list of files and hashes, and if there are more than one file with the same hash, it
        writes the file and hash to a text file.
        """
        self.dump_file = ROOT.joinpath("duplicate_matches.txt")

        console = Console(record=True)
        table = Table(title="Duplicates")
        table.add_column("File", style="cyan", no_wrap=True)
        table.add_column("Hash", style="magenta")

        for _hash, files in self.matches.items():
            if len(files) > 1:  # if file has more than 1 hash
                for _file in files:
                    table.add_row(_file, _hash)
                    UNIQUE.append(_hash)
        if UNIQUE:
            console.print(table)
            console.save_text(str(self.dump_file))


def main():
    """
    Takes a directory path and file extension as arguments, then finds all files with that extension
    in the directory and its subdirectories, and then finds all duplicate files by comparing their
    hashes
    """
    parser = argparse.ArgumentParser(description="Duplicate File Finder")
    parser.add_argument("PATH", help="directory path to scan")
    parser.add_argument("EXT", help="file extension")
    parser.add_argument("-c", "--csv", action="store_true", help="option to send out to csv file")
    args = parser.parse_args()

    wdir = args.PATH
    ftype = args.EXT
    dup = DupFinder(args.csv)

    try:
        dup.processor(wdir, ftype)
        dup.duplicates()
    except KeyboardInterrupt:
        sys.exit()

    if UNIQUE:
        print(f"{FOUND} Unique file hashes: {len(set(UNIQUE))} of {len(UNIQUE)}")
        print(f"{FOUND} Duplicate matches written to: {dup.dump_file.resolve(strict=True)}")
        if MISMATCH:
            print(SEP)
            print(f"{INVALID} Possibly invalid '{ftype}' file format?:")
            for num, filename in enumerate(MISMATCH, start=1):
                print(f"  [{num}] {filename}")
    else:
        print(f"{NOTFOUND} No duplicates found.")


if __name__ == "__main__":
    BANNER = r"""
        ____              _______ __        _______           __
       / __ \__  ______  / ____(_) /__     / ____(_)___  ____/ /__  _____
      / / / / / / / __ \/ /_  / / / _ \   / /_  / / __ \/ __  / _ \/ ___/
     / /_/ / /_/ / /_/ / __/ / / /  __/  / __/ / / / / / /_/ /  __/ /
    /_____/\__,_/ .___/_/   /_/_/\___/  /_/   /_/_/ /_/\__,_/\___/_/
               /_/
    """

    print(f"{Fore.CYAN}{BANNER}{Fore.RESET}")

    # check python version
    if sys.version_info.major != 3 and sys.version_info.minor >= 8:
        print("Python 3.8 or higher is required.")

    main()
