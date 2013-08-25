var game = (function () {
    var ctx;
    var ws;
    var States = {
        UNOPENED: 0,
        MAZE_WAIT: 1,
        STARTED: 3
    };
    var state = States.UNOPENED;
    var maze = {
        height: null,
        width: null,
        walls: null,
    };
    var player = {
        x: null,
        y: null,
        facing: null
    };
    var monsters = [];
    var donuts = [];
    var others = [];
    var sprites = {
        "wall": new Image(),
        "floor": new Image(),
        "player": {
            "up": new Image(),
            "down": new Image(),
            "left": new Image(),
            "right": new Image()
        },
        "donut": new Image(),
        "monsters": {
            "slime": {
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
    sprites.wall.src = "wall.png";
    sprites.floor.src = "floor.png";
    sprites.donut.src = "donut.png";
    sprites.player.up.src = "player_up.png";
    sprites.player.down.src = "player_down.png";
    sprites.player.left.src = "player_left.png";
    sprites.player.right.src = "player_right.png";
    sprites.monsters.slime.up.src = "slime.png";
    sprites.monsters.slime.down.src = "slime.png";
    sprites.monsters.slime.left.src = "slime.png";
    sprites.monsters.slime.right.src = "slime.png";
    sprites.monsters.splat.up.src = "splat.png";
    sprites.monsters.splat.down.src = "splat.png";
    sprites.monsters.splat.left.src = "splat.png";
    sprites.monsters.splat.right.src = "splat.png";

    var repaint = function(timestamp) {
        var off_x = Math.max(0, Math.min(player.x*32 - 336, maze.width*32 - 640));
        var off_y = Math.max(0, Math.min(player.y*32 - 256, maze.height*32 - 480));
        ctx.clearRect(0, 0, 640, 480);
        for (var x = 0; x < maze.width; ++x) {
            for (var y = 0; y < maze.height; ++y) {
                ctx.drawImage(sprites.floor, x*32 - off_x, y*32 - off_y, 32, 32);
                if (maze.walls[x][y]) {
                    ctx.drawImage(sprites.wall, x*32 - off_x, y*32 - off_y, 32, 32);
                }
            }
        }
        for (var i = 0; i < donuts.length; ++i) {
            var donut = donuts[i];
            ctx.drawImage(sprites.donut, donut.x*32 - off_x, donut.y*32 - off_y, 16, 16);
        }
        for (var i = 0; i < monsters.length; ++i) {
            var monster = monsters[i];
            ctx.drawImage(sprites.monsters[monster.name][monster.facing], monster.x*32 - off_x, monster.y*32 - off_y, 16, 16);
        }
        ctx.drawImage(sprites.player[player.facing], player.x*32 - off_x, player.y*32 - off_y, 16, 16);
        for (var i = 0; i < others.length; ++i) {
            var other = others[i];
            ctx.drawImage(sprites.player[other.facing], other.x*32 - off_x, other.y*32 - off_y, 16, 16);
        }
    };

    var keydown = function(e) {
        switch (e.keyCode) {
            case 37:
                ws.send("left");
                break;
            case 38:
                ws.send("up");
                break;
            case 39:
                ws.send("right");
                break;
            case 40:
                ws.send("down");
                break;
        };
    };

    var keyup = function(e) {
        switch (e.keyCode) {
            case 37:
                ws.send("!left");
                break;
            case 38:
                ws.send("!up");
                break;
            case 39:
                ws.send("!right");
                break;
            case 40:
                ws.send("!down");
                break;
        };
    }

    var message = function(msg) {
        switch (state) {
            case States.MAZE_WAIT:
                var maze_pattern = /^maze:\s+(\d+)\s+(\d+)\s+(.*)$/;
                if (result = maze_pattern.exec(msg)) {
                    maze.width = parseInt(result[1]);
                    maze.height = parseInt(result[2]);
                    maze.walls = [];
                    for (var x = 0; x < maze.width; ++x) {
                        maze.walls[x] = [];
                    }
                    for (var y = 0; y < maze.height; ++y) {
                        for (var x = 0; x < maze.width; ++x) {
                            maze.walls[x][y] = result[3].charAt(y * maze.width + x) == 'x';
                        }
                    }
                    console.log(maze.walls);
                    ws.send("ack");
                    state = States.STARTED;
                    // start paying attention to keyboard events
                    $(document).keydown(keydown);
                    $(document).keyup(keyup);
                } else {
                    throw "wtf?";
                }
                break;
            case States.STARTED:
                var state_pattern = /^state:\s*<(.*)>$/;
                if (result = state_pattern.exec(msg)) {
                    var packets = result[1].split(" ");
                    others = [];
                    monsters = [];
                    donuts = [];
                    for (var i = 0; i < packets.length; ++i) {
                        var packet_pattern = /^\((.*):(-?[\d.]+),(-?[\d.]+),(.*)\)$/;
                        if (p_result = packet_pattern.exec(packets[i])) {
                            var type = p_result[1];
                            var x = parseFloat(p_result[2]);
                            var y = parseFloat(p_result[3]);
                            var facing = p_result[4];
                            switch (type) {
                                case "you":
                                    player.x = x;
                                    player.y = y;
                                    player.facing = facing;
                                    break;
                                case "donut":
                                    donuts.push({
                                        x: x,
                                        y: y
                                    });
                                    break;
                                case "slime":
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
                                        facing: facing
                                    });
                                    break;
                            };
                        } else {
                            throw "wtf?";
                        }
                    }
                    ws.send("ack");
                    requestAnimationFrame(repaint);
                } else {
                    throw "wtf?";
                }
                break;
            default:
                throw "wtf?";
        }
    }

    return {
        start: function(host, port, game_id, player_id, canvas_context) {
                   ctx = canvas_context;
                   ws = new WebSocket("ws://" + host + ":" + port
                           + "/play-game/" + game_id + "/" + player_id);
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
