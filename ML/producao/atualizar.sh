#!/bin/bash
cd /root/ML
source /root/ML/venv/bin/activate
export $(cat /root/ML/.env | xargs)
python ML.py