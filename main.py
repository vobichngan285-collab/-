"""Entry point. Game Text Reader 1.0, Windows x64."""
import multiprocessing
from game_reader.app import run

if __name__ == "__main__":
    multiprocessing.freeze_support()
    run()
