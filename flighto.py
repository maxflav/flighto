from pprint import pprint
import math
import requests
import sys
import time

stopovers = [
  'AMS',
  'ATL',
  'BER',
  'BOS',
  'BWI',
  'CDG',
  'CLT',
  'DCA',
  'DEN',
  'DFW',
  'DTW',
  'DUB',
  'EWR',
  'FCO',
  'FRA',
  'IAD',
  'JFK',
  'LGA',
  'LGW',
  'LHR',
  'LIS',
  'MAN',
  'MCO',
  'MDW',
  'OPO',
  'ORD',
  'PDL',
  'PHL',
  'PIT',
  'PVD',
  'RDU',
  'YHZ',
  'YYT',
  'YYZ',
]

exclude_airlines = ['']

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

# approximate to 2 decimals
def hours(minutes):
  return math.floor(minutes / 36) / 100

# ([trips], done=True/False, last_offset)
def one_query(date0, from0, to0, offset=''):
  payload = {
    'date0': date0,
    'from0': from0,
    'to0': to0,
  }

  if offset == '':
    url = first_url
  else:
    url = search_url
    payload['offset'] = offset

  try:
    print("requesting", url, payload)
    time.sleep(2.5)
    r = requests.post(url, headers=headers, data=payload)
  except:
    print('failed to request', sys.exc_info()[0])
    return ([], True, '')

  try:
    response = r.json()
  except:
    print('failed to decode json', sys.exc_info()[0], r.text)
    return ([], True, '')

  if 'errors' in response:
    print(response['errors'])
    return ([], True, '')

  if 'routings' in response:
    routings.update(response['routings'])
  if 'legs' in response:
    legs.update(response['legs'])
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

    results.append({
      'arrive_iso': my_legs[-1]['arrive_iso'],
      'depart_iso': my_legs[0]['depart_iso'],
      'arrive': my_legs[-1]['arrive'],
      'depart': my_legs[0]['depart'],
      'flights': flights,
      'layovers': layovers,
      'price': itin['price'],
      'time': hours(my_legs[-1]['arrive'] - my_legs[0]['depart']),
    })

  print("got {} results".format(len(results)))
  return (results, response['done'], response['last_offset'])

# filtered trips where price and time is <= 2 * the minimum
# [{
#   layovers: [{airport: "CODE", layover: hours}],
#   time: hours,
#   depart_iso: iso in local time,
#   depart: epoch seconds,
#   arrive_iso: iso in local time,
#   arrive: epoch seconds,
#   price: USD,
# }]
def one_trip(date0, from0, to0):
  if from0 == to0:
    return []

  done = False
  offset = ""
  all_results = []
  while not done:
    (partial_results, done, offset) = one_query(date0, from0, to0, offset)
    all_results += partial_results

  return all_results

# same return value as one_trip
# [{
#   layovers: [{airport: "CODE", layover: hours}],
#   time: hours,
#   depart_iso: iso in local time,
#   depart: epoch seconds,
#   arrive_iso: iso in local time,
#   arrive: epoch seconds,
#   price: USD,
# }]
def try_stopover(date0, from0, to0, stopover):
  part1 = one_trip(date0, from0, stopover)
  if len(part1) == 0:
    return []

  part2 = one_trip(date0, stopover, to0)
  if len(part2) == 0:
    return []

  part1 = sorted(part1, key=lambda result: result['arrive'])
  part2 = sorted(part2, key=lambda result: result['depart'])

  stopover_results = []

  for result1 in part1:
    for result2 in part2:
      layover_time = hours(result2['depart'] - result1['arrive'])
      if layover_time < 2:
        # layover is too short
        continue

      total_time = result1['time'] + result2['time'] + layover_time
      new_layover = {'airport': stopover, 'layover': layover_time}

      new_result = {
        'arrive': result2['arrive'],
        'arrive_iso': result2['arrive_iso'],
        'depart': result1['depart'],
        'depart_iso': result1['depart_iso'],
        'flights': result1['flights'] + result2['flights'],
        'layovers': result1['layovers'] + [new_layover] + result2['layovers'],
        'price': result1['price'] + result2['price'],
        'time': total_time,
      }
      stopover_results.append(new_result)

  return stopover_results

def keep_best(results):
  if len(results) == 0:
    return []

  results = sorted(results, key=lambda result: result['price'])
  reduced_results = [results[0]]
  # cheapest first
  # then, remove any that are longer than the previous
  # duration must be getting shorter and shorter
  for result in results[1:]:
    prev_time = reduced_results[-1]['time']
    if result['time'] >= prev_time:
      continue
    reduced_results.append(result)

  return reduced_results

def run(date0, from0, to0):
  # first, try the regular route with no stopover
  all_results = one_trip(date0, from0, to0)
  # print("Finished direct trip")

  # then, try with stopovers
  for stopover in stopovers:
    # eliminate strictly worse results
    all_results = keep_best(all_results)
    pprint(all_results)

    stopover_results = try_stopover(date0, from0, to0, stopover=stopover)
    all_results = all_results + stopover_results

  return keep_best(all_results)

exclude_airlines = ['2V']
pprint(run('11/21/2018', 'BCN', 'MDT'))
