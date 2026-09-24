#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pathlib import Path
from pprint import pprint
import re
import shutil
import csv

from src.airac import Airac
from src.utils import airac_to_path, get_json_hash, get_pdf_hash, is_georefenceable, get_json_path, get_pdfs, airac_to_path

csv_out = None

def print_change(old_name, old_num, new_name, new_num, desc):
    global csv_out
    print(f"{old_name},{old_num},{new_name},{new_num},{desc}")
    
def get_num_desc_dict(airac_path):
    csv_path = airac_path / "id_descriptive_map.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"{csv_path} does not exist")
        
    with open(csv_path, mode='r') as f:
        reader = csv.reader(f)
        d = {rows[1]:rows[0] for rows in reader}
    return d

def get_id_file_dict(path: Path) -> dict:
    id_file_dict = {}
    pdfs = get_pdfs(path)
    icao_section_index_regex = re.compile("(EG[A-Z]{2}_[1-8]_[0-3][0-9]).*.pdf$")
    for pdf in pdfs:
        icao_section_index = re.match(icao_section_index_regex, pdf.name).group(1)
        if icao_section_index in id_file_dict.keys():
            print(f"Warning - duplicate icao_section_index {icao_section_index}")
        id_file_dict[icao_section_index] = Path(pdf)
    return id_file_dict

def check_pair(csv_out, old, new, old_num_desc_map, new_num_desc_map):
    old_json_path = get_json_path(old)
    if not old_json_path.exists():
        raise FileNotFoundError(f"Old chart json {old_json_path} does not exist")
    with open(old_json_path, 'r') as file:
        old_json = file.read()
        
    new_json_path = get_json_path(new)
    if not new_json_path.exists():
        raise FileNotFoundError(f"New chart json {new_json_path} does not exist")
    with open(new_json_path, 'r') as file:
        new_json = file.read()

    if old_json == new_json:
        csv_out.writerow((old.name, old_num_desc_map[old.name], "", "", "identical pdf & georef"))
    else:
        old_json_no_hash = re.sub("\"hash\": \"[0-9a-f]+\"", "", old_json)
        new_json_no_hash = re.sub("\"hash\": \"[0-9a-f]+\"", "", new_json)
        if old.name == new.name:
            if old_json_no_hash == new_json_no_hash:
                csv_out.writerow((old.name, old_num_desc_map[old.name], "", new_num_desc_map[new.name], "similar pdf same georef"))
            else:
                csv_out.writerow((old.name, old_num_desc_map[old.name], "", new_num_desc_map[new.name], "different pdf recalibrated"))
        else:
            if old_json_no_hash == new_json_no_hash:
                raise ValueError(f"{old.name} -> {new.name} name change, different chart, same georef ! ?")
            else:
                csv_out.writerow((old.name,  old_num_desc_map[old.name], new.name, new_num_desc_map[new.name], "name change with different chart and georef"))


def changes(cycle_identifier: str) -> Path:
    global outfile
    
    if not cycle_identifier.isdigit() or len(cycle_identifier) != 4:
        raise ValueError("Invalid AIRAC cycle identifier. Must be a 4-digit number.")
    
    airac = Airac.from_identifier(cycle_identifier)
    prev_airac = airac.get_previous()
    airac_new_path = airac_to_path(airac)
    airac_old_path = airac_to_path(prev_airac)

    old_num_desc_map = get_num_desc_dict(airac_old_path)
    new_num_desc_map = get_num_desc_dict(airac_new_path)
    
    if not airac_new_path.exists():
        raise FileNotFoundError(f"New charts dir {airac_new_path} does not exist")
    if not airac_old_path.exists():
        raise FileNotFoundError(f"Previous charts dir {airac_old_path} does not exist")

    new_pdfs = get_id_file_dict(airac_new_path)
    old_pdfs = get_id_file_dict(airac_old_path)
    all_pdfs = old_pdfs | new_pdfs
    
    out_file = open(airac_new_path / "changes.csv", mode='w')
    csv_out = csv.writer(out_file)

    for id in sorted(all_pdfs):
        if id not in old_pdfs:
            csv_out.writerow(("", "", new_pdfs[id].name, new_num_desc_map[new_pdfs[id].name], "new chart"))
        elif id not in new_pdfs:
            csv_out.writerow((old_pdfs[id].name, old_num_desc_map[old_pdfs[id].name], "", "", "deprecated"))
        else:
            check_pair(csv_out, old_pdfs[id], new_pdfs[id], old_num_desc_map, new_num_desc_map)
            
    out_file.close()


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} 4digit_airac_id")
        sys.exit(1)
        
    airac_cycle = sys.argv[1]
    
    try:
        changes(airac_cycle)
    except Exception as e:
        print(e)

if __name__ == "__main__":
    main()
