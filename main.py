import os

import jinja2
import webapp2


env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates")),
    autoescape=True
)


class TeamPage(webapp2.RequestHandler):
    def get(self, team):
        team = team.lower()
        template = env.get_template("team.html")

        self.response.write(template.render({
            "team": team.capitalize(),

            "image": {
                "red": "static/red.png",
                "blue": "static/blue.png",
                "yellow": "static/yellow.png"
            }.get(team, "static/unknown.png")
        }))


class ScorePage(webapp2.RequestHandler):
    def get(self, team):
        self.response.headers["Content-Type"] = "text/plain"
        self.response.write("Scores!")


routes = [
    ("(?i)/(yellow|blue|red)", TeamPage),
    ("(?i)/scores", ScorePage)
]


app = webapp2.WSGIApplication(routes=routes, debug=True)
