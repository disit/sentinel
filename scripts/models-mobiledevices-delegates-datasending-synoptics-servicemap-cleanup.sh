#!bin/bash
cd modeldevice

while getopts u:p: flag
do
    case "${flag}" in
        u) username_v=${OPTARG};;
        p) password_v=${OPTARG};;
    esac
done
python3 modelmobiledevice+synoptics+servicemap.py $username_v $password_v True
