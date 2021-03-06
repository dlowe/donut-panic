#!/usr/bin/env python

import datetime
import math
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

def distance(a, b):
    return math.sqrt(((b[0] - a[0]) ** 2) + ((b[1] - a[1]) ** 2))

def astar(start, goal, maze):
    closed = set()
    todo = set([start])
    came_from = {}

    def path_to(node):
        if node in came_from:
            return path_to(came_from[node]) + [node]
        else:
            return [node]

    g_score = {}
    g_score[start] = 0

    f_score = {}
    f_score[start] = g_score[start] + distance(start, goal)

    while todo:
        current = sorted(todo, cmp=lambda x,y: cmp(f_score[x], f_score[y]))[0]
        if current == goal:
            return path_to(goal)

        todo.remove(current)
        closed.add(current)
        for dx,dy in [[0,1], [0,-1], [1,0], [-1,0]]:
            nx = current[0] + dx
            ny = current[1] + dy
            neighbor = (nx, ny)
            if 0 <= nx < len(maze[0]) and 0 <= ny < len(maze) and not maze[ny][nx]:
                tentative_g_score = g_score[current] + 1
                if neighbor in closed and tentative_g_score >= g_score[neighbor]:
                    continue

                came_from[neighbor] = current
                g_score[neighbor] = tentative_g_score
                f_score[neighbor] = g_score[neighbor] + distance(neighbor, goal)

                if not neighbor in todo:
                    todo.add(neighbor)

    return None

class MoveMixin:
    def move(self):
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

class PathMixin:
    def pre_move(self):
        if len(self.path) >= 1:
            step = self.path[0]
            sx = step[0] + 0.25
            sy = step[1] + 0.25

            if sx > self.x:
                self.right = True
                self.left = False
            elif sx < self.x:
                self.left = True
                self.right = False
            else:
                self.left = False
                self.right = False
            if sy > self.y:
                self.down = True
                self.up = False
            elif sy < self.y:
                self.up = True
                self.down = False
            else:
                self.down = False
                self.up = False

    def post_move(self):
        if len(self.path) >= 1:
            step = self.path[0]
            sx = step[0] + 0.25
            sy = step[1] + 0.25

            if abs(self.x - sx) < self.speed and abs(self.y - sy) < self.speed:
                self.path = self.path[1:]

class EvilSlime(MoveMixin, PathMixin):
    def __init__(self, slime):
        self.game = slime.game
        self.name = "evilslime"
        self.x = slime.x
        self.y = slime.y
        self.maybe_fixate()
        self.speed = 0.01
        self.width = slime.width
        self.height = slime.height
        self.facing = slime.facing
        self.left = False
        self.right = False
        self.up = False
        self.down = False
        self.alive = True
        self.despawn_at = None
        self.upgrade = False

    def squirrel(self):
        self.path = astar((int(self.x), int(self.y)),
                self.game.random_empty_spot(),
                self.game.walls)

    def maybe_fixate(self):
        victims = [p for p in self.game.players.values() if p.desplat_at is not None]
        if victims:
            victim = random.choice(victims)
            self.path = astar((int(self.x), int(self.y)),
                    (int(victim.x), int(victim.y)),
                    self.game.walls)
        else:
            self.squirrel()

    def tick(self):
        if not self.path:
            self.maybe_fixate()

        self.pre_move()
        self.move()
        self.post_move()

    def splat(self, player):
        if player.splat():
            self.squirrel()
            return True
        return False

    def should_despawn(self):
        return False

    def omnomnom(self, donut):
        return False

    def maybe_upgrade(self):
        return self

