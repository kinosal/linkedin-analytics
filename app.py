"""Streamlit app to analyze LinkedIn posts."""

# Import from standard library
import logging
import pandas as pd

# Import from 3rd party libraries
import streamlit as st
import streamlit.components.v1 as components

# Import modules
import scrape as scr

# Configure logger
logging.basicConfig(format="\n%(asctime)s\n%(message)s", level=logging.INFO, force=True)


# Define functions
# @st.cache_data(ttl=60 * 60 * 24, show_spinner=False)
def analyze(
    login: str,
    password: str,
    user: str,
    since: str = "2024-01-01",
    until: str = "2025-01-01",
    include: list = ["urn", "time", "impressions", "reactions", "comments"],
):
    with spinner_placeholder:
        with st.spinner(
            "Please wait while your posts are being analyzed. "
            "This could take a minute..."
        ):
            linkedin = scr.LinkedInBrowser(headless=True)
            linkedin.login(login, password)
            st.session_state.analytics = pd.DataFrame(
                linkedin.get_post_analytics(user, since, until, include)
            )


# Configure Streamlit page and state
st.set_page_config(page_title="LinkedIn Analytics", page_icon="🤖")

if "analytics" not in st.session_state:
    st.session_state.analytics = pd.DataFrame()

# Force responsive layout for columns also on mobile
st.write(
    """<style>
    [data-testid="column"] {
        width: calc(50% - 1rem);
        flex: 1 1 calc(50% - 1rem);
        min-width: calc(50% - 1rem);
    }
    </style>""",
    unsafe_allow_html=True,
)

# Render Streamlit page
st.title("LinkedIn Post Analytics 2022")
st.markdown(
    """
        This mini-app allows you to analyze your LinkedIn post statistics for 2022, including the number of reactions, comments, and shares. It scrapes the LinkedIn post page, parses the HTML to extract the data, and displays the results in a table. Additionally, you can export the results to a CSV file.

        You need to provide your LinkedIn username and password to use this app since you need to log in to LinkedIn to access the post statistics page. The app will not store your credentials and will only use them to log in to LinkedIn for the duration of this session in order to to scrape the desired post analytics for you. However, I do not know if [Streamlit](https://streamlit.io) logs any of this.

        If you feel uncomfortable providing your credentials, you can run the underlying Python [script](https://github.com/kinosal/linkedin-analytics/blob/main/scrape.py) locally on your machine. Alternatively, you could try to use [Google Colab](https://colab.research.google.com/github/kinosal/linkedin-analytics/blob/main/notebook.ipynb) to run the script remotely in the cloud using a [Jupyter Notebook](https://jupyter.org/). However, I didn't get LinkedIn to allow me to log in with a headless browser using Colab. Please [let me know](mailto:nikolas@schriefer.me) if you do.
    """
)

login = st.text_input(label="LinkedIn Login (e.g. email)")
password = st.text_input(label="LinkedIn Password", type="password")
user = st.text_input(
    label="LinkedIn user to scrape (text after https://www.linkedin.com/in/"
)
st.button(
    label="Analyze posts",
    type="primary",
    on_click=analyze,
    args=(login, password, user),
)

spinner_placeholder = st.empty()

if len(st.session_state.analytics) > 0:
    st.markdown(
        f"Found {len(st.session_state.analytics)} posts with a total of "
        f"{st.session_state.analytics['impressions'].sum()} impressions, "
        f"{st.session_state.analytics['reactions'].sum()} reactions, and "
        f"{st.session_state.analytics['comments'].sum()} comments:"
    )

    # Inject CSS to hide index row from table
    hide_first_row = """
        <style>
        thead tr th:first-child {display:none}
        tbody th {display:none}
        </style>
    """
    st.markdown(hide_first_row, unsafe_allow_html=True)

    # Display urns as links and render table
    table = st.session_state.analytics.copy()
    table["urn"] = [
        f'<a target="_blank" href="https://www.linkedin.com/feed/update/{urn}">{urn}</a>'
        for urn in table["urn"]
    ]
    table.rename(
        columns={
            "urn": "urn (link to post)",
            "impressions": "impressions (active user only)"
        },
        inplace=True,
    )
    st.write(table.to_html(escape=False), unsafe_allow_html=True)

    # Add whitespace
    st.write("")

    st.download_button(
        label="Download CSV",
        data=st.session_state.analytics.to_csv(index=False).encode("utf-8"),
        file_name="posts.csv",
        mime="text/csv",
    )

    st.markdown("""---""")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            "**Other Streamlit apps by [@kinosal](https://twitter.com/kinosal)**"
        )
        st.markdown("[Tweet Generator](https://tweets.streamlit.app)")
        st.markdown("[Twitter Wrapped](https://twitter-likes.streamlit.app)")
        st.markdown("[Content Summarizer](https://web-summarizer.streamlit.app)")
        st.markdown("[Code Translator](https://english-to-code.streamlit.app)")
        st.markdown("[PDF Analyzer](https://pdf-keywords.streamlit.app)")
    with col2:
        st.write("If you like this app, please consider to")
        components.html(
            """
                <form action="https://www.paypal.com/donate" method="post" target="_top">
                <input type="hidden" name="hosted_button_id" value="8JJTGY95URQCQ" />
                <input type="image" src="https://pics.paypal.com/00/s/MDY0MzZhODAtNGI0MC00ZmU5LWI3ODYtZTY5YTcxOTNlMjRm/file.PNG" height="35" border="0" name="submit" title="Donate with PayPal" alt="Donate with PayPal button" />
                <img alt="" border="0" src="https://www.paypal.com/en_US/i/scr/pixel.gif" width="1" height="1" />
                </form>
            """,
            height=45,
        )
        st.write("so I can keep it alive. Thank you!")
