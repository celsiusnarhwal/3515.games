{% filter deline %}
The move you entered is invalid. You must enter a valid move using either algebraic or Universal Chess Interface (UCI)
notation. If you're having trouble, here are som epointers to keep in mind:
{% endfilter %}

{% filter deline %}
- **Moves must be legal.** Take a good look at the `/chess board` and make sure the move you're trying to make is
actually legal. Remember that if you're in check, you must defend your king, and if you're moving a pawn to its
last rank, you must prompte it.
{% endfilter %}

{% filter deline %}
- **Moves are case-sensitive.**. Be sure to use uppercase and lowercase letters as your chosen notation format requires.
{% endfilter %}

{% filter deline %}
- **Moves must be unambigous.**. The move you enter must be specific enough for me to be able to tell what you're
to do. When in doubt, err on the side of verbosity.
{% endfilter %}