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
# ---------------------------------------------------------
# Partner Duels Manager & Session Scoreboard
# ---------------------------------------------------------
class SessionScoreboard:
    """Tracks head-to-head game duel scores between connected strangers in a chat session."""

    def __init__(self) -> None:
        # session_id -> {user1_id: wins, user2_id: wins, "ties": count, "games": count}
        self._scores: dict[int, dict[Any, int]] = {}

    def record_result(
        self, session_id: int, winner_id: Optional[int], user1_id: int, user2_id: int
    ) -> tuple[int, int, int]:
        if session_id not in self._scores:
            self._scores[session_id] = {user1_id: 0, user2_id: 0, "ties": 0, "games": 0}
        sc = self._scores[session_id]
        sc["games"] = sc.get("games", 0) + 1
        if winner_id == user1_id:
            sc[user1_id] = sc.get(user1_id, 0) + 1
        elif winner_id == user2_id:
            sc[user2_id] = sc.get(user2_id, 0) + 1
        else:
            sc["ties"] = sc.get("ties", 0) + 1
        return sc.get(user1_id, 0), sc.get(user2_id, 0), sc.get("ties", 0)

    def get_score(self, session_id: int, my_id: int, partner_id: int) -> tuple[int, int, int]:
        sc = self._scores.get(session_id, {})
        return sc.get(my_id, 0), sc.get(partner_id, 0), sc.get("ties", 0)

    def reset_session(self, session_id: int) -> None:
        self._scores.pop(session_id, None)


@dataclass
class MathDuel:
    session_id: int
    user1_id: int
    user2_id: int
    puzzle: MathPuzzle
    winner_id: Optional[int] = None
    answered: bool = False
    started_at: float = field(default_factory=time.time)
    attempts: dict[int, int] = field(default_factory=dict)
    last_wrong_guess: dict[int, int] = field(default_factory=dict)


@dataclass
class RPSDuel:
    session_id: int
    user1_id: int
    user2_id: int
    moves: dict[int, str] = field(default_factory=dict)
    started_at: float = field(default_factory=time.time)
    finished: bool = False


@dataclass
class GuessDuel:
    session_id: int
    user1_id: int
    user2_id: int
    target: int
    winner_id: Optional[int] = None
    finished: bool = False
    started_at: float = field(default_factory=time.time)
    attempts: dict[int, int] = field(default_factory=dict)
    history: dict[int, list[tuple[int, str]]] = field(default_factory=dict)


@dataclass
class DiceDuel:
    session_id: int
    user1_id: int
    user2_id: int
    starter_id: int
    rolls: dict[int, int] = field(default_factory=dict)
    finished: bool = False
    started_at: float = field(default_factory=time.time)


