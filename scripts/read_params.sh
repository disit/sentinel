#!/bin/bash

while getopts u:a:f: flag
do
    case "${flag}" in
        u) username_v=${OPTARG};;
        a) age_v=${OPTARG};;
        f) fullname_v=${OPTARG};;
    esac
done
echo "Username: $username_v";
echo "Age: $age_v";
echo "Full Name: $fullname_v";

