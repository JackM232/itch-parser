import csv

def decode_add_order(msg): 
    return {
        'stock_locate': int.from_bytes(msg[1:3], 'big'),
        'tracking': int.from_bytes(msg[3:5], 'big'),
        'timestamp': int.from_bytes(msg[5:11], 'big'),
        'order_ref': int.from_bytes(msg[11:19], 'big'),
        'side': chr(msg[19]),
        'shares': int.from_bytes(msg[20:24], 'big'),
        'stock': msg[24:32].decode('ascii'),
        'price': int.from_bytes(msg[32:36])
    }

def parse_add_orders(data):

    orders = []
    pos = 0
    
    while pos < len(data):
        length = int.from_bytes(data[pos:pos+2], 'big')

        if pos + 2 + length > len(data):
            break

        msg = data[pos+2: pos + 2 + length]

        if chr(msg[0]) == 'A':
            orders.append(decode_add_order(msg))

        pos = pos + 2 + length

    return orders

if __name__ == '__main__':
    data = open('data/itch_sample.bin', 'rb').read()
    orders = parse_add_orders(data)
    print(len(orders), 'add orders')
    print(orders[0])

    with open('data/add_orders.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=orders[0].keys())
        writer.writeheader()
        writer.writerows(orders)
    print('wrote data/add_orders.csv')