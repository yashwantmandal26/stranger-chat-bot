import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# Math Puzzle Generator
# ---------------------------------------------------------
@dataclass
class MathPuzzle:
    question: str
    options: list[int]
    answer: int


def generate_math_puzzle() -> MathPuzzle:
    """Generates an arithmetic problem across +, -, *, / with 4 distinct options."""
    op = random.choice(["+", "-", "*", "/"])

    if op == "+":
        a = random.randint(12, 79)
        b = random.randint(11, 69)
        ans = a + b
        q_str = f"{a} + {b} = ?"
    elif op == "-":
        a = random.randint(35, 99)
        b = random.randint(12, a - 5)
        ans = a - b
        q_str = f"{a} - {b} = ?"
    elif op == "*":
        a = random.randint(3, 14)
        b = random.randint(3, 12)
        ans = a * b
        q_str = f"{a} × {b} = ?"
    else:  # "/"
        b = random.randint(2, 12)
        ans = random.randint(3, 15)
        a = b * ans
        q_str = f"{a} ÷ {b} = ?"

    # Generate 3 plausible unique distractors
    distractors: set[int] = set()
    offsets = [-10, 10, -2, 2, -1, 1, -5, 5, -3, 3]
    random.shuffle(offsets)

    for off in offsets:
        candidate = ans + off
        if candidate != ans and candidate >= 0:
            distractors.add(candidate)
        if len(distractors) == 3:
            break

    while len(distractors) < 3:
        candidate = max(1, ans + random.randint(-15, 15))
        if candidate != ans:
            distractors.add(candidate)

    options = list(distractors) + [ans]
    random.shuffle(options)

    return MathPuzzle(question=q_str, options=options, answer=ans)


# ---------------------------------------------------------
# Rock Paper Scissors
# ---------------------------------------------------------
RPS_MOVES = ["rock", "paper", "scissors"]
RPS_EMOJIS = {"rock": "🪨 Rock", "paper": "📄 Paper", "scissors": "✂️ Scissors"}


def evaluate_rps(move1: str, move2: str) -> str:
    """
    Evaluates RPS outcome for player 1 against player 2.
    Returns: 'win', 'lose', or 'tie'.
    """
    m1 = move1.lower()
    m2 = move2.lower()
    if m1 == m2:
        return "tie"
    if (
        (m1 == "rock" and m2 == "scissors")
        or (m1 == "paper" and m2 == "rock")
        or (m1 == "scissors" and m2 == "paper")
    ):
        return "win"
    return "lose"


# ---------------------------------------------------------
# Solo Games Manager
# ---------------------------------------------------------
class SoloGamesManager:
    """Tracks active solo game states for users."""

    def __init__(self) -> None:
        self._active_guess: dict[int, dict[str, Any]] = {}
        self._active_math: dict[int, MathPuzzle] = {}

    def start_guess(self, user_id: int) -> int:
        """Starts a number guessing game (0-9). Returns secret number."""
        target = random.randint(0, 9)
        self._active_guess[user_id] = {
            "target": target,
            "attempts": 0,
            "started_at": time.time(),
        }
        return target

    def check_guess(self, user_id: int, guess: int) -> tuple[str, int, int]:
        """
        Checks a guess.
        Returns (result, attempts, target).
        result: 'correct', 'higher' (target is higher), 'lower' (target is lower).
        """
        game = self._active_guess.get(user_id)
        if not game:
            target = self.start_guess(user_id)
            game = self._active_guess[user_id]
        else:
            target = game["target"]

        game["attempts"] += 1
        attempts = game["attempts"]

        if guess == target:
            del self._active_guess[user_id]
            return "correct", attempts, target
        elif guess < target:
            return "higher", attempts, target
        else:
            return "lower", attempts, target

    def start_math(self, user_id: int) -> MathPuzzle:
        """Starts a solo math puzzle."""
        puzzle = generate_math_puzzle()
        self._active_math[user_id] = puzzle
        return puzzle

    def check_math(self, user_id: int, selected_answer: int) -> tuple[bool, int]:
        """
        Checks solo math answer.
        Returns (is_correct, correct_answer).
        """
        puzzle = self._active_math.pop(user_id, None)
        if not puzzle:
            return False, selected_answer
        return selected_answer == puzzle.answer, puzzle.answer

    def play_rps(self, user_move: str) -> tuple[str, str]:
        """
        Plays RPS against the Bot.
        Returns (bot_move, outcome: 'win' | 'lose' | 'tie').
        """
        bot_move = random.choice(RPS_MOVES)
        outcome = evaluate_rps(user_move, bot_move)
        return bot_move, outcome

    def roll_dice(self) -> tuple[int, int, str]:
        """
        Rolls a 6-sided dice for user and bot.
        Returns (user_roll, bot_roll, outcome: 'win' | 'lose' | 'tie').
        """
        u_roll = random.randint(1, 6)
        b_roll = random.randint(1, 6)
        if u_roll > b_roll:
            outcome = "win"
        elif u_roll < b_roll:
            outcome = "lose"
        else:
            outcome = "tie"
        return u_roll, b_roll, outcome


