import tornado.options
import tornado.ioloop
import tornado.httpserver
import tornado.web
import tornado.websocket

from tornado.options import define
define("host", default="localhost", help="host", type=str)
define("port", default=5000, help="port", type=int)

GAMES = {}

class Player:
    def __init__(self, game, player_id):
        self.game = game
        self.x = 2.0
        self.y = 2.0
        self.speed = 0.05 # in blocks
        self.width = 0.5 # in blocks
        self.height = 0.5 # in blocks
        self.up = False
        self.down = False
        self.left = False
        self.right = False
        self.socket = None

    def tick(self):
        x = self.x
        if self.right:
            x = self.x + self.speed
            for y in (self.y, self.y + self.height):
                if self.game.walls[int(y)][int(x + self.width)]:
                    x = int(x + self.width) - self.width - 0.01
        elif self.left:
            x = self.x - self.speed
            for y in (self.y, self.y + self.height):
                if self.game.walls[int(y)][int(x)]:
                    x = int(x) + 1
        self.x = x

        y = self.y
        if self.down:
            y = self.y + self.speed
            for x in (self.x, self.x + self.height):
                if self.game.walls[int(y + self.height)][int(x)]:
                    y = int(y + self.height) - self.height - 0.01
        elif self.up:
            y = self.y - self.speed
            for x in (self.x, self.x + self.height):
                if self.game.walls[int(y)][int(x)]:
                    y = int(y) + 1
        self.y = y

class Game:
    def __init__(self, game_id):
        self.game_id = game_id
        self.players = {}
        self.started = False
        self.width = 15
        self.height = 14
        ## XXX: randomize
        self.walls = [
                [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
                [1,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
                [1,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
                [1,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
                [1,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
                [1,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
                [1,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
                [1,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
                [1,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
                [1,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
                [1,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
                [1,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
                [1,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
                [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
        ]

    def serialized_maze(self):
        return "".join(["x" if self.walls[y][x] else " " for y in range(0, self.height) for x in range(0,self.width)])

    def tick(self):
        ## move everything
        for player in self.players.values():
            player.tick()

        ## send updates
        for player in self.players.values():
            player.socket.maybe_send_player()

    def add_player(self, player_id):
        self.players[player_id] = Player(self, player_id)

    def get_player(self, player_id):
        return self.players[player_id]

class NewGameHandler(tornado.web.RequestHandler):
    def post(self):
        print "new game"
        game_id = "testing" ## XXX: randomize
        GAMES[game_id] = Game(game_id)
        self.set_header("Content-Type", "application/json")
        self.write({
            "game_id": game_id,
        })

class JoinGameHandler(tornado.web.RequestHandler):
    def post(self, game_id):
        print "[%s] join game" % game_id
        player_id = "cookie" ## XXX: randomize
        GAMES[game_id].add_player(player_id)
        self.set_header("Content-Type", "application/json")
        self.write({
            "host": tornado.options.options.host,
            "port": tornado.options.options.port,
            "game_id": game_id,
            "player_id": player_id
        })

class PlayGameSocket(tornado.websocket.WebSocketHandler):
    class States:
        OPEN = 0
        MAZE_SENT = 1
        ACK_WAIT = 2
        ACKED = 3

    def open(self, game_id, player_id):
        self.game_id = game_id
        self.player_id = player_id
        self.game = GAMES[game_id]
        self.player = self.game.get_player(player_id)

        self.state = self.States.OPEN
        self.player.socket = self
        print "[%s/%s] new connection" % (self.game_id, self.player_id)

    def maybe_send_player(self):
        if self.state == self.States.ACKED:
            self.write_message('player: %f %f' % (self.player.x, self.player.y))
            self.state = self.States.ACK_WAIT

    def on_message(self, message):
        # print "[%s/%s] new message %s" % (self.game_id, self.player_id, message)
        if self.state == self.States.OPEN:
            if message == 'ready':
                self.write_message('maze: %d %d %s' % (self.game.width,
                    self.game.height, self.game.serialized_maze()))
                self.state = self.States.MAZE_SENT
        elif self.state == self.States.MAZE_SENT:
            if message == 'ack':
                self.state = self.States.ACKED
                if not self.game.started:
                    tornado.ioloop.PeriodicCallback(lambda: self.game.tick(), 16).start()
                    self.game.started = True
        elif self.state == self.States.ACK_WAIT:
            if message == 'ack':
                self.state = self.States.ACKED

        if self.state == self.States.ACK_WAIT or self.state == self.States.ACKED:
            if message == 'right':
                self.player.right = True
            if message == '!right':
                self.player.right = False
            if message == 'left':
                self.player.left = True
            if message == '!left':
                self.player.left = False
            if message == 'down':
                self.player.down = True
            if message == '!down':
                self.player.down = False
            if message == 'up':
                self.player.up = True
            if message == '!up':
                self.player.up = False

class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("client/index.html")

if __name__ == "__main__":
    handlers = [
        (r"/", IndexHandler),
        (r"/api/new-game", NewGameHandler),
        (r"/api/join-game/(.*)", JoinGameHandler),
        (r"/play-game/([^/]+)/(.*)", PlayGameSocket),
        (r"/(.*)", tornado.web.StaticFileHandler, {"path": './client/'}),
    ]

    tornado.options.parse_command_line()
    server = tornado.web.Application(handlers,
            debug = True,
            static_path = './client/')
    server.listen(tornado.options.options.port)
    tornado.ioloop.IOLoop.instance().start()
