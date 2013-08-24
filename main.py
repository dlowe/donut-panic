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

GAMES = {}

def game_tick(game_id):
    ## move everything
    for player in GAMES[game_id]["players"].values():
        if player["right?"]:
            player["x"] += 0.03
        if player["up?"]:
            player["y"] -= 0.03
        if player["left?"]:
            player["x"] -= 0.03
        if player["down?"]:
            player["y"] += 0.03
    ## send updates
    for player in GAMES[game_id]["players"].values():
        player["socket"].maybe_send_player()

class NewGame(tornado.web.RequestHandler):
    def post(self):
        print "new game"
        game_id = "testing" ## XXX: randomize
        GAMES[game_id] = {
            "players": {},
            "tick": lambda: game_tick(game_id),
            "started": False,
            "width": 20,
            "height": 20,
            "maze": "".join( ## XXX: randomize
                    ['xxxxxxxxxxxxxxxxxxxx',
                     'x                  x',
                     'x                  x',
                     'x                  x',
                     'x                  x',
                     'x                  x',
                     'x                  x',
                     'x                  x',
                     'x                  x',
                     'x                  x',
                     'x                  x',
                     'x                  x',
                     'x                  x',
                     'x                  x',
                     'x                  x',
                     'x                  x',
                     'x                  x',
                     'x                  x',
                     'x                  x',
                     'xxxxxxxxxxxxxxxxxxxx',])
        }
        self.set_header("Content-Type", "application/json")
        self.write({
            "game_id": "testing",
        })

class JoinGame(tornado.web.RequestHandler):
    def post(self, game_id):
        print "[%s] join game" % game_id
        player_id = "cookie" ## XXX: randomize
        GAMES[game_id]["players"][player_id] = {
            ## XXX: randomize
            "x": 2.0,
            "y": 2.0,
            "up?": False,
            "down?": False,
            "left?": False,
            "right?": False,
            "socket": None,
        }
        self.set_header("Content-Type", "application/json")
        self.write({
            "host": tornado.options.options.host,
            "port": tornado.options.options.port,
            "game_id": game_id,
            "player_id": player_id
        })

class PlayGame(tornado.websocket.WebSocketHandler):
    class States:
        OPEN = 0
        MAZE_SENT = 1
        ACK_WAIT = 2
        ACKED = 3

    def open(self, game_id, player_id):
        self.game_id = game_id
        self.player_id = player_id
        self.state = self.States.OPEN
        GAMES[game_id]["players"][player_id]["socket"] = self
        print "[%s/%s] new connection" % (self.game_id, self.player_id)

    def maybe_send_player(self):
        if self.state == self.States.ACKED:
            self.write_message('player: %f %f' % (GAMES[self.game_id]["players"][self.player_id]["x"],
                GAMES[self.game_id]["players"][self.player_id]["y"]))
            self.state = self.States.ACK_WAIT

    def on_message(self, message):
        # print "[%s/%s] new message %s" % (self.game_id, self.player_id, message)
        if self.state == self.States.OPEN:
            if message == 'ready':
                self.write_message('maze: %d %d %s' % (GAMES[self.game_id]["width"],
                    GAMES[self.game_id]["height"],
                    GAMES[self.game_id]["maze"]))
                self.state = self.States.MAZE_SENT
        elif self.state == self.States.MAZE_SENT:
            if message == 'ack':
                self.state = self.States.ACKED
                if not GAMES[self.game_id]["started"]:
                    tornado.ioloop.PeriodicCallback(GAMES[self.game_id]["tick"], 16).start()
                    GAMES[self.game_id]["started"] = True
        elif self.state == self.States.ACK_WAIT:
            if message == 'ack':
                self.state = self.States.ACKED

        if self.state == self.States.ACK_WAIT or self.state == self.States.ACKED:
            if message == 'right':
                GAMES[self.game_id]["players"][self.player_id]["right?"] = True
            if message == '!right':
                GAMES[self.game_id]["players"][self.player_id]["right?"] = False
            if message == 'left':
                GAMES[self.game_id]["players"][self.player_id]["left?"] = True
            if message == '!left':
                GAMES[self.game_id]["players"][self.player_id]["left?"] = False
            if message == 'down':
                GAMES[self.game_id]["players"][self.player_id]["down?"] = True
            if message == '!down':
                GAMES[self.game_id]["players"][self.player_id]["down?"] = False
            if message == 'up':
                GAMES[self.game_id]["players"][self.player_id]["up?"] = True
            if message == '!up':
                GAMES[self.game_id]["players"][self.player_id]["up?"] = False

if __name__ == "__main__":
    handlers = [
        (r"/", Index),
        (r"/api/new-game", NewGame),
        (r"/api/join-game/(.*)", JoinGame),
        (r"/play-game/([^/]+)/(.*)", PlayGame),
        (r"/(.*)", tornado.web.StaticFileHandler, {"path": './client/'}),
    ]

    tornado.options.parse_command_line()
    server = tornado.web.Application(handlers,
            debug = True,
            static_path = './client/')
    server.listen(tornado.options.options.port)
    tornado.ioloop.IOLoop.instance().start()
