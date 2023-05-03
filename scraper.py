import urllib.parse
from typing import Dict, List, Tuple
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
        self.SHOULD_ENFORCE_CRAWL_BUDGET = False
        self.CRAWL_BUDGET = 8000  # stop crawling a certain domain if we've seen too many pages

        # data structure to temporarily track word frequencies
        self.word_freq_temp: Dict[str, int] = defaultdict(int)

        # initialize all the report stat data structures
        self.save = shelve.open(self.STATISTICS_SHELF_FILE)
        # unique page URLs (de-fragmented / de-schemed), e.g. {domain : {URLs}}
        self.save[ReportShelfKeys.GENERAL_VISITED_PAGES]: Dict[str, int] = defaultdict(int)
        # unique page URLs (de-fragmented / de-schemed), e.g. {ICS subdomain : {URLs}}
        self.save[ReportShelfKeys.ICS_VISITED_PAGES]: Dict[str, int] = defaultdict(int)
        # max encountered num words of page
        self.save[ReportShelfKeys.MAX_WORDS]: Tuple[int, str] = (0, '')
        # non-stop word frequency counts, e.g. {word : frequency}
        self.save[ReportShelfKeys.WORD_FREQUENCIES]: Dict[str, int] = defaultdict(int)

        # parse stop words into global set
        self._init_stop_words()

    def __del__(self):
        # close shelf object when done
        self.save.close()

    def _init_stop_words(self) -> None:
        try:
            with open('stop_words.txt') as file:
                self.STOP_WORDS = set(line.rstrip().lower() for line in file)
        except Exception as error:
            print("YOU DUMB BRUH! THE ONLY THING STOPPED IS YOUR BRAIN")
            raise error

    def update_max_word_count(self, new_count: int, url: str) -> None:
        if new_count > self.save[ReportShelfKeys.MAX_WORDS][0]:
            self.save[ReportShelfKeys.MAX_WORDS] = (new_count, url)
            self.save.sync()

    def count_word_freqs(self, raw_tokens: List[str]) -> int:
        num_good_tokens = 0
        for good_token in filter(lambda token: token not in self.STOP_WORDS, map(str.lower, raw_tokens)):
            self.word_freq_temp[good_token] += 1
            num_good_tokens += 1
        return num_good_tokens

    def update_word_freqs(self):
        saved_word_freq: Dict[str, int] = self.save[ReportShelfKeys.WORD_FREQUENCIES]
        for key, value in self.word_freq_temp.items():
            saved_word_freq[key] += value
        self.save[ReportShelfKeys.WORD_FREQUENCIES] = saved_word_freq
        self.save.sync()
        self.word_freq_temp.clear()

    def record_unique_url(self, url_components: urllib.parse.ParseResult) -> None:
        normalized_hostname = self.normalize_url(url_components.hostname)
        if self.ICS_DOMAIN in normalized_hostname:
            # URL is in the ics.uci.edu subdomain
            ics_visited_pages_temp: Dict[str, int] = self.save[ReportShelfKeys.ICS_VISITED_PAGES]
            ics_visited_pages_temp[normalized_hostname] += 1
            self.save[ReportShelfKeys.ICS_VISITED_PAGES] = ics_visited_pages_temp
        else:
            general_visited_pages_temp: Dict[str, int] = self.save[ReportShelfKeys.GENERAL_VISITED_PAGES]
            general_visited_pages_temp[normalized_hostname] += 1
            self.save[ReportShelfKeys.GENERAL_VISITED_PAGES] = general_visited_pages_temp
        self.save.sync()

    def url_is_under_domain_threshold(self, url_components: urllib.parse.ParseResult) -> bool:
        normalized_hostname = self.normalize_url(url_components.hostname)
        if self.ICS_DOMAIN in normalized_hostname:
            return self.save[ReportShelfKeys.ICS_VISITED_PAGES][normalized_hostname] < self.CRAWL_BUDGET
        else:
            return self.save[ReportShelfKeys.GENERAL_VISITED_PAGES][normalized_hostname] < self.CRAWL_BUDGET

    @staticmethod
    def normalize_url(url: str):
        normalized_url = url
        if url.endswith("/"):
            normalized_url = url.rstrip("/")
        if url.startswith("www."):
            normalized_url = url.lstrip("www.")
        return normalized_url.strip()


StatsLogger: ReportStatisticsShelf = ReportStatisticsShelf()

