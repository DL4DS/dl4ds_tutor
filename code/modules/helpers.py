import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import chainlit as cl
from langchain import PromptTemplate
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, urldefrag
import asyncio
import aiohttp
from aiohttp import ClientSession

try:
    from modules.constants import *
except:
    from constants import *

"""
Ref: https://python.plainenglish.io/scraping-the-subpages-on-a-website-ea2d4e3db113
"""


class WebpageCrawler:
    def __init__(self):
        self.dict_href_links = {}

    async def fetch(self, session: ClientSession, url: str) -> str:
        async with session.get(url) as response:
            try:
                return await response.text()
            except UnicodeDecodeError:
                return await response.text(encoding="latin1")

    def url_exists(self, url: str) -> bool:
        try:
            response = requests.head(url)
            return response.status_code == 200
        except requests.ConnectionError:
            return False

    async def get_links(self, session: ClientSession, website_link: str, base_url: str):
        html_data = await self.fetch(session, website_link)
        soup = BeautifulSoup(html_data, "html.parser")
        list_links = []
        for link in soup.find_all("a", href=True):
            href = link["href"].strip()
            full_url = urljoin(base_url, href)
            normalized_url = self.normalize_url(full_url)  # sections removed
            if (
                normalized_url not in self.dict_href_links
                and self.is_child_url(normalized_url, base_url)
                and self.url_exists(normalized_url)
            ):
                self.dict_href_links[normalized_url] = None
                list_links.append(normalized_url)

        return list_links

    async def get_subpage_links(
        self, session: ClientSession, urls: list, base_url: str
    ):
        tasks = [self.get_links(session, url, base_url) for url in urls]
        results = await asyncio.gather(*tasks)
        all_links = [link for sublist in results for link in sublist]
        return all_links

    async def get_all_pages(self, url: str, base_url: str):
        async with aiohttp.ClientSession() as session:
            dict_links = {url: "Not-checked"}
            counter = None
            while counter != 0:
                unchecked_links = [
                    link
                    for link, status in dict_links.items()
                    if status == "Not-checked"
                ]
                if not unchecked_links:
                    break
                new_links = await self.get_subpage_links(
                    session, unchecked_links, base_url
                )
                for link in unchecked_links:
                    dict_links[link] = "Checked"
                    print(f"Checked: {link}")
                dict_links.update(
                    {
                        link: "Not-checked"
                        for link in new_links
                        if link not in dict_links
                    }
                )
                counter = len(
                    [
                        status
                        for status in dict_links.values()
                        if status == "Not-checked"
                    ]
                )

            checked_urls = [
                url for url, status in dict_links.items() if status == "Checked"
            ]
            return checked_urls

    def is_webpage(self, url: str) -> bool:
        try:
            response = requests.head(url, allow_redirects=True)
            content_type = response.headers.get("Content-Type", "").lower()
            return "text/html" in content_type
        except requests.RequestException:
            return False

    def clean_url_list(self, urls):
        files, webpages = [], []

        for url in urls:
            if self.is_webpage(url):
                webpages.append(url)
            else:
                files.append(url)

        return files, webpages

    def is_child_url(self, url, base_url):
        return url.startswith(base_url)

    def normalize_url(self, url: str):
        # Strip the fragment identifier
        defragged_url, _ = urldefrag(url)
        return defragged_url


def get_urls_from_file(file_path: str):
    """
    Function to get urls from a file
    """
    with open(file_path, "r") as f:
        urls = f.readlines()
    urls = [url.strip() for url in urls]
    return urls


def get_base_url(url):
    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}/"
    return base_url


def get_prompt(config):
    if config["llm_params"]["use_history"]:
        if config["llm_params"]["llm_loader"] == "local_llm":
            custom_prompt_template = tinyllama_prompt_template_with_history
        elif config["llm_params"]["llm_loader"] == "openai":
            custom_prompt_template = openai_prompt_template_with_history
        # else:
        #     custom_prompt_template = tinyllama_prompt_template_with_history # default
        prompt = PromptTemplate(
            template=custom_prompt_template,
            input_variables=["context", "chat_history", "question"],
        )
    else:
        if config["llm_params"]["llm_loader"] == "local_llm":
            custom_prompt_template = tinyllama_prompt_template
        elif config["llm_params"]["llm_loader"] == "openai":
            custom_prompt_template = openai_prompt_template
        # else:
        #     custom_prompt_template = tinyllama_prompt_template
        prompt = PromptTemplate(
            template=custom_prompt_template,
            input_variables=["context", "question"],
        )
    return prompt


def get_sources(res, answer):
    source_elements = []
    source_dict = {}  # Dictionary to store URL elements

    for idx, source in enumerate(res["source_documents"]):
        source_metadata = source.metadata
        url = source_metadata["source"]
        score = source_metadata.get("score", "N/A")
        page = source_metadata.get("page", 1)
        date = source_metadata.get("date", "N/A")

        url_name = f"{url}_{page}"
        if url_name not in source_dict:
            source_dict[url_name] = {
                "text": source.page_content,
                "url": url,
                "score": score,
                "page": page,
                "date": date,
            }
        else:
            source_dict[url_name]["text"] += f"\n\n{source.page_content}"

    # First, display the answer
    full_answer = "**Answer:**\n"
    full_answer += answer

    # Then, display the sources
    full_answer += "\n\n**Sources:**\n"
    for idx, (url_name, source_data) in enumerate(source_dict.items()):
        full_answer += f"\nSource {idx + 1} (Score: {source_data['score']}): {source_data['url']}\n"

        name = f"Source {idx + 1} Text\n"
        full_answer += name
        source_elements.append(
            cl.Text(name=name, content=source_data["text"], display="side")
        )

        # Add a PDF element if the source is a PDF file
        if source_data["url"].lower().endswith(".pdf"):
            name = f"Source {idx + 1} PDF\n"
            full_answer += name
            pdf_url = f"{source_data['url']}#page={source_data['page']+1}"
            source_elements.append(cl.Pdf(name=name, url=pdf_url, display="side"))

    full_answer += "\n**Metadata:**\n"
    for idx, (url_name, source_data) in enumerate(source_dict.items()):
        full_answer += f"Source {idx+1} Metadata\n"
        source_elements.append(
            cl.Text(
                name=f"Source {idx+1} Metadata",
                content=f"Page: {source_data['page']}\nDate: {source_data['date']}\n",
                display="side",
            )
        )

    return full_answer, source_elements


def get_metadata(file_names):
    """
    Function to get any additional metadata from the files
    Returns a dict with the file_name: {metadata: value}
    """
    metadata_dict = {}
    for file in file_names:
        metadata_dict[file] = {
            "source_type": "N/A",
        }
    return metadata_dict
