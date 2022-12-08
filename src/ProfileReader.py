import csv
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Optional, Union

PathLike = Union[Path, str]

@dataclass
class Person:
    id: str
    profile_url: str
    page_source: Optional[str] = None
    exp_source: Optional[str] = None


def read_csv_for_scraping(filepath: PathLike, id_col: str, url_col: str) -> list[Person]:
    with open(filepath, "r", encoding="utf8") as csvfile:
        profiles = list(csv.DictReader(csvfile))

    person_list = []
    for profile in profiles:
        person = Person(
            id=profile[id_col], 
            profile_url=profile[url_col]
        )
        person_list.append(person)

    return person_list

def normalize_name(raw_name: str) -> str:
    bad_punctation = "`~!@#$%^*()_-+={[}]\\|:;\"'<>,?/" # keep & and . 
    raw_name = re.sub(r"(\u180B|\u200B|\u200C|\u200D|\u2060|\uFEFF)+", "", raw_name) # remove unicode whitespace
    raw_name = (
        raw_name.encode("ascii", "replace")
                .decode("utf-8")
                .lower() # lowercase
                .translate(str.maketrans("", "", bad_punctation)) # remove punctuation
                .strip() # strip extra whitespace
    )
    cleaned_name = " ".join(raw_name.split()) # normalize spaces to 1

    return cleaned_name

def normalize_company_name(raw_name: str) -> str:
    raw_name = normalize_name(raw_name)

    replace_mapper = {
        "&": "and"
    }
    for orig_word, new_word in replace_mapper.items():
        raw_name = raw_name.replace(orig_word, new_word)

    to_strip = {"pllc", "llc", "inc", "co", "company", "corp"}
    normalized_name = " ".join(word for word in raw_name.split() if word not in to_strip)
    
    return normalized_name
    