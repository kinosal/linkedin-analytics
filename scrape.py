"""Scrape LinkedIn posts and their analytics."""

# Import from standard library
import re
import time
import datetime
import csv
import os
import argparse
import tkinter
from tkinter import messagebox
from collections import Counter

# Import from third party libraries
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import bs4


class LinkedIn:
    loginname = os.getenv("LOGINNAME")  # LinkedIn login name
    password = os.getenv("PASSWORD")  # LinkedIn password

    options = Options()
    options.add_argument("start-maximized")
    options.add_argument("disable-infobars")
    options.add_argument("--disable-extensions")
    # Headless only works if no security verification is required
    # options.add_argument("--headless")
    # Fixed window size needed for scroll in headless mode
    # options.add_argument("window-size=1920,1080")
    browser = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )
    # Indicate if global bottom of page is reached, i.e. there are no more posts to show
    global_bottom = False

    element_identifiers = {
        "impressions": {
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
        time.sleep(1)
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

    def extract_reactors(self, post_soup: bs4.element.Tag) -> list:
        """Extract names of users who reacted to a post."""
        # Open modal with reactors
        post_div_id = post_soup.get("id")
        button = self.browser.find_element(
            "xpath", f"//div[@id='{post_div_id}']//button"
        )
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

    def get_shown_post_analytics(self, include_reactors: bool = True) -> list:
        """Get analytics post HTML tags."""
        soup = bs4.BeautifulSoup(self.browser.page_source, features="lxml")
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
            if include_reactors:
                tags["reactors"] = self.extract_reactors(post_soup)  # Slow (see method)
            posts.append(tags)
            print(f"Extracted analytics for {tags['url']}")
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
            self, user: str, since: str, include_reactors: bool = True
    ) -> list:
        """Get analytics for all posts for a user since the specified date."""
        # Load page with posts
        self.browser.get(
            "https://www.linkedin.com/in/" + user + "/detail/recent-activity/shares/"
        )
        time.sleep(1)

        # Scroll to bottom of page to load all posts from specified date
        post_analytics = linkedin.get_shown_post_analytics(include_reactors=False)
        last_date = post_analytics[-1]["time"]
        while not self.global_bottom and last_date >= since:
            linkedin.show_more_posts()
            post_analytics = linkedin.get_shown_post_analytics(include_reactors=False)
            last_date = post_analytics[-1]["time"]
        print("Scrolled to show all posts since specified date")

        # Scroll back to top of page to start extracting analytics
        self.browser.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)

        # Get analytics for all posts
        if include_reactors:
            post_analytics = linkedin.get_shown_post_analytics(include_reactors=True)
        else:
            post_analytics = linkedin.get_shown_post_analytics(include_reactors=False)
        print("Scraped all posts")

        return [p for p in post_analytics if p["time"] >= since]

    def add_post_hashtags(self, posts: list) -> list:
        """Get hashtags for all posts."""
        for post in posts:
            url = (
                "https://www.linkedin.com/feed/update/urn:li:activity:"
                + post["url"].split(":")[-1]
            )
            self.browser.get(url)
            time.sleep(1)
            soup = bs4.BeautifulSoup(self.browser.page_source, features="lxml")
            post_text = soup.find(
                "div",
                attrs={"class": "update-components-text relative feed-shared-update-v2__commentary"},
            ).text
            post["hashtags"] = [h.lower() for h in re.findall(r"#(\w+)", post_text)]
            print(f"Added hashtags for {url}")
        print("Added all hashtags")
        return posts

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
    parser.add_argument(
        "--since", help="Date to start scraping from", default="2022-01-01"
    )
    parser.add_argument("--reactors", help="Include reactors?", default=True)
    args = parser.parse_args()

    linkedin = LinkedIn()
    linkedin.login()
    post_analytics = linkedin.get_post_analytics(
        user=args.user, since=args.since, include_reactors=args.reactors
    )
    post_analytics = linkedin.add_post_hashtags(post_analytics)

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
