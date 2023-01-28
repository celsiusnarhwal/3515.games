{% filter deline %}
You're about to create a Cards Against Humanity game. There are a few things you need to know:
{% endfilter %}

{% filter deline %}
**Everyone gets to play.** Anyone who can both see and talk in this channel will be able to join or spectate your game.
{% endfilter %}

{% filter deline %}
**You'll be the Game Host**, which means you get special powers like kicking players from the game or ending it
prematurely, as well as special responsibilities like starting the game with `/cah host start` when all the other
players are ready. It also means that if you leave the game (or are kicked by me for inactivity), the game will end for
everyone else. If you feel you're not up to the task, you can delegate your powers to another player
with `/cah host transfer`.
{% endfilter %}

{% filter deline %}
**Speaking of inactivity**, I'll automatically kick players who I think are AFK. Like I just mentioned, being the Game
Host doesn't exempt you from this, and you getting kicked from the game will conclude it for everyone else. Keep that in
mind.
{% endfilter %}

{% filter deline %}
Before we start, let's review your game settings.
{% endfilter %}

**Game Settings**
**Players**: {{ max_players }}
**Points to Win**: {{ points }}
**Timeout**: {{ timeout }} seconds

{% filter deline %}
Once the game has been created, these settings can't be changed.
{% endfilter %}

{% filter deline %}
Proceed with creating this Cards Against Humanity game?
{% endfilter %}
