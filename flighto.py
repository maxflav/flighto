from math import floor
from pprint import pprint
import argparse
import csv
import dateutil.parser
import requests
import sys
import time

exclude_airlines = ['NK']

first_url = 'http://www.hipmunk.com/api/flights/v3/load_search_first'
search_url = 'http://www.hipmunk.com/api/flights/v3/load_search'

headers = {
    'accept':'application/json, text/javascript, */*; q=0.01',
    'accept-encoding':'gzip, deflate, br',
    'accept-language':'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
    'authority':'www.hipmunk.com',
    'content-type':'application/x-www-form-urlencoded; charset=UTF-8',
    # 'cookie'
    'origin':'https://www.hipmunk.com',
    'referer':'https://www.hipmunk.com/flights',
    'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36',
    # 'x-csrf-token'
    'x-hipmunk-api':'true',
    'x-requested-with':'XMLHttpRequest',
}

routings = {}
legs = {}

departbefore = None
departafter = None
arrivebefore = None
arriveafter = None

maxprice = None
maxtime = None


# approximate to 2 decimals
def hours(minutes):
  return floor(minutes / 36) / 100

# ([trips], done=True/False, last_offset)
def one_query(date, frm, to, offset='', arriving=False, departing=False):
  global routings
  global legs
  payload = {
    'date0': date,
    'from0': frm,
    'to0': to,
  }

  if offset == '':
    url = first_url
    legs = {}
    routings = {}
  else:
    url = search_url
    payload['offset'] = offset

  try:
    r = requests.post(url, headers=headers, data=payload)
    time.sleep(30)
  except (KeyboardInterrupt, SystemExit):
    raise
  except:
    print('failed to request', sys.exc_info()[0])
    return ([], True, '')

  try:
    response = r.json()
  except (KeyboardInterrupt, SystemExit):
    raise
  except:
    print('failed to decode json', sys.exc_info()[0], r.text)
    return ([], True, '')


  if 'errors' in response:
    print(response['errors'])
    return ([], True, '')

  if 'routings' in response:
    routings.update(response['routings'])
  if 'legs' in response:
    for new_leg, new_leg_data in response['legs'].items():
      if new_leg not in legs:
        legs[new_leg] = new_leg_data

  if 'itins' in response:
    itins = response['itins'].values()
  else:
    return ([], True, '')

  # construct my results from these itin objects
  results = []

  for itin in itins:
    if not itin:
      continue
    if 'routing_idens' not in itin:
      continue
    routing_iden = itin['routing_idens'][0]
    my_routing = routings[routing_iden]
    leg_idens = my_routing['leg_idens']
    my_legs = [legs[leg_iden] for leg_iden in leg_idens]

    layovers = []
    flights = []

    skip_itin = False
    # calculate layovers
    for i, leg in enumerate(my_legs):
      if 'from_code' not in leg or 'to_code' not in leg:
        print('leg is missing from_code or to_code?')
        pprint(leg)
        skip_itin = True
        break
      from_code = leg['from_code']
      to_code = leg['to_code']

      if i > 0:
        # not the first one
        prev_leg = my_legs[i - 1]
        layovers.append({
          'airport': from_code,
          'layover': hours(leg['depart'] - prev_leg['arrive']),
        })

      flight = leg['operating_num'] or leg['marketing_num']
      airline, flight_no = flight
      if airline in exclude_airlines:
        skip_itin = True
        break
      flights.append(airline + str(flight_no))

    if skip_itin:
      continue


    if maxprice and itin['price'] > maxprice:
      continue

    hr = hours(my_legs[-1]['arrive'] - my_legs[0]['depart'])
    if maxtime and hr > maxtime:
      continue


    arrive_iso = my_legs[-1]['arrive_iso']
    if arriving and (arrivebefore or arriveafter):
      arrive_dt = dateutil.parser.parse(arrive_iso)
      arrive_hhmm = arrive_dt.strftime('%H%M')
      if arrivebefore and arrive_hhmm > arrivebefore:
        continue
      if arriveafter and arrive_hhmm < arriveafter:
        continue

    depart_iso = my_legs[0]['depart_iso']
    if departing and (departbefore or departafter):
      depart_dt = dateutil.parser.parse(depart_iso)
      depart_hhmm = depart_dt.strftime('%H%M')
      if departbefore and depart_hhmm > departbefore:
        continue
      if departafter and depart_hhmm < departafter:
        continue

    results.append({
      'arrive_iso': arrive_iso,
      'depart_iso': depart_iso,
      'arrive': my_legs[-1]['arrive'],
      'depart': my_legs[0]['depart'],
      'flights': flights,
      'layovers': layovers,
      'price': itin['price'],
      'time': hr,
    })

  return (results, response['done'], response['last_offset'])

# [{
#   layovers: [{airport: 'CODE', layover: hours}],
#   time: hours,
#   depart_iso: iso in local time,
#   depart: epoch seconds,
#   arrive_iso: iso in local time,
#   arrive: epoch seconds,
#   price: USD,
# }]
def one_trip(date, frm, to, arriving=False, departing=False):
  if frm == to:
    return []

  done = False
  offset = ''
  all_results = []
  while not done:
    (partial_results, done, offset) = one_query(date, frm, to, offset, arriving=arriving, departing=departing)
    all_results += partial_results

  print(int(time.time()), date, frm, to, len(all_results))
  return all_results

