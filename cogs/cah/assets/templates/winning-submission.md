{% filter deline %}
{% if card_czar %}
The Card Czar has
{% else %}
The players have
{% endif %}
chosen {{ victor.mention|posessive }} submission.
{% endfilter %}

**{{ victor.name }}** now has {{ inflect.no("point", victor.points) }}.
