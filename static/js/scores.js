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

    function fetchScores() {
        fetch(apiPath)
            .then(function(response) {
                return response.json();
            })
            .then(function(scores) {
                updateScores(scores);
                setTimeout(fetchScores, 1000);
            });
    }

    fetchScores();
};
