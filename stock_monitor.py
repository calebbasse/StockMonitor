from Tkinter import *
from time import sleep
import threading
import requests
import copy
import Queue
import datetime
key = 'H29RZIPMQRR1LCH9'

import json
Ford = """
[{
    "symbol": "F",
    "marketPercent": 0.01555,
    "bidSize": 0,
    "bidPrice": 0,
    "askSize": 0,
    "askPrice": 0,
    "volume": 469462,
    "lastSalePrice": 11.125,
    "lastSaleSize": 500,
    "lastSaleTime": 1497038388608,
    "lastUpdated": 1497038400002
}]
"""

class StockMonitorRequests(object):

    def __init__(self, ui, key):
        # self.ui = ui
        self.key = key

        self.thread_lock = threading.Lock()
        pass

    def start_stock_thread(self, symbol, refresh=5.0):

        t = threading.Thread(target=self.make_stock_requests, args=[symbol, refresh])
        t.daemon = True
        t.start()

    def get_graph_data(self, symbol, interval, days):

        response = requests.get(
            url='http://www.alphavantage.co/query',
            params={'function':'TIME_SERIES_INTRADAY',
                    'symbol': symbol,
                    'outputsize':'full',
                    'interval':interval,
                    'apikey': self.key}
        )

        interval_data = response.json()['Time Series (%s)' % interval]

        time_fmt = '%Y-%m-%d %H:%M:%S'

        interval_data = sorted(
            interval_data.iteritems(), 
            key=lambda t: datetime.datetime.strptime(t[0], time_fmt)
        )

        min_day = datetime.datetime.today() - datetime.timedelta(days=days)

        interval_data = [ d for d in interval_data if datetime.datetime.strptime(d[0], time_fmt) > min_day ]

        avg = lambda d: (float(d[1]['2. high']) + float(d[1]['3. low'])) / 2
        date = lambda d: datetime.datetime.strptime(d[0], time_fmt).strftime('%b %d')

        interval_data = [ {'price': avg(d), 'date': date(d) } for d in interval_data ]

        return interval_data



    def make_stock_requests(self, symbol, refresh):

        response = requests.get(
            url='http://www.alphavantage.co/query',
            params={'symbol': symbol, 'function': 'GLOBAL_QUOTE', 'apikey': self.key}
        )
        current_data = response.json()['Realtime Global Securities Quote']

        val_fmt = '$%.2f'
        tid = threading.current_thread().name

        ui_queue.put((tid, 'create_row',
            { 'symbol': current_data['01. Symbol'], 
              'price': val_fmt % float(current_data['03. Latest Price']),
              'change': val_fmt % float(current_data['08. Price Change']),
              'percent_change': current_data['09. Price Change Percentage'], 
              'day_range': current_data['01. Symbol'],
              'week_range': current_data['01. Symbol'] })
        )

        interval_data = self.get_graph_data(symbol, interval='60min', days=30)
        ui_queue.put((tid, 'build_graph_month', {'prices_dates': interval_data}))

        interval_data = self.get_graph_data(symbol, interval='30min', days=7)
        ui_queue.put((tid, 'build_graph_week', {'prices_dates': interval_data}))

        interval_data = self.get_graph_data(symbol, interval='5min', days=1)
        ui_queue.put((tid, 'build_graph_day', 
                     {'prices_dates': interval_data,
                      'growing_graph_size': 100}))

        positive = True
        
        a = 1
        while True:

            response = requests.get(
                'http://www.alphavantage.co/query',
                params={'symbol': symbol, 'function': 'GLOBAL_QUOTE', 'apikey': self.key}
            )
            print symbol, response.status_code
            data = response.json()['Realtime Global Securities Quote']

            price_change = float(data['08. Price Change'])

            # if positive is True and price_change < 0:
            #     stock_widgets.set_red()
            # elif positive is False and price_change >= 0:
            #     stock_widgets.set_green()

            a += 1
            ui_queue.put((tid, 'update_values', 
                { 'price': val_fmt % float(data['03. Latest Price']),
                  'change': val_fmt % float(data['08. Price Change']),
                  'percent_change': data['09. Price Change Percentage']
                })
            )

            sleep(refresh)

