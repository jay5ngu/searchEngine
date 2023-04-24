import re
from collections import defaultdict
from urllib.parse import urlparse
from utils.response import Response
from bs4 import BeautifulSoup
import re

# global variables
number_of_unique_pages = 0
visited_hostnames_set = set()
longest_page_length = 0
word_freqs = defaultdict(int)
fifty_most_common_words = defaultdict(int)
subdomains_dict = defaultdict(int)


def write_statistics():
    global word_freqs
    word_tuples_list = sorted([(key, val) for key, val in word_freqs.items()], key=lambda x: -x[1])
    final_word_tuples_list = []

    if len(word_tuples_list) < 50:
        final_word_tuples_list = [key for key, val in word_tuples_list]
    else:
        final_word_tuples_list = [word_tuples_list[i][0] for i in range(50)]

    with open('statistics.txt', "w") as f:
        global number_of_unique_pages
        f.write(str(number_of_unique_pages) + '\n')

        global longest_page_length
        f.write(str(longest_page_length) + '\n')

        f.write(str(final_word_tuples_list) + '\n')

        global subdomains_dict
        f.write(str(subdomains_dict) + '\n')


def soup_playground():
    with open('urmom.txt', "r") as f:
        print("hello")

        soup = BeautifulSoup(f, "lxml")
        for link in soup.find_all('a'):
            print(f"URL : {link.get('href')}")


def scraper(url, resp: Response):
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!

    # TODO : check the status code
    if resp.status == 200:
        # TODO : parse webpage content & extract data
        soup = BeautifulSoup(resp.raw_response.content, "lxml")

        # checks if hostname has already been visited and increases number of unique pages if it hasn't (first bullet of second section of wiki)
        global visited_hostnames_set
        if str(soup.get('href')) not in visited_hostnames_set:
            global number_of_unique_pages
            number_of_unique_pages = number_of_unique_pages + 1

        visited_hostnames_set.add(soup.get('href'))

        # TODO : make these global?
        num_words = 0
        stop_words = {'and', 'but', 'to', 'for', 'nor', 'so'} # TODO : fill this out

        # refers to word frequencies (3rd bullet of section 3 of wiki)
        global word_freqs

        for tag_content in soup.stripped_strings:
            # printing out content
            tokens = re.findall("[A-Za-z]+'s|[A-Za-z0-9]+@[A-Za-z.]+|[A-Za-z-A-Za-z]+|[A-Za-z-A-Za-z]+$|[A-Za-z0-9][A-Za-z0-9:.-@]+", tag_content) # TODO : make time ranges work and solve bugs
            num_words += len(tokens)
            lower_tokens = map(str.lower, tokens)
            for token in lower_tokens:
                if token not in stop_words:
                    word_freqs[token] += 1

        # updates longest page variable (2nd bullet of section 2 of wiki)
        global longest_page_length
        longest_page_length = max(num_words, longest_page_length)

        # print(num_words)
        # print(word_freqs)

        # links = extract_next_links(url, resp)
        # return [link for link in links if is_valid(link)]
        return extract_next_links(url, resp)
    else:
        print(f'Error Code {resp.status}: {resp.error}')
        return []

def extract_next_links(url, resp):
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    # print(url)
    # print(resp.url)
    u = urlparse(url)
    domain = "https://" + u.netloc
    links = set()
    soup = BeautifulSoup(resp.raw_response.content, "lxml")
    for link in soup.find_all('a'):
        possible_url = link.get('href')
        # converts any relative url to become an absolute url
        if "html" not in link.get('href'): # checks if url missing scheme
            if "www" not in possible_url: # checks if is also url missing host:port
                possible_url = domain + possible_url
            else: 
                possible_url = "https:" + possible_url
        links.add(possible_url)
    return list()

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    domains = [
        '.ics.uci.edu/',
        '.cs.uci.edu/',
        '.informatics.uci.edu/',
        'stat.uci.edu/'
    ]
    
    try:
        parsed = urlparse(url)

        valid_domain = False

        for domain in domains:
            if domain in url:
                valid_domain = True
                break

        if parsed.scheme not in set(["http", "https"]):
            return False
        return valid_domain and not re.match(
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