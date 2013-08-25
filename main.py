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

class Slime(MoveMixin):
    def __init__(self, game):
        self.game = game
        self.name = "slime"
        self.x, self.y = self.game.random_empty_spot()
        self.maybe_fixate()
        self.x += 0.25
        self.y += 0.25
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
                self.move()
                if abs(self.x - sx) < self.speed and abs(self.y - sy) < self.speed:
                    self.path = self.path[1:]

    def splat(self):
        self.alive = False
        self.name = "splat"
        self.despawn_at = datetime.datetime.now() + datetime.timedelta(0, 10)

    def should_despawn(self):
        return (self.despawn_at is not None) and (self.despawn_at <= datetime.datetime.now())

class Player(MoveMixin):
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
        self.move()

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

class Game:
    def __init__(self, game_id):
        self.game_id = game_id
        self.players = {}
        self.monsters = []
        self.loop = None
        self.width = 39
        self.height = 35
        self.last_spawn = None
        self.walls = make_maze(self.width, self.height)
        self.donuts = [Donut(self.random_empty_spot()) for _ in range(5)]

    def serialized_state(self, player_id):
        return "<%s>" % " ".join(
            ["(%s:%f,%f,%s)" % ("you" if p.player_id == player_id else "other",
                p.x, p.y, p.facing) for p in self.players.values() if p.socket is not None] +
            ["(donut:%f,%f,_)" % (d.x, d.y) for d in self.donuts] +
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

        ## eaten?
        for donut in self.donuts:
            for monster in self.monsters:
                if monster.alive:
                    if collided(donut, monster):
                        donut.omnomnom()

        ## despawn
        self.monsters = [m for m in self.monsters if not m.should_despawn()]
        self.donuts = [d for d in self.donuts if not d.should_despawn]

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
