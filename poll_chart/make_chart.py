import BeautifulSoup
import logging
import datetime
import traceback

from urllib import quote_plus

from google.appengine.ext import db
from google.appengine.api.urlfetch import DownloadError

import gae_tools
import poll_chart.parsing

__author__ = 'egor83, egor.ryabkov()gmail.com'

def create_chart(thread_id, chart_type, show_percents):
    poll_data = get_poll_data(thread_id)

    if poll_data is not None:
        chart_url = build_chart_url(poll_data, chart_type, show_percents)
    else:
        logging.error('No data fetched for thread %s', thread_id)
        raise NoDataError(thread_id)
    
    return chart_url

def build_chart_url(poll_data, chart_type, show_percents):
    """(?)Construct chart URL from (parsed?) poll data."""

    # from http://code.google.com/intl/en/apis/chart/image/docs/chart_wizard.html
    chart_url_base = "http://chart.apis.google.com/chart"

    # set the common chart arguments (shared by both types)
    chart_arguments = [
        "chco=0000FF", # color
        "chs=750x400", # size
        "".join(["chtt=", quote_plus(poll_data.title)]), # title
        ]

    votes = poll_data.votes
    votes_text = ",".join(map(str, votes))
    # "chd=t:10,50,60,80,40,60,30", # data
    chart_arguments.append("".join(["chd=t:", votes_text]))

    max_votes = max(votes)
    # scale for text format with custom range
    chart_arguments.append("chds=0,%i" % max_votes)

    labels = map(quote_plus, poll_data.options)
    if show_percents:
        labels = add_percentages(labels, poll_data.percentages)

    # set type-specific chart arguments
    if chart_type == 'pie':
        chart_arguments.extend([
            "cht=p", # chart type
            "chp=4.71" # start pie slices from top (3*pi/2 = 4.71 radians)
            ])

        labels[0] = ("chl=%s" % labels[0]) # labels
        chart_arguments.append("|".join(labels))

    else: #if chart_type == 'bar': # default option
        chart_arguments.extend([
            "cht=bhs", # chart type
            "chxt=x,y", # visible axes
            "chbh=a", # bar width and spacing - needed?
        ])

        # Y labels (would contain voting options description)
        # "chxl=1:|one|two|three"
        # data set runs top-to-bottom, and labels the other way around, so I'll
        # reverse the latter
        labels.reverse()
        labels.insert(0, "chxl=1:")
        chart_arguments.append("|".join(labels))

        # axis ranges - calculate max votes number, put here
        chart_arguments.append("chxr=0,0,%i" % max_votes)

    args_line = "&".join(chart_arguments)
    return "?".join([chart_url_base, args_line])

def add_percentages(labels, percentages):
    for idx in range(len(labels)):
        labels[idx] = "%s (%.1f%%)" % (labels[idx], percentages[idx])
    return labels

def get_poll_data(thread_id):
    """Check poll data in cache, if not present or too old - fetch and parse"""

    caching_period = datetime.timedelta(minutes = 5)
    poll_data = PollData.gql("where thread_id = :1", thread_id).get()

    if(poll_data is None or
        datetime.datetime.now() - poll_data.caching_time > caching_period):

        # no data or data too old, fetch
        logging.info('Data for thread %s not found or too old, fetching' %
                      thread_id)

        try:
            url = 'http://news.ycombinator.com/item?id=%s' % thread_id
            header = 'Crawler, contact owner at egor.ryabkov(at)gmail.com'
            page = gae_tools.gae_fetch(url, header, 5)
        except DownloadError, de:
            # return cached version or None if no cached version is present
            logging.warning('Fetching failed (DownloadError: %s), using \
cached data', de)
            return poll_data
        
        soup = BeautifulSoup.BeautifulSoup(page)

        try:
            title, options, votes = poll_chart.parsing.parse_data(soup)
        except AttributeError, ae: # not a poll or access to the old page was denied
            logging.error('Thread %s page has no poll', thread_id)
#            logging.warning(page.read())
#            logging.error(traceback.format_exc())
            if poll_data:
                logging.warning('Access (probably) denied, using cached version.')
                return poll_data
            else:
                raise NoPollError(thread_id)
        except IndexError: # not a HN page
            logging.error(
                'IndexError @ thread %s - maybe trying to parse a non-HN page?',
                thread_id)
            raise NoPollOrNotHNPageError(thread_id)

        # add percentages, adjust title with total votes count
        if votes is not None:
            total = sum(votes)
            title = ('%s (%i votes)' % (title, total))
            percentages = map(lambda x: float(100*x)/total, votes)
        else:
            percentages = None

        # trim option descriptions to 40 chars max (chart look bad otherwise)
        max_desc_len = 40
        for opt_idx in range(len(options)):
            if len(options[opt_idx]) > max_desc_len:
                options[opt_idx] = options[opt_idx][0:max_desc_len] + '...'

        if poll_data is None:
            poll_data = PollData()

        poll_data.thread_id = thread_id
        poll_data.title = str(title)
        poll_data.options = options
        poll_data.votes = votes
        poll_data.percentages = percentages
        poll_data.put()
    else:
        logging.debug('Obtained data for thread %s from cache' % thread_id)

    return poll_data


class PollData(db.Model):
    thread_id = db.StringProperty()
    caching_time = db.DateTimeProperty(auto_now=True)
    title = db.StringProperty()
    options = db.StringListProperty()
    percentages = db.ListProperty(float)
    votes = db.ListProperty(int) # int iso IntProperty, see http://goo.gl/hnDpm

class ChartBuilderError(Exception):
    pass

class NoPollError(ChartBuilderError):
    def __init__(self, thread_id):
        self.thread_id = thread_id

class NoPollOrNotHNPageError(ChartBuilderError):
    def __init__(self, thread_id):
        self.thread_id = thread_id

class NoDataError(ChartBuilderError):
    def __init__(self, thread_id):
        self.thread_id = thread_id
