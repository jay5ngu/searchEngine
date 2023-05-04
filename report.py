import shelve, sys

with shelve.open(sys.argv[-1]) as save:
    # number of unique pages
    general_visited_pages = save['general_visited_pages'] # {domain : # URLs}
    gen_domains = '\n'.join(general_visited_pages.keys())
    print("Visited Domains:\n", gen_domains)

    for domain, num_URLs in sorted(general_visited_pages.items(), key=lambda domain: domain[0]):
        print(f'{domain} : {num_URLs} pages')
    
    ics_pages = save['ics_visited_pages'] # {ICS domain : {URLs}}
    print('ICS Domains (ordered):\n')
    for domain, num_URLs in sorted(ics_pages.items(), key=lambda domain: domain[0]):
        print(f'{domain} : {num_URLs} pages')
    
    unique_num = sum(general_visited_pages.values()) + sum(ics_pages.values())
    print(f'Unique Pages: {unique_num}', '\n')
    
    # longest page
    print(f"Longest Encountered Page Length: {save['max_words']}", '\n')
    
    # 50 most common words
    word_freqs = save['word_frequencies'] # {word: frequency}
    print('Word Frequencies: \n')
    for word, freq in sorted(word_freqs.items(), key = lambda val : (-val[1], val[0]))[:50]:
        print(f'{word} = {freq}')
        
    
    
