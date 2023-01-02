"""Scrape LinkedIn posts and their analytics."""

# Import from standard library
import re
import time
import datetime
import csv
import os
import argparse
import sys
# tk does not work remotely on Streamlit
# import tkinter
# from tkinter import messagebox
from collections import Counter

# Import from third party libraries
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions
from webdriver_manager.chrome import ChromeDriverManager
import bs4


class LinkedInBrowser:
    def __init__(self, headless: bool) -> None:
        options = Options()
        if headless:
            self.headless = True
            options.add_argument("headless")
            # Fixed window size needed to scroll in headless mode
            options.add_argument("window-size=1920,1080")
        if "google.colab" in sys.modules:  # Use installed chromedriver in Google Colab
            self.browser = webdriver.Chrome("chromedriver", options=options)
        else:
            self.browser = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()), options=options
            )
        # Indicate if global bottom of page is reached,
        # i.e. there are no more posts to show
        self.global_bottom = False

        self.element_identifiers = {
            "post": {
                "tag": "div",
                "attrs": {
                    "class": re.compile(
                        ".*feed-shared-update-v2 feed-shared-update-v2--minimal-padding.*"
                    )
                },
            },
            "analytics": {
                "tag": "div",
                "attrs": {
                    "class": "social-details-social-activity update-v2-social-activity"
                },
            },
            "impressions": {  # only available for post by the logged in user
                "tag": "span",
                "attrs": {"class": "ca-entry-point__num-views t-14"},
            },
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
        }

    # @staticmethod
    # def messagebox(title, message):
    #     """Show a message box to highlight required user input."""
    #     root = tkinter.Tk()
    #     root.withdraw()
    #     messagebox.showinfo(title, message)
    #     root.update()

    def login(self, loginname: str = None, password: str = None):
        """Login to LinkedIn with Selenium."""
        loginname = loginname or os.getenv("LOGINNAME")
        password = password or os.getenv("PASSWORD")
        self.browser.get("https://www.linkedin.com/login")
        user_field = self.browser.find_element("id", "username")
        user_field.send_keys(loginname)
        password_field = self.browser.find_element("id", "password")
        password_field.send_keys(password)
        password_field.submit()
        time.sleep(1)
        if "security verification" in self.browser.title.lower():
            if self.headless:
                raise Exception(
                    "Security verification cannot be completed in headless browser."
                )
            # Wait for 2-step verification and login to be completed,
            # i.e. the feed page to be loaded
            # TODO: WebDriverWait has not been tested since
            # the 2-step verification has not shown recently
            WebDriverWait(self.browser, 600).until(
                expected_conditions.title_is("Feed | LinkedIn")
            )
            # Alternative: Show message box to explicitly finish 2-step verification
            # self.messagebox(
            #     title="Security verification",
            #     message="Finish 2-step verification in browser, then click OK.",
            # )
        print("Logged in")

    def extract(self, post_soup: bs4.element.Tag, tag: str):
        """Point to various methods to extract data from a post HTML tag."""
        if tag == "urn":
            return self.extract_urn(post_soup)
        elif tag == "time":
            return self.extract_time(post_soup)
        elif tag == "impressions":
            return self.extract_count(
                post_soup, **self.element_identifiers["impressions"]
            )
        elif tag == "reactions":
            return self.extract_count(
                post_soup, **self.element_identifiers["reactions"]
            )
        elif tag == "comments":
            return self.extract_count(post_soup, **self.element_identifiers["comments"])
        elif tag == "reactors":
            return self.extract_reactors(post_soup)
        elif tag == "hashtags":
            return self.extract_hashtags(post_soup)
        else:
            raise Exception(f"Unknown tag: {tag}")

    @staticmethod
    def extract_urn(post_soup: bs4.element.Tag) -> str:
        """Extract URL from a post HTML tag."""
        return post_soup.get("data-urn")

    @staticmethod
    def extract_time(post_soup: bs4.element.Tag) -> str:
        """Extract time from a post HTML tag, using the post ID."""
        urn = post_soup.get("data-urn")
        post_id = urn[-19:]
        binary_time = format(int(post_id), "b")[:41]
        time = datetime.datetime.fromtimestamp(int(binary_time, 2) / 1e3)
        return time.strftime("%Y-%m-%d %H:%M:%S")

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

    def extract_reactors(self, post_soup: bs4.element.Tag) -> list:
        """Extract names of users who reacted to a post."""
        # Open modal with reactors
        analytics_soup = post_soup.find(
            self.element_identifiers["analytics"]["tag"],
            attrs=self.element_identifiers["analytics"]["attrs"],
        )
        div_id = analytics_soup.get("id")
        button = self.browser.find_element("xpath", f"//div[@id='{div_id}']//button")
        button.click()
        time.sleep(1)

        try:
            modal = self.browser.find_element(
                "xpath",
                "//div[@class='artdeco-modal__content social-details-reactors-modal__content ember-view']",
            )
            modal_content = self.browser.find_element(
                "xpath", "//div[@class='scaffold-finite-scroll__content']"
            )
        except Exception:
            print("No modal found")

        # Scroll to bottom of modal to load all reactors
        last_modal_height = 0
        new_modal_height = modal_content.get_attribute("scrollHeight")
        while last_modal_height != new_modal_height:
            last_modal_height = new_modal_height
            self.browser.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight", modal
            )
            time.sleep(1)
            new_modal_height = modal_content.get_attribute("scrollHeight")

        modal_soup = bs4.BeautifulSoup(
            modal_content.get_attribute("innerHTML"), features="lxml"
        )

        # Extract names of reactors
        reactor_names = []
        for person in modal_soup.find_all(
            "div", attrs={"class": "artdeco-entity-lockup__title ember-view"}
        ):
            name = person.find("span", attrs={"aria-hidden": "true"})
            if name:
                reactor_names.append(name.text)

        # Close modal
        close_button = self.browser.find_element(
            "xpath", "//button[@aria-label='Dismiss']"
        )
        close_button.click()
        time.sleep(1)

        return reactor_names

    def extract_hashtags(self, post_urn: str) -> list:
        """Get hashtags for post."""
        self.browser.get("https://www.linkedin.com/feed/update/" + post_urn)
        time.sleep(1)
        soup = bs4.BeautifulSoup(self.browser.page_source, features="lxml")
        post_text = soup.find(
            "div",
            attrs={
                "class": "update-components-text relative feed-shared-update-v2__commentary"
            },
        ).text
        hashtags = [h.lower() for h in re.findall(r"#(\w+)", post_text)]
        print(f"Extracted hashtags for {post_urn}")
        return hashtags

    def get_shown_post_analytics(self, include: list) -> list:
        """Get analytics post HTML tags."""
        soup = bs4.BeautifulSoup(self.browser.page_source, features="lxml")
        post_soups = soup.find_all(
            self.element_identifiers["post"]["tag"],
            attrs=self.element_identifiers["post"]["attrs"],
        )
        posts = []
        for post_soup in post_soups:
            tags = {}
            for tag_type in [t for t in include if not t == "hashtags"]:
                tags[tag_type] = self.extract(post_soup, tag_type)
            posts.append(tags)
            if "urn" in tags:
                print(f"Extracted analytics for {tags['urn']}")
        # Hashtags are not shown on the page and need to be extracted separately
        # for reactors to be extractable by interacting with the browser
        if "hashtags" in include:
            for post in posts:
                post["hashtags"] = self.extract_hashtags(post["urn"])
        return posts

    def show_more_posts(self):
        """Show more posts by scrolling the page."""
        # Get current scroll height
        self.last_height = self.browser.execute_script(
            "return document.body.scrollHeight"
        )

        # Scroll down to bottom and wait to load more posts on page
        self.browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)

        # Calculate new scroll height and stop if at global bottom
        new_height = self.browser.execute_script("return document.body.scrollHeight")
        if new_height == self.last_height:
            self.global_bottom = True
            print("Reached global bottom, no more posts to show")
        else:
            self.last_height = new_height
            print("Scrolled to show more posts")

    def get_post_analytics(
        self,
        user: str,
        since: str,
        until: str = None,
        include: list = ["urn", "time", "impressions", "reactions", "comments"],
    ) -> list:
        """Get analytics for all posts for a user since the specified date."""
        # Load page with posts
        self.browser.get(
            "https://www.linkedin.com/in/" + user + "/recent-activity/shares/"
        )
        time.sleep(1)

        # Scroll to bottom of page to load all posts from specified date
        post_analytics = self.get_shown_post_analytics(include=["time"])
        if not post_analytics:
            print("No posts found")
            return []

        last_date = post_analytics[-1]["time"]
        while not self.global_bottom and last_date >= since:
            self.show_more_posts()
            post_analytics = self.get_shown_post_analytics(include=["time"])
            last_date = post_analytics[-1]["time"]
        print("Scrolled to show all posts since specified date")

        # Scroll back to top of page to start extracting analytics
        self.browser.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)

        # Get analytics for all posts
        post_analytics = self.get_shown_post_analytics(include=include)
        print("Scraped all posts")

        return [p for p in post_analytics if p["time"] >= since and p["time"] <= until]

    @staticmethod
    def top_n(posts: list, tag: str, n: int = 10) -> list:
        """Find top n tags, e.g. reactors or hashtags."""
        tags = []
        for post in posts:
            tags.extend(post[tag])
        counts = Counter(tags)
        return counts.most_common(n)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", help="LinkedIn user to scrape", required=True)
    parser.add_argument("--since", help="First date to scrape", default="2022-01-01")
    parser.add_argument("--until", help="Last date to scrape", default="2023-01-01")
    parser.add_argument("--reactors", help="Include reactors?", default=False)
    parser.add_argument("--hashtags", help="Include hashtags?", default=False)
    parser.add_argument("--headless", help="Run headless browser?", default=True)
    # Headless needs to be True to solve potential LinkedIn security verification
    args = parser.parse_args()
    include = ["urn", "time", "impressions", "reactions", "comments"]
    if args.reactors:
        include.extend(["reactors"])
    if args.hashtags:
        include.extend(["hashtags"])

    linkedin = LinkedInBrowser(headless=args.headless)
    linkedin.login()
    post_analytics = linkedin.get_post_analytics(
        user=args.user, since=args.since, until=args.until, include=include
    )
    if post_analytics:
        with open(f"{args.user}_posts.csv", "w") as f:
            writer = csv.DictWriter(f, fieldnames=post_analytics[0].keys())
            writer.writeheader()
            writer.writerows(post_analytics)

        if "reactors" in post_analytics[0].keys():
            top_reactors = linkedin.top_n(post_analytics, "reactors", n=10)
            print(f"Top reactors: {top_reactors}")

        if "hashtags" in post_analytics[0].keys():
            top_hashtags = linkedin.top_n(post_analytics, "hashtags", n=10)
            print(f"Top hashtags: {top_hashtags}")
