#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pathlib import Path
import shutil
from datetime import datetime, timezone

from download import download
from reorganise import reorganise
from copy_matching_georefs import copy_matching_georefs
from copy_similar_georefs_gui import copy_similar_georefs_gui
from status import status
from src.airac import Airac
from src.utils import airac_to_path, get_team_avitab_zip_paths, download_zip

def is_georef_available(airac1, airac2):
    try:
        (url, zip_path, extract_dir) = get_team_avitab_zip_paths(airac1, airac2)  
        download_zip(url, zip_path)
        return True
    except:
        return False

def print_heading(msg):
    print("\n" '\033[4m' + msg + '\033[0m')

def build_prev_airac(airac_prev, airac_new, airac_prev_dir):
    if is_georef_available(airac_prev, airac_new):
        print(f"\nWARNING: Georef zip for {airac_prev}_{airac_new} already exists in TeamAvitab.")
        print(f"Does {airac_new} really need update?")
        print(f"Continuing anyway ...")
        
    print_heading(f"Download previous AIRAC {airac_prev} charts into {airac_prev_dir} ...")
    print(f"Cmdline equivalent : './scripts/download.py {airac_prev}'")
    download(str(airac_prev))

    print_heading(f"Reorganise charts in {airac_prev_dir} ...")
    print(f"Cmdline equivalent : './scripts/reorganise.py {airac_prev_dir.relative_to(Path.cwd())}'")
    reorganise(airac_prev_dir)

    print_heading("Copying hash matching georefs")
    print(f"from TeamAvitab avitab_georefs repo on github")
    print(f"  to {airac_prev_dir}")
    print(f"Cmdline equivalent : './scripts/copy_matching_georefs.py TeamAvitab {airac_prev_dir.relative_to(Path.cwd())}'")
    got_all_jsons = copy_matching_georefs("TeamAvitab", airac_prev_dir)
    print()
    
    if not got_all_jsons:
        print(f"\nIdeally, all georeference-able aerodrome charts in {airac_prev_dir}")
        print(f"should have had a georef json copied from {prev_georef_dir}")
        print(f"But the copy was incomplete")
        print(f"Please check AIRAC cycle and geoereference dir.")
        print(f"Or, if running an atypical use-case, you'll need to run the scripts individually")
        raise FileNotFoundError(f"Insufficient georef .json files for {airac_prev_dir}")

def start_update(airac_cycle):
    airac_new = Airac.from_identifier(airac_cycle)
    airac_prev = airac_new.get_previous()
    airac_new_dir = airac_to_path(airac_new)
    airac_prev_dir = airac_to_path(airac_prev)
    
    build_prev_airac(airac_prev, airac_new, airac_prev_dir)

    print_heading(f"Download new AIRAC {airac_new} charts into {airac_new_dir} ...")
    print(f"Cmdline equivalent : './scripts/download.py {airac_new}'")
    download(str(airac_new))

    print_heading(f"Reorganise charts in {airac_new_dir} ...")
    print(f"Cmdline equivalent : './scripts/reorganise.py {airac_new_dir.relative_to(Path.cwd())}'")
    reorganise(airac_new_dir)

    print_heading("Copying hash matching georefs")
    print(f"from {airac_prev_dir}")
    print(f"  to {airac_new_dir}")
    print(f"Cmdline equivalent : './scripts/copy_matching_georefs.py {airac_prev_dir.relative_to(Path.cwd())} {airac_new_dir.relative_to(Path.cwd())}'")
    got_all_jsons = copy_matching_georefs(airac_prev_dir, airac_new_dir)
    print()
    
    if got_all_jsons:
        return
        
    print_heading("Starting interactive UI to selectively copy georefs in similar PDFs")
    print(f"Cmdline equivalent : './scripts/copy_similar_georefs_gui.py {airac_prev_dir.relative_to(Path.cwd())} {airac_new_dir.relative_to(Path.cwd())}'")
    copy_similar_georefs_gui(airac_prev_dir, airac_new_dir)

    print_heading("Status:")
    print(f"Cmdline equivalent : './scripts/status.py {airac_new_dir.relative_to(Path.cwd())}'")
    status(airac_new_dir)


def guess_airac_cycle():
    curr_airac = Airac.from_instant(datetime.now(timezone.utc))
    next_airac = curr_airac.get_next()
    nextp1_airac = next_airac.get_next()
    print(f"Current AIRAC {curr_airac.description()}")
    print("UK NATS AIP should also have chart downloads for:")
    print(f"Next    AIRAC {next_airac.description()}")
    print(f"Next+1  AIRAC {nextp1_airac.description()}")

    print("TeamAvitab georefs available:")
    prev_airac = curr_airac.get_previous()
    prev_curr_avail = is_georef_available(prev_airac, curr_airac)
    print(f"Georefs for {prev_airac}_{curr_airac} {"" if prev_curr_avail else "not "}released")
    curr_next_avail = is_georef_available(curr_airac, next_airac)
    print(f"Georefs for {curr_airac}_{next_airac} {"" if curr_next_avail else "not "}released")
    next_nextp1_avail = is_georef_available(next_airac, nextp1_airac)
    print(f"Georefs for {next_airac}_{nextp1_airac} {"" if next_nextp1_avail else "not "}released")

    print()
    if next_nextp1_avail:
        nextp2_airac = nextp1_airac.get_next()
        print(f"All georefs up to date on TeamAvitab")
        print(f"Wait for NATS AIP to shift to AIRAC {next_airac.description()} for AIRAC {nextp2_airac} to be available")
        sys.exit(0)

    if curr_next_avail:
        return nextp1_airac
    elif prev_curr_avail:
        return next_airac
    else:
        print(f"Need to update to AIRAC {curr_airac}")
        print(f"No TeamAvitab georefs released that would georef previous AIRAC {prev_airac}")
        print(f"Download an alternative source of georefs (Avitab xplane.org forum) and run scripts individually")
        sys.exit(0)


def main() -> None:
    if len(sys.argv) > 2:
        print(f"Usage: {sys.argv[0]} [4digit_airac_id]")
        sys.exit(1)
        
    if len(sys.argv) == 2:
        airac = sys.argv[1]
    else:
        airac = str(guess_airac_cycle())
        print(f"Starting update for AIRAC {airac}")

    try:
        start_update(airac)
    except Exception as e:
        print(e)
    except KeyboardInterrupt:
        print("\nQuit - WARNING : charts may be left in an inconsistent state")
        
        
if __name__ == "__main__":
    main()
