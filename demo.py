#!/usr/bin/python

import pygame

import hardware as hw

hw.hardware_init()
siren = hw.Siren()

pygame.mixer.init()
pygame.mixer.music.load("goal.mp3")

while True:
    try:
        input("Press enter for goal")
        print("GOAL!!!")
        siren.enable()
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pass
        siren.disable()
    except KeyboardInterrupt:
        break
    finally:
        hw.hardware_deinit()
