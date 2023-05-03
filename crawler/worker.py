from threading import Thread
from urllib import robotparser
from urllib.parse import urlparse, ParseResult
from inspect import getsource
from utils.download import download
from utils import get_logger
from typing import Dict
import scraper
import time

class Worker(Thread):
    def __init__(self, worker_id, config, frontier):
        self.logger = get_logger(f"Worker-{worker_id}", "Worker")
        self.config = config
        self.frontier = frontier
        # basic check for requests in scraper
        assert {getsource(scraper).find(req) for req in {"from requests import", "import requests"}} == {-1}, "Do not use requests in scraper.py"
        assert {getsource(scraper).find(req) for req in {"from urllib.request import", "import urllib.request"}} == {-1}, "Do not use urllib.request in scraper.py"
        super().__init__(daemon=True)

    def is_not_prohibited(self, url, prohibited_urls: Dict[str, robotparser.RobotFileParser]):
        # extract url components
        parsed: ParseResult = urlparse(url)
        netloc = scraper.ReportStatisticsShelf.normalize_url(parsed.netloc)  # for consistency

        if netloc in prohibited_urls:
            # we already checked for this website's robots.txt rules
            if prohibited_urls[netloc]:
                # we successfully found rules
                return prohibited_urls[netloc].can_fetch('*', url)
            else:
                # website doesn't have or has an invalid robots.txt -- crawl anyways
                return True
        else:
            # we need to check for this website's robots.txt rules

            # generate robots.txt URL
            robots_url: str = parsed._replace(path='/robots.txt', fragment='').geturl()

            # attempt to retrieve robots.txt (from cache server) - don't bypass cache
            try:
                # download from cache
                resp = download(robots_url, self.config, self.logger)
                self.logger.info(
                    f"Robots file downloaded {robots_url}, status <{resp.status}>, "
                    f"using cache {self.config.cache_server}.")
                # check response content
                if not resp or resp.status != 200 or not resp.raw_response or not resp.raw_response.content:
                    # no robots.txt found or it is empty
                    prohibited_urls[netloc] = None
                    return True

                # need to create new parser
                rp: robotparser.RobotFileParser = robotparser.RobotFileParser()
                # parse the robots.txt content
                rp.parse(resp.raw_response.content)
                # save for future use
                prohibited_urls[netloc] = rp
                # verify site crawl-ability
                return rp.can_fetch('*', url)
            except Exception as e:
                self.logger.info(f"Robots.txt parsing error on {robots_url}. Error message: <{str(e)}>")
                prohibited_urls[netloc] = None  # invalid robots.txt
                return True  # by default, enable crawling

    def run(self):
        prohibited_urls: Dict[str, robotparser.RobotFileParser] = {}  # keeping local since no multithreading
        while True:
            tbd_url = self.frontier.get_tbd_url()
            if not tbd_url:
                self.logger.info("Frontier is empty. Stopping Crawler.")
                break

            # check site's robots.txt permissions before downloading URL content
            if self.is_not_prohibited(tbd_url, prohibited_urls):
                try:
                    # error handling for scraper / download
                    resp = download(tbd_url, self.config, self.logger)
                    self.logger.info(
                        f"Downloaded {tbd_url}, status <{resp.status}>, "
                        f"using cache {self.config.cache_server}.")
                    scraped_urls = scraper.scraper(tbd_url, resp)
                except Exception as e:
                    self.logger.info(f"Error with downloading or parsing {tbd_url}.  Error <{str(e)}>")
                else:
                    # add URLs to frontier if successful
                    for scraped_url in scraped_urls:
                        self.frontier.add_url(scraped_url)
            else:
                self.logger.info(
                    f"Skipped downloading {tbd_url}, robots.txt disallows.")

            self.frontier.mark_url_complete(tbd_url)
            time.sleep(self.config.time_delay)
