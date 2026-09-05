import random

ICEBREAKERS: list[str] = [
    "If you could have dinner with any historical figure, who would it be and why?",
    "What's the weirdest food combination you secretly enjoy?",
    "If you had to survive a zombie apocalypse, which 3 people (real or fictional) would be on your team?",
    "What's the best concert or live show you've ever been to?",
    "If you could instantly become an expert in any skill, what would you choose?",
    "What's the most spontaneous thing you've ever done?",
    "If your life had a theme song, what would it be right now?",
    "What's a movie you can watch over and over without ever getting tired of it?",
    "Beach vacation, mountain cabin, or bustling big city: which one are you picking?",
    "What's something you're really passionate about that not many people know?",
    "If you could wake up tomorrow anywhere in the world, where would you want to be?",
    "What's the best piece of advice you've ever received?",
    "Coffee or tea? And how do you take it?",
    "What's your ultimate comfort food after a long tiring day?",
    "Are you a night owl or an early bird?",
    "If you had a million dollars to spend in 24 hours, what would you buy first?",
    "What's the funniest joke or meme you've seen recently?",
    "What's one thing on your bucket list that you plan to do this year?",
    "Cats, dogs, or exotic pets?",
    "If you could have any superpower for just one hour, what would you do with it?",
    "What's your go-to karaoke song?",
    "If you could time-travel 50 years into the future or 50 years into the past, which would you pick?",
    "What's the coolest place you've ever traveled to?",
    "What hobby did you pick up recently that you really enjoy?",
    "If you were an ice cream flavor, what would you be and why?",
    "What's the last book, podcast, or show that blew your mind?",
    "Would you rather explore deep ocean depths or outer space?",
    "What's your favorite holiday tradition?",
    "What's a trend from the past that you wish would come back?",
    "If you had your own late-night talk show, who would be your first celebrity guest?",
]


def get_random_icebreaker() -> str:
    """Returns a fun, engaging icebreaker question."""
    return random.choice(ICEBREAKERS)
