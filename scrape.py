"""Scrape LinkedIn posts and their analytics."""

# Import from standard library
import re
import time
import datetime
import csv
import os

# Import from third party libraries
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup


class LinkedIn:
    loginname = os.getenv("LOGINNAME")
    password = os.getenv("PASSWORD")
    username = os.getenv("USERNAME")

    options = Options()
    options.add_argument("start-maximized")
    options.add_argument("disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument("--headless")
    # Fixed window size needed for scroll in headless mode
    options.add_argument("window-size=1920,1080")
    browser = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )

    element_identifiers = {
        "reactions": {
            "tag": "li",
            "attrs": {
                "class": "social-details-social-counts__item social-details-social-counts__reactions social-details-social-counts__reactions--with-social-proof"
            },
        },
        "comments": {
            "tag": "li",
            "attrs": {
                "class": "social-details-social-counts__item social-details-social-counts__comments social-details-social-counts__item--with-social-proof"
            },
        },
        "impressions": {
            "tag": "span",
            "attrs": {"class": "ca-entry-point__num-views t-14"},
        },
    }

    def login(self):
        self.browser.get("https://www.linkedin.com/login")
        user_field = self.browser.find_element("id", "username")
        user_field.send_keys(self.loginname)
        password_field = self.browser.find_element("id", "password")
        password_field.send_keys(self.password)
        password_field.submit()

    @staticmethod
    def extract_count(post_soup, tag, attrs):
        tag = post_soup.find(tag, attrs=attrs)
        if not tag:
            return 0
        list_of_matches = re.findall("[,0-9]+", str(tag))
        last_string = list_of_matches.pop()
        without_comma = last_string.replace(",", "")
        # Add 1 if a user name "and" an added number are displayed
        if re.search(re.compile(r"\band\b"), str(tag)):
            return int(without_comma) + 1
        return int(without_comma)

    @staticmethod
    def extract_url(post_soup) -> str:
        div = post_soup.find("div", attrs={"class": "content-analytics-entry-point"})
        if not div:
            return ""
        return "https://www.linkedin.com" + div.find("a").get("href")

    @staticmethod
    def extract_time(post_soup):
        div = post_soup.find("div", attrs={"class": "content-analytics-entry-point"})
        if not div:
            return ""
        post_id = div.find("a").get("href")[-20:-1]
        binary_time = format(int(post_id), "b")[:41]
        time = datetime.datetime.fromtimestamp(int(binary_time, 2) / 1e3)
        return time.strftime("%Y-%m-%d %H:%M:%S")

    def get_post_analytics(self):
        soup = BeautifulSoup(linkedin.browser.page_source, features="lxml")
        post_soups = soup.find_all(
            "div",
            attrs={"class": "social-details-social-activity update-v2-social-activity"},
        )
        posts = []
        for post_soup in post_soups:
            tags = {}
            tags["url"] = self.extract_url(post_soup)
            if not tags["url"]:
                continue
            tags["time"] = self.extract_time(post_soup)
            for tag_type in self.element_identifiers:
                tags[tag_type] = self.extract_count(
                    post_soup,
                    self.element_identifiers[tag_type]["tag"],
                    self.element_identifiers[tag_type]["attrs"],
                )
            posts.append(tags)
        return posts

    def show_posts(self, n_posts):
        self.browser.get(
            "https://www.linkedin.com/in/"
            + self.username
            + "/detail/recent-activity/shares/"
        )

        # Calculate number of necessary scrolls (5 posts per scroll)
        n_scrolls = -(-n_posts // 5)

        # Get current scroll height
        last_height = self.browser.execute_script("return document.body.scrollHeight")

        for scroll in range(n_scrolls):
            # Scroll down to bottom
            self.browser.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )
            # Wait to load page
            time.sleep(4)
            # Calculate new scroll height and stop if at global bottom
            new_height = self.browser.execute_script(
                "return document.body.scrollHeight"
            )
            if new_height == last_height:
                break
            last_height = new_height


if __name__ == "__main__":
    linkedin = LinkedIn()
    linkedin.login()
    print("Logged in")
    linkedin.show_posts(n_posts=50)
    print("Scrolled to show posts")
    post_analytics = linkedin.get_post_analytics()
    print("Scraped posts")
    with open("posts.csv", "w") as f:
        writer = csv.DictWriter(f, fieldnames=post_analytics[0].keys())
        writer.writeheader()
        writer.writerows(post_analytics)