class Slime(MoveMixin, PathMixin):
    def __init__(self, game, spawner):
        self.game = game
        self.name = "slime"
        self.x = spawner.x
        self.y = spawner.y
        self.x += 0.25
        self.y += 0.25
        self.maybe_fixate()
        self.speed = 0.04
        self.width = 0.5 # blocks
        self.height = 0.5 # blocks
        self.facing = "down"
        self.left = False
        self.right = False
        self.up = False
        self.down = False
        self.alive = True
        self.despawn_at = None
        self.upgrade = False

    def maybe_fixate(self):
        if self.game.donuts:
            self.objective_donut = random.randrange(0, len(self.game.donuts))
            donut = self.game.donuts[self.objective_donut]
            self.path = astar((int(self.x), int(self.y)),
                    (int(donut.x), int(donut.y)),
                    self.game.walls)

    def tick(self):
        if self.alive and self.game.donuts:
            if self.objective_donut >= len(self.game.donuts) or not self.path:
                self.maybe_fixate()

            self.pre_move()
            self.move()
            self.post_move()

    def splat(self, player):
        if player.desplat_at is None:
            self.alive = False
            self.name = "splat"
            self.despawn_at = datetime.datetime.now() + datetime.timedelta(0, 10)
            return True
        return False

    def should_despawn(self):
        return (self.despawn_at is not None) and (self.despawn_at <= datetime.datetime.now())

    def omnomnom(self, donut):
        donut.omnomnom()
        self.upgrade = True
        return True

    def maybe_upgrade(self):
        if self.upgrade:
            return EvilSlime(self)
        return self

class Player(MoveMixin):
    def __init__(self, game, player_id, nick):
        self.game = game
        self.player_id = player_id
        self.nick = nick
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
        self.events = []
        self.desplat_at = None
        self.msg = ""
        self.unsay_at = None

    def serialized_events(self):
        return "<%s>" % " ".join(self.events)

    def splat(self):
        if self.desplat_at is None:
            self.facing = "splat"
            self.up = False
            self.down = False
            self.left = False
            self.right = False
            self.desplat_at = datetime.datetime.now() + datetime.timedelta(0, 10)
            return True
        else:
            return False

    def say(self, msg):
        self.msg = msg
        self.unsay_at = datetime.datetime.now() + datetime.timedelta(0, 10)

    def tick(self):
        if self.desplat_at is None:
            self.move()

        now = datetime.datetime.now()
        if (self.desplat_at is not None) and (self.desplat_at <= now):
            self.facing = "down"
            self.desplat_at = None
        if (self.unsay_at is not None) and (self.unsay_at <= now):
            self.msg = ""
            self.unsay_at = None

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
                    maze[iy][ix] = 0
                    carve(nx, ny, maze)

    carve(1, 1, maze)
    return maze

class Donut:
    def __init__(self, coords):
        self.x, self.y = coords
        self.x += 0.25
        self.y += 0.25
        self.width = 0.5
        self.height = 0.5
        self.eaten = False
        self.should_despawn = False

    def omnomnom(self):
        self.should_despawn = True

class Spawner:
    def __init__(self, coords):
        self.x, self.y = coords
        self.width = 1.0
        self.height = 1.0

class Game:
    def __init__(self, game_id, height, width, n_donuts, n_spawners):
        self.game_id = game_id
        self.players = {}
        self.monsters = []
        self.loop = None
        self.width = width
        self.height = height
        self.last_spawn = None
        self.walls = make_maze(self.width, self.height)
        self.donuts = [Donut(self.random_empty_spot()) for _ in range(n_donuts)]
        self.spawners = [Spawner(self.random_empty_spot()) for _ in range(n_spawners)]
        self.gameover = False

    def serialized_state(self, player_id):
        return "<%s>" % " ".join(
            ["(%s:%f,%f,%s,%s,%s)" % ("you" if p.player_id == player_id else "other",
                p.x, p.y, p.facing, p.nick, p.msg.replace(" ", "_")) for p in self.players.values() if p.socket is not None] +
            ["(donut:%f,%f,_,_,_)" % (d.x, d.y) for d in self.donuts] +
            ["(%s:%f,%f,%s,_,_)" % (m.name, m.x, m.y, m.facing) for m in self.monsters])

    def serialized_point(self, x, y):
        if self.walls[y][x]:
            return "x"
        elif [True for s in self.spawners if s.x == x and s.y == y]:
            return "s"
        else:
            return " "

    def serialized_maze(self):
        return "".join([self.serialized_point(x, y) for y in range(0, self.height) for x in range(0,self.width)])

    def maybe_spawn(self):
        now = datetime.datetime.now()
        if self.last_spawn is None or ((now - self.last_spawn).total_seconds() >= 10):
            if self.last_spawn is not None:
                self.add_event("spawn")
            self.monsters.append(Slime(self, random.choice(self.spawners)))
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

    def maybe_game_over(self):
        if not self.donuts:
            self.add_event("gameover")
            self.gameover = True

    def add_event(self, event):
        for player in self.players.values():
            player.events.append(event)

    def tick(self):
        if not self.gameover:
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
                            if monster.splat(player):
                                self.add_event("splat")

            ## eaten?
            for donut in self.donuts:
                for monster in self.monsters:
                    if monster.alive:
                        if collided(donut, monster):
                            if monster.omnomnom(donut):
                                self.add_event("omnomnom")

            ## despawn
            self.monsters = [m.maybe_upgrade() for m in self.monsters if not m.should_despawn()]
            self.donuts = [d for d in self.donuts if not d.should_despawn]
            self.maybe_game_over()

        ## send updates
        for player in self.players.values():
            if player.socket is not None:
                player.socket.maybe_send_player()

    def add_player(self, player_id, nick):
        self.players[player_id] = Player(self, player_id, nick)
        self.add_event("oink")

    def get_player(self, player_id):
        return self.players[player_id]

