# Analyze LinkedIn posts

## Description

This is a simple script to analyze LinkedIn post statistics, including the number of reactions, comments, and shares. It scrapes the LinkedIn post page, parses the HTML to extract the statistics, and saves the results to a CSV file.

## Usage

1. Install dependencies using [Poetry](https://github.com/python-poetry/poetry) with `poetry install`
2. Add a `.env` file to source from with the following variables:
    - LOGINNAME (the email address you use to log in to LinkedIn)
    - PASSWORD (the password you use to log in to LinkedIn)
    - USERNAME (the username whose posts you'd like to scrape)
3. Run the script with `poetry run python scrape.py`
