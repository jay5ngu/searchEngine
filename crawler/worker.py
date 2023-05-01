import http.client
import urllib.error
from threading import Thread
from urllib import robotparser
from inspect import getsource
from utils.download import download
from utils import get_logger
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
        
    def run(self):
        no_robot_file_found = False
        while True:
            tbd_url = self.frontier.get_tbd_url()
            if not tbd_url:
                self.logger.info("Frontier is empty. Stopping Crawler.")
                break

            robots_parser = robotparser.RobotFileParser(str(tbd_url).rstrip("/") + "/robots.txt")
            try:
                robots_parser.read()
            except urllib.error.URLError:
                no_robot_file_found = True
            except http.client.InvalidURL:
                no_robot_file_found = True
            except UnicodeDecodeError:
                no_robot_file_found = True
            except UnicodeEncodeError:
                no_robot_file_found = True
            except Exception:
                no_robot_file_found = True
            if no_robot_file_found or robots_parser.can_fetch("*", str(tbd_url)):
                resp = download(tbd_url, self.config, self.logger)
                self.logger.info(
                    f"Downloaded {tbd_url}, status <{resp.status}>, "
                    f"using cache {self.config.cache_server}.")
                scraped_urls = scraper.scraper(tbd_url, resp)
                for scraped_url in scraped_urls:
                    self.frontier.add_url(scraped_url)
            else:
                pass # TODO : log
            self.frontier.mark_url_complete(tbd_url)
            time.sleep(self.config.time_delay)
            no_robot_file_found = False
