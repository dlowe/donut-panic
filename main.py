import tornado.options
import tornado.ioloop
import tornado.httpserver
import tornado.web
import tornado.websocket

from tornado.options import define
define("host", default="localhost", help="host", type=str)
define("port", default=5000, help="port", type=int)

class NewGame(tornado.web.RequestHandler):
    def post(self):
        print "new game"
        self.set_header("Content-Type", "application/json")
        self.write({"game_id": "testing"})

class JoinGame(tornado.web.RequestHandler):
    def post(self, game_id):
        self.set_header("Content-Type", "application/json")
        self.write({
            "host": tornado.options.options.host,
            "port": tornado.options.options.port,
            "cookie": "testing-cookie",
        })

class PlayGame(tornado.websocket.WebSocketHandler):
    def open(self, thingy):
        print "new connection %s" % thingy

    def on_message(self, message):
        print "new message %s" % message
        self.write_message(u"You said: " + message)

if __name__ == "__main__":
    handlers = [
        (r"/api/new-game", NewGame),
        (r"/api/join-game/(.*)", JoinGame),
        (r"/play-game/(.*)", PlayGame),
        (r"/(.*)", tornado.web.StaticFileHandler, {"path": "index.html"}),
    ]

    tornado.options.parse_command_line()
    server = tornado.web.Application(handlers, debug=True)
    server.listen(tornado.options.options.port)
    tornado.ioloop.IOLoop.instance().start()
