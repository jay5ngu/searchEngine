import urllib.parse
from typing import Set, Dict, List, Tuple
from collections import defaultdict
from urllib.parse import urlparse
from utils.response import Response
from bs4 import BeautifulSoup
import re, shelve

class ReportShelfKeys():
    GENERAL_VISITED_PAGES = "general_visited_pages"
    ICS_VISITED_PAGES = "ics_visited_pages"
    MAX_WORDS = "max_words"
    WORD_FREQUENCIES = "word_frequencies"

class ReportStatisticsShelf:
    def __init__(self):
        # constants
        self.ICS_DOMAIN = ".ics.uci.edu"
        self.STATISTICS_SHELF_FILE = "report_stats.shelve"
        self.CRAWL_BUDGET = 1000  # stop crawling if we've seen 1000 pages in a web domain

        # initialize all the report stat data structures
        self.save = shelve.open(self.STATISTICS_SHELF_FILE)
        # unique page URLs (de-fragmented / de-schemed), e.g. {domain : {URLs}}
        self.save[ReportShelfKeys.GENERAL_VISITED_PAGES]: Dict[str, Set[str]] = defaultdict(set)
        # unique page URLs (de-fragmented / de-schemed), e.g. {ICS subdomain : {URLs}}
        self.save[ReportShelfKeys.ICS_VISITED_PAGES]: Dict[str, Set[str]] = defaultdict(set)
        # max encountered num words of page
        self.save[ReportShelfKeys.MAX_WORDS]: int = 0
        # non-stop word frequency counts, e.g. {word : frequency}
        self.save[ReportShelfKeys.WORD_FREQUENCIES]: Dict[str, int] = defaultdict(int)

        # parse stop words into global set
        self._init_stop_words()

    def __del__(self):
        # close shelf object when done
        self.save.close()

    def _init_stop_words(self) -> None:
        # TODO : fix the stop words
        try:
            with open('stop_words.txt') as file:
                self.STOP_WORDS = set(line.rstrip().lower() for line in file)
        except Exception as error:
            print("YOU DUMB BRUH! THE ONLY THING STOPPED IS YOUR BRAIN")
            raise error

    def update_max_word_count(self, new_count: int) -> None:
        if new_count > self.save[ReportShelfKeys.MAX_WORDS]:
            self.save[ReportShelfKeys.MAX_WORDS] = new_count
            self.save.sync()

    def update_word_freqs(self, raw_tokens: List[str]) -> int:
        num_good_tokens = 0
        word_freq_temp: Dict[str, int] = self.save[ReportShelfKeys.WORD_FREQUENCIES]
        for good_token in filter(lambda token: token not in self.STOP_WORDS, map(str.lower, raw_tokens)):
            word_freq_temp[good_token] += 1
            num_good_tokens += 1
        self.save[ReportShelfKeys.WORD_FREQUENCIES] = word_freq_temp
        self.save.sync()
        return num_good_tokens

    def record_unique_url(self, url_components: urllib.parse.ParseResult) -> bool:
        stripped_url_str: str = self.normalize_url(url_components._replace(scheme='', fragment='').geturl())
        normalized_hostname = self.normalize_url(url_components.hostname)
        if self.ICS_DOMAIN in normalized_hostname:  # TODO : more efficient way to check?
            # URL is in the ics.uci.edu subdomain
            ics_visited_pages_temp: Dict[str, Set[str]] = self.save[ReportShelfKeys.ICS_VISITED_PAGES]
            is_unique = stripped_url_str not in ics_visited_pages_temp[normalized_hostname]
            if is_unique:
                ics_visited_pages_temp[normalized_hostname].add(stripped_url_str)
                self.save[ReportShelfKeys.ICS_VISITED_PAGES] = ics_visited_pages_temp
                self.save.sync()
        else:
            general_visited_pages_temp = Dict[str, Set[str]] = self.save[ReportShelfKeys.GENERAL_VISITED_PAGES]
            is_unique = stripped_url_str not in general_visited_pages_temp
            if is_unique:
                general_visited_pages_temp[normalized_hostname].add(stripped_url_str)
                self.save[ReportShelfKeys.GENERAL_VISITED_PAGES] = general_visited_pages_temp
                self.save.sync()
        return is_unique

    def url_is_under_domain_threshold(self, url_components: urllib.parse.ParseResult) -> bool:
        normalized_hostname = self.normalize_url(url_components.hostname)
        if self.ICS_DOMAIN in normalized_hostname:
            return len(self.save[ReportShelfKeys.ICS_VISITED_PAGES][normalized_hostname]) < self.CRAWL_BUDGET
        else:
            return len(self.save[ReportShelfKeys.GENERAL_VISITED_PAGES][normalized_hostname]) < self.CRAWL_BUDGET

    @staticmethod
    def normalize_url(url: str):
        if url.endswith("/"):
            return url.rstrip("/")
        return url


