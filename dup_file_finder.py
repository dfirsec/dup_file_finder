import argparse
import csv
import hashlib
import json
import os
import sys
from pathlib import Path

import fleep
from colorama import Fore, Style, init
from prettytable import PrettyTable
from tqdm import tqdm

__author__ = "DFIRSec (@pulsecode)"
__version__ = "v0.0.7"
__description__ = "Search for duplicate files based on extension"

parent = Path(__file__).resolve().parent

# Holder for unique hashes and file mismatches
uniqhashes = []
mismatch = []

# Unicode Symbols and colors -  ref: http://www.fileformat.info/info/unicode/char/a.htm
init()
processing = f"{Fore.CYAN}\u2BA9{Fore.RESET}"
found = f"{Fore.GREEN}\u2714{Fore.RESET}"
notfound = f"{Fore.YELLOW}\u00D8{Fore.RESET}"
invalid = f"{Fore.RED}\u2718{Fore.RESET}"
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
    def file_finder(directory, extension):
        with open(parent.joinpath("known_exts.json")) as _file:
            known_ftypes = json.load(_file)

        if extension in known_ftypes["file_types"]:
            print(f"{processing} Scanning: {directory} for '{extension}' files")
            for root, _, files in tqdm(
                os.walk(directory), ascii=True, desc=f"{processing} Processing", ncols=80, unit=" files"
            ):
                for filename in files:
                    if filename.endswith("." + extension):
                        try:
                            with open(os.path.join(root, filename), "rb") as _file:
                                info = fleep.get(_file.read(128))
                            if info.extension_matches(extension):
                                yield os.path.join(root, filename)
                            else:
                                mismatch.append(os.path.join(root, filename))
                        except FileNotFoundError:
                            continue
        else:
            sys.exit(f"{invalid}  Oops, '{extension}' is not a supported file extension.")

    def file_processor(self, workingdir, filetype):
        for filename in self.file_finder(workingdir, filetype):
            try:
                self.file_dict.update({filename: file_hash(filename)})
            except Exception as error:
                return error

    def find_duplicates(self):
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
    parser.add_argument("WORKING_DIR", help="directory path to scan")
    parser.add_argument("FILE_TYPE", help="file type -- use file extension")
    parser.add_argument("-c", "--csv", action="store_true", help="option to send out to csv file")
    args = parser.parse_args()

    wdir = args.WORKING_DIR
    ftype = args.FILE_TYPE
    dup = DupFinder(args.csv)

    try:
        dup.file_processor(wdir, ftype)
        dup.find_duplicates()
    except KeyboardInterrupt:
        sys.exit()

    if uniqhashes:
        print(f"{found} Unique file hashes: {len(set(uniqhashes))} of {len(uniqhashes)}")
        print(f"{found} Duplicate matches written to: {dup.dump_file.resolve(strict=True)}")
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
    main()
