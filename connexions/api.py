import cgi
import datetime
import  time
import sha
import sys
import urllib
import urllib2
from BeautifulSoup.BeautifulSoup import BeautifulSoup as BS
from google.appengine.ext import db
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import mail
from google.appengine.ext import webapp
class Users(db.Model):
    username = db.StringProperty()
    useremail = db.StringProperty(multiline=True)
    slideshow_id = db.IntegerProperty()
    slideshow_uploaded_at = db.DateTimeProperty()
    last_checked_at = db.DateTimeProperty(auto_now_add=True)
    to_be_scanned = db.BooleanProperty()

class SlideShareApi:
    def __init__(self,params_as_dict,proxy=None):
        if ('api_key' not in params_as_dict) or ('api_secret' not in params_as_dict):
            print >> sys.stderr, "API Key and Secret Missing"
            return 0
        if proxy:
            self.use_proxy = True
            if not isinstance(proxy,dict):
                print >> sys.stderr," Proxy Config should be a dictionary"
                return 0
            self.proxy = proxy
        else:
            self.use_proxy = False

        self.params = params_as_dict
        if self.use_proxy:
            self.setup_proxy()

    def set_api_parameters(self,encode = True, **args):
        timestamp = int(time.time())
        all_params = {'api_key' : self.params['api_key'],'ts' :
                timestamp,'hash' : sha.new(self.params['api_secret'] + str(timestamp)).hexdigest()}
        for argument in args:
            if argument != 'slideshare_src':
                all_params[argument] = args[argument]
        if encode:
            return urllib.urlencode(all_params)
        else:
            return all_params

    def setup_proxy(self):
        proxy_support = urllib2.ProxyHandler({'http':'http://%(username)s:%(password)s@%(host)s:%(port)s'%self.proxy})
        proxy_opener = urllib2.build_opener(proxy_support, urllib2.HTTPHandler)
        urllib2.install_opener(proxy_opener)

    def get_slideshow_by_user(self,username_for):
        params = self.set_api_parameters()
        url = "http://www.slideshare.net/api/2/get_slideshows_by_user?username_for=" + str(username_for)
        data = urllib2.urlopen(url,params).read()
        soup = BS(data)
        return soup


    def get_slideshow_info(self,slideshow_id):
        params = self.set_api_parameters(encode=True,slideshow_id=str(slideshow_id))
        data = urllib2.urlopen("http://www.slideshare.net/api/2/get_slideshow", params).read()
        soup = BS(data)
        #status = soup.find('status').string
        return soup

    def get_detailed_info(self,slideshow_id):
        params = self.set_api_parameters(encode=True,slideshow_id=str(slideshow_id),detailed=1,get_transcript=1)
        data = urllib2.urlopen("http://www.slideshare.net/api/2/get_slideshow", params).read()
        soup = BS(data)
        return soup


def get_slideshow_status(soup):
    return soup.find('status').string
    """<Status>{ 0 if queued for conversion, 1 if converting, 2 if converted,
            3 if conversion failed }</Status>"""


def get_download_link(soup):
    try:
        return soup.find('downloadurl').string
    except:
        return "No Download link generated yet"


def get_transcript(soup):
    try:
        return soup.find('transcript').string
    except:
        return ""

def show_slideshow(slideshow_id):
    ss_api = SlideShareApi({"api_key":"oQO2stCt", "api_secret":"CnaNZzxx"})
    return ss_api.get_slideshow_info(slideshow_id)

def get_details(slideshow_id):
    ss_api = SlideShareApi({"api_key":"oQO2stCt", "api_secret":"CnaNZzxx"})
    return ss_api.get_detailed_info(slideshow_id)

def get_slideshow_url(soup):
	return soup.find('url').string

def api_key(api_key=None):
    return db.Key.from_path('Api', api_key or 'default_api')

def send_mail(subject="Slideshow Converted", send_to="saketkc@gmail.com", body="test", slideshow_id="1213"):
    message = mail.EmailMessage(sender="Connexions OERPUB <saketkc@gmail.com>",
                            subject="Slideshow Converted")
    message.to = send_to
    message.cc = "saketkc@gmail.com"
    message.html = body
    message.send()

class MainPage(webapp.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write('Hello, webapp World!')
        users = db.GqlQuery("SELECT * FROM Users ")
        self.response.out.write('Hello, webapp Worldsdfsssssss!')
        for user in users:
            if user.username:
                self.response.out.write('<b>%s</b> wrote:' % user.username)
            #else:
                self.response.out.write('An anonymous person wrote:')
                self.response.out.write('<blockquote>%s</blockquote>' % cgi.escape(user.useremail))

    def post(self):
        username = self.request.get('username')
        email = self.request.get('email')
        slideshow_id = self.request.get('slideshow_id')
        users = Users()
        users.username =  username
        users.useremail = email
        users.slideshow_id = int(slideshow_id)
        users.slideshow_uploaded_at = datetime.datetime.now()
        users.to_be_scanned = True
        users.put()

def slideshare_cron():
	users = db.GqlQuery("SELECT * FROM Users")
	for user in users:
		if user.username:
			ss_api = SlideShareApi({"api_key":"oQO2stCt", "api_secret":"CnaNZzxx"})
			soup = ss_api.get_slideshow_info(str(user.slideshow_id))
			slideshow_status = get_slideshow_status(soup)
			if str(slideshow_status) == "3":
				user.delete()
				send_mail(subject="Slideshow Conversion Failed", send_to=user.useremail,body="Your slideshow conversion to SlideShare failed. This means that the slideshare embed in the module on cnx.org will not work.Please create the module again. ",slideshow_id=str(user.slideshow_id))

			elif str(slideshow_status) == "2":
				user.delete()
				slideshow_url = get_slideshow_url(soup)
				send_mail(subject="Slideshow Conversion Successful", send_to=user.useremail,body="Your slideshow id <a href='"+str(slideshow_url) +"'>"+str(user.slideshow_id)+"</a> has been converterd successfully",slideshow_id=str(user.slideshow_id))

class SlideSharePage(webapp.RequestHandler):
    def get(self):
		slideshare_cron()
application = webapp.WSGIApplication(
                                     [('/', MainPage),('/mail',SlideSharePage),],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
