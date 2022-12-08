# Imports

# stdlib
from dataclasses import dataclass
import decimal
import logging
from pathlib import Path
import random
import time
from typing import Optional, Union

# 3rd-party
from bs4 import BeautifulSoup
import requests

# Own

try:
    from ProfileReader import Person
except ModuleNotFoundError:
    from src.ProfileReader import Person

# Type Definitons

PathLike = Union[Path, str]

@dataclass
class EducDegree:
    degree: str = None
    field_of_study: str = None

@dataclass
class EducResult:
    school: str = None
    degree: str = None
    years: str = None

@dataclass
class EducYears:
    start_year: str = None
    end_year: str = None
    start_month: str = None
    end_month: str = None

@dataclass
class ExpResult:
    company: str = None
    company_id: str = None
    desc: str = None
    title: str = None
    years: str = None

@dataclass
class ExpYears:
    start_month: str = None
    end_month: str = None
    start_year: str = None
    end_year: str = None
    duration: str = None

@dataclass
class LocationInfo:
    city: str = None
    state: str = None
    country: str = None

# Globals

logging.basicConfig(level=logging.INFO)

# Functions

def random_delay(min_delay: int, max_delay: int):
    time.sleep(float(decimal.Decimal(random.randrange(min_delay, max_delay)) / 100))

def clean_string(string: str, sep: str=" ") -> str:
    string = string.strip()
    string = sep.join(string.split(sep))

    return string

# Classes

