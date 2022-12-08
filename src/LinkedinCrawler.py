# Imports

# stdlib
from dataclasses import dataclass
import decimal
import logging
from pathlib import Path
import pickle
import platform
import random
import re
import time
from typing import Literal, Optional, Union

# 3rd-party
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import InvalidCookieDomainException, NoSuchElementException, \
                                       TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# Own

try:
    from ProfileReader import Person
except ModuleNotFoundError:
    from src.ProfileReader import Person

# Type Definitons

PathLike = Union[Path, str]
KeyLike = Union[Keys, str]

class UnableToLoginException(Exception):
    pass

class Error404(Exception):
    pass

@dataclass
class Employee:
    input_company: str = None
    searched_company: str = None
    name: str = None
    sales_navigator_url: str = None
    profile_url: str = None
    currently_at_company: bool = None

# Globals

INITIAL_LOGIN_PAGE = "https://www.linkedin.com/"
SUCCESSFUL_LOGIN_PAGE = "https://www.linkedin.com/feed/?trk=homepage-basic_signin-form_submit"
LINUX_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"

# Functions

def random_delay(min_delay: int, max_delay: int):
    time.sleep(float(decimal.Decimal(random.randrange(min_delay, max_delay)) / 100))

# Classes

class Crawler():

    def __init__(self, username: str, password: str):
        base_path = Path(__file__).resolve().parents[0]
        self.base_path = base_path
        operating_system = platform.system()

        self.username = username
        self.password = password

        executable_path = ChromeDriverManager().install()
        chrome_options = webdriver.ChromeOptions()
        prefs = {"profile.default_content_setting_values.notifications": 2}
        chrome_options.add_experimental_option("prefs", prefs)

        if operating_system == "Linux":
            chrome_options.add_argument("--no-sandbox") # make sure to add this first
            chrome_options.add_argument("--headless")
            chrome_options.add_argument(f"user-agent = {LINUX_USER_AGENT}")
            chrome_options.binary_location = "/usr/bin/google-chrome"

        driver = webdriver.Chrome(executable_path, chrome_options=chrome_options)
        driver.set_window_position(0, 0)
        driver.set_window_size(1440, 960)
        self.driver = driver

        driver.get(INITIAL_LOGIN_PAGE)

        WebDriverWait(driver, 40).until(
            EC.element_to_be_clickable((By.ID, "session_key"))
        )

        self.load_cookie(base_path / "cookies.pkl")
        random_delay(5, 10)

        self.login()
        random_delay(200, 300)

        self.start_time = time.time()

    def reset_start_time(self):
        self.start_time = time.time()

    def get_time_active(self):
        return time.time() - self.start_time
    
    def load_cookie(self, cookies_path: PathLike):
        driver = self.driver
        driver.delete_all_cookies()

        cookies = pickle.load(open(cookies_path, "rb"))

        try:
            for cookie in cookies:
                driver.add_cookie(cookie)
        except InvalidCookieDomainException:
            logging.warning("Cookies were unable to be loaded.")

        driver.refresh()

    @staticmethod
    def human_type(element, keys: KeyLike, min_delay: int=10, max_delay: int=90):
        """Type in keys with random delay in between. This meant to mimic human typing.

        Args:
            element (_type_): the input box
            keys (KeyLike): any string or keyboard key
            min_delay (int, optional): lower bound on spacing. Defaults to 10.
            max_delay (int, optional): upper bound on spacing. Defaults to 90.
        """
        for char in keys:
            random_delay(min_delay, max_delay)
            element.send_keys(char)

    def send_username_on_initial_login_page(self):
        """Types in the username on the initial login page. Randomly make mistakes in order to
        mimic human behavior as closely as possible. Also, make sure that the mistakes are in
        random places, and happen a random amount of times.
        """
        driver = self.driver

        inputs = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!#$%&()*+,-./:;<=>?@[\\]^_`{|}~"
        split_index = random.randrange(len(self.username))
        username_part_1 = f"{self.username[:split_index]}{random.choice(inputs)}"
        username_part_2 = self.username[split_index:]
    
        num_chars = random.randint(3, 7)
        bad_inputs = random.choices(inputs, k=num_chars)
        
        username = driver.find_element("id", "session_key")

        self.human_type(username, username_part_1)
        self.human_type(username, [Keys.BACKSPACE])

        self.human_type(username, username_part_2)
        self.human_type(username, bad_inputs)
        self.human_type(username, [Keys.BACKSPACE for _ in range(len(bad_inputs))])

    def send_password(self, id_name: str):
        driver = self.driver

        password = driver.find_element("id", id_name)
        self.human_type(password, self.password)

    def click_sign_in_button(self):
        driver = self.driver

        sign_in_button = driver.find_element("xpath", '//*[@type="submit"]')
        random_delay(10, 20)
        sign_in_button.click()

    def _login(self) -> str:
        driver = self.driver

        driver.get(INITIAL_LOGIN_PAGE)

        self.send_username_on_initial_login_page()
        random_delay(6, 10)
        self.send_password(id_name="session_password")
        random_delay(14, 22)
        self.click_sign_in_button()

        random_delay(15, 20)

        return driver.current_url

    def login(self, max_tries: int=3):
        """Logins fail for unknown reasons, possibly due to variance in the human_type method.
        Try until max_tries to login, otherwise exit.

        Args:
            max_tries (int, optional): Defaults to 3.

        Raises:
            UnableToLoginException
        """
        tries = 0
        res_url = self._login()
        while res_url != SUCCESSFUL_LOGIN_PAGE and tries < max_tries:
            random_delay(300, 400)
            res_url = self._login()
            tries += 1
        
        if tries >= max_tries:
            raise UnableToLoginException("Max tries exceeded, unable to login.")

    def visit_page(
        self, 
        person: Person, 
        download: bool=True, 
        page_folder: PathLike=None,
        exp_folder: PathLike=None
    ) -> str:
        driver = self.driver
        page_url = person.profile_url
        id = person.id

        # lets get the original page
        driver.get(page_url)
        random_delay(900, 1100)
        self.wait_until_element_located(By.ID, "experience")
        page_source = driver.page_source

        # we also need get all the experiences, hidden under show all
        driver.get(f"{page_url}/details/experience/")
        random_delay(900, 1100)
        self.wait_until_element_located(By.ID, "profile-content")
        experience_source = driver.page_source

        person.page_source = page_source
        person.exp_source = experience_source

        if download:
            source_result = [
                {"source": page_source, "folder": page_folder},
                {"source": experience_source, "folder": exp_folder}
            ]

            for val in source_result:
                source = val["source"]
                target_folder = val["folder"]

                if target_folder is None:
                    target_folder = self.base_path

                if isinstance(target_folder, str):
                    target_folder = Path(target_folder)

                with open(target_folder / f"{id}.txt", "w", encoding="utf8") as f:
                    f.write(source)

        return person

    def search_company(self, company: str, how: Literal["current", "past"]) -> str:
        """On the LinkedIn SalesNavigator page, click on "add companies" and type in the company
        name to search. Type in the whole company name. In certain cases, LinkedIn will have a
        list of results to choose from. In that case, select the first one. Otherwise, simply press
        enter. 

        Args:
            company (str): company name
            how (Literal[current, past]): search through current or past company

        Returns:
            str: company name searched in LinkedIn, autocompleted or original
        """
        driver = self.driver

        id_text = f"//span[contains(text(), 'Expand {how.capitalize()} Company filter')]"
        company_child = driver.find_element(By.XPATH, id_text)
        company_button = company_child.find_element(By.XPATH, "..")
        company_button.click()

        company_selector = f"[placeholder='Add {how} companies']"

        self.wait_until_element_located(By.CSS_SELECTOR, company_selector)
        random_delay(3, 6)
        search_box = driver.find_element(By.CSS_SELECTOR, company_selector)
        self.human_type(search_box, company)

        search_box_suggestions_xpath = f"//ul[@aria-label='Add {how} companies'][@role='listbox']"
        try:
            first_match = (
                search_box.find_element(By.XPATH, search_box_suggestions_xpath)
                          .find_element(By.XPATH, "./li[@aria-selected='false']")
                          .find_element(By.CSS_SELECTOR, "button[aria-label^='Include']")
            )
            title = first_match.get_attribute("title")
            title_cleaned = title.encode("ascii", "replace").decode("utf-8")
            pattern = re.compile(r".*?\?(.*)\?.*")
            searched_company_name = re.match(pattern, title_cleaned).group(1)

            first_match.click()
        except NoSuchElementException:
            search_box.send_keys(Keys.ENTER)
            searched_company_name = company

        return searched_company_name

    def load_all_profiles(self, safe: bool=True):
        """On the SalesNavigator page, after entering in the company name, move to the right box
        where the profiles are. Not all profile information for the later profiles
        is loaded initially-- the name will be loaded, but not the link. Scroll down to each profile
        list element to load.

        Args:
            safe (bool, optional): After scrolling down, scroll back up. Defaults to True.
        """
        driver = self.driver

        random_delay(50, 60)
        self.wait_until_element_located(By.ID, "search-results-container")
        profile_container = (
            driver.find_element(By.ID, "search-results-container")
                  .find_elements(By.XPATH, ".//li[@class='artdeco-list__item pl3 pv3 ']")
        )
        for profile in profile_container:
            driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", 
                profile
            )
            random_delay(10, 15)
        random_delay(50, 60)

        if safe:
            for profile in reversed(profile_container):
                driver.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", 
                    profile
                )
                random_delay(10, 15)
            random_delay(50, 60)

    def wait_until_element_located(self, by: By, element: str, max_wait: int=30):
        driver = self.driver
        try:
            WebDriverWait(driver, max_wait).until(EC.presence_of_element_located((by, element)))
        except TimeoutException:
            if driver.current_url == "https://www.linkedin.com/404/":
                raise Error404
            else:
                raise TimeoutException

    def check_if_results_exist(self) -> bool:
        driver = self.driver

        try:
            driver.find_element(By.XPATH, "//*[contains(text(), 'No leads matched your search')]")
        except NoSuchElementException:
            return True

        return False
        
    def check_if_pages_left(self, soup: BeautifulSoup) -> bool:
        """If there are multiple result pages, the last page can have two different properties.
        Either the 'Next' button is greyed out (so we check for the 'disabled') property, or
        a 'no results' page is displayed.

        Args:
            soup (BeautifulSoup): the html of the page

        Returns:
            bool: if there are pages left
        """
        has_results = self.check_if_results_exist()
        next_button = soup.find("button", {"aria-label": "Next"})

        if has_results is False or next_button is None:
            return False

        try:
            next_button["disabled"]
        except KeyError:
            return True

        return False

    def get_profile_url_from_sales_page(self, sales_navigator_url: str) -> Optional[str]:
        driver = self.driver
        driver.get(sales_navigator_url)

        random_delay(50, 60)
        try:
            self.wait_until_element_located(By.CSS_SELECTOR, "section[data-x--lead-actions-bar='']")
        except TimeoutException:
            return None

        try:
            driver.find_element(By.CSS_SELECTOR, "section[data-x--lead-actions-bar='']") \
                  .find_element(By.CSS_SELECTOR, "button[data-x--lead-actions-bar-overflow-menu='']") \
                  .click()
        except NoSuchElementException:
            return None

        random_delay(30, 40)
        profile_url = driver.find_element(By.CSS_SELECTOR, "div[id='hue-web-menu-outlet']") \
                            .find_element(By.CSS_SELECTOR, "a[href^='https']") \
                            .get_attribute("href")

        return profile_url

    def get_user_links(self, company_i: str, company_s: str, current: bool) -> list[Employee]:
        driver = self.driver

        first_page_url = driver.current_url
        split_url = first_page_url.split("?", 1)
        first_part = split_url[0]
        second_part = split_url[1]

        random_delay(50, 60)
        profiles_exist = self.check_if_results_exist()
        if profiles_exist is False:
            return [Employee(input_company=company_i, currently_at_company=current)]
        
        employees = []
        i = 1
        pages_left = True
        while pages_left:
            if i >= 2:
                page_url = f"{first_part}?page={i}&{second_part}"
                driver.get(page_url)
                self.wait_until_element_located(By.CSS_SELECTOR, "button[aria-label='Next']")

            self.load_all_profiles()
            soup = BeautifulSoup(driver.page_source, "lxml")
            
            profile_list = soup.find("div", {"id": "search-results-container"}).find_all("li")
            for profile in profile_list:
                link_soup = profile.find(
                    "a", 
                    {"data-control-name": "view_lead_panel_via_search_lead_name"}
                )
                if link_soup is None:
                    continue
                
                raw_link = link_soup["href"]
                name = link_soup.find("span", {"data-anonymize": "person-name"}).get_text()
                employee_res = Employee(
                    input_company=company_i,
                    searched_company=company_s,
                    name=name,
                    sales_navigator_url=f"https://linkedin.com{raw_link.strip()}",
                    currently_at_company=current
                )
                employees.append(employee_res)

            pages_left = self.check_if_pages_left(soup)
            i += 1

        return employees

    def clear_sales_navigator_filters(self):
        driver = self.driver

        clear_all_selector = "[aria-label='Clear all filter values']"
        self.wait_until_element_located(By.CSS_SELECTOR, clear_all_selector)
        random_delay(30, 60)
        driver.find_element(By.CSS_SELECTOR, clear_all_selector).click()

    def initialize_sales_navigator_page(self):
        driver = self.driver

        driver.get("https://www.linkedin.com/sales/search/people")
        expand_button_aria = "[aria-label='Expand filter panel']"
        WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, expand_button_aria))
        )
        random_delay(30, 60)
        expand_button = driver.find_element(By.CSS_SELECTOR, expand_button_aria)
        expand_button.click()

    def visit_sales_navigator_page(self, company: str):
        searched_company = self.search_company(company, how="current")
        current_employees = self.get_user_links(
            company_i=company, 
            company_s=searched_company, 
            current=True
        )
        self.clear_sales_navigator_filters()

        searched_company = self.search_company(company, how="past")
        past_employees = self.get_user_links(
            company_i=company, 
            company_s=searched_company, 
            current=False
        )        
        self.clear_sales_navigator_filters()

        employees = current_employees + past_employees

        return employees
    