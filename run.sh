#!/bin/bash
cd ~/dpro_notify && export $(cat .env | xargs) && python3 dpro_monitor.py
