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
from prettytable import PrettyTable
from tqdm import tqdm

__author__ = "DFIRSec (@pulsecode)"
__version__ = "v0.0.9"
__description__ = "Search for duplicate files based on extension"

# Base directory paths
parent = Path(__file__).resolve().parent

# Holder for unique hashes and file mismatches
uniqhashes = []
mismatch = []

# Unicode Symbols and colors -  ref: http://www.fileformat.info/info/unicode/char/a.htm
init()
processing = f"{Fore.CYAN}\u2BA9{Fore.RESET}"
found = f"{Fore.GREEN}\u2714{Fore.RESET}"
notfound = f"{Fore.YELLOW}\u00D8{Fore.RESET}"
invalid = f"{Fore.RED}\u2716{Fore.RESET}"
sepline = f'{Fore.BLACK}{Style.BRIGHT}{"=" * 40}{Fore.RESET}'


def file_hash(file_path, blocksize=65536):
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
        self.file_dict = {}
        self.matches = {}
        self.csv_out = csv_out
        self.dump_file = None

    def scantree(self, basepath):
        """
        Recursively scans a directory and returns a list of all files in that directory.

        :param basepath: The path to the directory you want to scan
        """
        with scandir(basepath) as entries:
            for entry in entries:
                try:
                    if not entry.name.startswith(".") and entry.is_dir(
                        follow_symlinks=False
                    ):
                        yield from self.scantree(entry.path)
                    else:
                        yield entry.path
                except PermissionError:
                    continue

    def finder(self, directory, extension):
        """
        Scans a directory for files with a given extension, and if the file has the given extension,
        it yields the filepath.

        :param directory: The directory to scan
        :param extension: The file extension to search for
        """
        with open(parent.joinpath("known_exts.json"), encoding="utf-8") as file_obj:
            known = json.load(file_obj)

        if extension in known["extensions"]:
            print(f"{processing} Scanning: {directory} for '{extension}' files")
            print(f"{processing} Getting file count...", sep=" ", end=" ")
            filecounter = len(list(self.scantree(directory)))
            print(f"{filecounter:,} files")

            for filepath in tqdm(
                self.scantree(directory),
                total=filecounter,
                desc=f"{processing} Processing",
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
                            mismatch.append(filepath)
                    except FileNotFoundError:
                        continue
        else:
            self.extract_ext(known, extension)

    @staticmethod
    def extract_ext(known, extension):
        """
        Takes a dictionary and a string as arguments, and prints a message to the user if the string is
        not in the dictionary.

        :param known: This is the dictionary of known file extensions
        :param extension: The file extension of the file to be converted
        """
        wrapper = TextWrapper(width=60)
        knownlist = wrapper.wrap(str(known["extensions"]))
        print(
            f"{invalid}  File extension not a supported: {Fore.LIGHTMAGENTA_EX}{extension}{Fore.RESET}"
        )
        print(f"\nUse only the following:\n{sepline}")
        for ext in knownlist:
            print(ext)
        sys.exit()

    def processor(self, workingdir, extension):
        """
        Takes a working directory and an extension as arguments, and then it uses the finder function
        to find all files with that extension in the working directory.  Then it uses the file_hash
        function to hash each file and then adds the filename and the hash to the file_dict
        dictionary.

        :param workingdir: The directory to search for files
        :param extension: the file extension you want to search for
        """
        for filename in self.finder(workingdir, extension):
            self.file_dict.update({filename: file_hash(filename).upper()})

    def duplicates(self):
        """
        For each file in the file_dict, append the file to the matches dictionary, using the hash as the
        key.
        """
        for files, hashes in self.file_dict.items():
            self.matches.setdefault(hashes, []).append(files)

        if self.csv_out:
            self.dump_file = parent.joinpath("duplicate_matches.csv")
            with open(self.dump_file, "w", newline="", encoding="utf-8") as csvfile:
                fieldnames = ["File", "Hash"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for _hash, files in self.matches.items():
                    if len(files) > 1:  # if file has more than 1 hash
                        for _file in files:
                            if _hash:
                                writer.writerow({"File": _file, "Hash": _hash})
                                uniqhashes.append(_hash)
        else:
            self.dump_duplicates()

    def dump_duplicates(self):
        """
        Takes a list of files and hashes, and if there are more than one file with the same hash, it
        writes the file and hash to a text file.
        """
        self.dump_file = parent.joinpath("duplicate_matches.txt")
        ptable = PrettyTable(["File", "Hash"])
        ptable.align = "l"
        ptable.sortby = "Hash"

        for _hash, files in self.matches.items():
            if len(files) > 1:  # if file has more than 1 hash
                for _file in files:
                    ptable.add_row([_file, _hash])
                    uniqhashes.append(_hash)
        if uniqhashes:
            with open(self.dump_file, "w", encoding="utf-8") as output:
                output.write(ptable.get_string())


def main():
    parser = argparse.ArgumentParser(description="Duplicate File Finder")
    parser.add_argument("PATH", help="directory path to scan")
    parser.add_argument("EXT", help="file extension")
    parser.add_argument(
        "-c", "--csv", action="store_true", help="option to send out to csv file"
    )
    args = parser.parse_args()

    wdir = args.PATH
    ftype = args.EXT
    dup = DupFinder(args.csv)

    try:
        dup.processor(wdir, ftype)
        dup.duplicates()
    except KeyboardInterrupt:
        sys.exit()

    if uniqhashes:
        print(
            f"{found} Unique file hashes: {len(set(uniqhashes))} of {len(uniqhashes)}"
        )
        print(
            f"{found} Duplicate matches written to: {dup.dump_file.resolve(strict=True)}"
        )
        if mismatch:
            print(sepline)
            print(f"{invalid} Possibly invalid '{ftype}' file format?:")
            for num, filename in enumerate(mismatch, start=1):
                print(f"  [{num}] {filename}")
    else:
        print(f"{notfound} No duplicates found.")


if __name__ == "__main__":
    banner = rf"""
        ____              _______ __        _______           __
       / __ \__  ______  / ____(_) /__     / ____(_)___  ____/ /__  _____
      / / / / / / / __ \/ /_  / / / _ \   / /_  / / __ \/ __  / _ \/ ___/
     / /_/ / /_/ / /_/ / __/ / / /  __/  / __/ / / / / / /_/ /  __/ /
    /_____/\__,_/ .___/_/   /_/_/\___/  /_/   /_/_/ /_/\__,_/\___/_/
               /_/
                                                        {__version__}
                                                        {__author__}
    """

    print(f"{Fore.CYAN}{banner}{Fore.RESET}")

    # check python version
    if sys.version_info.major != 3 and sys.version_info.minor >= 7:
        print("Python 3.7 or higher is required.")
        sys.exit(
            f"Your Python Version: {sys.version_info.major}.{sys.version_info.minor}"
        )

    main()
