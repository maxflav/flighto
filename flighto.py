import requests
from pprint import pprint

first_url = 'https://www.hipmunk.com/api/flights/v3/load_search_first'

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

stopovers = ['LHR', 'LGW', 'BOS', 'JFK']

# filtered trips where price or time is > 2.5 the minimum
# {
#   layovers: [{airport: "CODE", layover: seconds}],
#   time: seconds,
#   depart: iso in local time,
#   arrive: iso in local time,
#   price: USD,
#   airlines: [code],
#   agony: number,
# }
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
        airlines = []

        # calculate layovers and airlines
        for i, leg in enumerate(my_legs):
            from_code = leg['from_code']
            to_code = leg['to_code']

            if i > 0:
                # not the first one
                prev_leg = my_legs[i - 1]
                layovers.append({
                    'airport': from_code,
                    'layover': leg['depart'] - prev_leg['arrive'],
                })

            flight = leg['operating_num'] or leg['marketing_num']
            airline, flight_no = flight
            if airline not in airlines:
                airlines.append(airline)

        results.append({
            'layovers': layovers,
            'airlines': airlines,
            'time': my_legs[-1]['arrive'] - my_legs[0]['depart'],
            'depart': my_legs[0]['depart_iso'],
            'arrive': my_legs[-1]['arrive_iso'],
            'price': itin['price'],
            'agony': itin['agony'],
        })

    # filter to <= min price * 2.5 and <= min time * 2.5
    min_price = min(results, key=lambda result: result['price'])['price']
    price_limit = min_price * 2.5
    price_limit = max(price_limit, 200)

    min_time = min(results, key=lambda result: result['time'])['time']
    time_limit = min_time * 2.5
    time_limit = max(time_limit, 3600)

    filtered_results = [result for result in results if result['price'] <= price_limit and result['time'] <= time_limit]

    return filtered_results

pprint(one_trip('11/22/2018', 'LHR', 'JFK'))
