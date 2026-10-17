import csv
import glob
from datetime import datetime
import difflib

def test():
    search_dir = "data-pipeline/output/parsed_licenses/*.csv"
    files = glob.glob(search_dir)
    print(f"Found {len(files)} files.")
    
    all_names = set()
    for file in files:
        with open(file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get('ТЗААН-ийн нэр', '')
                if name:
                    all_names.add(name.strip())
                    
    print(f"Found {len(all_names)} unique companies.")
    company_name = "нартдизайн"
    matches = difflib.get_close_matches(company_name.upper(), [n.upper() for n in all_names], n=3, cutoff=0.6)
    print(f"Matches for '{company_name}': {matches}")

test()
