import requests, os, json
import logging
import streamlit as st
from google import genai
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from models import Summarizer
from datetime import datetime
from typing import List

load_dotenv()

# Logging setup
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/app.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(module)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d-%H-%M-%S",
    filemode="a"
)
logger = logging.getLogger(__name__)

# Persistent cache
CACHE_FILE = "cache.json"
BASE_URL = "https://news.ycombinator.com"

# Helper functions
def _load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {}

def _save_cache(cache: dict):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

def get_or_analyze(url: str, title: str, api_key: str) -> str:
    '''
    Function to check if url to fetch is present in cache or not.
    '''
    cache = _load_cache()
    if url in cache:
        logger.info(f"Cache hit: {url}")
        # st.info(f"Loaded from cache: {url}")
        st.session_state.cache_log.append(url)
        return cache[url]

    logger.info(f"Cache miss, analyzing: {url}")
    result = gemini_completions(url, api_key)
    formatted = format_result(title, url, result)
    cache[url] = formatted
    _save_cache(cache)
    logger.info(f"Saved to cache: {url}")
    return formatted

def get_page_title(url: str) -> str:
    '''
    Helper function to fetch title/heading from the URL
    '''
    try:
        html = read_data_url(url)
        soup = BeautifulSoup(html, "html.parser")
        title = soup.find("title")
        return title.get_text().strip() if title else url
    except Exception:
        return url

# Core functions
def read_data_url(url: str) -> str:
    logger.debug(f"Fetching URL: {url}")
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    logger.debug(f"Fetched {len(response.text)} chars from {url}")
    return response.text

def get_top_posts(n: int = 5, base_url: str='') -> List[dict]:
    logger.info(f"Fetching top {n} posts from {base_url}")
    response = requests.get(base_url, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    posts = []
    titles = soup.select(".titleline > a")
    discussion_links = soup.select("span.subline > a[href^='item?id=']")

    for title_tag, disc_tag in zip(titles, discussion_links):
        if len(posts) == n:
            break
        href = disc_tag["href"]
        if href.startswith("item?id="):
            href = f"{base_url}/{href}"
        posts.append({"title": title_tag.get_text(), "url": href})
    logger.info(f"Found {len(posts)} posts from {base_url}")

    return posts

def gemini_completions(url: str, api_key: str) -> Summarizer:
    logger.info(f"Calling Gemini for summarizing {url}")
    client = genai.Client(api_key=api_key)
    contents = read_data_url(url)
    prompt = (
        "For the given Hacker News discussion page HTML, extract the comments and community discussion. "
        "Provide a detailed analysis covering: the story summary, key themes being debated, "
        "notable insights from the comments, overall community sentiment, and controversy level. "
        f"Here is the html content: {contents}"
    )
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_json_schema": Summarizer.model_json_schema(),
        },
    )
    logger.debug(f"Gemini response received for: {url}")
    return Summarizer.model_validate(response.parsed)

def format_result(title: str, url: str, result: Summarizer) -> str:
    themes = "\n".join(f"  • {t}" for t in result.key_themes)
    insights = "\n".join(f"  {i+1}. {ins}" for i, ins in enumerate(result.notable_insights))
    return f"""{'='*60}
{title}
{url}
{'='*60}

SUMMARY
-------
{result.summary}

KEY THEMES
----------
{themes}

NOTABLE INSIGHTS
----------------
{insights}

COMMUNITY SENTIMENT
-------------------
{result.community_sentiment}

CONTROVERSY SIGNAL
------------------
{result.controversy_signal}

REASONING TRACE
---------------
{result.reasoning_trace}
"""

