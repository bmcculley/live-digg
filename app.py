#!/usr/bin/python
from functools import partial
from apscheduler.schedulers.tornado import TornadoScheduler
from tornado.options import define, options
from tornado import gen
import tornado.httpserver
import tornado.websocket
import tornado.escape
import tornado.ioloop
import tornado.web
import torndb
import bcrypt
import concurrent.futures
import threading
import redis
import math
import os
import pushmsgs

define("port", default=8888, help="run on the given port", type=int)
define("mysql_host", default="127.0.0.1:3306", help="database host")
define("mysql_database", default="database", help="database name")
define("mysql_user", default="username", help="database user")
define("mysql_password", default="password", help="database password")

LISTENERS = []

# A thread pool to be used for password hashing with bcrypt.
executor = concurrent.futures.ThreadPoolExecutor(2)


def redis_listener():
    r = redis.Redis()
    ps = r.pubsub()
    ps.subscribe('live_digg')
    io_loop = tornado.ioloop.IOLoop.instance()
    for message in ps.listen():
        for element in LISTENERS:
            io_loop.add_callback(partial(element.on_message, message))


class Application(tornado.web.Application):

    def __init__(self):
        handlers = [
            (r"/", HomeHandler),
            (r'/realtime/', RealtimeHandler),
            (r"/auth/register", AuthCreateHandler),
            (r"/auth/login", AuthLoginHandler),
            (r"/auth/logout", AuthLogoutHandler),
        ]
        settings = dict(
            site_title=u"Live Digg",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            ui_modules={"Entry": EntryModule},
            xsrf_cookies=True,
            cookie_secret="cookie_secret_key",
            login_url="/auth/login",
            debug=True,
        )
        super(Application, self).__init__(handlers, **settings)
        # Have one global connection to the blog DB across all handlers
        self.db = torndb.Connection(
            host=options.mysql_host, database=options.mysql_database,
            user=options.mysql_user, password=options.mysql_password)


class BaseHandler(tornado.web.RequestHandler):

    @property
    def db(self):
        return self.application.db

    def get_current_user(self):
        user_id = self.get_secure_cookie("live_digg")
        if not user_id:
            return None
        return self.db.get("SELECT * FROM users WHERE id = %s", int(user_id))

    def any_author_exists(self):
        return bool(self.db.get("SELECT * FROM users LIMIT 1"))

    # return human readable date from epoch string
    def epochToStr(epochString):
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(epochString))


class HomeHandler(BaseHandler):

    def get(self):
        # do some pagination
        prev_page = None
        next_page = None
        current_page = self.get_argument("page", 1)
        if current_page:
            current_page = int(current_page)
        items_per_page = 10
        limit_id = self.db.query("SELECT id FROM stories ORDER BY id "
                                 "DESC LIMIT 1")

        row_count = self.db.query("SELECT count(*) as count FROM stories")

        if row_count:
            row_count = int(row_count[0]["count"])
        else:
            row_count = 0

        total_pages = int(math.ceil(row_count/items_per_page)) + 1

        if current_page >= 2:
            prev_page = current_page-1
        if current_page < total_pages:
            next_page = current_page+1

        if limit_id:
            limit_id = int(limit_id[0]["id"]) + 1
        else:
            limit_id = 0

        if current_page > 1:
            limit_id = limit_id - (items_per_page * (current_page-1))

        entries = self.db.query(
            "SELECT * FROM stories where id < %i ORDER BY id "
            "DESC LIMIT 10" % limit_id)

        self.render(
            "home.html", entries=entries,
            prevpage=prev_page, nextpage=next_page
        )


class RealtimeHandler(tornado.websocket.WebSocketHandler):

    def open(self):
        LISTENERS.append(self)

    def on_message(self, message):
        self.write_message(message['data'])

    def on_close(self):
        LISTENERS.remove(self)


class AuthCreateHandler(BaseHandler):

    def get(self):
        self.render("create_user.html")

    @gen.coroutine
    def post(self):
        # if self.any_author_exists():
        #    raise tornado.web.HTTPError(400, "author already created")
        hashed_password = yield executor.submit(
            bcrypt.hashpw, tornado.escape.utf8(self.get_argument("password")),
            bcrypt.gensalt())
        author_id = self.db.execute(
            "INSERT INTO users (email, name, hashed_password) "
            "VALUES (%s, %s, %s)",
            self.get_argument("email"), self.get_argument("username"),
            hashed_password)
        self.set_secure_cookie("live_digg", str(author_id))
        self.redirect(self.get_argument("next", "/"))


class AuthLoginHandler(BaseHandler):

    def get(self):
        # If there are no authors, redirect to the account creation page.
        if not self.any_author_exists():
            self.redirect("/auth/register")
        else:
            self.render("login.html", error=None)

    @gen.coroutine
    def post(self):
        author = self.db.get(
            "SELECT * FROM users WHERE email = %s or name = %s",
            self.get_argument("email"), self.get_argument("email"))

        if not author:
            self.render("login.html", error="email not found")
            return
        hashed_password = yield executor.submit(
            bcrypt.hashpw, tornado.escape.utf8(self.get_argument("password")),
            tornado.escape.utf8(author.hashed_password))
        if hashed_password == author.hashed_password:
            self.set_secure_cookie("live_digg", str(author.id))
            self.redirect(self.get_argument("next", "/"))
        else:
            self.render("login.html", error="incorrect password")


class AuthLogoutHandler(BaseHandler):

    def get(self):
        self.clear_cookie("live_digg")
        self.redirect(self.get_argument("next", "/"))


class EntryModule(tornado.web.UIModule):

    def render(self, entry):
        return self.render_string("modules/entry.html", entry=entry)


if __name__ == "__main__":
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    scheduler = TornadoScheduler()
    scheduler.add_job(pushmsgs.scraper, 'cron', day_of_week='mon-fri',
                      hour='*', minute='*/15', id="diggScraper")
    scheduler.start()

    print('Press Ctrl+{0} to exit'.format('Break' if os.name == 'nt' else 'C'))
    try:
        threading.Thread(target=redis_listener).start()
        tornado.ioloop.IOLoop.current().start()
    except (KeyboardInterrupt, SystemExit):
        pass