class StockWidgets(object):

    def __init__(self, row, symbol, price, change, percent_change,
                 day_range, week_range, graph_day, graph_week, graph_month):
        
        self.row = row
        self.symbol = symbol
        self.price = price
        self.change = change
        self.percent_change = percent_change
        self.day_range = day_range
        self.week_range = week_range
        self.graph_day = graph_day
        self.graph_week = graph_week
        self.graph_month = graph_month

        # self.build_graph(self.graph_day)
        # self.build_graph(self.graph_week)
        # self.build_graph(self.graph_month)

        self.graph_day.update()
        self.prev_width_day = self.graph_day.winfo_width()
        self.prev_width_week = self.graph_day.winfo_width()
        self.prev_width_month = self.graph_day.winfo_width()

        self.graph_day.bind('<Configure>', self.scale_day)
        self.graph_week.bind('<Configure>', self.scale_week)
        self.graph_month.bind('<Configure>', self.scale_month)

    def scale_day(self, event):
        # scale = event.width/float(self.root.graph.winfo_width())
        scale = event.width/float(self.prev_width_day)
        event.widget.scale('all', 0,0,scale,1)
        self.prev_width_day = event.width

    def scale_week(self, event):
        # scale = event.width/float(self.root.graph.winfo_width())
        scale = event.width/float(self.prev_width_week)
        event.widget.scale('all', 0,0,scale,1)
        self.prev_width_week = event.width
    
    def scale_month(self, event):
        scale = event.width/float(self.prev_width_month)
        event.widget.scale('all', 0,0,scale,1)
        self.prev_width_month = event.width
    
    def update_values(self, symbol=None, price=None, change=None, percent_change=None, 
                      day_range=None, week_range=None):

        if symbol is not None:
            self.symbol['text'] = symbol
        if price is not None:
            self.price['text'] = price
        if change is not None:
            self.change['text'] = change
        if percent_change is not None:
            self.percent_change['text'] = percent_change

    def set_red(self):

        red = '#FF0516'

        self.symbol['bg'] = red
        self.price['bg'] = red
        self.change['bg'] = red
        self.percent_change['bg'] = red
        # self.graph['bg'] = red
        self.day_range['bg'] = red
        self.week_range['bg'] = red

    def set_green(self):

        green = '#1EFF05'

        self.symbol['bg'] = green
        self.price['bg'] = green
        self.change['bg'] = green
        self.percent_change['bg'] = green
        # self.graph['bg'] = green
        self.day_range['bg'] = green
        self.week_range['bg'] = green

    def build_graph(self, graph, prices_dates, growing_graph_size=None):
        graph.update()
        min_w = 15
        min_h = 20
        max_w = graph.winfo_width() - 10
        max_h = graph.winfo_height() - 20
        line_width = 2
        line_color = '#737373'
        low_line = graph.create_line(
            min_w, max_h, max_w, max_h, 

        )
        high_line = graph.create_line(
            min_w, min_h, max_w, min_h, 
            fill=line_color, width=line_width, tags='high', dash=(4,4)
        )
        # import random
        # numbers = random.sample(range(50, 120),10)

        prices = [ p['price'] for p in prices_dates ]

        high = max(prices)
        low = min(prices)

        low_text = graph.create_text(
            min_w, max_h+min_h-2, anchor=SW, text=str(low), fill=line_color
        )
        high_text = graph.create_text(
            min_w, 2, anchor=NW, text=str(high), fill=line_color
        )

        max_hw = max_h - min_h
        high_low = high - low
        calc_y = lambda price: (1-(float(price-low) / high_low)) * max_hw + min_h
        
        graph_size = len(prices) if growing_graph_size is None else growing_graph_size
        width = float(max_w-min_w) / (graph_size - 1)

        x = min_w
        y = calc_y(prices[0])

        
        line_repeat = [(graph_size / 4) * i for i in [1,2,3,4]][:-1]
        count = 0
        trend_coords = [min_w, max_h, x, y]
        for price in prices[1:]:

            x += width

            y = calc_y(price)
            
            if count in line_repeat:
                # print count
                vertical_line = graph.create_line(
                    x, max_h, x, min_h, 
                    fill=line_color, width=1, tags='high'
                )

                line_time = graph.create_text(
                    x, max_h+2,
                    fill=line_color, anchor=N, text=prices_dates[count]['date']
                )

            trend_coords += [round(x), round(y)]

            count += 1


        trend_coords += [x, max_h]

        trend_line = graph.create_polygon(
            *trend_coords, fill='blue', width=line_width, tags='high'
        )


