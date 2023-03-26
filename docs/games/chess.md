---
icon: fontawesome/solid/chess
---

# Chess :fontawesome-solid-chess:

Chess is a board game in which your objective is employ smarts and strategy to checkmate your opponent.

## Getting Started

You can challenge someone to a chess game with :command: `/chess challenge`.

???+ command "`/chess challenge`: Challenge someone to a game of chess."
    <div style="text-align:center">

    | **Option** | **Type** | **Description** | **Limited To** | **Required** | **Default** |
    | --- | --- | --- | --- | --- | --- |
    | `opponent` | \@mention | The player you want to challenge. | Server members | Yes  | N/A |
    | `saving` | boolean | Whether to enable game saving. | True/False | No | True |

    </div>

Once you issue your challenge and your opponent accepts, a thread will be created for you to play in.

??? guide "Game saving? What's that?"
    At the end of a chess game, 3515.games can give you the option to save a record of that game. You can watch replays
    of saved games and export them as PGN[^1] files (see [Replaying Games](#replaying-games)).

    When you save a game, basic information about it, like the usernames of its players and the server it took place in,
    is stored in a database accessible by 3515.games' developer. Game saving can be disabled on a per-game basis in case
    this extra information collection makes you uncomfortable.

The game begins after you and your opponent both use :command: `/chess ready` in the thread.

## Playing the Game

### Making Moves

When it's your turn, you can make a move with — you're not gonna believe this — :command: `/chess move`.

??? command "`/chess move`: Make a move in a chess game."
    <div style="text-align:center">

    | **Option** | **Type** | **Description** | **Limited To** | **Required** | **Default** |
    | --- | --- | --- | --- | --- | --- |
    | `move` | text | Specify a move using algebraic or UCI notation. If you're confused, leave this blank. | ≤4000 characters | No | None |

    </div>


:command: `/chess move` pulls up an menu where you'll select the piece you want to move and the square you want to move
it to. Once you confirm your move, your opponent will do the same, and then you, and then your opponent, and then you,
and then your opponent, and then your opponent, and then you, and then duck season, rabbit season, rabbit season, 
duck season, fire. What were we talking about, again?

Oh, right. So basically, just use :command: `/chess move` ad nauseam until you win. Or lose. Not my problem. You can
remember that much, right?

!!! tip "Moving with notation"
    As you may have noticed, :command: `/chess move` has an (optional) option called `move`. If moving with the menu is
    too slow for your tastes, you can type an algebraic[^2] or UCI[^3] notation move into this option and skip all of
    that hassle. 3515.games understands both notations perfectly and can automatically tell which one you're using.
    Now you're playing with power!

### Viewing the Board

You can use :command: `/chess board` to view the current, past, and future states of the board. Okay, maybe not that
last one, but you can definitely view the board at present and the entire move history up to the point you used
:command: `/chess board`.

While browsing through the move history, you can use the buttons to highlight the move made on a particular turn, flip
the board to see things from your ~~enemy's~~ opponent's perspective, and choose whether to show or hide the board
coordinates. Pretty cool, right?

### Giving Up

If you feel like you're at a disadvantage and you're ready to throw in the towel, you can do just that with
:command: `/chess forfeit`. This will end the game and award your opponent a win.

If you don't like that, maybe you'd rather opt for :command: `/chess draw`. :command: `/chess draw` proposes to your
opponent that you both agree its time to wrap things up. If your opponent accepts your offer by using :command:
`/chess draw` themselves, the game will end in a draw. If they don't, well...good luck!

### Replaying Games

When you finish a game, 3515.games will *usually* give you the option to save it. But just what happens when you 
do that?

Enter :command: `/chess replay`. Use it, pick one your saved games from the menu, and browse through your games move
history in a :command: `/chess board`-like interface. If that wasn't enough, you can even export your games as PGN[^1] 
files! And if *that* wasn't enough, you can even *import* PGNs (1) *and* replay them! The future is now, folks.
{ .annotate }

You can save up to 25 games at a time. If you save more, your oldest games will be deleted to make room.

1. They have to be 4000 characters or fewer, though. Blame Discord. 😡


[^1]: Abbreviation for "Portable Game Notation". https://en.wikipedia.org/wiki/Portable_Game_Notation
[^2]: https://www.chess.com/terms/chess-notation
[^3]: Abbreviation for "Universal Chess Interface". https://en.wikipedia.org/wiki/Universal_Chess_Interface