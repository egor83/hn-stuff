import urllib2
import logging

from google.appengine.api.urlfetch import DownloadError

def gae_fetch(url, header = None, maxreload = 3):
    # construct custom opener IF custom header is given
    if header is not None:
        opener = urllib2.build_opener()
##        header example:
##        'Crawler, contact owner at egor.ryabkov(at)gmail.com'
        opener.addheaders = [('User-agent', header)]
        gae_opener = opener.open # custom opener version
    else:
        gae_opener = urllib2.urlopen

    count = 0
    page = None
    while count < maxreload:
        try:
##            raise DownloadError('testing') # testing
            page = gae_opener(url)
            break
        except DownloadError, de:
            logging.error("A DownloadError (%s) has occurred while fetching, "
                          "repeating" % de)
            errorMsg = de
            count += 1
            if count >= maxreload:
                raise DownloadError(errorMsg)

    return page
