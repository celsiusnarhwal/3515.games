{% filter deline %}
In Cards Against Humanity, your goal is to earn points by being funny. Easy enough.
{% endfilter %}

{% filter deline %}
Every round, you'll be given a fill-in-the-blank prompt in the form of a black card. Your task to to pick one
(sometimes two!) of the white cards you've been dealt to fill that blank in what you think is the funniest way possible.

{% if settings.use_czar %}
The Card Czar then gets to choose the combination they thought was funniest, and the person who played it gets an
Awesome Point.
{% else %}
Everyone then votes on which combination they thought was funniest, and the person who played the highest-voted
one gets a point.
{% endif %}
Nice!
{% endfilter %}

{% filter deline %}
The first player to reach **{{ settings.points_to_win }}** Awesome Points wins the game!
{% endfilter %}

{% filter deline %}
Let's play!
{% endfilter %}
