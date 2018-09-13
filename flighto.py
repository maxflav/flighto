from pprint import pprint
import math
import requests
import sys

# stopovers = ['LHR', 'LGW', 'BOS', 'JFK']
# stopovers = ['BOS', 'YYZ', 'FRA', 'PHL']
# stopovers = ['LIS', 'LGA', 'BWI', 'IAD']
# stopovers = ['CLT', 'PIT', 'EWR', 'CDG']
# stopovers = ['AMS', 'DFW', 'ATL', 'ORD']
# stopovers = ['MCO', 'DEN', 'RDU', 'FCO']
# stopovers = ['DUB', 'MAN', 'BER', 'OPO', 'YHZ', 'PVD']
stopovers = ['MDW', 'DCA', 'DTW', 'YYT']

# american stopovers: ['BOS', 'JFK', 'YYZ', 'PHL', 'LGA', 'BWI', 'IAD', 'CLT', 'PIT', 'EWR', 'DFW', 'ATL', 'ORD', 'MCO', 'DEN', 'RDU', 'YHZ', 'PVD', 'MDW', 'DCA', 'DTW', 'YYT']
# european stopovers: ['LHR', 'LGW', 'FRA', 'LIS', 'CDG', 'AMS', 'FCO', 'DUB', 'MAN', 'BER', 'OPO']

first_url = 'http://www.hipmunk.com/api/flights/v3/load_search_first'

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

# approximate to 2 decimals
def hours(minutes):
  return math.floor(minutes / 36) / 100


def get_price_limit(results):
  return 1300

  # if len(results) == 0:
  #   return 1500

  # min_price = min(results, key=lambda result: result['price'])['price']
  # print("current min price: {}".format(min_price))
  # price_limit = min_price * 2.5
  # price_limit = max(price_limit, 200)
  # price_limit = min(price_limit, 1000)
  # return price_limit


def get_time_limit(results):
  return 24

  # if len(results) == 0:
  #   return 20

  # min_time = min(results, key=lambda result: result['time'])['time']
  # print("current min time: {}".format(min_time))
  # time_limit = min_time * 2
  # time_limit = max(time_limit, 1)
  # time_limit = min(time_limit, 20)
  # return time_limit


# filtered trips where price and time is <= 2 * the minimum
# [{
#   layovers: [{airport: "CODE", layover: hours}],
#   time: hours,
#   depart_iso: iso in local time,
#   depart: epoch seconds,
#   arrive_iso: iso in local time,
#   arrive: epoch seconds,
#   price: USD,
#   agony: number,
# }]
def one_trip(date0, from0, to0):
  payload = {
    'date0': date0,
    'from0': from0,
    'to0': to0,
  }

  try:
    r = requests.post(first_url, headers=headers, data=payload)
  except:
    print('failed to request', sys.exc_info()[0])
    return

  response = r.json()
  if 'errors' in response:
    print(response['errors'])
    return

  routings = response['routings']
  legs = response['legs']
  itins = response['itins'].values()

  # construct my results from these itin objects
  results = []

  for itin in itins:
    routing_iden = itin['routing_idens'][0]
    my_routing = routings[routing_iden]
    leg_idens = my_routing['leg_idens']
    my_legs = [legs[leg_iden] for leg_iden in leg_idens]

    layovers = []
    # airlines = []
    flights = []

    # calculate layovers and airlines
    for i, leg in enumerate(my_legs):
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
      # if airline not in airlines:
      #   airlines.append(airline)
      flights.append(airline + str(flight_no))

    results.append({
      'agony': itin['agony'],
      # 'airlines': airlines,
      'arrive_iso': my_legs[-1]['arrive_iso'],
      'depart_iso': my_legs[0]['depart_iso'],
      'arrive': my_legs[-1]['arrive'],
      'depart': my_legs[0]['depart'],
      'flights': flights,
      'layovers': layovers,
      'price': itin['price'],
      'time': hours(my_legs[-1]['arrive'] - my_legs[0]['depart']),
    })

  # filter to <= min price * 2 and <= min time * 2

  price_limit = get_price_limit(results)
  time_limit = get_time_limit(results)

  # filtered_results = results
  filtered_results = [result for result in results if result['price'] <= price_limit and result['time'] <= time_limit]
  sorted_results = sorted(filtered_results, key=lambda result: result['agony'])

  # de-dupe on the list of flights
  flight_lists = set()
  deduped_results = []
  for result in sorted_results:
    flight_tuple = tuple(result['flights'])
    if flight_tuple in flight_lists:
      continue
    flight_lists.add(flight_tuple)
    deduped_results.append(result)

  return deduped_results


# same return value as one_trip
# [{
#   layovers: [{airport: "CODE", layover: hours}],
#   time: hours,
#   depart_iso: iso in local time,
#   depart: epoch seconds,
#   arrive_iso: iso in local time,
#   arrive: epoch seconds,
#   price: USD,
#   agony: number,
# }]
def try_stopover(date0, from0, to0, stopover, price_limit=1500, time_limit=20):
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
      if result1['price'] + result2['price'] > price_limit:
        # too expensive
        continue

      layover_time = hours(result2['depart'] - result1['arrive'])
      if layover_time < 1:
        # layover is too short
        continue

      total_time = result1['time'] + result2['time'] + layover_time
      if total_time > time_limit:
        # too long
        continue

      new_layover = {'airport': stopover, 'layover': layover_time}

      new_result = {
        'agony': result1['agony'] + result2['agony'],
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
  # print("keep_best")
  # pprint(results)
  # print("\n")
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
      # print("removing {} because it is worse than {}".format(result['flights'], reduced_results[-1]['flights']))
      continue
    reduced_results.append(result)

  return reduced_results

def run(date0, from0, to0):
  # first, try the regular route with no stopover
  all_results = one_trip(date0, from0, to0)
  print("Finished direct trip")

  # then, try with stopovers
  for stopover in stopovers:
    # eliminate strictly worse results
    all_results = keep_best(all_results)
    print("Currently {} results".format(len(all_results)))

    price_limit = get_price_limit(all_results)
    time_limit = get_time_limit(all_results)

    stopover_results = try_stopover(date0, from0, to0, stopover=stopover, price_limit=price_limit, time_limit=time_limit)
    print("Finished {} stopover".format(stopover))

    all_results = all_results + stopover_results

  return keep_best(all_results)

pprint(run('11/21/2018', 'BCN', 'MDT'))