ADJECTIVES = ["big", "red", "old", "hot", "dry", "sad", "wee"]
NOUNS = ["pig", "cup", "fox", "pot", "tub", "mug", "zoo"]

class NewGameHandler(tornado.web.RequestHandler):
    def post(self, *args, **kwargs):
        height = int(self.get_argument("height"))
        width = int(self.get_argument("width"))
        n_donuts = int(self.get_argument("n_donuts"))
        n_spawners = int(self.get_argument("n_spawners"))
        game_id = "%s-%s-%d" % (random.choice(ADJECTIVES),
                random.choice(NOUNS), random.randrange(10,100))
        print "new game %s" % game_id
        if not game_id in GAMES:
            GAMES[game_id] = Game(game_id, height, width, n_donuts, n_spawners)
        self.set_header("Content-Type", "application/json")
        self.write({
            "game_id": game_id,
        })

class JoinGameHandler(tornado.web.RequestHandler):
    def post(self, game_id):
        print "[%s] join game" % game_id
        nick = self.get_argument("nick").replace(" ", "_").replace(",",".")
        player_id = str(uuid.uuid4())
        GAMES[game_id].add_player(player_id, nick)
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
            self.write_message('state: %s%s%s' % ("gameover" if self.game.gameover else "",
                self.player.serialized_events(),
                self.game.serialized_state(self.player_id)))
            self.player.events = []
            self.state = self.States.ACK_WAIT

    def on_message(self, message):
        if self.state == self.States.OPEN:
            if message == 'ready':
                self.write_message('maze: %d %d %s' % (self.game.width,
                    self.game.height, self.game.serialized_maze()))
                self.state = self.States.MAZE_SENT
                return
        elif self.state == self.States.MAZE_SENT:
            if message == 'ack':
                self.state = self.States.ACKED
                if not self.game.loop:
                    self.game.loop = tornado.ioloop.PeriodicCallback(lambda: self.game.tick(), 16)
                    self.game.loop.start()
                return
        elif self.state == self.States.ACK_WAIT:
            if message == 'ack':
                self.state = self.States.ACKED
                return

        if self.state == self.States.ACK_WAIT or self.state == self.States.ACKED:
            if message.startswith('say: '):
                self.player.say(message[5:])
                return

            if self.player.desplat_at is None:
                if message == 'right':
                    self.player.right = True
                    self.player.facing = "right"
                elif message == '!right':
                    self.player.right = False
                elif message == 'left':
                    self.player.left = True
                    self.player.facing = "left"
                elif message == '!left':
                    self.player.left = False
                elif message == 'down':
                    self.player.down = True
                    self.player.facing = "down"
                elif message == '!down':
                    self.player.down = False
                elif message == 'up':
                    self.player.up = True
                    self.player.facing = "up"
                elif message == '!up':
                    self.player.up = False
                return

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
