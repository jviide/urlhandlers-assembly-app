import os
import json
import base64
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
    shards = ndb.IntegerProperty(default=25, indexed=False)


class CounterShard(ndb.Model):
    count = ndb.IntegerProperty(default=0, indexed=False)


class Hash(ndb.Model):
    pass


def _key(*parts):
    hasher = hashlib.sha256()
    for part in parts:
        hasher.update(base64.b64encode(part) + "\x00")
    return base64.b64encode(hasher.digest())


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

    memcache.incr(_key("count", team, attr))

    counter = CounterShard.get_or_insert(_shard_key(team, attr, shard))
    counter.count += 1
    counter.put()


@ndb.tasklet
def count_tasklet(team, attr, shards):
    cache_key = _key("count", team, attr)

    count = memcache.get(cache_key)
    if count is None:
        keys = [ndb.Key(CounterShard, _shard_key(team, attr, shard)) for shard in xrange(shards)]

        results = yield ndb.get_multi_async(keys)

        count = 0
        for counter in results:
            if counter is None:
                continue
            count += counter.count
        memcache.add(cache_key, count, 15)

    raise ndb.Return((team, attr, count))


class TeamPage(webapp2.RequestHandler):
    def get(self, team):
        team = team.lower()
        template = env.get_template("team.html")

        user_agent = self.request.headers.get("user-agent", "")
        mark(team, "user_agents", user_agent)

        remote_addr = self.request.remote_addr
        mark(team, "remote_addrs", remote_addr)

        self.response.write(template.render({
            "team": team.capitalize(),

            "image": {
                "red": "/static/redteam.png",
                "blue": "/static/blueteam.png",
                "yellow": "/static/yellowteam.png"
            }.get(team, "/static/unknown.png"),

            "color": jinja2.Markup({
                "yellow": "#FFEF00",
                "red": "#53140A",
                "blue": "#0056B9"
            }.get(team, "#777777"))
        }))


@ndb.synctasklet
def scores(teams=["yellow", "blue", "red"]):
    config = yield CounterConfig.get_or_insert_async("main")

    tasklets = []
    for team in teams:
        tasklets.extend([
            count_tasklet(team, "user_agents", config.shards),
            count_tasklet(team, "remote_addrs", config.shards)
        ])
    results = yield tasklets

    scores = {}
    for team, attr, count in results:
        scores.setdefault(team, {}).setdefault(attr, count)
    raise ndb.Return(scores)


class ScorePage(webapp2.RequestHandler):
    def get(self):
        template = env.get_template("scores.html")
        self.response.write(template.render({}))


class ScoreAPI(webapp2.RequestHandler):
    def get(self):
        self.response.headers["Content-Type"] = "application/json"
        self.response.write(json.dumps(scores()))


routes = [
    ("(?i)/(yellow|blue|red)/?", TeamPage),
    ("(?i)/scores/api/?", ScoreAPI),
    ("(?i)/scores/?", ScorePage)
]


app = webapp2.WSGIApplication(routes=routes)
