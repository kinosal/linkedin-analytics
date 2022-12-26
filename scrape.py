"""Scrape LinkedIn posts and their analytics."""

# Import from standard library
import re
import time
import datetime
import csv
import os
import tkinter
from tkinter import messagebox

# Import from third party libraries
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import bs4


class LinkedIn:
    loginname = os.getenv("LOGINNAME")  # LinkedIn login name
    password = os.getenv("PASSWORD")  # LinkedIn password
    username = os.getenv("USERNAME")  # LinkedIn username to scrape posts from

    options = Options()
    options.add_argument("start-maximized")
    options.add_argument("disable-infobars")
    options.add_argument("--disable-extensions")
    # options.add_argument("--headless")
    # Fixed window size needed for scroll in headless mode
    options.add_argument("window-size=1920,1080")
    browser = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )
    # Indicate if global bottom of page is reached, i.e. there are no more posts to show
    global_bottom = False

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

    @staticmethod
    def messagebox(title, message):
        """Show a message box to highlight required user input."""
        root = tkinter.Tk()
        root.withdraw()
        messagebox.showinfo(title, message)
        root.update()

    def login(self):
        """Login to LinkedIn with Selenium."""
        self.browser.get("https://www.linkedin.com/login")
        user_field = self.browser.find_element("id", "username")
        user_field.send_keys(self.loginname)
        password_field = self.browser.find_element("id", "password")
        password_field.send_keys(self.password)
        password_field.submit()
        if "security verification" in self.browser.title.lower():
            # Wait for 2-step verification to be completed
            self.messagebox(
                title="Security verification",
                message="Finish 2-step verification in browser, then click OK.",
            )
        print("Logged in")

    @staticmethod
    def extract_count(post_soup: bs4.element.Tag, tag: str, attrs: dict) -> int:
        """Extract number from a post HTML tag."""
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
    def extract_url(post_soup: bs4.element.Tag) -> str:
        """Extract URL from a post HTML tag."""
        div = post_soup.find("div", attrs={"class": "content-analytics-entry-point"})
        if not div:
            return ""
        return "https://www.linkedin.com" + div.find("a").get("href")

    @staticmethod
    def extract_time(post_soup: bs4.element.Tag) -> str:
        """Extract time from a post HTML tag, using the post ID."""
        div = post_soup.find("div", attrs={"class": "content-analytics-entry-point"})
        if not div:
            return ""
        post_id = div.find("a").get("href")[-20:-1]
        binary_time = format(int(post_id), "b")[:41]
        time = datetime.datetime.fromtimestamp(int(binary_time, 2) / 1e3)
        return time.strftime("%Y-%m-%d %H:%M:%S")

    def get_shown_post_analytics(self) -> list:
        """Get analytics post HTML tags."""
        soup = bs4.BeautifulSoup(linkedin.browser.page_source, features="lxml")
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

    def show_more_posts(self):
        """Show more posts by scrolling the page."""
        # Get current scroll height
        self.last_height = self.browser.execute_script(
            "return document.body.scrollHeight"
        )

        # Scroll down to bottom and wait to load more posts on page
        self.browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(4)

        # Calculate new scroll height and stop if at global bottom
        new_height = self.browser.execute_script("return document.body.scrollHeight")
        if new_height == self.last_height:
            self.global_bottom = True
            print("Reached global bottom, no more posts to show")
        else:
            self.last_height = new_height
            print("Scrolled to show more posts")

    def get_post_analytics(self, since: str) -> list:
        """Get analytics for all posts since the specified date."""
        self.browser.get(
            "https://www.linkedin.com/in/"
            + self.username
            + "/detail/recent-activity/shares/"
        )
        post_analytics = linkedin.get_shown_post_analytics()
        # TODO: Only extract time for checking if still greater than since
        last_date = post_analytics[-1]["time"]
        while not self.global_bottom and last_date >= since:
            linkedin.show_more_posts()
            post_analytics = linkedin.get_shown_post_analytics()
            last_date = post_analytics[-1]["time"]
        print("Scraped posts")
        return [p for p in post_analytics if p["time"] >= since]


if __name__ == "__main__":
    linkedin = LinkedIn()
    linkedin.login()
    post_analytics = linkedin.get_post_analytics(since="2022-01-01")
    with open("posts.csv", "w") as f:
        writer = csv.DictWriter(f, fieldnames=post_analytics[0].keys())
        writer.writeheader()
        writer.writerows(post_analytics)