# ---------------------------------------------------------
# Partner Duels Manager
# ---------------------------------------------------------
@dataclass
class MathDuel:
    session_id: int
    user1_id: int
    user2_id: int
    puzzle: MathPuzzle
    winner_id: Optional[int] = None
    answered: bool = False


@dataclass
class RPSDuel:
    session_id: int
    user1_id: int
    user2_id: int
    moves: dict[int, str] = field(default_factory=dict)
    finished: bool = False


@dataclass
class GuessDuel:
    session_id: int
    user1_id: int
    user2_id: int
    target: int
    winner_id: Optional[int] = None
    finished: bool = False


class DuelGamesManager:
    """Manages real-time multiplayer duels between connected strangers."""

    def __init__(self) -> None:
        self._math_duels: dict[int, MathDuel] = {}
        self._rps_duels: dict[int, RPSDuel] = {}
        self._guess_duels: dict[int, GuessDuel] = {}
        self._lock = asyncio.Lock()

    async def start_math_duel(self, session_id: int, user1_id: int, user2_id: int) -> MathPuzzle:
        """Starts a live math duel between two chatting users."""
        puzzle = generate_math_puzzle()
        async with self._lock:
            self._math_duels[session_id] = MathDuel(
                session_id=session_id,
                user1_id=user1_id,
                user2_id=user2_id,
                puzzle=puzzle,
            )
        return puzzle

    async def submit_math_answer(
        self, session_id: int, user_id: int, answer: int
    ) -> tuple[str, Optional[int], int]:
        """
        Evaluates a math duel answer.
        Returns:
          - 'winner': user was the first to submit the correct answer!
          - 'wrong': user guessed wrong.
          - 'already_finished': someone else already won.
          - 'no_game': game not found.
        """
        async with self._lock:
            duel = self._math_duels.get(session_id)
            if not duel:
                return "no_game", None, answer

            if duel.answered:
                return "already_finished", duel.winner_id, duel.puzzle.answer

            if answer == duel.puzzle.answer:
                duel.answered = True
                duel.winner_id = user_id
                return "winner", user_id, duel.puzzle.answer
            else:
                return "wrong", None, duel.puzzle.answer

    async def start_rps_duel(self, session_id: int, user1_id: int, user2_id: int) -> None:
        """Starts a hidden-move RPS duel."""
        async with self._lock:
            self._rps_duels[session_id] = RPSDuel(
                session_id=session_id,
                user1_id=user1_id,
                user2_id=user2_id,
                moves={},
                finished=False,
            )

    async def submit_rps_move(
        self, session_id: int, user_id: int, move: str
    ) -> tuple[bool, Optional[dict[int, str]], Optional[int]]:
        """
        Submits an RPS move.
        Returns:
          (is_finished, moves_dict, winner_id_or_none)
        """
        async with self._lock:
            duel = self._rps_duels.get(session_id)
            if not duel:
                return False, None, None

            duel.moves[user_id] = move.lower()

            # If both have answered
            if len(duel.moves) >= 2:
                duel.finished = True
                u1 = duel.user1_id
                u2 = duel.user2_id
                m1 = duel.moves.get(u1, "rock")
                m2 = duel.moves.get(u2, "rock")

                result = evaluate_rps(m1, m2)
                winner_id: Optional[int] = None
                if result == "win":
                    winner_id = u1
                elif result == "lose":
                    winner_id = u2
                else:
                    winner_id = None  # tie

                return True, dict(duel.moves), winner_id

            return False, dict(duel.moves), None

    async def start_guess_duel(self, session_id: int, user1_id: int, user2_id: int) -> int:
        """Starts a number guess race between both users."""
        target = random.randint(0, 9)
        async with self._lock:
            self._guess_duels[session_id] = GuessDuel(
                session_id=session_id,
                user1_id=user1_id,
                user2_id=user2_id,
                target=target,
            )
        return target

    async def submit_guess_duel(
        self, session_id: int, user_id: int, guess: int
    ) -> tuple[str, int, Optional[int]]:
        """
        Checks a guess in duel mode.
        Returns: ('correct', target, winner_id), ('higher', target, None), ('lower', target, None), ('already_finished', target, winner_id)
        """
        async with self._lock:
            duel = self._guess_duels.get(session_id)
            if not duel:
                return "no_game", 0, None

            if duel.finished:
                return "already_finished", duel.target, duel.winner_id

            target = duel.target
            if guess == target:
                duel.finished = True
                duel.winner_id = user_id
                return "correct", target, user_id
            elif guess < target:
                return "higher", target, None
            else:
                return "lower", target, None


# Global singletons
solo_games = SoloGamesManager()
duel_games = DuelGamesManager()
