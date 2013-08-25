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
    var entities = null;
    var sprites = {
        "wall": new Image(),
        "floor": new Image(),
        "player": {
            "up": new Image(),
            "down": new Image(),
            "left": new Image(),
            "right": new Image()
        }
    }
    sprites.wall.src = "wall.png";
    sprites.floor.src = "floor.png";
    sprites.player.up.src = "player_up.png";
    sprites.player.down.src = "player_down.png";
    sprites.player.left.src = "player_left.png";
    sprites.player.right.src = "player_right.png";

    var repaint = function(timestamp) {
        var off_x = Math.max(0, Math.min(player.x*32 - 336, maze.width*32 - 640));
        var off_y = Math.max(0, Math.min(player.y*32 - 256, maze.height*32 - 480));
        ctx.clearRect(0, 0, 640, 480);
        for (var x = 0; x < maze.width; ++x) {
            for (var y = 0; y < maze.height; ++y) {
                if (maze.walls[x][y]) {
                    ctx.drawImage(sprites.wall, x*32 - off_x, y*32 - off_y, 32, 32);
                } else {
                    ctx.drawImage(sprites.floor, x*32 - off_x, y*32 - off_y, 32, 32);
                }
            }
        }
        ctx.drawImage(sprites.player[player.facing], player.x*32 - off_x, player.y*32 - off_y, 16, 16);
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
                    console.log(result);
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
                var player_pattern = /^player:\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(.*)$/;
                if (result = player_pattern.exec(msg)) {
                    ws.send("ack");
                    player.x = parseFloat(result[1]);
                    player.y = parseFloat(result[2]);
                    player.facing = result[3];
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
