import argparse
import csv
import hashlib
import json
import os
import sys
from pathlib import Path
from textwrap import TextWrapper

import fleep
from colorama import Fore, Style, init
from prettytable import PrettyTable
from tqdm import tqdm

__author__ = "DFIRSec (@pulsecode)"
__version__ = "v0.0.8"
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


def file_hash(file_path):
    with open(file_path, "rb") as _file:
        md5_hash = hashlib.md5(_file.read(65536)).hexdigest()
    return md5_hash


class DupFinder(object):
    def __init__(self, csv_out):
        self.file_dict = dict()
        self.matches = dict()
        self.csv_out = csv_out
        self.dump_file = None

    @staticmethod
    def walkdir(folder):
        for root, _, files in os.walk(folder):
            for filename in files:
                yield Path(root).joinpath(filename).resolve()

    def finder(self, directory, extension):
        with open(parent.joinpath("known_exts.json")) as f:
            known = json.load(f)

        if extension in known["extensions"]:
            print(f"{processing} Scanning: {directory} for '{extension}' files")
            filecounter = 0
            for filepath in self.walkdir(directory):
                filecounter += 1

            for filepath in tqdm(
                self.walkdir(directory),
                total=filecounter,
                desc=f"{processing} Processing",
                ncols=90,
                unit=" files",
            ):
                p = Path(filepath)
                if p.suffix == f".{extension}":
                    try:
                        with open(filepath, "rb") as f:
                            data = fleep.get(f.read(128))
                        if data.extension_matches(extension):
                            yield filepath
                        else:
                            mismatch.append(filepath)
                    except FileNotFoundError:
                        continue
        else:
            wrapper = TextWrapper(width=60)
            knownlist = wrapper.wrap(str(known["extensions"]))
            print(
                f"{invalid}  File extension not a supported: {Fore.LIGHTMAGENTA_EX}{extension}{Fore.RESET}"
            )
            print(f"\nUse only the following:\n{sepline}")
            for extension in knownlist:
                print(extension)
            sys.exit()

    def processor(self, workingdir, extension):
        for filename in self.finder(workingdir, extension):
            try:
                self.file_dict.update({filename: file_hash(filename)})
            except Exception as error:
                return error

    def duplicates(self):
        for files, hashes in self.file_dict.items():
            self.matches.setdefault(hashes, []).append(files)

        if self.csv_out:
            self.dump_file = parent.joinpath(f"duplicate_matches.csv")
            with open(self.dump_file, "w", newline="") as csvfile:
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
            self.dump_file = parent.joinpath(f"duplicate_matches.txt")
            x = PrettyTable(["File", "Hash"])
            x.align = "l"
            x.sortby = "Hash"

            for _hash, files in self.matches.items():
                if len(files) > 1:  # if file has more than 1 hash
                    for _file in files:
                        x.add_row([_file, _hash])
                        uniqhashes.append(_hash)
            if uniqhashes:
                with open(self.dump_file, "w") as output:
                    output.write(x.get_string())


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
            print(f"{invalid} Possibly invalid '{ftype}' file format:")
            for num, item in enumerate(mismatch, start=1):
                print(f"  [{num}] {item}")
    else:
        print(f"{notfound} No duplicates found.")


if __name__ == "__main__":
    banner = fr"""
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
    if not sys.version_info.major == 3 and sys.version_info.minor >= 7:
        print("Python 3.7 or higher is required.")
        sys.exit(
            f"Your Python Version: {sys.version_info.major}.{sys.version_info.minor}"
        )

    main()
