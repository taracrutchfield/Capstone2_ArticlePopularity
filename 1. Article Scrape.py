import numpy as np
import pandas as pd
import os
import requests
from bs4 import BeautifulSoup

# Multithreading
import asyncio
from concurrent.futures import ThreadPoolExecutor
import nest_asyncio

nest_asyncio.apply()

#-- Functions ----------------------------------------------------------------------------------------------------------------------------------------
def make_dir(path):
    """Creates folders specified in a given path if they don't already exist.
    
    Parameters
    ----------
    path : str
        path containing folders to be created.
    """
    final_path = '.'
    for folder in path.split('/'):
        if folder not in os.listdir(final_path):
            os.mkdir(final_path+'/'+folder)
        final_path += '/'+folder

def fetch(url,session):
    """Takes article URL and finds the title, text, references, amount of images and videos, topics, publish date, and data channel.
    
    Parameters
    ----------
    url: str
        article url
    
    session:
        Idk the code freaks out if I don't include this I'm still trying to figure out why.

    Returns
    -------
    dict:
        returns a dictionary with the following keys.
        'title'  : article title
        'text'   : article text
        'refs'   : other articles referenced in the text
        'images' : amount of images
        'videos' : amount of videos
        'topics' : all topic keywords
        'date'   : publish date
        'time'   : publish time
        'channel': labeled data channel
    """
    global data, urls, urls_collected
    
    save_url = url[:]
    urls_collected.append(save_url)

    html = requests.get(url).text
    soup = BeautifulSoup(html, 'html.parser')

    article = dict()

    try: # At some point mashable changed the style of their article urls, this checks 
         # whether an error page comes up and if so makes the required replacement.
        if str(soup.findAll('h1')[0]) == '<h1>The Bad News</h1>':
            url_sub = url[:20]+'article'+url[30:]
            html = requests.get(url_sub).text
            soup = BeautifulSoup(html, 'html.parser')
            url = url_sub
    except:
        return np.nan
    
    # get article title
    try:
        article['title'] = soup.findAll('title')[0].text
    except:
        article['title'] = np.nan

    # get article text and refrences
    try:
        section = soup.findAll("section", {"class":"article-content"})[0]
        article['text'] = section.text.replace('\n','')
        article['refs'] = [a['href'] for a in section.findAll("a") if 'href' in str(a)]
    except:
        article['text'],article['refs'] = [np.nan]*2

    # get the amount of images
    try:
        article['images'] = len(soup.findAll('img')[3:-9])
    except:
        article['images'] = np.nan
    # get the amount of videos
    try:
        article['videos'] = len(soup.findAll('iframe'))
    except:
        article['videos'] = np.nan

    # get all the labeled topics
    try:
        article['topics'] = [a.text for a in soup.findAll('footer', {'class':'article-topics'})[0].findAll('a')]
    except:
        article['topics'] = np.nan

    # get the publish date and time
    try:
        article['date'], article['time'] = soup.findAll('time')[0].text.split(" ")[:-1]
    except:
        article['date'], article['time'] = [np.nan]*2

    # get the labled data channel
    try:
        article['channel'] = soup.findAll('article',{'class':'full post story'})[0]['data-channel']
    except:
        article['channel'] = np.nan

    # put everything together
    data[save_url] = article
    print('\r%d/%d Articles Collected (%.2f%%)' % (len(data),len(urls),len(data)/len(urls) * 100),end="")

async def get_data_asynchronus(urls):
    with ThreadPoolExecutor(max_workers=40) as executor:
        with requests.Session() as session:
            loop = asyncio.get_event_loop()
            tasks = [
                loop.run_in_executor(
                    executor,
                    fetch,
                    *(url,session),
                )
                for url in urls
            ]
            for response in await asyncio.gather(*tasks):
                pass

def main(urls):
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(get_data_asynchronus(urls))
    loop.run_until_complete(future)

#-- Script ----------------------------------------------------------------------------------------------------------------------------------------
urls = pd.read_csv('Data/OnlineNewsPopularity.csv')['url']
save_path = 'Data/Raw.csv'

# empty dict for article entries
data = dict()
# empty list for all collected urls
urls_collected = []

while len(urls_collected) != len(urls):
    urls_to_be_collected = urls.drop(urls_collected)
    main(urls_to_be_collected)
    print('\r%d/%d Articles Collected (%.2f%%)' % (len(urls_collected),len(urls_collected),len(data)/len(urls) * 100),end="")
print("\nProcess Complete")

# put in dataframe
final = pd.DataFrame(data).T
# and save to csv
final.to_csv(save_path)