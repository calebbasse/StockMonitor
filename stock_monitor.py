from Tkinter import *
from time import sleep
import threading
import requests
import copy

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
        self.ui = ui
        self.key = key

        self.thread_lock = threading.Lock()
        pass

    def start_stock_thread(self, symbol, fake_data=None):

        t = threading.Thread(target=self.make_stock_requests, args=[symbol, 5.0], 
                             kwargs={'fake_data': fake_data})
        t.daemon = True
        t.start()

    def make_stock_requests(self, symbol, refresh, fake_data=None):


        if not fake_data:
            response = requests.get(
                'http://www.alphavantage.co/query',
                params={'symbol': symbol, 'function': 'GLOBAL_QUOTE', 'apikey': self.key}
            )
            data = response.json()['Realtime Global Securities Quote']

        else:
            fake_data = json.loads(fake_data)
            data = fake_data

        val_fmt = '$%.2f'

        self.thread_lock.acquire()
        stock_widgets = self.ui.create_row(
            symbol=data['01. Symbol'], 
            price=val_fmt % float(data['03. Latest Price']),
            change=val_fmt % float(data['08. Price Change']),
            percent_change=data['09. Price Change Percentage'], 
            day_range=data['01. Symbol'],
            week_range=data['01. Symbol']
        )
        self.thread_lock.release()

        positive = True
        
        a = 1
        while True:

            response = requests.get(
                'http://www.alphavantage.co/query',
                params={'symbol': symbol, 'function': 'GLOBAL_QUOTE', 'apikey': self.key}
            )
            data = response.json()['Realtime Global Securities Quote']

            price_change = float(data['08. Price Change'])

            if positive is True and price_change < 0:
                stock_widgets.set_red()
            elif positive is False and price_change >= 0:
                stock_widgets.set_green()

            a += 1
            stock_widgets.update_values(
                price=val_fmt % float(data['03. Latest Price']),
                change=val_fmt % float(data['08. Price Change']),
                percent_change=data['09. Price Change Percentage']
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

        self.build_graph(self.graph_day)
        self.build_graph(self.graph_week)
        self.build_graph(self.graph_month)

        self.graph_day.bind('<Configure>', self.scale_day)
        self.graph_week.bind('<Configure>', self.scale_week)
        self.graph_month.bind('<Configure>', self.scale_month)

        self.graph_day.update()
        self.prev_width_day = self.graph_day.winfo_width()
        self.prev_width_week = self.graph_day.winfo_width()
        self.prev_width_month = self.graph_day.winfo_width()

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

    def build_graph(self, graph):

        graph.update()
        min_w = 15
        min_h = 20
        max_w = graph.winfo_width() - 10
        max_h = graph.winfo_height() - 20

        line_width = 2
        line_color = '#737373'
        
        low_line = graph.create_line(
            min_w, max_h, max_w, max_h, 
            fill=line_color, width=line_width, tags='low', dash=(4,4)
        )
        high_line = graph.create_line(
            min_w, min_h, max_w, min_h, 
            fill=line_color, width=line_width, tags='high', dash=(4,4)
        )

        import random
        numbers = random.sample(range(50, 120), 66)

        high = max(numbers)
        low = min(numbers)

        low_text = graph.create_text(
            min_w, max_h+min_h-2, anchor=SW, text=str(low), fill=line_color
        )
        high_text = graph.create_text(
            min_w, 2, anchor=NW, text=str(high), fill=line_color
        )

        max_hw = max_h - min_h
        high_low = high - low
        calc_y = lambda num: (1-(float(num-low) / high_low)) * max_hw + min_h
        width = max_w / len(numbers)

        last_x = min_w
        last_y = calc_y(numbers[0])

        
        line_repeat = [(len(numbers) / 4) * x for x in [1,2,3,4]][:-1]
        # print line_repeat
        count = 0
        for num in numbers[1:]:

            new_x = last_x+width
            new_y = calc_y(num)
            
            if count in line_repeat:
                # print count
                vertical_line = graph.create_line(
                    last_x, max_h, last_x, min_h, 
                    fill=line_color, width=1, tags='high'
                )

                line_time = graph.create_text(
                    last_x, max_h+2,
                    fill=line_color, anchor=N, text='today'
                )


            high_line = graph.create_line(
                last_x, last_y, new_x, new_y, 
                fill=line_color, width=line_width, tags='high'
            )

            count += 1

            last_x = new_x
            last_y = new_y 






class StockMonitorUI(object):

    def __init__(self, root):
        self.root = root
        self.row = 0

        for x in range(0,7):
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
        print self.row
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

        self.root.graph_day = Canvas(height=200)
        self.root.graph_day.grid(columnspan=2, row=self.row+1, column=0, sticky=N+E+S+W)

        self.root.graph_week = Canvas(height=200)
        self.root.graph_week.grid(columnspan=2, row=self.row+1, column=2, sticky=N+E+S+W)

        self.root.graph_month = Canvas(height=200)
        self.root.graph_month.grid(columnspan=2, row=self.row+1, column=4, sticky=N+E+S+W)

        sw = StockWidgets(self.row, self.root.symbol, self.root.price, self.root.change, 
                          self.root.percent_change, self.root.day_range, self.root.week_range,
                          self.root.graph_day, self.root.graph_week, self.root.graph_month)

        self.row += 1
        
        return sw


if __name__ == '__main__':
    root = Tk()
    ui = StockMonitorUI(root)
    smr = StockMonitorRequests(ui, key)
    smr.start_stock_thread('MSFT')
    smr.start_stock_thread('MSFT')

        # smr.start_stock_thread('NTDOY')
    # smr.start_stock_thread('ATVI')
    # smr.start_stock_thread('SNE')

    root.mainloop()