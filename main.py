import tornado.options
import tornado.ioloop
import tornado.httpserver
import tornado.web
import tornado.websocket

from tornado.options import define
define("host", default="localhost", help="host", type=str)
define("port", default=5000, help="port", type=int)

class Index(tornado.web.RequestHandler):
    def get(self):
        self.render("client/index.html")

class NewGame(tornado.web.RequestHandler):
    def post(self):
        print "new game"
        self.set_header("Content-Type", "application/json")
        self.write({
            "game_id": "testing",
        })

class JoinGame(tornado.web.RequestHandler):
    def post(self, game_id):
        print "join game"
        self.set_header("Content-Type", "application/json")
        self.write({
            "host": tornado.options.options.host,
            "port": tornado.options.options.port,
            "cookie": "testing-cookie",
        })

class PlayGame(tornado.websocket.WebSocketHandler):
    class States:
        OPEN = 0
        READY = 1
        STARTED = 2

    def open(self, cookie):
        self.cookie = cookie
        self.state = self.States.OPEN
        print "[%s] new connection" % cookie

    def on_message(self, message):
        print "[%s] new message %s" % (self.cookie, message)
        if message == 'ready':
            if self.state == self.States.OPEN:
                self.write_message('start: 2 2 xxxx')
                self.state = self.States.READY
            else:
                raise Exception('wtf?')
        elif message == 'started':
            if self.state == self.States.READY:
                self.state = self.States.STARTED
            else:
                raise Exception('wtf?')
        else:
            self.write_message(u"You said: " + message)

if __name__ == "__main__":
    handlers = [
        (r"/", Index),
        (r"/api/new-game", NewGame),
        (r"/api/join-game/(.*)", JoinGame),
        (r"/play-game/(.*)", PlayGame),
        (r"/(.*)", tornado.web.StaticFileHandler, {"path": './client/'}),
    ]

    tornado.options.parse_command_line()
    server = tornado.web.Application(handlers,
            debug = True,
            static_path = './client/')
    server.listen(tornado.options.options.port)
    tornado.ioloop.IOLoop.instance().start()