# crawler trap thresholds
# source : https://support.archive-it.org/hc/en-us/articles/208332943-Identify-and-avoid-crawler-traps-
USEFUL_WORD_THRESHOLD = 100
MAX_URL_PATH_LENGTH = 250  # very long paths are usual indicators of crawler traps
MAX_URL_DIRECTORIES = 15  # paths with many directories are usually indicators of crawler traps
MAX_FILE_SIZE = 500000  # bytes object from response.raw_response.content
USEFULNESS_RATIO_THRESHOLD = 0.6  # ratio of non-stop to total words in web page


def scraper(url, resp: Response):
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there
    # was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!

    ''' LOG UNIQUE WEB PAGES ---------------- '''
    # track all unique pages visited (including ones we decide not to crawl)
    response_url_components: urllib.parse.ParseResult = urlparse(resp.url)
    StatsLogger.record_unique_url(response_url_components)  # frontier always returns a unique URL

    ''' STATUS CHECKS ---------------- '''
    if resp.status < 200 or resp.status > 300:  # 20X range indicates valid results
        return []

    if not resp or not resp.raw_response or not resp.raw_response.content:
        # don't crawl dead pages - 200 status but no data
        return []

    ''' ENFORCE CRAWLER CHECKS ---------------- '''
    soup: BeautifulSoup = BeautifulSoup(resp.raw_response.content, "lxml")

    num_words: int = 0  # temp var to track web page word count
    textual_info_count: int = 0

    for tag_content in soup.stripped_strings:
        tokens = re.findall("[\w]+(?:[:.'@/-]+[\w]+)+|[A-Za-z]{3,}", tag_content)
        num_words += len(tokens)
        textual_info_count += StatsLogger.count_word_freqs(tokens)

    # only crawl pages with high textual information content
    # avoid large files with low information value
    response_size = len(resp.raw_response.content)
    if textual_info_count < USEFUL_WORD_THRESHOLD \
            or response_size > MAX_FILE_SIZE and textual_info_count / num_words > USEFULNESS_RATIO_THRESHOLD:
        StatsLogger.word_freq_temp.clear()
        return []

    ''' LOG CONTENT STATS ---------------- '''
    # record non-stop word frequencies
    StatsLogger.update_word_freqs()
    # record max word counts
    StatsLogger.update_max_word_count(num_words, resp.url)

    # extract links from web content & convert to absolute URLs
    # ensure links are ASCII strings
    discovered_links = [convert_to_abs_url(link.get('href'), response_url_components)
                        for link in soup.find_all('a') if link.get('href') and link.get('href').isascii()]

    # filter extracted links for valid ones
    return [link for link in discovered_links if is_valid(link)]


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
        if StatsLogger.SHOULD_ENFORCE_CRAWL_BUDGET and not StatsLogger.url_is_under_domain_threshold(parsed):
            # enforce crawling budget for each valid web domain
            return False
        if len(parsed.path) > MAX_URL_PATH_LENGTH:
            # ensure that query and path are not extremely long (trap)
            return False
        if parsed.path.count("/") > MAX_URL_DIRECTORIES:
            # ensure that query doesn't have large amount of directories (traps)
            return False
        if re.match(r".*(/blog/|/calendar/|mailto:|http).*", parsed.path.lower()):
            # we analyzed / researched that many pages with these paths were redundant or prone to wasting crawl budget
            return False
        if re.match(r".*(do=.*|action=.*|version=.*).*", parsed.query.lower()):
            # check for common trap / redundant query parameters
            return False
        if re.match(
                r".*\.(apk|css|js|bmp|gif|jpe?g|ico"
                + r"|png|tiff?|mid|mp2|mp3|mp4"
                + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf|ppsx"
                + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
                + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
                + r"|epub|dll|cnf|tgz|sha1"
                + r"|thmx|mso|arff|rtf|jar|csv"
                + r"|rm|smil|wmv|swf|wma|zip|rar|gz)", parsed.query.lower()):
            # ignore non-web page file patterns in URL path
            return False
        return not re.match(
            r".*\.(apk|css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf|ppsx"
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

    # print(urlparse('https://www.informatics.uci.edu/%20http://ambassador.google.uci.edu'))
    #
    # print(is_valid("http://sli.ics.uci.edu/Classes/2012W-178?action=download&upname=L09.pdf"))
    # print(is_valid("http://computableplant.ics.uci.edu/2006/plcb-02-12-12_Wold?action=download"))
    # print(bool(re.match(r".*(/blog/|mailto:|http.).*", "")))
    #
    # print(urlparse("http://computableplant.ics.uci.edu/2006/plcb-02-12-12_Wold?action=download").path)

    test = "https://www.informatics.uci.edu/%20http://ambassador.google.uci.edu"
    print(urlparse(test)._replace(path='/robots.txt', fragment='').geturl())
