function main(parentElement, teams, apiPath) {
    var elements = {};

    teams.forEach(function(team) {
        var element = document.createElement("div");
        element.className = "team " + team;
        elements[team] = element;
        parentElement.appendChild(element);
    });

    function get(obj, key, _default) {
        if (!obj || !obj.hasOwnProperty(key)) {
            return _default;
        }
        return obj[key];
    }

    function updateScores(scores) {
        teams.forEach(function(team) {
            var teamScore = get(scores, team, {});
            var userAgents = get(teamScore, "user_agents", 0);
            var remoteAddrs = get(teamScore, "remote_addrs", 0);
            elements[team].textContent = "Team " + team + ": " + userAgents + " user agents, " + remoteAddrs + " addresses";
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
