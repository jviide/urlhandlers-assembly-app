import os
import json
import base64
import random
import hashlib

import jinja2
import webapp2
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
        hasher.update(base64.b64encode(part) + "\x00")
    return base64.b64encode(hasher.digest())


def _shard_key(team, attr, shard):
    return _key(team, attr, str(shard))


@ndb.tasklet
def _shards():
    cache_key = _key("shards")
    context = ndb.get_context()

    shards = yield context.memcache_get(cache_key)
    if shards is None:
        config = yield CounterConfig.get_or_insert_async("main")
        shards = config.shards
        yield context.memcache_add(cache_key, shards)
    raise ndb.Return(shards)


@ndb.tasklet
def mark_tasklet(team, attr, value):
    cache_key = _key("hash", team, attr, value)
    context = ndb.get_context()

    exists = yield context.memcache_get(cache_key)
    if exists:
        return

    yield [
        context.memcache_add(cache_key, True),
        _mark_tasklet(team, attr, value)
    ]


@ndb.transactional_tasklet(xg=True)
def _mark_tasklet(team, attr, value):
    key_name = _key(team, attr, value)

    hash_entity = yield Hash.get_by_id_async(key_name)
    if hash_entity is not None:
        return

    yield [
        Hash(key=ndb.Key(Hash, key_name)).put_async(),
        ndb.get_context().memcache_incr(_key("count", team, attr)),
        _incr_tasklet(team, attr)
    ]


@ndb.transactional_tasklet
def _incr_tasklet(team, attr):
    shards = yield _shards()
    shard = random.randint(0, shards - 1)
    counter = yield CounterShard.get_or_insert_async(_shard_key(team, attr, shard))
    counter.count += 1
    yield counter.put_async()


@ndb.tasklet
def count_tasklet(team, attr, force_recount=False):
    cache_key = _key("count", team, attr)
    context = ndb.get_context()

    if not force_recount:
        count = yield context.memcache_get(cache_key)
        if count is not None:
            raise ndb.Return((team, attr, count))

    shards = yield _shards()
    keys = [ndb.Key(CounterShard, _shard_key(team, attr, shard)) for shard in xrange(shards)]
    results = yield ndb.get_multi_async(keys)

    count = 0
    for counter in results:
        if counter is None:
            continue
        count += counter.count

    cache_key = _key("count", team, attr)
    context = ndb.get_context()
    yield context.memcache_set(cache_key, count, random.randint(90, 120))
    raise ndb.Return((team, attr, count))


@ndb.synctasklet
def scores(teams=["yellow", "blue", "red"], force_recount=False):
    tasklets = []
    for team in teams:
        tasklets.extend([
            count_tasklet(team, "user_agents", force_recount),
            count_tasklet(team, "remote_addrs", force_recount)
        ])
    results = yield tasklets

    scores = {}
    for team, attr, count in results:
        scores.setdefault(team, {}).setdefault(attr, count)
    raise ndb.Return(scores)


class TeamPage(webapp2.RequestHandler):
    @ndb.synctasklet
    def get(self, team):
        team = team.lower()
        user_agent = self.request.headers.get("user-agent", "")
        remote_addr = self.request.remote_addr
        yield [
            mark_tasklet(team, "user_agents", user_agent),
            mark_tasklet(team, "remote_addrs", remote_addr)
        ]

        template = env.get_template("team.html")
        self.response.write(template.render({
            "team": team.capitalize(),

            "image": {
                "yellow": "/static/yellowteam.png",
                "blue": "/static/blueteam.png",
                "red": "/static/redteam.png"
            }.get(team, "/static/unknown.png"),

            "color": jinja2.Markup({
                "yellow": "#FFEF00",
                "red": "#53140A",
                "blue": "#0056B9"
            }.get(team, "#777777"))
        }))


class ScorePage(webapp2.RequestHandler):
    def get(self):
        template = env.get_template("scores.html")
        self.response.write(template.render({}))


class ScoreAPI(webapp2.RequestHandler):
    def get(self):
        self.response.headers["Content-Type"] = "application/json"
        self.response.write(json.dumps(scores()))


class RecalcTask(webapp2.RequestHandler):
    def get(self):
        scores(force_recount=True)


class MainPage(webapp2.RequestHandler):
    def get(self):
        template = env.get_template("index.html")
        self.response.write(template.render({}))


app = webapp2.WSGIApplication(routes=[
    ("(?i)/(yellow|blue|red)/?", TeamPage),
    ("(?i)/scores/api/?", ScoreAPI),
    ("(?i)/scores/?", ScorePage),
    ("/", MainPage)
])


tasks = webapp2.WSGIApplication(routes=[
    ("/tasks/recalc_scores", RecalcTask)
])
