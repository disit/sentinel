#!bin/bash
cd synoptics

while getopts u:p:d: flag
do
    case "${flag}" in
        u) username_v=${OPTARG};;
        p) password_v=${OPTARG};;
        p) device_v=${OPTARG};;
    esac
done
python3 synoptics.py $username_v $password_v $device_v
