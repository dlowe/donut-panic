import datetime
import random
import uuid

import tornado.options
import tornado.ioloop
import tornado.httpserver
import tornado.web
import tornado.websocket

from tornado.options import define
define("port", default=5000, help="port", type=int)

GAMES = {}

class Slime:
    def __init__(self, game):
        self.game = game
        self.name = "slime"
        self.x, self.y = self.game.random_empty_spot()
        self.x += 0.25
        self.y += 0.25
        self.width = 0.5 # blocks
        self.height = 0.5 # blocks
        self.facing = "down"
        self.alive = True
        self.despawn_at = None

    def tick(self):
        pass

    def splat(self):
        self.alive = False
        self.name = "splat"
        self.despawn_at = datetime.datetime.now() + datetime.timedelta(0, 10)

    def should_despawn(self):
        return (self.despawn_at is not None) and (self.despawn_at <= datetime.datetime.now())

class Player:
    def __init__(self, game, player_id):
        self.game = game
        self.player_id = player_id
        self.x, self.y = self.game.random_empty_spot()
        self.x += 0.25
        self.y += 0.25
        self.facing = "down"
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

def within(thing, x, y):
    return ((x >= thing.x) and
            (y >= thing.y) and
            (x <= (thing.x + thing.width)) and
            (y <= (thing.y + thing.height)))

def collided(thing1, thing2):
    return (within(thing1, thing2.x, thing2.y) or
        within(thing1, thing2.x, thing2.y + thing2.height) or
        within(thing1, thing2.x + thing2.width, thing2.y) or
        within(thing1, thing2.x + thing2.width, thing2.y + thing2.height))

def make_maze(width, height):
    maze = [[1 for _ in range(width)] for _ in range(height)]

    def carve(cx, cy, maze):
        maze[cy][cx] = 0
        directions = [[0,1], [0,-1], [1,0], [-1,0]]
        random.shuffle(directions)
        for dx,dy in directions:
            ix, iy = [cx+dx, cy+dy]
            if (0 <= ix < len(maze[0])) and (0 <= iy < len(maze)) and maze[iy][ix]:
                nx, ny = [ix+dx, iy+dy]
                if (1 <= nx < (len(maze[0]) - 1)) and (1 <= ny < (len(maze) - 1)) and maze[ny][nx]:
                    print dx,dy
                    maze[iy][ix] = 0
                    carve(nx, ny, maze)

    carve(1, 1, maze)
    return maze

class Game:
    def __init__(self, game_id):
        self.game_id = game_id
        self.players = {}
        self.monsters = []
        self.loop = None
        self.width = 45
        self.height = 21
        self.last_spawn = None
        self.walls = make_maze(self.width, self.height)

    def serialized_state(self, player_id):
        return "<%s>" % " ".join(
            ["(%s:%f,%f,%s)" % ("you" if p.player_id == player_id else "other",
                p.x, p.y, p.facing) for p in self.players.values() if p.socket is not None] +
            ["(%s:%f,%f,%s)" % (m.name, m.x, m.y, m.facing) for m in self.monsters])

    def serialized_maze(self):
        return "".join(["x" if self.walls[y][x] else " " for y in range(0, self.height) for x in range(0,self.width)])

    def maybe_spawn(self):
        now = datetime.datetime.now()
        if self.last_spawn is None or ((now - self.last_spawn).total_seconds() >= 10):
            self.monsters.append(Slime(self))
            self.last_spawn = now

    def maybe_stop(self):
        for player in self.players.values():
            if player.socket is not None:
                return
        self.loop.stop()
        self.loop = None
        print "stop game %s" % self.game_id

    def random_empty_spot(self):
        x = None
        y = None
        while x is None or y is None or self.walls[y][x]:
            x = random.randrange(self.width)
            y = random.randrange(self.height)
        return x, y

    def tick(self):
        ## spawn
        self.maybe_spawn()

        ## move everything
        for player in self.players.values():
            player.tick()
        for monster in self.monsters:
            monster.tick()

        ## squished?
        for monster in self.monsters:
            if monster.alive:
                for player in self.players.values():
                    if collided(monster, player):
                        monster.splat()

        ## despawn
        self.monsters = [m for m in self.monsters if not m.should_despawn()]

        ## send updates
        for player in self.players.values():
            if player.socket is not None:
                player.socket.maybe_send_player()

    def add_player(self, player_id):
        self.players[player_id] = Player(self, player_id)

    def get_player(self, player_id):
        return self.players[player_id]

class NewGameHandler(tornado.web.RequestHandler):
    def post(self):
        game_id = "testing" ## XXX: randomize
        print "new game %s" % game_id
        if not game_id in GAMES:
            GAMES[game_id] = Game(game_id)
        self.set_header("Content-Type", "application/json")
        self.write({
            "game_id": game_id,
        })

class JoinGameHandler(tornado.web.RequestHandler):
    def post(self, game_id):
        print "[%s] join game" % game_id
        player_id = str(uuid.uuid4())
        GAMES[game_id].add_player(player_id)
        self.set_header("Content-Type", "application/json")
        self.write({
            "game_id": game_id,
            "player_id": player_id
        })

class PlayGameSocket(tornado.websocket.WebSocketHandler):
    class States:
        OPEN = 0
        MAZE_SENT = 1
        ACK_WAIT = 2
        ACKED = 3
        CLOSED = 4

    def open(self, game_id, player_id):
        self.game_id = game_id
        self.player_id = player_id
        self.game = GAMES[game_id]
        self.player = self.game.get_player(player_id)

        self.state = self.States.OPEN
        self.player.socket = self
        print "[%s/%s] new connection" % (self.game_id, self.player_id)

    def on_close(self):
        self.state = self.States.CLOSED
        print "[%s/%s] close connection" % (self.game_id, self.player_id)
        self.player.socket = None
        self.game.maybe_stop()

    def maybe_send_player(self):
        if self.state == self.States.ACKED:
            self.write_message('state: %s' % self.game.serialized_state(self.player_id))
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
                if not self.game.loop:
                    self.game.loop = tornado.ioloop.PeriodicCallback(lambda: self.game.tick(), 16)
                    self.game.loop.start()
        elif self.state == self.States.ACK_WAIT:
            if message == 'ack':
                self.state = self.States.ACKED

        if self.state == self.States.ACK_WAIT or self.state == self.States.ACKED:
            if message == 'right':
                self.player.right = True
                self.player.facing = "right"
            if message == '!right':
                self.player.right = False
            if message == 'left':
                self.player.left = True
                self.player.facing = "left"
            if message == '!left':
                self.player.left = False
            if message == 'down':
                self.player.down = True
                self.player.facing = "down"
            if message == '!down':
                self.player.down = False
            if message == 'up':
                self.player.up = True
                self.player.facing = "up"
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
