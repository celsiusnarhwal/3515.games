---
icon: fontawesome/solid/cards-blank
---

# UNO :fontawesome-solid-cards-blank:


UNO is a card game in which your objective is to be the first player to rid themselves of all their cards in a given
round. This is accomplished by playing cards that match the color or suit of the previous card played, and repeating
this ad infinitum until you have no cards left.

## Getting Started

To get started, you'll need to create an UNO game with :command: `/uno create`.

??? command "`/uno create`: Create an UNO game."
    <div style="text-align: center;">

    | **Option** | **Type** | **Description** | **Limited To** | **Required?** | **Default** |
    |---|---|---|---|---|---|
    | `players` | number | The maximum number of players that can join your game. | 2-20 | No | 20 |
    | `points` | number | The number of points required to win the game. | ≤1000 | No | 500 |
    | `timeout` | number | The number of seconds in which players have to move before being penalized. | 30-120 | No | 60 |

    </div>

!!! info
    Creating a game makes you the Game Host, which endows you with certain powers and responsibilities, including starting
    the game when everyone is ready to play. For more, see [Hosting a Game](#hosting-a-game).

Once a game has been created, players can join it with :command: `/uno ciao`. UNO games are played in threads, so anyone
who can both see and talk in the thread's parent channel can join in the game.

Once everyone's ready to play, the Game Host can start the game with :command: `/uno manage > Start Game`.

## Playing the Game

Everything you need to do during a game can be done with :command: `/uno play`.

??? command "`/uno play`: Play a card, draw a card, view your hand, make a callout, or Say "UNO!"."
    <div style="text-align: center;">

    | **Option** | **Type** | **Description** | **Limited To** | **Required?** | **Default** |
    |---|---|---|---|---|---|
    | `action` | choice | The action you want to perform. | <ul><li>Play Card</li><li>Draw Card</li><li>View Hand</li><li>Make Callout</li><li>Say "UNO!"</li></ul> | Yes | N/A |
    
    </div>

### Playing Cards

You can play cards with :command: `/uno play > Play Card`. You'll get a dropdown menu of cards to select from, and can
choose anyone that matches the color or suit of the last card played.

When applicable, the menu will tell you what the last card played was to aid you in your decision.

!!! tip

    You can use the "Show Playable Cards" button to filter the card selection menu down to only the cards that can be
    played on the current turn. If you don't have any playable cards, you'll be told as much.

??? guide "The different types of UNO cards"

    ### Color Cards

    Most UNO Cards come in one of four different colors **Red**, **Blue**, **Green**, and **Yellow**. Each of these
    colors comes in 13 differnet suits: 10 suits numbered **0-9** and three special suits: 
    :fontawesome-solid-clock-rotate-left: **Reverse**, :fontawesome-solid-forward: **Skip**, and :cards-plus: **+2**.
    
    When it's your turn, you can play any card that matches the color or suit of the last card played. For example,
    if the last card played was a Blue 4, you could play a Red 4, a Blue 5, or a Blue Reverse.

    :fontawesome-solid-clock-rotate-left: **Reverse**, :fontawesome-solid-forward: **Skip**, and :cards-plus: **+2** have special effects when played:

    - :fontawesome-solid-clock-rotate-left: **Reverse**: Reverses the turn order.
    - :fontawesome-solid-forward: **Skip**: Skips the next player's turn.
    - :cards-plus: **+2**: Forces the next player to draw two cards and forfeit their turn.

    ### Wild Cards

    :fontawesome-solid-wand-magic: **Wild** cards are special cards that can always be played regardless of the color 
    or suit of the last card played. They also allow you to choose what the next color in play will be.

    :fontawesome-solid-wand-magic-sparkles: **Wild +4** cards are Wild cards with the additional benefit of making the 
    next player draw four cards and forfeit their turn. This is the most powerful card in the game, so if you have one, use it wisely.

### Drawing Cards

!!! tip inline end
    You have a perfectly equal chance of drawing any given card. This means cards with <b>special effects</b> can appear
    more often than you may be predisposed to expect.

If it's your turn and you don't have any playable cards, you can draw one with :command: `/uno play > Draw Card`. When you draw
a card, you have two options: either you can a) draw the card and keep it, or b) draw the card and, if possible
play it on the same turn.

You can always choose to draw a card, even if you have cards that can be played on the current turn.

### Viewing Your Hand

