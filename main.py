import os
import json
import random
import hashlib

import jinja2
import webapp2
from google.appengine.api import memcache
from google.appengine.ext import ndb


env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates")),
    autoescape=True
)


class CounterConfig(ndb.Model):
    shards = ndb.IntegerProperty(default=50, indexed=False)


class CounterShard(ndb.Model):
    count = ndb.IntegerProperty(default=0, indexed=False)


class Hash(ndb.Model):
    pass


def _key(*parts):
    hasher = hashlib.sha256()
    for part in parts:
        hasher.update(part.encode("base64") + "\x00")
    return hasher.hexdigest()


def _shard_key(team, attr, shard):
    return _key(team, attr, str(shard))


@ndb.transactional(xg=True)
def mark(team, attr, value):
    key_name = _key(team, attr, value)
    if Hash.get_by_id(key_name) is not None:
        return
    Hash(key=ndb.Key(Hash, key_name)).put()

    shards = CounterConfig.get_or_insert("main").shards
    shard = random.randint(0, shards - 1)

    counter = CounterShard.get_or_insert(_shard_key(team, attr, shard))
    counter.count += 1
    counter.put()


def count(team, attr):
    shards = CounterConfig.get_or_insert("main").shards
    keys = [ndb.Key(CounterShard, _shard_key(team, attr, shard)) for shard in xrange(shards)]

    count = 0
    for counter in ndb.get_multi(keys):
        if counter is None:
            continue
        count += counter.count
    return count


class TeamPage(webapp2.RequestHandler):
    def get(self, team):
        team = team.lower()
        template = env.get_template("team.html")

        user_agent = self.request.headers.get("user-agent", "")
        mark(team, "user_agent", user_agent)

        remote_addr = self.request.remote_addr
        mark(team, "remote_addr", remote_addr)

        self.response.write(template.render({
            "team": team.capitalize(),

            "image": {
                "red": "static/red.png",
                "blue": "static/blue.png",
                "yellow": "static/yellow.png"
            }.get(team, "static/unknown.png")
        }))


def scores(teams=["yellow", "blue", "red"]):
    cache_key = _key("scores", *teams)

    scores = memcache.get(cache_key)
    if scores is None:
        scores = {}
        for team in teams:
            scores[team] = {
                "user_agents": count(team, "user_agent"),
                "remote_addrs": count(team, "remote_addr")
            }
        memcache.add(cache_key, scores, 1)

    return scores


class ScorePage(webapp2.RequestHandler):
    def get(self):
        template = env.get_template("scores.html")
        self.response.write(template.render({
            "initial_scores": json.dumps(scores())
        }))


class ScoreAPI(webapp2.RequestHandler):
    def get(self):
        self.response.headers["Content-Type"] = "application/json"
        self.response.write(json.dumps(scores()))


routes = [
    ("(?i)/(yellow|blue|red)", TeamPage),
    ("(?i)/scores/api", ScoreAPI),
    ("(?i)/scores", ScorePage)
]


app = webapp2.WSGIApplication(routes=routes)
