#!/bin/bash

# Directly run the model using the arguments passed to the script ($1, $2)
~/Desktop/llm/models-testings-locally/kitten/kitten-tts \
    ~/Desktop/llm/models-testings-locally/kitten/models/kitten-tts-mini \
    "$1" "${2:-Rosie}" --speed 1.2 \
    -o ~/Desktop/llm/models-testings-locally/kitten/output.wav \
    && pw-play ~/Desktop/llm/models-testings-locally/kitten/output.wav
