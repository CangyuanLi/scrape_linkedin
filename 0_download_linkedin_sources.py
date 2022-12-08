# Imports

from dataclasses import dataclass
import json
import logging
from pathlib import Path
import random

import cutils
from selenium.common.exceptions import TimeoutException, WebDriverException
import wakepy

import src.LinkedinCrawler as LinkedinCrawler
import src.ProfileReader as ProfileReader
from src.ProfileReader import Person
from setup_vars import BASE_PATH, LINKEDIN_PATH, OUTPUT_DAT_PATH, PathLike

@dataclass(frozen=True)
class Account:
    id: int
    username: str
    password: str
    location: str
    server: str

    def __eq__(self, __o: object) -> bool:
        return self.id == __o.id

SECONDS_IN_HOUR = 3600
PAGE_FOLDER_PATH = OUTPUT_DAT_PATH / "Page_Sources"
EXP_FOLDER_PATH = OUTPUT_DAT_PATH / "Experience_Sources"

def load_linkedin_accounts(account_path: PathLike) -> list[Account]:
    with open(account_path) as f:
        profiles = json.loads(f.read())

    accounts = []
    for profile in profiles:
        account = Account(
            id = profile["profile_id"],
            username = profile["email"],
            password = profile["password"],
            location = profile["vpn_location"],
            server = profile["vpn_server"]
        )
        accounts.append(account)

    return accounts

@cutils.rate_limited(limit=45, period=SECONDS_IN_HOUR)
def download_page_source(
    crawler: LinkedinCrawler.Crawler,
    person: Person,
    page_folder: PathLike=PAGE_FOLDER_PATH,
    exp_folder: PathLike=EXP_FOLDER_PATH
):
    error = False
    try:
        crawler.visit_page(
            person, 
            download=True, 
            page_folder=page_folder,
            exp_folder=exp_folder
        )
    except (LinkedinCrawler.Error404, TimeoutException, WebDriverException) as e:
        error = True

    if error:
        logging.warning(
            f"Something went wrong, please check {person.id} ({person.profile_url})."
        )

def main():
    all_person_list = ProfileReader.read_csv_for_scraping(
        filepath=BASE_PATH / "ppp_pb_images/cung_lendio_second_tranche_employers/cung_employers_noimages.csv",
        id_col="id",
        url_col="linkedin_url"
    )

    visited_ids = []
    for file in Path(BASE_PATH / "CL_Page_Sources").glob("*.txt"):
        visited_ids.append(file.stem)

    all_person_list = [person for person in all_person_list if person.id not in visited_ids]

    chunked_person_list = cutils.random_chunk_seq(all_person_list)
    accounts = load_linkedin_accounts(LINKEDIN_PATH / "Credentials/profiles.json")

    with wakepy.keepawake(keep_screen_awake=True):
        for chunk in chunked_person_list:
            account = random.choice(accounts)
            crawler = LinkedinCrawler.Crawler(username=account.username, password=account.password)
            for person in chunk:
                download_page_source(
                    crawler=crawler, 
                    person=person,
                    page_folder=BASE_PATH / "CL_Page_Sources/",
                    exp_folder=BASE_PATH / "CL_Experience_Sources/"
                )


if __name__ == "__main__":
    main()