class PageParser():

    def __init__(
        self, 
        person: Person, 
        from_file: bool=True, 
        page_file: PathLike=None, 
        exp_file: PathLike=None
    ):
        if not from_file:
            page_soup, exp_soup = self.initialize_from_person_only()
        elif from_file:
            with open(page_file, "r", encoding="utf-8") as f:
                page_source = f.read()
            
            with open(exp_file, "r", encoding="utf-8") as f:
                exp_source = f.read()

            page_soup = self.soupify(page_source)
            exp_soup = self.soupify(exp_source)

        self.page_soup = page_soup
        self.exp_soup = exp_soup
        self.id = person.id
        self.url = person.profile_url

    def initialize_from_person_only(self, person: Person) -> tuple[BeautifulSoup, BeautifulSoup]:
        page_soup = self.soupify(person.page_source)
        exp_soup = self.soupify(person.exp_source)

        return page_soup, exp_soup

    @staticmethod
    def initialize_education_dictionary() -> dict:
        educ_dict = dict()

        educ_keys = {
            "degree", "end_month", "end_year", "field_of_study", "school", "start_month",
            "start_year", "raw_years", "raw_degree"
        }

        for key in educ_keys:
            educ_dict[key] = None

        return educ_dict

    @staticmethod
    def initialize_experience_dictionary() -> dict:
        exp_dict = dict()

        exp_keys = {
            "company", "company_id", "description", "raw_years", "end_month", "end_year", 
            "start_month", "start_year", "title"
        }
        
        for key in exp_keys:
            exp_dict[key] = None

        return exp_dict

    def initialize_master_dictionary(self) -> dict:
        data_dict = dict()

        master_string_keys = {
            "headline", "location" 
        }
        # "city", "country", "first_name", "last_name", "state", "original_url", "picture_filename"

        for key in master_string_keys:
            data_dict[key] = None

        data_dict["personid"] = self.id
        data_dict["linkedin_url"] = self.url
        # data_dict["educations"] = None

        return data_dict

    def soupify(self, page_source: str) -> BeautifulSoup:
        soup = BeautifulSoup(page_source, "lxml")

        return soup

    def get_name_from_title(self) -> Optional[str]:
        soup = self.page_soup

        try:
            raw_name = (
                soup.find("div", {"class": "mt2 relative"})
                    .find("div", {"class": "pv-text-details__left-panel"})
                    .find("h1", {"class": "text-heading-xlarge inline t-24 v-align-middle break-words"})
                    .get_text()
            )
        except AttributeError:
            return None

        name = clean_string(raw_name)

        return name

    def get_name_from_connect(self) -> Optional[str]:
        soup = self.page_soup
        stopwords = {"Invite", "to", "connect"}

        try:
            label_text = (
                soup.find("div", {"class": "pvs-profile-actions"})
                    .find("button", {"id": "ember99"})
                    .get_text()
            )
        except AttributeError:
            return None

        label_words = label_text.split(" ")
        name_list = [word for word in label_words if word not in stopwords]
        name = clean_string(" ".join(name_list))

        return name

    def get_name(self) -> str:
        name = self.get_name_from_title()

        if name is None:
            name = self.get_name_from_connect()

        if name is None:
            logging.warn("Could not find a name on the page. Did something go wrong?")

        return name

    def get_location(self) -> Optional[str]:
        soup = self.page_soup

        try:
            loc_string = (
                soup.find("div", {"class": "mt2 relative"})
                    .find("div", {"class": "pv-text-details__left-panel pb2"})
                    .find("span", {"class": "text-body-small inline t-black--light break-words"})
                    .get_text()
            )
        except AttributeError:
            return None

        cleaned_loc = clean_string(loc_string, sep=",")
        
        return cleaned_loc

    def get_headline_school(self) -> Optional[str]:
        soup = self.page_soup

        try:
            educ_string = (
                soup.find("div", {"class": "mt2 relative"})
                    .find("a", {"href": "#education"})
                    .find("div", {"aria-label": "Education"})
                    .get_text()
            )
        except AttributeError:
            return None

        cleaned_educ = clean_string(educ_string)

        return cleaned_educ

    def get_headline(self) -> str:
        soup = self.page_soup

        try:
            raw_headline = (
                soup.find("div", {"class": "mt2 relative"})
                    .find("div", {"class": "text-body-medium break-words"})
                    .get_text()
            )
        except AttributeError:
            return None

        headline = clean_string(raw_headline)
        
        return headline

    def get_headshot_link(self):
        soup = self.page_soup

        try:
            raw_link = (
                soup.find("div", {"class": "pv-profile-sticky-header-v2__container pv1"})
                    .find("img")
            )
            raw_link = raw_link["src"]
        except (AttributeError, TypeError):
            return None

        link = clean_string(raw_link)

        return link

    def download_image(self, link, filename) -> bool:
        valid_image = True
        try:
            img = requests.get(link)
            with open(filename, "wb") as f:
                f.write(img.content)
        except requests.exceptions.InvalidSchema:
            logging.warn(f"{self.id} has a blank profile picture.")
            valid_image = False

        random_delay(5, 10)

        return valid_image

    def __get_school(self, educ: BeautifulSoup) -> str:
        try:
            school = (
                educ.find("span", {"class": "mr1 hoverable-link-text t-bold"})
                    .find("span", {"class": "visually-hidden"})
                    .get_text()
            )
        except AttributeError:
            return None

        school = clean_string("".join(school).replace("\n", ""))

        return school

    def __get_degree(self, educ: BeautifulSoup):
        try:
            degree = (
                educ.find("span", {"class": "t-14 t-normal"})
                    .find("span", {"class": "visually-hidden"})
                    .get_text(strip=True)
            )
        except AttributeError:
            return None

        degree = clean_string("".join(degree).replace("\n", ""))

        return degree

    def __get_school_years(self, educ: BeautifulSoup) -> str:
        try:
            years = (
                educ.find("span", {"class": "t-14 t-normal t-black--light"})
                    .find("span", {"class": "visually-hidden"})
                    .get_text()
            )
        except AttributeError:
            return None

        years = clean_string("".join(years).replace("\n", ""))

        return years

    def get_education(self) -> list:
        soup = self.page_soup

        try:
            educ_list = (
                soup.find("div", {"id": "education", "class": "pv-profile-card-anchor"})
                    .parent
                    .find("ul", {"class": "pvs-list ph5 display-flex flex-row flex-wrap"})
                    .find_all("li", {"class": "artdeco-list__item pvs-list__item--line-separated pvs-list__item--one-column"})
            )
        except AttributeError:
            return None

        result_list = []
        for educ in educ_list:
            school = self.__get_school(educ)
            degree = self.__get_degree(educ)
            years = self.__get_school_years(educ)
            
            result = EducResult(
                school=school,
                degree=degree,
                years=years
            )

            result_list.append(result)

        return result_list

    def __get_experience_title(self, exp: BeautifulSoup):
        try:
            title = (
                exp.find("span", {"class": "mr1 t-bold"})
                   .find("span", {"class": "visually-hidden"})
                   .get_text()
            )
        except AttributeError:
            return None

        title = clean_string(title)

        return title

    def __get_experience_title_collapsed(self, exp: BeautifulSoup):
        try:
            title = (
                exp.find("span", {"class": "mr1 hoverable-link-text t-bold"})
                   .find("span", {"class": "visually-hidden"})
                   .get_text()
            )
        except AttributeError:
            return None

        title = clean_string(title)

        return title

    def __get_experience_company(self, exp: BeautifulSoup):
        try:
            company = (
                exp.find("span", {"class": "t-14 t-normal"})
                   .find("span", {"aria-hidden": "true"})
                   .get_text()
            )
        except AttributeError:
            return None

        company = clean_string(company)

        return company

    def __get_experience_company_collapsed(self, exp: BeautifulSoup):
        try:
            company = (
                exp.find("span", {"class": "mr1 hoverable-link-text t-bold"})
                   .find("span", {"aria-hidden": "true"})
                   .get_text()
            )
        except AttributeError:
            return None

        company = clean_string(company)

        return company
        
    def __get_experience_years(self, exp: BeautifulSoup):
        try:
            years = (
                exp.find("span", {"class": "t-14 t-normal t-black--light"})
                   .find("span", {"class": "visually-hidden"})
                   .get_text()
            )
        except AttributeError:
            return None

        years = clean_string(years)

        return years

    def __get_experience_description(self, exp: BeautifulSoup):
        try:
            desc = (
                exp.find("div", {"class": "pvs-list__outer-container"})
                   .find("span", {"class": "visually-hidden"})
                   .get_text()
            )
        except AttributeError:
            return None

        desc = clean_string(desc)
        if desc.split(":", 1)[0] == "Skills":
            desc = None

        return desc

    def __get_company_id(self, exp: BeautifulSoup):
        # here we try two methods of finding, preferring the first
        image_info = exp.find("a", {"class": "optional-action-target-wrapper display-flex"})
        if image_info is None:
            image_info = exp.find("a", {"class": "optional-action-target-wrapper"})

        try:
            comp_link = image_info["href"]
        except TypeError:
            return None

        comp_list = comp_link.split("/")
        if "search" in comp_link or comp_list[3] != "company":
            return None

        comp_id = int(clean_string(comp_list[-2]).rstrip("/"))

        return comp_id

    def get_experience(self):
        soup = self.exp_soup

        try:
            exp_list = (
                soup.find("div", {"class": "pvs-list__container"})
                    .find("ul", {"class": "pvs-list"})
                    .find_all("li", recursive=False)
            )
        except AttributeError:
            return [ExpResult()]

        result_list = []
        for exp in exp_list:
            collapsed_company = exp.find("li", {"class": "pvs-list__paged-list-item"})
            is_collapsed = False
            if collapsed_company is not None:
                is_collapsed = True
                res_list = exp.find_all("li", {"class": "pvs-list__paged-list-item"})
            else:
                text_info = exp.find("div", {"class": "display-flex flex-column full-width align-self-center"})
                res_list = [text_info]

            for text_info in res_list:
                result = ExpResult(
                    company_id=self.__get_company_id(exp),
                    desc=self.__get_experience_description(text_info),
                    years=self.__get_experience_years(text_info)
                )

                if is_collapsed:
                    result.company = self.__get_experience_company_collapsed(exp)
                    result.title = self.__get_experience_title_collapsed(text_info)
                else:
                    result.company = self.__get_experience_company(text_info)
                    result.title = self.__get_experience_title(text_info)

                result_list.append(result)

        return result_list

    @staticmethod
    def parse_degree(degree_info: str):
        if degree_info is None:
            return EducDegree()

        degree_list = degree_info.split(",", 1)

        res = EducDegree()

        res.degree = degree_list[0]
        try:
            res.field_of_study = clean_string(degree_list[1])
        except IndexError:
            pass
        
        return res

    @staticmethod
    def parse_educ_years(year_info: str):
        if year_info is None:
            return EducYears()

        allowed_numerics = {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "-", " "}
        year_info = clean_string(year_info)

        all_numeric = True
        for char in year_info:
            if char not in allowed_numerics:
                all_numeric = False
                break

        year_list = year_info.split("-")
        start = clean_string(year_list[0])

        try:
            end = clean_string(year_list[1])
        except IndexError:
            end = None

        res = EducYears()

        if all_numeric:
            start_year = start
            end_year = end
        else:
            start_list = start.split(" ")
            res.start_month = start_list[0]
            start_year = start_list[1]

            if end is not None:
                end_list = end.split(" ")
                res.end_month = end_list[0]
                end_year = end_list[1]

        res.start_year = start_year
        res.end_year = end_year

        return res

    def education_to_dict(self) -> list[dict]:
        educ_list = self.get_education()
        if educ_list is None:
            return educ_list

        educ_dict_list = []
        for educ in educ_list:
            educ_dict = self.initialize_education_dictionary()

            degree_res = self.parse_degree(educ.degree)
            year_res = self.parse_educ_years(educ.years)

            educ_dict["school"] = educ.school
            educ_dict["field_of_study"] = degree_res.field_of_study
            educ_dict["degree"] = degree_res.degree
            educ_dict["start_month"] = year_res.start_month
            educ_dict["end_month"] = year_res.end_month
            educ_dict["start_year"] = year_res.start_year
            educ_dict["end_year"] = year_res.end_year
            educ_dict["raw_years"] = educ.years
            educ_dict["raw_degree"] = educ.degree

            if all(value is None for value in educ_dict.values()):
                continue
            
            educ_dict_list.append(educ_dict)

        return educ_dict_list

    @staticmethod
    def parse_exp_years(year_info: str):
        if year_info is None or all(not char.isnumeric for char in year_info):
            return ExpYears()

        # replace unicode chars with "?"
        year_info = year_info.encode("ascii", "replace").decode("utf-8")
        parts = year_info.split("?", 1)

        if len(parts) == 1:
            return ExpYears()

        res = ExpYears()

        # Parse the first part of the string (start date - end date)
        years = parts[0]
        years_list = years.split("-")

        # starting date
        start_list = clean_string(years_list[0]).split(" ")
        if len(start_list) == 1:
            res.start_year = int(start_list[0])
        elif len(start_list) == 2:
            res.start_month = start_list[0]
            res.start_year = int(start_list[1])
        else:
            logging.warn(f"You have a bad string: {year_info}")

        if len(years_list) == 1:
            end_list = [None]
        else:
            end_list = clean_string(years_list[1]).split(" ")

        if len(end_list) == 1:
            res.end_year = end_list[0]
        elif len(end_list) == 2:
            res.end_month = end_list[0]
            res.end_year = int(end_list[1])
        else:
            logging.warn(f"You have a bad string: {year_info}")

        res.duration = clean_string(parts[1])

        return res

    def experience_to_dict(self):
        exp_list = self.get_experience()
        if exp_list is None:
            return None
        
        exp_dict_list = []
        for exp in exp_list:
            exp_dict = self.initialize_experience_dictionary()
            year_res = self.parse_exp_years(exp.years)

            exp_dict["company"] = exp.company
            exp_dict["company_id"] = exp.company_id
            exp_dict["description"] = exp.desc
            exp_dict["raw_years"] = exp.years
            exp_dict["start_month"] = year_res.start_month
            exp_dict["end_month"] = year_res.end_month
            exp_dict["start_year"] = year_res.start_year
            exp_dict["end_year"] = year_res.end_year
            exp_dict["duration"] = year_res.duration
            exp_dict["title"] = exp.title

            if all(value is None for value in exp_dict.values()):
                continue

            exp_dict_list.append(exp_dict)

        return exp_dict_list

    @staticmethod
    def parse_location(location_info: str):
        if location_info is None:
            return LocationInfo()

        res = LocationInfo()
        loc_list = location_info.split(",")
        res.city = loc_list[0]

        try:
            res.state = clean_string(loc_list[1])
        except IndexError:
            pass

        try:
            res.country = clean_string(loc_list[2])
        except IndexError:
            pass

        return res

    def parse_page(self):
        mast_dict = self.initialize_master_dictionary()

        loc = self.get_location()
        loc_res = self.parse_location(loc)

        mast_dict["city"] = loc_res.city
        mast_dict["state"] = loc_res.state
        mast_dict["country"] = loc_res.country
        mast_dict["educations"] = self.education_to_dict()
        mast_dict["experiences"] = self.experience_to_dict()
        mast_dict["name"] = self.get_name()
        mast_dict["location"] = loc
        mast_dict["headline"] = self.get_headline()

        return mast_dict
