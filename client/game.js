var game = (function () {
    var ws;
    var States = {
        UNOPENED: 0,
        READY: 1,
        STARTED: 2
    };
    var state = States.UNOPENED;

    var message = function(msg) {
        switch (state) {
            case States.READY:
                if (msg.lastIndexOf('start:', 0) === 0) {
                    ws.send("started");
                    state = States.STARTED;
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
        start: function(host, port, cookie) {
                   ws = new WebSocket("ws://" + host + ":" + port + "/play-game/" + cookie);
                   ws.onopen = function() {
                       ws.send("ready");
                       state = States.READY;
                   }
                   ws.onmessage = function(event) {
                       message(event.data);
                   }
               }
    };
})();
