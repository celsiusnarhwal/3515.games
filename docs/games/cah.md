---
icon: fontawesome/solid/pencil
hide:
    - next
---

# Cards Against Humanity :fontawesome-solid-pencil:

Cards Against Humanity is a card game where you earn points by being funny. Every round, you're given fill-in-the-blank
prompt called a black card, which you get to complete using the words on any of the white cards you happen to be
holding. The funnnier your answer, the more likely you are to earn points. Easy enough, right? Yeah. Easy enough.

!!! danger "This game is not family-friendly"

    Cards Against Humanity contains content that's likely to gross you out, offend you, violate the rules of your
    Discord server, or some combination of the three. You've been warned.

    If you're one of the elite few people with the `Manage Server` permission, you can disable Cards Against Humanity
    in your Discord server by changing the permissions for the :command: `/cah` command in 
    **Server Settings** > **Integrations** > **3515.games**.

!!! voice "This game supports voice chat"

    Cards Against Humanity supports the creation of special linked voice channels via the :command:`/voice` command. [Learn more.](/games/features/voice)

## Getting Started

To get started, you'll need to create a Cards Against Humanity game with :command: `/cah create`.

??? command "`/cah create`: Create a CAH game."

    <div style="text-align: center;">

    | **Option** | **Type** | **Description** | **Limited To** | **Required?** | **Default** |
    |---|---|---|---|---|---|
    | `players` | number | The maximum number of players that can join your game. | 3-20 | No | 20 |
    | `points` | number | The number of points required to win the game. | 5-100 | No | 10 |
    | `timeout` | number | The number of seconds in which players have to move before being penalized. | 30-120 | No | 60 |
    | `voting` | choice | Choose whether round winners are selected by Card Czar or popular vote. | <ul><li>Card Czar</li><li>Popular Vote</li></ul> | No | Card Czar |

    </div>

!!! info

    Creating a game makes you the Game Host, which endows you with certain powers and responsibilities, including starting
    the game when everyone is ready to play. For more, see [Hosting a Game](#hosting-a-game).

Once a game has been created, players can join it with :command: `/cah ciao`. Cards Against Humanity games are played in
threads,
so anyone who can both see and talk in the thread's parent channel can join in the game.

<small>...déjà vu, anyone?</small>

## Playing the Game

There are two phases to a Cards Against Humanity game: the **playing** phase and the **voting** phase.

### The Playing Phase

In the playing phase, everyone who isn't the Card Czar (or *everyone*, period, if you're playing in popular vote mode)
uses :command: `/cah play` to pick one (and maybe even two!) white cards to complete the current black card. If you're
asked to pick two cards, you'll also be asked to pick the order in which you want to play them. (1)
{ .annotate }

1. "But can't 3515.games automatically figure that out based on the order I select them in?" No, no it cannot.
   Thank you, Discord!

Once everyone's played their cards, the game moves on to the voting phase.

### The Voting Phase

In the voting phase, the Card Czar (or everyone, if you're playing in popular vote mode) uses :command: `/cah play` (1)
to pick what they think is the funniest answer. Whoever gets the Card Czar's vote (or the most votes, if you're playing
in popular vote mode) wins the round and earns a point.
{ .annotate }

1. Yes, that's the same command. It does something different this time. Promise.

??? question "But what if there's a tie?"
    
    You didn't ask that, but great question! If there's a vote tie in a popular vote game, 3515.games secretly picks a
    winner from among the tied players. It doesn't tell you that there was a tie or how many votes each player got,
    though, so you'll never actually know when or if this happens. 🤫

Also, you can view the cards you're currently holding with :command: `/cah hand`. This works in both phases, in case
that needed clearing up. That's basically everything though.

### Inactivity Rules


The Game Host chooses how long players have to move during their turns. If you exceed this time limit, you'll
**time out** and be penalized by being made to draw a card and forfeit your turn.

If you time out for three turns in a row, **you'll be kicked from the game**.

<small>...seriously, is anyone else getting déjà vu?</small>

## Hosting a Game

When you create an Cards Against Humanity game, you become its **Game Host**. This grants you exclusive access to 
the :command: `/cah manage` command.

??? command "`/cah manage`: Manage an Cards Against Humanity game."
    <div style="text-align: center">

    | **Option** | **Type** | **Description** | **Limited To** | **Required** | **Default** |
    | --- | --- | --- | --- | --- | --- |
    | `action` | choice | The action you want to perform. | <ul><li>Start Game</li><li>End Game</li><li>Kick Player</li><li>Transfer Host Powers</li> | Yes | N/A |

    </div>

### Starting a Game

As mentioned [previously](#getting-started), you're the one responsible for starting the game when everyone's ready.
You can do this with :commmand: `/cah manage > Start Game`.

### Ending a Game

You can end an ongoing game at any time with :command: `/cah manage > End Game`. This prematurely concludes the game without
a winner and locks its thread to anyone who isn't a moderator.

### Kicking Players

You can kick unruly players from the game with :command: `/cah manage > Kick Player`. You'll get a dropdown menu of players to
choose from; all you have to do is select the one you want to kick. Everyone will be notified when a player is kicked,
and the kicked player will get a DM about it.

Kicked players can still spectate your game and chat in its thread.

### Transferring Host Powers

If you don't want to be the Game Host anymore, you can transfer your powers to another player with
:command: `/cah manage > Transfer Host Powers`. This will lift all the rights and responsibilities of being the Game Host off of
you and onto whoever you select.

!!! danger "Better keep your head in the game"
    If you're the Game Host, you leaving the game will end it for all other players. Keep in mind that :command:
    `/cah ciao` isn't the only way to leave a game — leaving the game thread will also kick you out, and being the 
    Game Host **does not** exempt you from being kicked for inactivity.

<small>The déjà vu is getting weird now, please send help.</small>

## Bad Endings

Cards Against Humanity games end normally when someone wins and can be forcefully ended by their Game Host. However, there are some
situations where 3515.games will take matters into its own hands and prematurely close a game.

This can happen if:

<div class="annotate" markdown>

- The player count falls below 3 at any time after the game starts
- The Game Host leaves or is removed from the game
- All players are deemed inactive (1)
- The game thread, its parent channel, or the server it's in is deleted
- The game takes too long to end by other means (2)

</div>

1. This happens if the game completes a full cycle through the turn order during which *no one* moves within the 
time limit.
2. Specifically, you have four hours to wrap things up or 3515.games will close the curtain for you.


