---
icon: fontawesome/solid/hand-back-fist
hide:
    - previous
---

# Rock-Paper-Scissors :fontawesome-solid-hand-back-fist: :fontawesome-solid-hand: :fontawesome-solid-hand-scissors:

In Rock-Paper-Scissors, your objective is to best your opponent each round by choosing either rock, paper, or scissors,
and hoping they choose the option that loses to yours. Rock beats scissors, scissors beats paper, and paper beats rock.
You probably already know the rules. Let's get to the important stuff.

## How to Play

To start a game of Rock-Paper-Scissors, use the :command: `/rps challenge` command.

??? command "`/rps challenge`: Challenge someone to a game of Rock-Paper-Scissors."
    <div style="text-align: center;">

    | **Options** | **Type** | **Description** | **Limited To** | **Required** | **Default** |
    | ------------ | -------- | --------------- | -------------- | ------------ | ----------- |
    | `opponent` | \@mention | The user you want to challenge. | Server members | Yes | N/A |
    | `format` | choice | The format of the game. | <ul><li>Best of Three</li><li>Best of Five</li><li>Best of Nine</li></ul> | Yes | N/A |

    </div>

Once you issue your challenge and your opponent accepts, your game will begin!

<figure markdown>
  ![Image title](/assets/img/games/rps/game-start.png){ width="500" }
  <figcaption>A rock-paper-scissors game begins.</figcaption>
</figure>


You'll be asked to choosed between rock, paper, or scissors. Click the button that corresponds to your choice,
then wait for your opponent to do the same. Once both players have made their moves, the winner of the round will be announced.

<figure markdown>
  ![Image title](/assets/img/games/rps/round-winner.png){ width="500" }
  <figcaption>The end of a round.</figcaption>
</figure>

The first player to win a majority of rounds will win the game. In a Best of Three game, this will be the first player
to win two rounds; in a Best of Five game, the first to win three rounds; in a Best of Nine game, five rounds.

That's all there is to it. Have fun!