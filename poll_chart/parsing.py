import re

def parse_data(soup):
    """Parse the page, return a list of voting options and a list of votes."""

    # How should I store data? List of tuples looks more logical, but I'll have
    # to split it in two lists later anyway, when preparing the data for the
    # chart; however, storing data in two lists and assuming that elements with
    # the same indices would denote the same option doesn't seem to be the
    # best idea
    votes, options = [], []

#    1) find the second voting option in the post (<a> tag with id starting with
#       "up_"; the first option is voting for the post itself); its 3x
#       grandparent is the <tr> tag containing the votiong option text; pass it
#       on to get_votes()
#    2) that <tr>'s third next sibling is the next voting option's <tr>;
#       get its votes
#    3) repeat until the next option is None
    title = soup.html.head.title.contents[0]
    title = title.replace('Hacker News | Poll: ', '')

    vote_option_tag = get_first_voting_option(soup)
    while vote_option_tag is not None:
        option, vote = get_votes(vote_option_tag)
        options.append(option)
        votes.append(vote)
        vote_option_tag = get_next_voting_option(vote_option_tag)

    return title, options, votes

def get_first_voting_option(soup):
    """Return the tag containing the first voting option from the page's soup."""

    # First occurence is the upvote for the post itself, return the second
    a_tag = soup.html.body.findAll('a', id=re.compile('^up_'))[1]
    return a_tag.parent.parent.parent # <tr> containing the description

def get_next_voting_option(tag):
    # for the last voting option this would return None
    return tag.nextSibling.nextSibling.nextSibling

def get_votes(tag):
    """Return the tuple: a text of a voting option and the number of votes.

    Input is the <tr> tag containing the option text; next <tr> contains the
    number of votes, and the following one is the delimiter from the next
    option.

    """

    text = str(tag.find('font').contents[0])

    votes_tag = tag.nextSibling
    if votes_tag is not None:
        # smth like '336 points'
        votes_string = votes_tag.find('span',
                                      id=re.compile('^score_')).contents[0]
        votes = int(votes_string.split(' ')[0])
    else: # couldn't find number of votes, the post is probably not a poll
        text = None
        votes = 0

    return text, votes