class StockMonitorUI(object):

    def __init__(self, root):
        self.root = root
        self.row = 0

        for x in range(0,6):
            self.root.grid_columnconfigure(x, weight=1)

        self.root.grid()
        self.create_header()


    def create_header(self):

        padx = 20
        pady = 5
        bg = '#00E5D3'

        self.root.symbol = Label(self.root, text='symbol', padx=padx, pady=pady, bg=bg)
        self.root.symbol.grid(row=0, column=0, sticky=N+E+S+W)
        
        self.root.price = Label(self.root, text='price', padx=padx, pady=pady, bg=bg)
        self.root.price.grid(row=0, column=1, sticky=N+E+S+W)

        self.root.change = Label(self.root, text='change', padx=padx, pady=pady, bg=bg)
        self.root.change.grid(row=0, column=2, sticky=N+E+S+W)

        self.root.percent_change = Label(self.root, text=r'%change', padx=padx, pady=pady, bg=bg)
        self.root.percent_change.grid(row=0, column=3, sticky=N+E+S+W)

        self.root.day_range = Label(self.root, text='day range', padx=padx, pady=pady, bg=bg)
        self.root.day_range.grid(row=0, column=4, sticky=N+E+S+W)

        self.root.week_range = Label(self.root, text='week range', padx=padx, pady=pady, bg=bg)
        self.root.week_range.grid(row=0, column=5, sticky=N+E+S+W)

    def create_row(self, symbol, price, change, percent_change, day_range, week_range):

        self.row += 1
        
        graph_height = 100
        self.root.symbol = Label(self.root, text=symbol, pady=10)
        self.root.symbol.grid(row=self.row, column=0, sticky=N+E+S+W)

        self.root.price = Label(self.root, text=price)
        self.root.price.grid(row=self.row, column=1, sticky=N+E+S+W)

        self.root.change = Label(self.root, text=change)
        self.root.change.grid(row=self.row, column=2, sticky=N+E+S+W)

        self.root.percent_change = Label(self.root, text=percent_change)
        self.root.percent_change.grid(row=self.row, column=3, sticky=N+E+S+W)

        self.root.day_range = Label(self.root, text=day_range)
        self.root.day_range.grid(row=self.row, column=4, sticky=N+E+S+W)

        self.root.week_range = Label(self.root, text=week_range)
        self.root.week_range.grid(row=self.row, column=5, sticky=N+E+S+W)

        self.root.graph_day = Canvas(height=graph_height)
        self.root.graph_day.grid(columnspan=2, row=self.row+1, column=0, sticky=N+E+S+W)

        self.root.graph_week = Canvas(height=graph_height)
        self.root.graph_week.grid(columnspan=2, row=self.row+1, column=2, sticky=N+E+S+W)

        self.root.graph_month = Canvas(height=graph_height)
        self.root.graph_month.grid(columnspan=2, row=self.row+1, column=4, sticky=N+E+S+W)

        sw = StockWidgets(self.row, self.root.symbol, self.root.price, self.root.change, 
                          self.root.percent_change, self.root.day_range, self.root.week_range,
                          self.root.graph_day, self.root.graph_week, self.root.graph_month)

        self.row += 1
        
        return sw

ui_queue = Queue.Queue()
stock_rows = {}

def thread_controller(ui):
    try:
        tid, func, kwargs = ui_queue.get_nowait()
        if func == 'create_row':
            stock_widget = ui.create_row(**kwargs)
            stock_rows[tid] = stock_widget
        elif func == 'update_values':
            stock_rows[tid].update_values(**kwargs)
        elif func == 'build_graph_month':
            stock_rows[tid].build_graph(stock_rows[tid].graph_month, **kwargs)
        elif func == 'build_graph_week':
            stock_rows[tid].build_graph(stock_rows[tid].graph_week, **kwargs)
        elif func == 'build_graph_day':
            stock_rows[tid].build_graph(stock_rows[tid].graph_day, **kwargs)
    except Queue.Empty:
        pass

    root.after(1000, thread_controller, ui)


if __name__ == '__main__':
    root = Tk()
    ui = StockMonitorUI(root)
    a = root.after(1000, thread_controller, ui)

    smr = StockMonitorRequests(ui, key)
    smr.start_stock_thread('MSFT')
    #smr.start_stock_thread('ATVI')

    # smr.start_stock_thread('NTDOY')
    # smr.start_stock_thread('ATVI')
    # smr.start_stock_thread('SNE')

    root.mainloop()