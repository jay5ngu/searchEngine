import re
from collections import defaultdict
from urllib.parse import urlparse
from utils.response import Response
from bs4 import BeautifulSoup
import re

def scraper(url, resp: Response):
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!

    # TODO : check the status code

    # TODO : parse webpage content & extract data
    soup = BeautifulSoup(resp.raw_response.content, "lxml")

    # TODO : make these global?
    num_words = 0
    stop_words = {'and', 'but', 'to', 'for', 'nor', 'so'} # TODO : fill this out
    word_freqs = defaultdict(int)

    for tag_content in soup.stripped_strings:
        # printing out content
        tokens = re.findall('[A-Za-z0-9]+', tag_content) # TODO : update regex to include special cases
        num_words += len(tokens)
        lower_tokens = map(str.lower, tokens)
        for token in lower_tokens:
            if token not in stop_words:
                word_freqs[token] += 1
    print(num_words)
    print(word_freqs)

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
        print ("TypeError for ", parsed)
        raise
