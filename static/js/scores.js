function main(parentElement, teams, apiPath) {
    function get(obj, key, _default) {
        if (!obj || !obj.hasOwnProperty(key)) {
            return _default;
        }
        return obj[key];
    }

    function updateScores(scores) {
        var max = 0;
        teams.forEach(function(team) {
            var teamScore = get(scores, team, {});
            var userAgents = get(teamScore, "user_agents", 0);
            var remoteAddrs = get(teamScore, "remote_addrs", 0);
            max = Math.max(max, userAgents + remoteAddrs);
        });
        max += 5;

        teams.forEach(function(team) {
            var element = document.getElementById(team);
            if (!element) {
                return;
            }

            var teamScore = get(scores, team, {});
            var userAgents = get(teamScore, "user_agents", 0);
            var remoteAddrs = get(teamScore, "remote_addrs", 0);
            var score = userAgents + remoteAddrs;
            var percentage = max > 0 ? 100 * score / max : 0;
            element.style.height = Math.round(percentage) + "%";
        });
    }

    function scheduleFetch() {
        setTimeout(fetchScores, 1000);
    }

    function fetchScores() {
        var request = new XMLHttpRequest();
        request.open("GET", apiPath);

        request.timeout = 5000;

        request.addEventListener("error", scheduleFetch, false);
        request.addEventListener("timeout", scheduleFetch, false);
        request.addEventListener("load", function() {
            try {
                updateScores(JSON.parse(request.response));
            } finally {
                scheduleFetch();
            }
        }, false);

        request.send();
    }

    fetchScores();
};
