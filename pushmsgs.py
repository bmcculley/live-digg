#!/usr/bin/python
from bs4 import BeautifulSoup
import MySQLdb as db
import datetime
import urllib2
import redis
import json
import time


def removeNonAscii(s): return "".join(i for i in s if ord(i) < 128)


def scraper():
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor())
    opener.addheaders = [('User-agent', 'Live Digg')]
    # grab the feed
    xml = opener.open("http://digg.com/rss/top.rss").read()

    # parse the return with beautifulsoup
    soup = BeautifulSoup(xml, features="xml")
    # find all the items
    items = soup.findAll("item")

    add_date = datetime.date.today()

    # create redis and mysql connections
    r = redis.Redis()
    con = db.connect("localhost", "user", "password", "database")
    cur = con.cursor()

    # loop through the items, check whether they are already in the db
    # if not publish in redis and add to db[]
    for n, item in enumerate(items):
        title = removeNonAscii(item.find("title").text)
        description = removeNonAscii(item.find("description").text)
        link = item.find("link").text
        digg_link = item.find("guid").text
        pub_date = item.find("pubDate")
        # pretty janky way of making sure we only get stories
        if n == 43:
            break

        cur.execute(
            "select id from stories where link = '%s'" %
            db.escape_string(link))
        result_set = cur.fetchone()

        if not result_set:
            # need to build a dataset to send
            data = {
                "link": str(link),
                "title": str(title),
                "date_added": str(add_date),
                "description": str(description),
                "digg_link": str(digg_link)
            }
            r.publish('live_digg', json.dumps(data))

            cur.execute("insert into stories "
                        "(date_added, title, description, link, digg_link) "
                        "values ('%s', '%s', '%s', '%s', '%s')" % (
                            add_date,
                            db.escape_string(title),
                            db.escape_string(description),
                            db.escape_string(link),
                            db.escape_string(digg_link))
                        )
            con.commit()
            # don't go crazy pushing all the new stories in one shot
            time.sleep(1.5)

    con.close()
