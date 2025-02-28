#!/usr/bin/python

import pygame

from hardware import Siren

siren = Siren()

pygame.mixer.init()
pygame.mixer.music.load("goal.mp3")

try:
    while True:
        input("Press enter for goal")
        print("GOAL!!!")
        siren.enable()
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pass
        siren.disable()
except KeyboardInterrupt:
    siren.shutdown()
