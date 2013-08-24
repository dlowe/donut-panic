var game = (function () {
    var ctx;
    var ws;
    var States = {
        UNOPENED: 0,
        MAZE_WAIT: 1,
        PLAYER_WAIT: 2,
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
    };
    var entities = null;
    var sprites = {
        "wall": new Image(),
        "player": new Image(),
    }
    sprites.wall.src = "wall.png";
    sprites.player.src = "player.png";

    var repaint = function(timestamp) {
        for (var x = 0; x < maze.width; ++x) {
            for (var y = 0; y < maze.height; ++y) {
                if (maze.walls[x][y]) {
                    ctx.drawImage(sprites.wall, x*64, y*64, 64, 64);
                }
            }
        }
        ctx.drawImage(sprites.player, player.x*64, player.y*64, 64, 64);
        requestAnimationFrame(repaint);
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
                    ws.send("maze_ack");
                    state = States.PLAYER_WAIT;
                } else {
                    throw "wtf?";
                }
                break;
            case States.PLAYER_WAIT:
                var player_pattern = /^player:\s+(\d+)\s+(\d+)$/;
                if (result = player_pattern.exec(msg)) {
                    console.log(result);
                    player.x = parseInt(result[1]);
                    player.y = parseInt(result[2]);
                    ws.send("player_ack");
                    state = States.STARTED;
                    // start painting!
                    requestAnimationFrame(repaint);
                } else {
                    throw "wtf?";
                }
                break;
            case States.STARTED:
                break;
            default:
                throw "wtf?";
        }
    }

    return {
        start: function(host, port, cookie, canvas_context) {
                   ctx = canvas_context;
                   ws = new WebSocket("ws://" + host + ":" + port + "/play-game/" + cookie);
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
