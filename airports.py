from math import asin, cos, radians, sin, sqrt
import argparse
import csv
import dateutil.parser
import sys

def haversine(latlon1, latlon2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    lat1, lon1 = latlon1
    lat2, lon2 = latlon2

    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    r = 6371 # Radius of earth in kilometers. Use 3956 for miles
    return c * r


def get_airports_between(origin_code, dest_code, max_dist=150):
    airport_locations = {}
    with open('airports.csv') as csvfile:
        for row in csv.reader(csvfile):
            [airport_id, name, city, country, iata, icao, latitude, longitude, \
            altitude, timezone, dst, tz, airport_type, source] = row

            if iata[0] == "\\":
                continue

            airport_locations[iata] = (float(latitude), float(longitude))

    origin_latlon = airport_locations[origin_code]
    dest_latlon = airport_locations[dest_code]

    total_dist = haversine(origin_latlon, dest_latlon)
    stopovers = []

    for airport_code, latlon in airport_locations.items():
        if airport_code == origin_code or airport_code == dest_code:
            continue

        newdist = haversine(origin_latlon, latlon) + haversine(latlon, dest_latlon)
        if newdist - total_dist < max_dist:
            stopovers.append(airport_code)

    return stopovers
