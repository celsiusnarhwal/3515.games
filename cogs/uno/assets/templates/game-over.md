{% filter deline %}
Congratulations, {{ winner }}! You won the game with a total of **{{ inflect.no("point", winner.points) }}**.
To see the final leaderboard for this game, use the button below.
{% endfilter %}

{% filter deline %}
This thread will be automatically deleted in 60 seconds. Thanks for playing!
{% endfilter %}
