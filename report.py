import shelve, sys, re
from urllib.parse import urlparse


def normalize_url(url: str):
    normalized_url = url
    if url.endswith("/"):
        normalized_url = url.rstrip("/")
    if url.startswith("www."):
        normalized_url = url.lstrip("www.")
    return normalized_url.strip()

with shelve.open(sys.argv[-1]) as save:
    # number of unique pages - general domains
    general_visited_pages = save['general_visited_pages'] # {domain : # URLs}
    ics_pages = save['ics_visited_pages'] # {ICS domain : {URLs}}

    print('#1 = Unique Pages Found')
    unique_num = sum(general_visited_pages.values()) + sum(ics_pages.values())
    print(f'Unique Pages: {unique_num}', '\n')

    print('#2 = Longest Page (token word counts, including valid stopwords)')
    print(f"Longest Encountered Page Length: {save['max_words']}", '\n')

    print('#3 = 50 most common non stop words')
    # 50 most common words
    word_freqs = save['word_frequencies']  # {word: frequency}
    print('Word Frequencies: \n')
    counter = 1
    for word, freq in sorted(word_freqs.items(), key=lambda val: (-val[1], val[0]))[:50]:
        print(f'#{counter:>4}: {word:>20}, {freq}')
        counter += 1
    print()

    print('#4 = ICS subdomains and unique page count, ordered alphabetically')
    # reconstruct original URL based on Log
    hostnames = dict(ics_pages)
    with open('Worker.log') as f:
        for line in f:
            urls = re.findall('https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', line)
            for url in urls:
                parsed = urlparse(url)
                if normalize_url(parsed.hostname) in hostnames:
                    hostnames[normalize_url(parsed.hostname)] = url

    counter = 1
    for norm_url, num_pages in sorted(ics_pages.items(), key=lambda domain: domain[0]):
        print(f'{counter:>5} = {hostnames[norm_url]:>50}, {num_pages}')
        counter += 1
        
    
    
