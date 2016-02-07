#!/usr/bin/env python
# xwiebelbot. small script to explain ticket links for #tails-dev
# loosely based on weasels ticketbot plugin for supybot
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
###

import sys
import sleekxmpp
import re
import BeautifulSoup
import urllib2
import time
import getpass
from optparse import OptionParser
import logging

if sys.version_info < (3, 0):
    reload(sys)
    sys.setdefaultencoding('utf8')
else:
    raw_input = input

class MUCBot(sleekxmpp.ClientXMPP):

    def __init__(self, jid, password, room, nick):
        sleekxmpp.ClientXMPP.__init__(self, jid, password)
        self.nick = nick

        self.add_event_handler("session_start", self.session_start)
        self.add_event_handler("groupchat_message", self.groupchat_message)

    def session_start(self,event):
        self.send_presence()
        for channel in opts.channel:
            logging.debug('Joining channel ' + channel)
            self.plugin['xep_0045'].joinMUC(channel, self.nick, wait=True)

    def groupchat_message(self, msg):
        if msg['mucnick'] != self.nick:
            logging.debug('Got a Groupchat Messsage.')
            self.parsemsg(msg)

    def parsemsg(self, msg):
        logging.debug('Parsing Groupchat Message.')
        room = msg['from'].bare
        for key in self.parsearray.keys():
            logging.debug('Checking Groupchat Message for ' + key)
            for match in re.findall(self.parsearray[key]['re'], msg['body']):
                logging.info('Found match for '+key+' in Groupchat message.')
                url = self.parsearray[key]['url'] + match[1]
                if url in self.urlcache:
                    logging.debug('URL is in cache')
                    if room in self.urlcache[url]['rooms']:
                        logging.debug(self.urlcache[url]['rooms'])
                        if self.urlcache[url]['rooms'][room]['timestamp'] + self.deduptime < time.time():
                            #logging.debug('URL timestamp %f is less than %f - %f', self.urlcache[url]['rooms'][room]['timestamp'], time.time(), self.deduptime)
                            title = self.urlcache[url]['title']
                            self.urlcache[url]['rooms'][room]['timestamp'] = time.time()
                            self.send_message(mto=room, mbody="%s %s %s %s" %(key, u"\u263A", title, url), mtype='groupchat')
                    else:
                        logging.debug('Adding url with another room to urlcache.')
                        title = self.urlcache[url]['title']
                        self.urlcache[url]['rooms'][room] = {'timestamp': time.time() }
                        self.send_message(mto=msg['from'].bare, mbody="%s %s %s %s" %(key, u"\u263A", title, url), mtype='groupchat')
                else:
                    logging.debug('URL not yet in cache')
                    title = self.fixtitle(self.gettitlefromhtml(url, room))
                    self.send_message(mto=room, mbody="%s %s %s %s" %(key, u"\u263A", title, url), mtype='groupchat')

    def gettitlefromhtml(self, url, room):

        try:
            response = urllib2.urlopen(url)
        except urllib2.HTTPError as e:
            raise IndexError(e)

        data = response.read()

        charset = response.headers.getparam('charset')
        if charset: data = data.decode(charset)

        b = BeautifulSoup.BeautifulSoup(data, convertEntities=BeautifulSoup.BeautifulSoup.HTML_ENTITIES)
        title = b.find('title').contents[0]
        self.addtourlcache(url, title, room)
        return title

    def addtourlcache(self, url, title, room):
        if url not in self.urlcache:
            logging.info(url + ' is not in urlcache yet.')
            self.checklength()
            rooms = { room: {'timestamp': time.time() } }
            self.urlcache[url] = {'title': title, 'rooms': rooms }

    def checklength(self):
        logging.debug('Checking the length of the urlcache dict.')
        if len(self.urlcache) >= self.cachesize:
            ts = time.time()
            for url in self.urlcache:
                for room in self.urlcache[url]['rooms']:
                    avgts += self.urlcache[url]['rooms'][room]['timestamp']
                if avgts < ts:
                    remkey = url
                    ts = avgts
            self.urlcache.pop(remkey)

    def fixtitle(self, title):
        #title = title.replace("\n", "")
        title = re.sub( '\s+', ' ', title ).strip()
        title = title.replace(" - Tails - RiseupLabs Code Repository", "")
        title = title.replace("- Debian Bug report logs", "")
        title = title.replace(" Tor Bug Tracker & Wiki ", "")
        return title


if __name__ == '__main__':

    optp = OptionParser()
    optp.add_option('-q', '--quiet', help='set logging to ERROR',
            action='store_const', dest='loglevel',
            const=logging.ERROR, default=logging.INFO)
    optp.add_option('-d', '--debug', help='set logging to DEBUG',
            action='store_const', dest='loglevel',
            const=logging.DEBUG, default=logging.INFO)
    optp.add_option('-v', '--verbose', help='set logging to COMM',
            action='store_const', dest='loglevel',
            const=5, default=logging.INFO)

    optp.add_option('-j', '--jid', dest='jid', help='JID to use')
    optp.add_option('-p', '--pass', dest='password', help='password to use')
    optp.add_option('-c', '--channel', action="append", dest='channel', help='Channel to join')
    optp.add_option('-n', '--nick', dest='nick', help='Nickname to use')

    opts, args = optp.parse_args()
    if opts.jid is None:
        opts.jid = raw_input("Jid: ")
    if opts.password is None:
        opts.password = getpass.getpass("Password: ")
    if opts.channel is None:
        opts.channel = raw_input("Channel: ")
    if opts.nick is None:
        opts.nick = raw_input("Nick: ")

    xmpp = MUCBot(opts.jid, opts.password, opts.channel, opts.nick)
    xmpp.use_signals(signals=["SIGHUP", "SIGTERM", "SIGINT"])
    xmpp.register_plugin('xep_0030') # Service Discovery
    xmpp.register_plugin('xep_0045') # Multi-User Chat
    xmpp.register_plugin('xep_0199') # XMPP Ping
    xmpp.debug = False
    xmpp.parsearray = {
            'Tails': { 
                're': r'(^#|#|[tT]ails#|https://labs.riseup.net/code/issues/)([0-9]{3,5})', 
                'url': 'https://labs.riseup.net/code/issues/' },
            'Debian': { 
                're': '([dD]ebian#|https://bugs.debian.org/cgi-bin/bugreport.cgi\?bug=)([0-9]{3,6})', 
                'url': 'https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=' },
            'Tor': {
                're': '([tT]or#|https://trac.torproject.org/projects/tor/ticket/)([0-9]{3,5})',
                'url': 'https://trac.torproject.org/projects/tor/ticket/' },
            'Mat': {
                're': r'([mM]at#)([0-9]{3,5})', 
                'url': 'https://labs.riseup.net/code/issues/' },
            }
    xmpp.urlcache = {}
    xmpp.cachesize = 50
    xmpp.deduptime = 1800
    logging.basicConfig(level=opts.loglevel, 
            format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
            datefmt='%m-%d %H:%M',
            filename='xwiebelbot.log',
            filemode='w')

    if xmpp.connect():
        xmpp.process(block=True)
        print("Done")
    else:
        print("Unable to connect.")
