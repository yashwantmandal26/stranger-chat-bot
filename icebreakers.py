import random

ICEBREAKERS: list[str] = [
    "What's something good that happened to you today? 😊",
    "Where are you from, and what's your favorite thing about your city?",
    "What kind of music do you listen to the most?",
    "What do you usually love doing on your days off or weekends?",
    "Are you more into movies, anime, or series? Any recommendations?",
    "What's your ultimate comfort food after a long day?",
    "Are you a morning person or a night owl? 🌙",
    "If you could travel anywhere in the world right now, where would you go?",
    "What's a hobby or skill you've always wanted to learn?",
    "Coffee, tea, or cold drinks: what's your go-to?",
    "What's the best trip or vacation you've ever taken?",
    "Do you have any pets, or are you more of a dog or cat person?",
    "What kind of personality traits do you value most in friends?",
    "What's a movie or series you can rewatch without getting bored?",
    "What's your idea of a perfect, relaxing evening?",
    "What's something small that always makes you happy?",
    "Do you prefer cozy indoor vibes or going out exploring?",
    "What's the coolest place you've ever visited?",
    "What are you currently studying or working on?",
    "What was your favorite childhood cartoon or game?",
    "What's a song that always puts you in a good mood?",
    "What's the best advice someone has given you?",
    "If you could instantly speak any language fluently, which would you pick?",
    "What's something exciting you're looking forward to recently?",
    "What's your favorite season of the year, and why?",
    "Do you like cooking, or do you prefer ordering in?",
    "What's something you're really passionate about?",
    "Beach sunset or mountain sunrise: which one do you pick?",
    "What's the funniest thing that happened to you recently?",
    "What's your favorite book or story?",
    "What's one goal you want to achieve this year?",
    "What's your favorite dessert or sweet treat?",
    "How do you usually unwind when you feel stressed?",
    "If you could attend any concert or music festival, who would you see?",
    "What's a talent or skill you have that not many people know about?",
    "What's your favorite board game or video game?",
    "Do you prefer deep late-night conversations or fun casual chats?",
    "What's something you tried recently that surprised you?",
    "If you could design your dream house, what's one must-have room?",
    "What's the most thoughtful thing someone has done for you recently?",
]


def get_random_icebreaker() -> str:
    """Returns a warm, friendly icebreaker question to know someone better."""
    return random.choice(ICEBREAKERS)