class DuelGamesManager:
    """Manages real-time multiplayer duels between connected strangers."""

    def __init__(self) -> None:
        self._math_duels: dict[int, MathDuel] = {}
        self._rps_duels: dict[int, RPSDuel] = {}
        self._guess_duels: dict[int, GuessDuel] = {}
        self._dice_duels: dict[int, DiceDuel] = {}
        self._scoreboard = SessionScoreboard()
        self._lock = asyncio.Lock()

    def get_session_score(
        self, session_id: int, my_id: int, partner_id: int
    ) -> tuple[int, int, int]:
        return self._scoreboard.get_score(session_id, my_id, partner_id)

    def reset_session(self, session_id: int) -> None:
        self._scoreboard.reset_session(session_id)
        self._math_duels.pop(session_id, None)
        self._rps_duels.pop(session_id, None)
        self._guess_duels.pop(session_id, None)
        self._dice_duels.pop(session_id, None)

    # --- Math Duel ---
    async def start_math_duel(self, session_id: int, user1_id: int, user2_id: int) -> MathPuzzle:
        """Starts a live math duel between two connected strangers."""
        puzzle = generate_math_puzzle()
        async with self._lock:
            self._math_duels[session_id] = MathDuel(
                session_id=session_id,
                user1_id=user1_id,
                user2_id=user2_id,
                puzzle=puzzle,
                attempts={user1_id: 0, user2_id: 0},
            )
        return puzzle

    async def submit_math_answer(
        self, session_id: int, user_id: int, answer: int
    ) -> tuple[str, Optional[int], int, int, float, tuple[int, int, int]]:
        """
        Evaluates a math duel answer.
        Returns:
          (status, winner_id, correct_ans, user_attempts, elapsed_secs, (my_score, partner_score, ties))
          status: 'winner' | 'wrong' | 'already_finished' | 'no_game'
        """
        async with self._lock:
            duel = self._math_duels.get(session_id)
            if not duel:
                return "no_game", None, answer, 0, 0.0, (0, 0, 0)

            p_id = duel.user2_id if duel.user1_id == user_id else duel.user1_id
            if duel.answered:
                scores = self._scoreboard.get_score(session_id, user_id, p_id)
                return "already_finished", duel.winner_id, duel.puzzle.answer, duel.attempts.get(user_id, 0), 0.0, scores

            duel.attempts[user_id] = duel.attempts.get(user_id, 0) + 1
            user_att = duel.attempts[user_id]

            if answer == duel.puzzle.answer:
                duel.answered = True
                duel.winner_id = user_id
                elapsed = max(0.5, round(time.time() - duel.started_at, 1))
                self._scoreboard.record_result(session_id, user_id, duel.user1_id, duel.user2_id)
                scores = self._scoreboard.get_score(session_id, user_id, p_id)
                return "winner", user_id, duel.puzzle.answer, user_att, elapsed, scores
            else:
                duel.last_wrong_guess[user_id] = answer
                scores = self._scoreboard.get_score(session_id, user_id, p_id)
                return "wrong", None, duel.puzzle.answer, user_att, 0.0, scores

    # --- RPS Duel ---
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
    ) -> tuple[bool, dict[int, str], Optional[int], tuple[int, int, int]]:
        """
        Submits an RPS move.
        Returns:
          (is_finished, moves_dict, winner_id, (my_score, partner_score, ties))
        """
        async with self._lock:
            duel = self._rps_duels.get(session_id)
            if not duel:
                return False, {}, None, (0, 0, 0)

            p_id = duel.user2_id if duel.user1_id == user_id else duel.user1_id
            duel.moves[user_id] = move.lower()

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
                    winner_id = None

                self._scoreboard.record_result(session_id, winner_id, u1, u2)
                scores = self._scoreboard.get_score(session_id, user_id, p_id)
                return True, dict(duel.moves), winner_id, scores

            scores = self._scoreboard.get_score(session_id, user_id, p_id)
            return False, dict(duel.moves), None, scores

    # --- Number Guess Duel ---
    async def start_guess_duel(self, session_id: int, user1_id: int, user2_id: int) -> int:
        """Starts a number guess race between both users."""
        target = random.randint(0, 9)
        async with self._lock:
            self._guess_duels[session_id] = GuessDuel(
                session_id=session_id,
                user1_id=user1_id,
                user2_id=user2_id,
                target=target,
                attempts={user1_id: 0, user2_id: 0},
                history={user1_id: [], user2_id: []},
            )
        return target

    async def submit_guess_duel(
        self, session_id: int, user_id: int, guess: int
    ) -> tuple[str, int, Optional[int], int, int, float, tuple[int, int, int]]:
        """
        Evaluates a guess in duel mode.
        Returns:
          (status, target, winner_id, my_attempts, partner_attempts, elapsed_secs, (my_score, partner_score, ties))
          status: 'correct' | 'higher' | 'lower' | 'already_finished' | 'no_game'
        """
        async with self._lock:
            duel = self._guess_duels.get(session_id)
            if not duel:
                return "no_game", 0, None, 0, 0, 0.0, (0, 0, 0)

            p_id = duel.user2_id if duel.user1_id == user_id else duel.user1_id
            if duel.finished:
                scores = self._scoreboard.get_score(session_id, user_id, p_id)
                return (
                    "already_finished",
                    duel.target,
                    duel.winner_id,
                    duel.attempts.get(user_id, 0),
                    duel.attempts.get(p_id, 0),
                    0.0,
                    scores,
                )

            duel.attempts[user_id] = duel.attempts.get(user_id, 0) + 1
            my_att = duel.attempts[user_id]
            p_att = duel.attempts.get(p_id, 0)
            target = duel.target

            if guess == target:
                duel.finished = True
                duel.winner_id = user_id
                elapsed = max(1.0, round(time.time() - duel.started_at, 1))
                self._scoreboard.record_result(session_id, user_id, duel.user1_id, duel.user2_id)
                scores = self._scoreboard.get_score(session_id, user_id, p_id)
                return "correct", target, user_id, my_att, p_att, elapsed, scores
            elif guess < target:
                duel.history.setdefault(user_id, []).append((guess, "higher"))
                scores = self._scoreboard.get_score(session_id, user_id, p_id)
                return "higher", target, None, my_att, p_att, 0.0, scores
            else:
                duel.history.setdefault(user_id, []).append((guess, "lower"))
                scores = self._scoreboard.get_score(session_id, user_id, p_id)
                return "lower", target, None, my_att, p_att, 0.0, scores

    # --- Interactive Turn Dice Duel ---
    async def start_dice_duel(
        self, session_id: int, user1_id: int, user2_id: int, starter_id: int
    ) -> int:
        """Starter rolls their dice to challenge partner."""
        starter_roll = random.randint(1, 6)
        async with self._lock:
            self._dice_duels[session_id] = DiceDuel(
                session_id=session_id,
                user1_id=user1_id,
                user2_id=user2_id,
                starter_id=starter_id,
                rolls={starter_id: starter_roll},
                finished=False,
            )
        return starter_roll

    async def submit_dice_roll(
        self, session_id: int, challenger_id: int
    ) -> tuple[str, int, int, Optional[int], tuple[int, int, int]]:
        """
        Challenger rolls dice to answer challenge.
        Returns:
          (status, starter_roll, challenger_roll, winner_id, (challenger_score, starter_score, ties))
          status: 'finished' | 'already_finished' | 'same_player' | 'no_game'
        """
        async with self._lock:
            duel = self._dice_duels.get(session_id)
            if not duel:
                return "no_game", 0, 0, None, (0, 0, 0)

            starter_id = duel.starter_id
            if challenger_id == starter_id:
                return "same_player", duel.rolls.get(starter_id, 0), 0, None, (0, 0, 0)

            if duel.finished:
                scores = self._scoreboard.get_score(session_id, challenger_id, starter_id)
                return (
                    "already_finished",
                    duel.rolls.get(starter_id, 0),
                    duel.rolls.get(challenger_id, 0),
                    duel.rolls.get("winner_id"),
                    scores,
                )

            challenger_roll = random.randint(1, 6)
            starter_roll = duel.rolls.get(starter_id, random.randint(1, 6))
            duel.rolls[challenger_id] = challenger_roll
            duel.finished = True

            if challenger_roll > starter_roll:
                winner_id = challenger_id
            elif starter_roll > challenger_roll:
                winner_id = starter_id
            else:
                winner_id = None

            duel.rolls["winner_id"] = winner_id
            self._scoreboard.record_result(session_id, winner_id, duel.user1_id, duel.user2_id)
            scores = self._scoreboard.get_score(session_id, challenger_id, starter_id)
            return "finished", starter_roll, challenger_roll, winner_id, scores


# Global singletons
solo_games = SoloGamesManager()
duel_games = DuelGamesManager()
