import urllib.parse
from typing import Set, Dict, List
from collections import defaultdict
from urllib.parse import urlparse
from utils.response import Response
from bs4 import BeautifulSoup
import re


class ReportStatisticsLogger:
    def __init__(self):
        # set of non-ICS subdomain unique page URLs (de-fragmented)
        self._general_visited_pages: Set[str] = set()
        # ICS subdomain unique page URLs (de-fragmented), e.g. {subdomain : {URLs}}
        self._ics_visited_pages: Dict[str, Set[str]] = defaultdict(set)
        # max encountered num words of page
        self._max_words: int = 0
        # non-stop word frequency counts, e.g. {word : frequency}
        self._word_frequencies: Dict[str, int] = defaultdict(int)

        # parse stop words into global set
        self._init_stop_words()

        # ICS domain
        self.ICS_DOMAIN = "ics.uci.edu"

    def _init_stop_words(self) -> None:
        # TODO : fix the stop words
        try:
            with open('stop_words.txt') as file:
                self.STOP_WORDS = set(line.rstrip().lower() for line in file)
        except Exception as error:
            print("YOU DUMB BRUH! THE ONLY THING STOPPED IS YOUR BRAIN")
            raise error

    def update_max_word_count(self, new_count: int) -> None:
        if new_count > self._max_words:
            self._max_words = new_count

    def update_word_freqs(self, raw_tokens: List[str]) -> int:
        num_good_tokens = 0
        for good_token in filter(lambda token: token not in self.STOP_WORDS, map(str.lower, raw_tokens)):
            self._word_frequencies[good_token] += 1
            num_good_tokens += 1
        return num_good_tokens

    def record_unique_url(self, url: str) -> bool:
        response_url_components: urllib.parse.ParseResult = urlparse(url)
        stripped_url_str: str = response_url_components._replace(scheme='', fragment='').geturl()
        if self.ICS_DOMAIN in response_url_components.hostname:  # TODO : more efficient way to check?
            # URL is in the ics.uci.edu subdomain
            is_unique = stripped_url_str not in self._ics_visited_pages[response_url_components.hostname]
            if is_unique:
                self._ics_visited_pages[response_url_components.hostname].add(stripped_url_str)
        else:
            is_unique = stripped_url_str not in self._general_visited_pages
            if is_unique:
                self._general_visited_pages.add(stripped_url_str)
        return is_unique


StatsLogger: ReportStatisticsLogger = ReportStatisticsLogger()


def scraper(url, resp: Response):
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there
    # was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!

    # TODO : enforce valid URL check - assuming is valid for now

    # TODO : check status
    resp.status

    # track unique page
    if not StatsLogger.record_unique_url(resp.url):
        # recorded a duplicate URL
        return

    # TODO : parse webpage content & extract data
    soup: BeautifulSoup = BeautifulSoup(resp.raw_response.content, "lxml")

    num_words: int = 0  # temp var to track web page word count
    textual_info_count: int = 0

    for tag_content in soup.stripped_strings:
        tokens = re.findall('[A-Za-z0-9]+', tag_content)  # TODO : update regex to include special cases
        num_words += len(tokens)
        textual_info_count += StatsLogger.update_word_freqs(tokens)  # TODO : utilize textual relevance score
    StatsLogger.update_max_word_count(num_words)

    # TODO : scrape out links from webpage hrefs
    for link in soup.find_all('a'):
        # printing out hyperlinks
        print(f"URL : {link.get('href')}")

    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]


def extract_next_links(url, resp):
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    return list()


def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False
        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

    except TypeError:
        print("TypeError for ", parsed)
        raise


if __name__ == "__main__":
    print(StatsLogger.STOP_WORDS)
    print(len(StatsLogger.STOP_WORDS))
