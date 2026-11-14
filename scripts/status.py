#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO
from typing import NamedTuple
import re
import shutil

from src.utils import get_json_hash, get_pdf_hash, is_georefenceable, get_json_path, get_pdfs, airac_id_to_path


class StatusResults(NamedTuple):
    total_pdfs: int
    total_georeferenced: int
    total_missing_json: int
    total_hash_mismatches: int


def status(charts_dir_path, print_output=True) -> StatusResults:
    def print_if_output(*args):
        if print_output:
            print(*args)

    if not charts_dir_path.exists():
        raise FileNotFoundError(f"{charts_dir_path} does not exist")

    if not print_output:
        with redirect_stdout(StringIO()):
            pdfs = get_pdfs(charts_dir_path)
    else:
        pdfs = get_pdfs(charts_dir_path)
    if not pdfs:
        print_if_output(f"{charts_dir_path} has no pdfs")
        return StatusResults(0, 0, 0, 0)

    no_json_list = []
    hash_mismatch_count = 0
    for pdf in pdfs:
        json = get_json_path(pdf)
        if json.exists():
            pdf_hash = get_pdf_hash(pdf)
            json_hash = get_json_hash(json)
            if pdf_hash != json_hash or not json_hash:
                hash_mismatch_count += 1
                print_if_output(f"Hash mismatch for {pdf}")
                print_if_output(f"pdf  hash {pdf_hash}")
                print_if_output(f"json hash {json_hash}")
        else:
            no_json_list.append(pdf)
            
    if no_json_list:
        print_if_output("\nFailed to find georef .json files for the following pdfs:")
        last_pdf = Path()
        for pdf in no_json_list:
            if re.findall("/EG[A-Z]{2}_", str(pdf)) != re.findall("/EG[A-Z]{2}_", str(last_pdf)):
                print_if_output()
            print_if_output(pdf)
            last_pdf = pdf
        print_if_output(f"\n{len(no_json_list)} pdfs without georef .json")
    else:
        print_if_output("All aerodrome pdfs georeferenced")

    total_pdfs = len(pdfs)
    total_missing_json = len(no_json_list)
    return StatusResults(
        total_pdfs,
        total_pdfs - total_missing_json,
        total_missing_json,
        hash_mismatch_count,
    )


def main():
    if len(sys.argv) > 2:
        print("Usage : " + sys.argv[0] + " [charts_dir]")
        sys.exit(1)
        
    if len(sys.argv) == 2:
        charts_dir_paths = [Path(sys.argv[1])]
    else:
        charts_dir_paths = list((Path('.') / "charts").glob("EG_AIRAC_2[0-9][01][0-9]"))
    try:
        for charts_dir_path in charts_dir_paths:
            status(charts_dir_path)
            print("\n")
    except Exception as e:
        print(e)

if __name__ == "__main__":
    main()
