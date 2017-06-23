from Tkinter import *
from time import sleep
import threading
import requests
import copy
import Queue
import datetime
import colorsys
key = 'H29RZIPMQRR1LCH9'

import json

color_red = '#894747'
color_green = '#4c8946'
update_red = '#7c3f3f'
update_green = '#3f7c48'
header_grey = '#CFCFCF'
time_line_color = '#adadad'
graph_colors = '#adadad'

text_color = 'white'


class StockMonitorRequests(object):

    def __init__(self, ui, key):

        self.key = key
        self.thread_lock = threading.Lock()


    def start_stock_thread(self, symbol, refresh=5.0):

        t = threading.Thread(target=self.make_stock_requests, args=[symbol, refresh])
        t.daemon = True
        t.start()

    def get_graph_data(self, symbol, interval, days, time_format):

        while True:
            try: 
                response = requests.get(
                    url='http://www.alphavantage.co/query',
                    params={'function':'TIME_SERIES_INTRADAY',
                            'symbol': symbol,
                            'outputsize':'full',
                            'interval':interval,
                            'apikey': self.key}
                )
                interval_data = response.json()['Time Series (%s)' % interval]

            except:
                continue
            break

        time_fmt = '%Y-%m-%d %H:%M:%S'

        interval_data = sorted(
            interval_data.iteritems(), 
            key=lambda t: datetime.datetime.strptime(t[0], time_fmt)
        )


        min_day = datetime.datetime.strptime(interval_data[-1][0], time_fmt) - datetime.timedelta(days=days)
        print min_day
        interval_data = [ d for d in interval_data if datetime.datetime.strptime(d[0], time_fmt) > min_day ]

        avg = lambda d: round((float(d[1]['2. high']) + float(d[1]['3. low'])) / 2, 2)
        date = lambda d: datetime.datetime.strptime(d[0], time_fmt).strftime(time_format)

        interval_data = [ {'price': avg(d), 'date': date(d) } for d in interval_data ]

        return interval_data



    def make_stock_requests(self, symbol, refresh):

        while True:
            try: 
                response = requests.get(
                    url='http://www.alphavantage.co/query',
                    params={'symbol': symbol, 'function': 'GLOBAL_QUOTE', 'apikey': self.key}
                )
                current_data = response.json()['Realtime Global Securities Quote']
                print symbol, response.status_code
            except Exception as e:
                print e
                continue
            break

        val_fmt = '$%.2f'
        tid = threading.current_thread().name

        ui_queue.put((tid, StockMonitorUI.create_row,
            { 'symbol': current_data['01. Symbol'], 
              'price': val_fmt % float(current_data['03. Latest Price']),
              'change': val_fmt % float(current_data['08. Price Change']),
              'percent_change': current_data['09. Price Change Percentage']})
        )

        # month_data = self.get_graph_data(symbol, interval='60min', days=30)
        # ui_queue.put((tid, 'build_graph_month', {'prices_dates': month_data}))

        week_data = self.get_graph_data(symbol, interval='30min', days=7, time_format='%a')
        ui_queue.put((tid, StockWidgets.build_graph_week, {'prices_dates': week_data}))

        day_data = self.get_graph_data(symbol, interval='5min', days=1, time_format='%I')
        ui_queue.put((tid, StockWidgets.build_graph_day, 
                     {'prices_dates': day_data,
                      'growing_graph_size': 79}))
        print len(day_data)

        color = color_green if float(current_data['08. Price Change']) > 0 else color_green
        ui_queue.put((tid, StockWidgets.set_color, {'color': color}))
        
        a = 1
        prev_time = datetime.datetime.today()

        while True:
            try:
                response = requests.get(
                    'http://www.alphavantage.co/query',
                    params={'symbol': symbol, 'function': 'GLOBAL_QUOTE', 'apikey': self.key}
                )
                data = response.json()['Realtime Global Securities Quote']

                price_change = float(data['08. Price Change'])

                if color == color_green and price_change < 0:
                    color = color_red
                    ui_queue.put((tid, StockWidgets.set_color, {'color': color}))
                elif color == color_red and price_change >= 0:
                    color = color_green
                    ui_queue.put((tid, StockWidgets.set_color, {'color': color}))

                a += 1
                ui_queue.put((tid, StockWidgets.update_values, 
                    { 'price': a,
                      'change': val_fmt % float(data['08. Price Change']),
                      'percent_change': data['09. Price Change Percentage']})
                )

                if datetime.datetime.today() > prev_time + datetime.timedelta(seconds=300):
                    prev_time = prev_time + datetime.timedelta(seconds=300)
                    day_data = self.get_graph_data(symbol, interval='5min', days=1, time_format='%I')
                    ui_queue.put((tid, StockWidgets.build_graph_day, 
                                 {'prices_dates': day_data,
                                  'growing_graph_size': 79}))
            except Exception as e:
                print e
                pass
            
            sleep(refresh)