You can see your hand (i.e. the cards you're currently holding) with :command: `/uno play > View Hand`. You can do this at
any time, regardless of whether it's your turn.

If you have a great many cards, you might have to click through multiple pages to see them all.

### Saying "UNO!"

When you have one card left, you can say "UNO!" with :command: `/uno play > Say "UNO!"`. Doing so notifies everyone else in the
game that you're on the verge of winning the round. Congrats!

Note that if you say "UNO!", draw one or more cards, and then later find yourself again with only one card left, you'll
need to say "UNO!" once more or risk being penalized.

3515.games will tell you when you need to say "UNO!", so you don't need to worry about remembering the semantics.

!!! tip
    It doesn't have to be your turn for you to be able to say "UNO!".

### Making Callouts

If you have one card left, you must either say "UNO!" or risk being penalized. That penalty comes in the form of
of a **callout** from another player.

If you think someone else has one card left and hasn't said "UNO!", you can call then out for it with
:command: `/uno play > Make Callout`. You'll get a dropdown menu of players to choose from; all you have to do is 
select the one you think is holding out.

Callouts are a gamble. If you're correct, the player you call out will draw two cards; if you're wrong, you'll draw
one and forfeit your turn.

### Winning the Game

The winner of the game is the first person to meet or exceed the number of points required to win, as set by the Game
Host. You earn points by winning rounds, and you win a round by being the first player to get rid of all your cards
during one.

When you win a round, you're awarded points based on the cards everyone else is holding at the time. Each card is worth
a certain number of points, and the number of points you earn is the sum of the point values of all unplayed cards
at the end of the round. In the unlikely (but not impossible) event that sum is 0, you'll be awarded one point.

???+ guide "How many points is my card worth?"
    <div class="grid cards" markdown>
    
    - :fontawesome-solid-wand-magic: **Wild** cards are worth 50 points
    - :fontawesome-solid-wand-magic-sparkles: **Wild +4** cards are also worth 50 points
    - :fontawesome-solid-clock-rotate-left: **Reverse**, :fontawesome-solid-forward: **Skip**, and :cards-plus: **+2** cards are worth 20 points
    - :octicons-number-16: **Numbered** cards are worth their face value

    </div>

!!! tip "Zero-point games"
    If you create an UNO game where the number of points required to win is 0, the first player to get rid of all their
    cards will win the entire game.

### Viewing Statistics

You can view statistics about an ongoing UNO game with :command: `/uno status`. This command opens the UNO Status Center,
where you can see:

- The game settings, including the number of points required to win
- A list of the game's players
- The current turn order
- The current leaderboard
- The events of the previous turn
- Your personal game statistics, such as how many cards you've played and drawn

### Inactivity Rules


The Game Host chooses how long players have to move during their turns. If you exceed this time limit, you'll
**time out** and be penalized by being made to draw a card and forfeit your turn.

If you time out for three turns in a row, **you'll be kicked from the game**.

??? example "The clockworks of the inactivity timer"
    The inactivity timer always lasts a *little* longer or a *little* shorter than what the host sets it
    to. This is to prevent players from making a move exactly as the timer runs out and causing, erm...*undesirable*
    effects.
    
    Other games that use inactivity timers work like this, too.

## Hosting a Game

When you create an UNO game, you become its **Game Host**. This grants you exclusive access to 
the :command: `/uno manage` command.

??? command "`/uno manage`: Manage an UNO game."
    <div style="text-align: center">

    | **Option** | **Type** | **Description** | **Limited To** | **Required** | **Default** |
    | --- | --- | --- | --- | --- | --- |
    | `action` | choice | The action you want to perform. | <ul><li>Start Game</li><li>End Game</li><li>Kick Player</li><li>Transfer Host Powers</li> | Yes | N/A |

    </div>

### Starting a Game

As mentioned [previously](#getting-started), you're the one responsible for starting the game when everyone's ready.
You can do this with :commmand: `/uno manage > Start Game`.

### Ending a Game

You can end an ongoing game at any time with :command: `/uno manage > End Game`. This prematurely concludes the game without
a winner and locks its thread to anyone who isn't a moderator.

### Kicking Players

You can kick unruly players from the game with :command: `/uno manage > Kick Player`. You'll get a dropdown menu of players to
choose from; all you have to do is select the one you want to kick. Everyone will be notified when a player is kicked,
and the kicked player will get a DM about it.

Kicked players can still spectate your game and chat in its thread.

### Transferring Host Powers

If you don't want to be the Game Host anymore, you can transfer your powers to another player with
:command: `/uno manage > Transfer Host Powers`. This will lift all the rights and responsibilities of being the Game Host off of
you and onto whoever you select.

!!! danger "Better keep your head in the game"
    If you're the Game Host, you leaving the game will end it for all other players. Keep in mind that :command:
    `/uno ciao` isn't the only way to leave a game — leaving the game thread will also kick you out, and being the 
    Game Host **does not** exempt you from being kicked for inactivity.

## Bad Endings

UNO games end normally when someone wins and can be forcefully ended by their Game Host. However, there are some
situations where 3515.games will take matters into its own hands and prematurely close a game.

This can happen if:

<div class="annotate" markdown>

- The player count falls below 2 at any time after the game starts
- The Game Host leaves or is removed from the game
- All players are deemed inactive (1)
- The game thread, its parent channel, or the server it's in is deleted
- The game takes too long to end by other means (2)

</div>

1. This happens if the game completes a full cycle through the turn order during which *no one* moves within the 
time limit.
2. Specifically, you have eight hours to wrap things up or 3515.games will close the curtain for you.

??? example annotate "Implementation details"
    While 3515.games stays as close to the [official UNO rules](https://service.mattel.com/instruction_sheets/42001pr.pdf)
    as reasonably possible, there are a few notable deviations.

    - There's no limitation on when you can play Wild +4 cards. (1)
    - If you only have one card left and haven't said "UNO!", you're eligible to be penalized for it by other players
    until either you say "UNO!" or the round ends. (2)
    - The minimum number of points you can earn for winning a round is 1. (3)
    - Wild and Wild +4 cards can't be played automatically when drawn, despite being compatible with all other cards
    in the game. (4)

1.  In the official rules, you can only legally play a Wild +4 card if you have no other playable cards in your hand.
    If you play one while still having other playable cards, the person who would draw four cards can call you
    out for it and make you draw four cards instead.
2.  In the official rules, only the player who moves after you can call you out. If they don't, you're safe from any
    penalty.
3. In the *very* unlikely event that you win a round with every other player holding exclusively cards of suit
    0, the official rules would have you earn zero points. Because awarding zero points for winning a round is
    stupid, 3515.games will always award you at least one.
4. I cannot overstate how much of a pain in the ass this would be to implement, so it isn't supported. Womp womp.

<small>You didn't think *every* page would be as short as the one for Rock-Paper-Scissors, did you?</small>