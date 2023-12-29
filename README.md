# Analyze LinkedIn posts

## Description

This is a simple Python script to analyze LinkedIn post statistics, including the number of reactions, comments, and shares. It scrapes the LinkedIn post page, parses the HTML to extract the statistics, and saves the results to a CSV file.

Additionally, the script scrapes the reactors for each of the specified user's to identify their top fans as well as all of the hastags used in the posts to identify the most popular topics.

## Usage

1. Install dependencies using [Poetry](https://github.com/python-poetry/poetry) with `poetry install` (using Python 3.11)
2. Add a `.env` file to source from with the following variables:
    - LOGINNAME (the email address you use to log in to LinkedIn)
    - PASSWORD (the password you use to log in to LinkedIn)
3. Run the script with `poetry run python scrape.py --user <username>`
4. Optionally specify
    - `--since` as the date to scrape posts from (defaults to `2023-01-01`),
    - `--until` as the date to scrape posts until (defaults to `2024-01-01`),
    - `--reactors` to also scrape the reactors for each post (defaults to `False`)
    - `--hashtags` to also scrape the hashtags for each post (defaults to `False`)
    - `--headless` to run the script without a browser window (defaults to `True`, requires `False` to solve the login verification challenge)
5. Complete the login verification challenge if prompted

## Issues

I tried to run the script remotely using `notebook.ipynb`on [Google Colab](https://colab.research.google.com) and `app.py` on [Streamlit](https://streamlit.io). However, LinkedIn asks for a security verification on both environments and they don't support running a headful Selenium browser to manually solve it. If you have any ideas on how to get around this, please let me know.