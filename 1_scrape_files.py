import concurrent.futures
import json

import cutils

import src.ProfileReader as ProfileReader
import src.LinkedinParser as LinkedinParser
from setup_vars import BASE_PATH

def get_all_sources():
    person_list = ProfileReader.read_csv_for_scraping(
        filepath=BASE_PATH / "ppp_pb_images/cung_lendio_second_tranche_employers/cung_employers_noimages.csv",
        id_col="id",
        url_col="linkedin_url"
    )

    return person_list

def parse_page_func(the_person):
    id = the_person.id

    page = LinkedinParser.PageParser(
        person=the_person,
        page_file=BASE_PATH / f"CL_Page_Sources/{id}.txt",
        exp_file=BASE_PATH / f"CL_Experience_Sources/{id}.txt"
    )
    res = page.parse_page()
    res["image_url"] = None

    filename = BASE_PATH / f"CL_Headshots/{id}.png"
    link = page.get_headshot_link()
    print(link)
    if link:
        valid_image = page.download_image(link=link, filename=filename)
        if valid_image:
            res["image_url"] = link

    with open(BASE_PATH / f"CL_Profiles/{id}.json", "w", encoding="utf-8") as f:
        json.dump(res, f, indent=4, sort_keys=True)

def try_parse_page(file):
    try:
        parse_page_func(file)
    except FileNotFoundError:
        pass

def main():
    files = get_all_sources()

    with concurrent.futures.ProcessPoolExecutor() as pool:
        pool.map(try_parse_page, files)


if __name__ == "__main__":
    cutils.time_func(lambda: main())

    