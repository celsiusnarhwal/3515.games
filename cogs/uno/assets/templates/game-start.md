{{ funny|deline }}

{% filter deline %}
In UNO, your goal is to be the first player to get rid of all your cards each rouned. Once a players gets rid of all
their cards, the round ends and that player is awarded points based on the cards everyone else is still holding.
{% endfilter %}

{{ rules|deline }}

{% filter deline %}
You can view the cards you currently hold at any time with `/uno hand`. When it's your turn, you can play a card with
`/uno play` or draw one with `/uno draw`.
{% endfilter %}

{% filter deline %}
You can view a range of information about this UNO game with `/uno status`, including the current turn order and
score leaderboard.
{% endfilter %}

{% filter deline %}
Let's play!
{% endfilter %}