# same return value as one_trip
# [{
#   layovers: [{airport: 'CODE', layover: hours}],
#   time: hours,
#   depart_iso: iso in local time,
#   depart: epoch seconds,
#   arrive_iso: iso in local time,
#   arrive: epoch seconds,
#   price: USD,
# }]
def try_stopover(date, frm, to, stopover):
  if frm == stopover or to == stopover:
    return []

  part1 = one_trip(date, frm, stopover, departing=True)
  if len(part1) == 0:
    return []

  part2 = one_trip(date + "+1", stopover, to, arriving=True)
  if len(part2) == 0:
    return []

  part1 = sorted(part1, key=lambda result: result['arrive'])
  part2 = sorted(part2, key=lambda result: result['depart'])

  stopover_results = []

  for result1 in part1:
    for result2 in part2:
      layover_time = hours(result2['depart'] - result1['arrive'])
      if layover_time < 1.5:
        # layover is too short
        continue

      total_time = result1['time'] + result2['time'] + layover_time
      if maxtime and total_time > maxtime:
        # too long
        continue

      total_price = result1['price'] + result2['price']
      if maxprice and total_price > maxprice:
        # too expensive
        continue

      new_layover = {'airport': stopover, 'layover': layover_time}

      new_result = {
        'arrive': result2['arrive'],
        'arrive_iso': result2['arrive_iso'],
        'depart': result1['depart'],
        'depart_iso': result1['depart_iso'],
        'flights': result1['flights'] + result2['flights'],
        'layovers': result1['layovers'] + [new_layover] + result2['layovers'],
        'price': total_price,
        'time': total_time,
      }
      stopover_results.append(new_result)
      stopover_results = keep_best(stopover_results)

  return stopover_results

def keep_best(results):
  if len(results) == 0:
    return []

  results = sorted(results, key=lambda result: (result['price'], result['time']))
  reduced_results = [results[0]]
  # cheapest first
  # then, remove any that are longer than the previous
  # duration must be getting shorter and shorter
  for result in results[1:]:
    if maxtime and result['time'] > maxtime:
      continue

    if maxprice and result['price'] > maxprice:
      break

    prev_time = reduced_results[-1]['time']
    if result['time'] >= prev_time:
      continue
    reduced_results.append(result)

  return reduced_results

def run(date, frm, fromcity, to, tocity, skipdirect, skipairports=[]):
  skipairports = set(skipairports)
  stopovers = []
  with open('airports.csv') as csvfile:
    for row in csv.reader(csvfile):
        [iata, latitude, longitude] = row
        if iata not in skipairports:
          stopovers.append(iata)

  stopovers = sorted(stopovers)
  print("Going to try these stopovers:", stopovers)

  if skipdirect:
    all_results = []
  else:
    # first, try the regular route with no stopover
    all_results = one_trip(date, fromcity or frm, tocity or to, arriving=True, departing=True)
  
  prev_results = all_results[:]

  # then, try with stopovers
  for stopover in stopovers:
    # eliminate strictly worse results
    all_results = keep_best(all_results)
    if all_results != prev_results:
      pprint(all_results)
    prev_results = all_results[:]

    stopover_results = try_stopover(date, fromcity or frm, tocity or to, stopover=stopover)
    all_results = all_results + stopover_results

  return keep_best(all_results)

parser = argparse.ArgumentParser()
parser.add_argument('--date', type=str, help='e.g. 11/21/2018', required=True)
parser.add_argument('--from', type=str, help='e.g. BCN', required=True, dest='frm')
parser.add_argument('--fromcity', type=str, help='Hipmunk allows cities e.g. QSF, NYC')
parser.add_argument('--to', type=str, help='e.g. MDT', required=True)
parser.add_argument('--tocity', type=str, help='e.g. QSF/NYC')
parser.add_argument('--departbefore', type=str, help='HHMM e.g. 2030, for 8:30pm')
parser.add_argument('--departafter', type=str)
parser.add_argument('--arrivebefore', type=str)
parser.add_argument('--arriveafter', type=str)
parser.add_argument('--maxprice', type=int, help='USD e.g. 1000')
parser.add_argument('--maxtime', type=int, help='in hours, e.g. 20')
parser.add_argument('--skipdirect', help='Don\'t try the direct route', action='store_true')
parser.add_argument('--skip', type=str, nargs='+', help='A list of airports to skip, separated by spaces?')

args = parser.parse_args()

departbefore = args.departbefore
departafter = args.departafter
arrivebefore = args.arrivebefore
arriveafter = args.arriveafter

maxprice = args.maxprice
maxtime = args.maxtime

pprint(run(
  date=args.date,
  frm=args.frm,
  fromcity=args.fromcity,
  to=args.to,
  tocity=args.tocity,
  skipdirect=args.skipdirect,
  skipairports=args.skip or [],
))
