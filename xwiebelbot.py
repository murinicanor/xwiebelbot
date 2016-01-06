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

import sleekxmpp
import re
import BeautifulSoup
import urllib2
import time
import getpass
from optparse import OptionParser

class MUCBot(sleekxmpp.ClientXMPP):

    def __init__(self, jid, password, room):
        sleekxmpp.ClientXMPP.__init__(self, jid, password)
        self.nick, self.domain = str(jid).split('@')

        self.add_event_handler("session_start", self.start)
        self.add_event_handler("groupchat_message", self.muc_message)

    def log(self, message):
        if self.debug is True:
            print(message)

    def start(self,event):
        self.plugin['xep_0045'].joinMUC(opts.channel, self.nick, wait=True)

    def muc_message(self, msg):
        if msg['mucnick'] != self.nick:
            #self.log("message!")
            self.parsemsg(msg)

    def parsemsg(self, msg):
        for key in self.parsearray.keys():
            for match in re.findall(self.parsearray[key]['re'], msg['body']):
                url = self.parsearray[key]['url'] + match[1]
                title = self.fixtitle(self.gettitlefromhtml(url))
                self.send_message(mto=msg['from'].bare, mbody="%s %s %s %s" %(key, u"\u2764", title, url), mtype='groupchat')

    def gettitlefromhtml(self, url):
        if url in self.urlcache:
            return self.urlcache[url]['title']

        try:
            response = urllib2.urlopen(url)
        except urllib2.HTTPError as e:
            raise IndexError(e)

        data = response.read()

        charset = response.headers.getparam('charset')
        if charset: data = data.decode(charset)

        b = BeautifulSoup.BeautifulSoup(data, convertEntities=BeautifulSoup.BeautifulSoup.HTML_ENTITIES)
        title = b.find('title').contents[0]
        self.addtourlcache(url, title)
        return title

    def addtourlcache(self, url, title):
        if url not in self.urlcache:
            self.log(url + " not yet in urlcache")
            self.checklength()
            self.urlcache[url] = {'title': title, 'timestamp': time.time() }

    def checklength(self):
        self.log("checking length")
        if len(self.urlcache) >= self.cachesize:
            ts = time.time()
            for key in self.urlcache:
                if self.urlcache[key]['timestamp'] < ts:
                    remkey = key
                    ts = self.urlcache[key]['timestamp']
            self.urlcache.pop(remkey)

    def fixtitle(self, title):
        title = title.replace(" - Tails - RiseupLabs Code Repository", "")
        title = title.replace("- Debian Bug report logs", "")
        return title


if __name__ == '__main__':

    optp = OptionParser()
    # --debug not in use
    optp.add_option('-d', '--debug', dest='debug', help='set logging to DEBUG')
    optp.add_option('-j', '--jid', dest='jid', help='JID to use')
    optp.add_option('-p', '--pass', dest='password', help='password to use')
    optp.add_option('-c', '--channel', dest='channel', help='Channel to join')

    opts, args = optp.parse_args()
    if opts.jid is None:
        opts.jid = raw_input("Jid: ")
    if opts.password is None:
        opts.password = getpass.getpass("Password: ")
    if opts.channel is None:
        opts.channel = raw_input("Channel: ")

    xmpp = MUCBot(opts.jid, opts.password, opts.channel)
    xmpp.use_signals(signals=["SIGHUP", "SIGTERM", "SIGINT"])
    xmpp.register_plugin('xep_0045') # group chat
    xmpp.debug = False
    xmpp.parsearray = {
            'Tails': { 
                're': r'([tT]ails#|https://labs.riseup.net/code/issues/)([0-9]{4,})', 
                'url': 'https://labs.riseup.net/code/issues/' },
            'Debian': { 
                're': '([dD]ebian#|https://bugs.debian.org/cgi-bin/bugreport.cgi\?bug=)([0-9]{6,})', 
                'url': 'https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=' }
            }
    xmpp.urlcache = {}
    xmpp.cachesize = 50

    if xmpp.connect():
        xmpp.process(block=True)
        print("Done")
    else:
        print("Unable to connect.")