class StockWidgets(object):

    def __init__(self, row, symbol, price, change, percent_change,
                 graph_day, graph_week, graph_month=None):
        
        self.row = row
        self.symbol = symbol
        self.price = price
        self.change = change
        self.percent_change = percent_change
        self.graph_day = graph_day
        self.graph_week = graph_week
        self.graph_month = graph_month

        self.graph_day.update()
        self.prev_width_day = self.graph_day.winfo_width()
        self.prev_width_week = self.graph_day.winfo_width()
        # self.prev_width_month = self.graph_day.winfo_width()

        self.graph_day.bind('<Configure>', self.scale_day)
        self.graph_week.bind('<Configure>', self.scale_week)
        # self.graph_month.bind('<Configure>', self.scale_month)

    def scale_day(self, event):
        self.prev_width_day = self._scale_graph(event, self.prev_width_day)

    def scale_week(self, event):
        self.prev_width_week = self._scale_graph(event, self.prev_width_week)
    
    def scale_month(self, event):
        self.prev_width_month = self._scale_graph(event, self.prev_width_month)

    def _scale_graph(self, event, prev_width):
        scale = event.width/float(prev_width)
        event.widget.scale('all', 0,0,scale,1)
        return event.width
    
    def update_values(self, symbol=None, price=None, change=None, percent_change=None, 
                      day_range=None, week_range=None):

        def change_notification(widget, pos):

            def reset_notification(widget, curr_bg, curr_fg):
                widget['bg'] = curr_bg
                widget['fg'] = curr_fg

            curr_bg = widget['bg']
            curr_fg = widget['fg']

            widget['bg'] = update_green if pos else update_red
            widget['fg'] = 'white'

            widget.after(80, reset_notification, widget, curr_bg, curr_fg)

        if symbol is not None:
            self.symbol['text'] = symbol
        if price is not None:
            pos = True if price > self.price['text'] else False
            self.price['text'] = price
            self.change['text'] = change
            self.percent_change['text'] = percent_change
            change_notification(self.price, pos)
            change_notification(self.change, pos)
            change_notification(self.percent_change, pos)

    def set_color(self, color):

        self.symbol['bg'] = color
        self.price['bg'] = color
        self.change['bg'] = color
        self.percent_change['bg'] = color
        self.graph_day['bg'] = color 
        self.graph_week['bg'] = color 
        self.symbol.update()

    def build_graph_month(self, prices_dates, growing_graph_size=None):

        self._build_graph(self.graph_day, prices_dates, growing_graph_size)

    def build_graph_week(self, prices_dates, growing_graph_size=None):

        self._build_graph(self.graph_week, prices_dates, growing_graph_size)

    def build_graph_day(self, prices_dates, growing_graph_size=None):

        self._build_graph(self.graph_day, prices_dates, growing_graph_size)

    def _build_graph(self, graph, prices_dates, growing_graph_size=None):
        
        graph.delete('all')
        graph.update()
        min_w = 10
        min_h = 5
        max_w = graph.winfo_width() - min_w
        max_h = graph.winfo_height() - 15
        line_width = 1

        low_line = graph.create_line(
            min_w, max_h, max_w, max_h, 
            fill=graph_colors, width=line_width, tags='high', dash=(2,5)
        )
        high_line = graph.create_line(
            min_w, min_h, max_w, min_h, 
            fill=graph_colors, width=line_width, tags='high', dash=(2,5)
        )

        prices = [ p['price'] for p in prices_dates ]

        high = max(prices)
        low = min(prices)

        percent_diff = (high - low) / high
        if percent_diff < 0.012:
            midpoint = ((high - low) / 2) + low
            high = round(midpoint + 0.006 * midpoint, 2)
            low = round(midpoint - 0.006 * midpoint, 2)

        low_text = graph.create_text(
            min_w, max_h+min_h-5, anchor=NW, text=str(low), fill=graph_colors
        )
        high_text = graph.create_text(
            min_w, min_h+1, anchor=NW, text=str(high), fill=graph_colors
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
        trend_coords = [(x, y)]
        for price in prices[1:]:

            x += width

            y = calc_y(price)
            
            if count in line_repeat:
                # print count
                vertical_line = graph.create_line(
                    x, graph.winfo_height(), x, 0, 
                    fill=time_line_color, width=1, tags='high'
                )

                line_time = graph.create_text(
                    x+2, max_h+2,
                    fill=graph_colors, anchor=NW, text=prices_dates[count]['date']
                )

            trend_coords += [(round(x), round(y))]

            count += 1


        # trend_coords += [x, max_h]
        p_x, p_y = trend_coords[0]
        for x, y in trend_coords[1:]:
            graph.create_line(p_x, p_y, x, y, fill=text_color)
            p_x = x
            p_y = y


class StockMonitorUI(object):

    def __init__(self, root):
        self.root = root
        self.row = 0

        for x in range(0,4):
            self.root.grid_columnconfigure(x, weight=1)

        self.root.grid()
        self.create_header()


    def create_header(self):

        pady = 5
        bg = header_grey

        self.root.symbol = Label(self.root, text='sym', pady=pady, bg=bg)
        self.root.symbol.grid(row=0, column=0, sticky=N+E+S+W)
        
        self.root.price = Label(self.root, text='price', pady=pady, bg=bg)
        self.root.price.grid(row=0, column=1, sticky=N+E+S+W)

        self.root.change = Label(self.root, text='day', pady=pady, bg=bg)
        self.root.change.grid(row=0, column=2, sticky=N+E+S+W)

        self.root.percent_change = Label(self.root, text='week', pady=pady, bg=bg)
        self.root.percent_change.grid(row=0, column=3, sticky=N+E+S+W)

    def create_row(self, symbol, price, change, percent_change):

        self.row += 1
        
        graph_height = 100
        self.root.symbol = Label(self.root, text=symbol, fg=text_color)
        self.root.symbol.grid(row=self.row, column=0, rowspan=3, sticky=N+E+S+W)
        self.root.grid_columnconfigure(0, weight=0)

        self.root.price = Label(self.root, text=price, fg=text_color)
        self.root.price.grid(row=self.row, column=1, sticky=N+E+S+W)
        self.root.grid_columnconfigure(1, weight=0)

        self.root.change = Label(self.root, text=change, fg=text_color)
        self.root.change.grid(row=self.row+1, column=1, sticky=N+E+S+W)

        self.root.percent_change = Label(self.root, text=percent_change, fg=text_color)
        self.root.percent_change.grid(row=self.row+2, column=1, sticky=N+E+S+W)

        # self.root.day_range = Label(self.root, text=day_range)
        # self.root.day_range.grid(row=self.row, column=4, sticky=N+E+S+W)

        # self.root.week_range = Label(self.root, text=week_range)
        # self.root.week_range.grid(row=self.row, column=5, sticky=N+E+S+W)

        self.root.graph_day = Canvas(height=graph_height, highlightthickness=0)
        self.root.graph_day.grid(row=self.row, column=2, rowspan=3, sticky=N+E+S+W)

        self.root.graph_week = Canvas(height=graph_height, highlightthickness=0)
        self.root.graph_week.grid(row=self.row, column=3, rowspan=3, sticky=N+E+S+W)

        # self.root.graph_month = Canvas(height=graph_height)
        # self.root.graph_month.grid(columnspan=2, row=self.row+1, column=4, sticky=N+E+S+W)

        sw = StockWidgets(self.row, self.root.symbol, self.root.price, self.root.change, 
                          self.root.percent_change, self.root.graph_day, self.root.graph_week)

        self.row += 3
        
        return sw

ui_queue = Queue.Queue()
stock_widgets = {}

def thread_controller(ui):
    try:
        tid, func, kwargs = ui_queue.get_nowait()

        if func.__name__ == 'create_row':
            stock_row = func(ui, **kwargs)
            stock_widgets[tid] = stock_row
        else:
            func(stock_widgets[tid], **kwargs)
    except Queue.Empty:
        pass

    root.after(50, thread_controller, ui)


if __name__ == '__main__':
    root = Tk()
    ui = StockMonitorUI(root)
    a = root.after(50, thread_controller, ui)

    smr = StockMonitorRequests(ui, key)
    smr.start_stock_thread('MSFT')
    smr.start_stock_thread('ATVI')
    smr.start_stock_thread('NTDOY')
    smr.start_stock_thread('SNE')

    root.mainloop()