if __name__ == "__main__":
    st.set_page_config(page_title="HN Summarizer", layout="centered")
    st.title("🔶 Post Summarizer")

    # Define session states
    if "processing" not in st.session_state:
        st.session_state.processing = False
    if "cache_log" not in st.session_state:
        st.session_state.cache_log = []
    if "custom_url" not in st.session_state:
        st.session_state.custom_url = ""
    if "mode" not in st.session_state:
        st.session_state.mode = ""
    if "n_posts" not in st.session_state:
        st.session_state.n_posts = ""

    # UI Sidebar 
    with st.sidebar:
        st.header("Settings")
        with st.expander("🔑 API Key"):
            api_key = st.text_input(
                "Gemini API Key", value=os.environ.get("GEMINI_API_KEY", ""),
                type="password", placeholder="AIza..."
                )
        st.divider()
        st.markdown("**Cache**")
        cached_urls = list(_load_cache().keys())
        st.caption(f"{len(cached_urls)} URL(s) cached")
        if cached_urls and st.button("Clear cache"):
            _save_cache({})
            st.success("Cache cleared.")
            st.rerun()
        st.divider()
        mode = st.radio("Mode", ["Top N Posts", "Single URL"], disabled=st.session_state.processing)
        st.session_state.mode = mode
        if mode == "Top N Posts":
            n_posts = st.slider("Number of posts", 1, 20, 2, disabled=st.session_state.processing)
            st.session_state.n_posts = n_posts
        else:
            custom_url = st.text_input("HN Discussion URL", placeholder="https://news.ycombinator.com/item?id=...", 
                                       disabled=st.session_state.processing)
            st.session_state.custom_url = custom_url

    # Main
    if st.button("Analyze", type="primary", disabled=st.session_state.processing):
        st.session_state.processing = True
        # st.rerun()
        logger.info(f"Analysis started — mode: {mode}")
    
    if st.session_state.processing:
        try:
            if not api_key:
                st.error("Please enter your Gemini API key.")
                st.stop()

            # output_text = ""
            output_results = []

            if mode == "Top N Posts":
                with st.spinner("Fetching top posts..."):
                    posts = get_top_posts(n_posts, base_url=BASE_URL)
                    logger.debug(f"Fetched posts: {n_posts}")

                progress = st.progress(0, text="Analyzing posts...")
                for i, post in enumerate(posts):
                    with st.spinner(f"Analyzing post {i+1}/{len(posts)}: {post['title'][:50]}..."):
                        try:
                            # output_text += get_or_analyze(post["url"], post["title"], api_key) + "\n\n"
                            output_results.append({
                                "title": post["title"],
                                "url": post["url"],
                                "text": get_or_analyze(post["url"], post["title"], api_key)
                            })
                        except Exception as e:
                            output_text = f"[ERROR] Failed to analyze {post['url']}: {e}\n\n"
                            output_results.append({
                                "title": post["title"],
                                "url": post["url"],
                                "text": output_text
                            })
                            logger.error(f"Error in mode Top_N_posts analysis: url: {post['url']}")
                    progress.progress((i + 1) / len(posts), text=f"Done {i+1}/{len(posts)}")
                progress.empty()

            else:
                if not st.session_state.get("custom_url"):
                    st.error("Please enter a URL.")
                    st.stop()
                with st.spinner("Analyzing..."):
                    try:
                        title = get_page_title(st.session_state.custom_url)
                        # output_text = get_or_analyze(st.session_state.custom_url, title, api_key)
                        output_results.append({
                            "title": title,
                            "url": st.session_state.custom_url,
                            "text": get_or_analyze(st.session_state.custom_url, title, api_key)
                        })
                        # logger.info(f'Analyzed given url {st.session_state.custom_url}. Result: {output_text}')
                        logger.info(f'Analyzed given url {st.session_state.custom_url}. Result: {output_results}')
                    except Exception as e:
                        logger.error(f"Analysis failed: {e}")
                        st.error(f"Analysis failed: {e}")
                        st.stop()
            
            if st.session_state.cache_log:
                with st.expander(f"{len(st.session_state.cache_log)} loaded from cache"):
                    for url in st.session_state.cache_log:
                        st.caption(url)
                st.session_state.cache_log = []  # reset after displaying

            # st.text_area("Results", value=output_text, height=600)
            full_text = ""
            for item in output_results:
                with st.expander(f"📄 {item['title']}"):
                    st.text_area("Result", value=item["text"], height=400, key=item["url"], label_visibility="hidden")
                full_text += item["text"] + "\n\n"

            st.download_button(
                label="Download Results",
                data=full_text,
                file_name="hn_summary.txt",
                mime="text/plain"
            )
            logger.info("Analysis completed successfully")
        except Exception as e:
            logger.exception(f"Analysis failed: {e}")
            st.error(f"Analysis failed: {e}")
            st.session_state.processing = False
        finally:
            st.session_state.processing = False
