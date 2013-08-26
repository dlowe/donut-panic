var game = (function () {
    var ctx;
    var ws;
    var on_quit;
    var States = {
        UNOPENED: 0,
        MAZE_WAIT: 1,
        STARTED: 3,
        CLOSED: 4
    };
    var error_message = null;
    var state = States.UNOPENED;
    var maze = {
        height: null,
        width: null,
        walls: null,
        spawners: null
    };
    var player = {
        x: null,
        y: null,
        facing: null,
        nick: null,
        msg: null
    };
    var monsters = [];
    var donuts = [];
    var others = [];
    var gameover = false;
    var saying = null;
    var sounds = {
        "bg": new Audio("bg.ogg"),
        "splat": new Audio("splat.ogg"),
        "omnomnom": new Audio("omnomnom.ogg"),
        "oink": new Audio("oink.ogg"),
        "spawn": new Audio("spawn.ogg"),
        "crash": new Audio("crash.ogg"),
        "gameover": new Audio("gameover.ogg")
    }
    var sprites = {
        "gameover": new Image(),
        "wall": new Image(),
        "spawner": new Image(),
        "floor": new Image(),
        "player": {
            "up": new Image(),
            "down": new Image(),
            "left": new Image(),
            "right": new Image(),
            "splat": new Image(),
        },
        "donut": new Image(),
        "monsters": {
            "slime": {
                "up": new Image(),
                "down": new Image(),
                "left": new Image(),
                "right": new Image()
            },
            "evilslime": {
                "up": new Image(),
                "down": new Image(),
                "left": new Image(),
                "right": new Image()
            },
            "splat": {
                "up": new Image(),
                "down": new Image(),
                "left": new Image(),
                "right": new Image()
            },
        }
    }
    sprites.gameover.src = "gameover.png";
    sprites.wall.src = "wall.png";
    sprites.spawner.src = "spawner.png";
    sprites.floor.src = "floor.png";
    sprites.donut.src = "donut.png";
    sprites.player.up.src = "player_up.png";
    sprites.player.down.src = "player_down.png";
    sprites.player.left.src = "player_left.png";
    sprites.player.right.src = "player_right.png";
    sprites.player.splat.src = "player_splat.png";
    sprites.monsters.slime.up.src = "slime.png";
    sprites.monsters.slime.down.src = "slime.png";
    sprites.monsters.slime.left.src = "slime.png";
    sprites.monsters.slime.right.src = "slime.png";
    sprites.monsters.evilslime.up.src = "evilslime.png";
    sprites.monsters.evilslime.down.src = "evilslime.png";
    sprites.monsters.evilslime.left.src = "evilslime.png";
    sprites.monsters.evilslime.right.src = "evilslime.png";
    sprites.monsters.splat.up.src = "splat.png";
    sprites.monsters.splat.down.src = "splat.png";
    sprites.monsters.splat.left.src = "splat.png";
    sprites.monsters.splat.right.src = "splat.png";

    var repaint = function(timestamp) {
        var off_x = Math.max(0, Math.min(player.x*32 - 336, maze.width*32 - 640));
        var off_y = Math.max(0, Math.min(player.y*32 - 256, maze.height*32 - 480));
        var di = function(s, x, y, d) {
            ctx.drawImage(s, x*32 - off_x, y*32 - off_y, d, d);
        }
        var dp = function(p) {
            // sprite
            di(sprites.player[p.facing], p.x, p.y, 16);
            // nametag
            ctx.fillStyle = "white";
            ctx.font = "8px Courier";
            ctx.fillText(p.nick, p.x*32 - off_x, p.y*32 - off_y + 25);
            // message
            if (p.msg) {
                ctx.font = "9px Courier";
                var msg_width = ctx.measureText(p.msg);
                ctx.fillRect(p.x*32 - off_x + 6, p.y*32 - off_y - 13, msg_width.width + 2, 11);
                ctx.fillStyle = "black";
                ctx.fillText(p.msg, p.x*32 - off_x + 7, p.y*32 - off_y - 5);
            }
        }
        ctx.clearRect(0, 0, 640, 480);
        for (var x = 0; x < maze.width; ++x) {
            for (var y = 0; y < maze.height; ++y) {
                di(sprites.floor, x, y, 32);
                if (maze.walls[x][y]) {
                    di(sprites.wall, x, y, 32);
                } else if (maze.spawners[x][y]) {
                    di(sprites.spawner, x, y, 32);
                }
            }
        }
        for (var i = 0; i < donuts.length; ++i) {
            var donut = donuts[i];
            di(sprites.donut, donut.x, donut.y, 16);
        }
        for (var i = 0; i < monsters.length; ++i) {
            var monster = monsters[i];
            di(sprites.monsters[monster.name][monster.facing], monster.x, monster.y, 16);
        }

        dp(player);
        for (var i = 0; i < others.length; ++i) {
            dp(others[i]);
        }

        if (gameover) {
            ctx.drawImage(sprites.gameover, 0, 0, 640, 480);
        } else if (state == States.CLOSED) {
            ctx.fillStyle = "#FFCCCC";
            ctx.font = "40px Courier";
            ctx.fillText(error_message, 20, 200);
        } else if (saying != null) {
            ctx.fillStyle = "#CCCCCC";
            ctx.font = "30px Courier";
            ctx.fillText("SAY> " + saying, 20, 400);
        }
    };

    var send = function(msg) {
        if (state != States.CLOSED) {
            ws.send(msg);
        }
    }

    var stop = function() {
        ws.onclose = function () {};
        ws.close();
        sounds["bg"].pause();
        $(document).unbind("keydown");
        $(document).unbind("keyup");
    }

    var keypress = function(e) {
        switch (e.keyCode) {
            case 113:
                stop();
                $(document).unbind("keypress");
                on_quit();
                break;
            case 116:
                saying = "";
                $(document).unbind("keypress");
                $(document).unbind("keydown");
                $(document).keypress(function (e) {
                    switch (e.keyCode) {
                        case 13:
                            send("say: " + saying);
                            saying = null;
                            $(document).unbind("keypress");
                            $(document).keypress(keypress);
                            $(document).keydown(keydown);
                            break;
                        default:
                            saying += String.fromCharCode(e.charCode);
                            break;
                    };
                });
                // $(document).unbind("keyup");
                break;
        }
    }

    var keydown = function(e) {
        switch (e.keyCode) {
            case 27:
                stop();
                $(document).unbind("keypress");
                on_quit();
                break;
            case 37:
            case 65:
                send("left");
                break;
            case 38:
            case 87:
                send("up");
                break;
            case 39:
            case 68:
                send("right");
                break;
            case 40:
            case 83:
                send("down");
                break;
        };
    };

    var keyup = function(e) {
        switch (e.keyCode) {
            case 37:
            case 65:
                send("!left");
                break;
            case 38:
            case 87:
                send("!up");
                break;
            case 39:
            case 68:
                send("!right");
                break;
            case 40:
            case 83:
                send("!down");
                break;
        };
    }

    var error = function(err) {
        state = States.CLOSED;
        error_message = err;
        console.log(err);
        stop();
        sounds["crash"].load();
        sounds["crash"].play();
        requestAnimationFrame(repaint);
    };

    var message = function(msg) {
        switch (state) {
            case States.MAZE_WAIT:
                var maze_pattern = /^maze:\s+(\d+)\s+(\d+)\s+(.*)$/;
                if (result = maze_pattern.exec(msg)) {
                    maze.width = parseInt(result[1]);
                    maze.height = parseInt(result[2]);
                    maze.walls = [];
                    maze.spawners = [];
                    for (var x = 0; x < maze.width; ++x) {
                        maze.walls[x] = [];
                        maze.spawners[x] = [];
                    }
                    for (var y = 0; y < maze.height; ++y) {
                        for (var x = 0; x < maze.width; ++x) {
                            maze.walls[x][y] = result[3].charAt(y * maze.width + x) == 'x';
                            maze.spawners[x][y] = result[3].charAt(y * maze.width + x) == 's';
                        }
                    }
                    send("ack");
                    state = States.STARTED;
                    // start music
                    sounds["bg"].load();
                    sounds["bg"].loop = true;
                    sounds["bg"].play();
                    // start paying attention to keyboard events
                    $(document).keydown(keydown);
                    $(document).keyup(keyup);
                    $(document).keypress(keypress);
                } else {
                    error("Unparseable Maze");
                }
                break;
            case States.STARTED:
                var state_pattern = /^state:\s*((gameover)?)<(.*)><(.*)>$/;
                if (result = state_pattern.exec(msg)) {
                    gameover = result[2] === "gameover";
                    if (gameover) {
                        sounds["bg"].pause();
                    }
                    var events = result[3].split(" ");
                    for (var i = 0; i < events.length; ++i) {
                        if (events[i] !== "") {
                            sounds[events[i]].load();
                            sounds[events[i]].play();
                        }
                    }
                    var packets = result[4].split(" ");
                    others = [];
                    monsters = [];
                    donuts = [];
                    for (var i = 0; i < packets.length; ++i) {
                        var packet_pattern = /^\((.*):(-?[\d.]+),(-?[\d.]+),([^,]*),([^,]*),(.*)\)$/;
                        if (p_result = packet_pattern.exec(packets[i])) {
                            var type = p_result[1];
                            var x = parseFloat(p_result[2]);
                            var y = parseFloat(p_result[3]);
                            var facing = p_result[4];
                            var nick = p_result[5];
                            var msg = p_result[6].replace(/_/g, " ");
                            switch (type) {
                                case "you":
                                    player.x = x;
                                    player.y = y;
                                    player.facing = facing;
                                    player.nick = nick;
                                    player.msg = msg;
                                    break;
                                case "donut":
                                    donuts.push({
                                        x: x,
                                        y: y
                                    });
                                    break;
                                case "slime":
                                case "evilslime":
                                case "splat":
                                    monsters.push({
                                        name: type,
                                        x: x,
                                        y: y,
                                        facing: facing
                                    });
                                    break;
                                 default:
                                    others.push({
                                        name: type,
                                        x: x,
                                        y: y,
                                        facing: facing,
                                        nick: nick,
                                        msg: msg
                                    });
                                    break;
                            };
                        } else {
                            error("Unparseable State Packet");
                        }
                    }
                    send("ack");
                    requestAnimationFrame(repaint);
                } else {
                    error("Unparseable State");
                }
                break;
            default:
                error("Unknown State");
                break;
        }
    }

    return {
        new_game: function(width, height, n_donuts, n_spawners, cb) {
                      $.ajax({
                          'url': '/api/new-game',
                          'type': 'POST',
                          'data': {
                              'width': width,
                              'height': height,
                              'n_donuts': n_donuts,
                              'n_spawners': n_spawners
                          },
                          'success': function (data) {
                              cb(data.game_id);
                          }
                      });
                  },
        join_game: function(game_id, nick, cb) {
                       $.ajax({
                           'url': '/api/join-game/' + game_id,
                           'type': 'POST',
                           'data': {
                               'nick': nick
                           },
                           'success': function (data) {
                               cb(data.game_id, data.player_id);
                           }
                       });
                   },
        start: function(host, port, game_id, player_id, canvas_context, quit) {
                   ctx = canvas_context;
                   on_quit = quit;
                   ws = new WebSocket("ws://" + host + ":" + port
                           + "/play-game/" + game_id + "/" + player_id);
                   ws.onclose = function () {
                       error("Connection Lost");
                   }
                   ws.onopen = function() {
                       ws.send("ready");
                       state = States.MAZE_WAIT;
                   }
                   ws.onmessage = function(event) {
                       message(event.data);
                   }
               }
    };
})();
