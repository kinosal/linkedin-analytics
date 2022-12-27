# Analyze LinkedIn posts

## Description

This is a simple script to analyze LinkedIn post statistics, including the number of reactions, comments, and shares. It scrapes the LinkedIn post page, parses the HTML to extract the statistics, and saves the results to a CSV file.

Additionally, the script scrapes the reactors for each of the specified user's to identify their top fans as well as all of the hastags used in the posts to identify the most popular topics.

## Usage

1. Install dependencies using [Poetry](https://github.com/python-poetry/poetry) with `poetry install`
2. Add a `.env` file to source from with the following variables:
    - LOGINNAME (the email address you use to log in to LinkedIn)
    - PASSWORD (the password you use to log in to LinkedIn)
3. Run the script with `poetry run python scrape.py --user <username>`
(optionally specify `--since` as the date to scrape posts from - defaults to `2022-01-01` - and/or `--reactors` if to scrape the reactors for each post, too - defaults to `True`)
4. Complete the login verification challenge if prompted