# class ReportStatisticsLogger:
#     def __init__(self):
#         # set of non-ICS subdomain unique page URLs (de-fragmented)
#         self._general_visited_pages: Set[str] = set()
#         # ICS subdomain unique page URLs (de-fragmented), e.g. {subdomain : {URLs}}
#         self._ics_visited_pages: Dict[str, Set[str]] = defaultdict(set)
#         # max encountered num words of page
#         self._max_words: int = 0
#         # non-stop word frequency counts, e.g. {word : frequency}
#         self._word_frequencies: Dict[str, int] = defaultdict(int)
#
#         # parse stop words into global set
#         self._init_stop_words()
#
#         # ICS domain
#         self.ICS_DOMAIN = ".ics.uci.edu"
#
#     def _init_stop_words(self) -> None:
#         # TODO : fix the stop words
#         try:
#             with open('stop_words.txt') as file:
#                 self.STOP_WORDS = set(line.rstrip().lower() for line in file)
#         except Exception as error:
#             print("YOU DUMB BRUH! THE ONLY THING STOPPED IS YOUR BRAIN")
#             raise error
#
#     def update_max_word_count(self, new_count: int) -> None:
#         if new_count > self._max_words:
#             self._max_words = new_count
#
#     def update_word_freqs(self, raw_tokens: List[str]) -> int:
#         num_good_tokens = 0
#         for good_token in filter(lambda token: token not in self.STOP_WORDS, map(str.lower, raw_tokens)):
#             self._word_frequencies[good_token] += 1
#             num_good_tokens += 1
#         return num_good_tokens
#
#     def record_unique_url(self, url_components: urllib.parse.ParseResult) -> bool:
#         stripped_url_str: str = url_components._replace(scheme='', fragment='').geturl()
#         if self.ICS_DOMAIN in url_components.hostname:  # TODO : more efficient way to check?
#             # URL is in the ics.uci.edu subdomain
#             is_unique = stripped_url_str not in self._ics_visited_pages[url_components.hostname]
#             if is_unique:
#                 self._ics_visited_pages[url_components.hostname].add(stripped_url_str)
#         else:
#             is_unique = stripped_url_str not in self._general_visited_pages
#             if is_unique:
#                 self._general_visited_pages.add(stripped_url_str)
#         return is_unique

StatsLogger: ReportStatisticsShelf = ReportStatisticsShelf()
USEFUL_WORD_THRESHOLD = 100 # TODO : adjust this threshold

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

    if resp.status != 200:
        # TODO : handle this case
        print(resp.error)

    if not resp or not resp.raw_response or not resp.raw_response.content:
        # don't crawl dead pages - 200 status but no data
        # TODO : handle this case
        return []

    soup: BeautifulSoup = BeautifulSoup(resp.raw_response.content, "lxml")

    num_words: int = 0  # temp var to track web page word count
    textual_info_count: int = 0

    # TODO : check web page size??

    # TODO : IMPORTANT --- check before updating stats
    for tag_content in soup.stripped_strings:
        tokens = re.findall('[A-Za-z0-9]+', tag_content)  # TODO : update regex to include special cases
        num_words += len(tokens)
        textual_info_count += StatsLogger.update_word_freqs(tokens)  # TODO : utilize textual relevance score
    StatsLogger.update_max_word_count(num_words)

    if textual_info_count < USEFUL_WORD_THRESHOLD:
        # TODO : handle this case
        return []

    # track unique pages with high textual information content
    response_url_components: urllib.parse.ParseResult = urlparse(resp.url)
    if not StatsLogger.record_unique_url(response_url_components):
        # recorded a duplicate URL
        print(f"URL : {resp.url} is a duplicate")
        return

    # extract links from web content & convert to absolute URLs
    discovered_links = [convert_to_abs_url(link.get('href'), response_url_components) for link in soup.find_all('a')]
    for link in discovered_links:
        print(f"URL : {link}")

    # filter extracted links for valid ones
    return [link for link in discovered_links if is_valid(link)]  # TODO : optimize / check for traps?


def convert_to_abs_url(relative_url: str, reference_url: urllib.parse.ParseResult) -> str:
    url_components: urllib.parse.ParseResult = urlparse(relative_url)

    # ensure absolute url elements exist
    if not url_components.scheme:
        url_components = url_components._replace(scheme=reference_url.scheme)
    if not url_components.netloc:
        url_components = url_components._replace(netloc=reference_url.netloc)
    if not url_components.path:
        url_components = url_components._replace(path='/')

    # de-fragment
    url_components = url_components._replace(fragment='')

    # regenerate URL
    return url_components.geturl()


def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False
        if not parsed.hostname or not re.match(r".*\.(ics|cs|informatics|stat)\.uci\.edu$", parsed.hostname):
            # check domain is valid
            return False
        if not StatsLogger.url_is_under_domain_threshold(parsed):
            # enforce crawling budget for each valid web domain
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
    # print(StatsLogger.STOP_WORDS)
    # print(len(StatsLogger.STOP_WORDS))

    print(is_valid("http://www.vision.ics.uci.edu"))
