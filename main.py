import tornado.options
import tornado.ioloop
import tornado.httpserver
import tornado.web

from tornado.options import define
define("port", default=5000, help="port", type=int)

if __name__ == "__main__":
    handlers = [
            (r"/(.*)", tornado.web.StaticFileHandler, {"path": "index.html"}),
            ]

    tornado.options.parse_command_line()
    server = tornado.web.Application(handlers, debug=True)
    server.listen(tornado.options.options.port)
    tornado.ioloop.IOLoop.instance().start()
