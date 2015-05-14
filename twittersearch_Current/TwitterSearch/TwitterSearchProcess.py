import multiprocessing as mp
from argparse import Namespace
from TwitterSearch import TwitterSearch, TwitterSearchOrder, TweetCSVWriter, TweetKMLWriter, TweetStdoutWriter, RollingWriter
from TwitterSearchException import TwitterSearchException
import logging
import datetime
import time

class date_iter(object):
    def __init__(self, i):
        self.i = i
        self.c = 0
        self.today = datetime.date.today()
    def __next__(self):
        if self.c >= self.i:
            return None
        td = datetime.timedelta(days=self.c+1)
        self.c += 1
        return self.today - td


class TwitterSearchProcess(mp.Process):
    def __init__(self, status_queue, res_dir, *args, **kwargs):
        super().__init__()
        self.api_limit_window_time = kwargs.get('window_limit', 15 * 60) # Default Twitter window time is 15 minutes
        self.opts = kwargs.get('options')
        if self.opts is None or type(self.opts) != Namespace:
            raise TypeError("options keyword argument is of a invalid type: %s" % type(self.opts))
        self.tapi = kwargs.get('tapi')
        if self.tapi is None or type(self.tapi) != TwitterSearch:
            raise TypeError("tapi keyword argument is of a invalid type: %s" % type(self.tapi))
        self.tsearch = kwargs.get('tsearch')
        if self.tsearch is None or type(self.tsearch) != TwitterSearchOrder:
            raise TypeError("options argument is of a invalid type: %s" % type(self.cli_opts))
        self.status_queue = status_queue

        self.res_dir = res_dir

    def init_objs(self):
        # Default search type is mixed
        self.tsearch.setResultType('mixed')
        if self.opts.recent:
            self.tsearch.setResultType('recent')
            self.search_iterator = 0
            self.search_order_queue = []

        writer_classes = []
        if self.opts.csv:
            writer_classes.append(TweetCSVWriter)

        if self.opts.kml:
            writer_classes.append(TweetKMLWriter)

        if not self.opts.csv or not self.opts.kml:
            writer_classes.append(TweetStdoutWriter)

        self.writer = RollingWriter(self.res_dir, self.opts, self.opts.fields, writer_classes, date_iter(self.opts.recent))

        # Set limites
        self.limit_reset_datetime = datetime.datetime.utcnow()
        self.limit_remaining = 180 # Default number of requests allowed in a window
        self.limit_limit = 180

        # Set statistics
        self.count_queries = 0
        self.count_tweet_received = 0
        self.count_tweet_saved = 0

    def update_limits(self):
        self.limit_reset_datetime = datetime.datetime.fromtimestamp(int(self.metadata['x-rate-limit-reset']))
        self.limit_remaining = int(self.metadata['x-rate-limit-remaining'])
        self.limit_limit = int(self.metadata['x-rate-limit-limit'])
        #print(self.limit_reset_datetime, self.limit_remaining, self.limit_limit)

    def update_status(self):
        self.count_queries = self.tapi.getStatistics()['tweets']
        self.count_tweet_received = self.tapi.getStatistics()['queries']
        status_str = "Queries done: {0:d} Tweets received: {1} Tweets saved: {2}".format(
            int(self.count_queries/100),
            self.count_tweet_received,
            self.count_tweet_saved)
        print(str(status_str))
        self.send_status(status_str)

    def next_twitter_search(self):
        if not self.opts.recent:
            t = self.tsearch
            self.tsearch = None
            return t
        # Build n search orders
        if self.search_iterator >= self.opts.recent:
            return None
        if self.search_order_queue:
            i = self.search_iterator
            self.search_iterator += 1
            (date_start, date_end) =  self.search_order_queue[i]
            self.tsearch.setSince(date_start)
            self.tsearch.setUntil(date_end)
            return self.tsearch
        else:
            today_date = datetime.date.today()
            for i in range(self.opts.recent):
                td_start = datetime.timedelta(days=i+1)
                td_end = datetime.timedelta(days=i)
                self.search_order_queue.append((today_date-td_start, today_date-td_end))
            logging.debug("Task queue: %s" % str(self.search_order_queue))
            return self.next_twitter_search()

    def send_status(self, status_str):
        try:
            self.status_queue.put_nowait(status_str)
        except Queue.Full:
            logging.warning("Queue is full, cannot put status string in it.")

    def limit_check_wait(self):
        if self.limit_remaining <= 0:
            if self.limit_reset_datetime < datetime.datetime.now():
                self.metadata = self.tapi.getMetadata()
                self.update_limits()
            sleep_secs = (self.limit_reset_datetime - datetime.datetime.now()).total_seconds()
            if sleep_secs <= 0:
                return
            self.send_status("Waiting for Twitter API limit to reset, will continue on " + self.limit_reset_datetime.strftime("%H:%M:%S"))
            ##
            status_str= "Waiting for Twitter API limit to reset, will continue on " + self.limit_reset_datetime.strftime("%H:%M:%S")
            print(str(status_str))
            ##
            logging.info("Sleep for %d seconds" % sleep_secs)
            time.sleep(sleep_secs+1)
            self.send_status("Continue search...")

    def run(self):
        # Should be only run in a separate process/thread
        self.init_objs()
        tsearch = self.next_twitter_search()
        while tsearch:
            count = 0
            try:
                for tweet in self.tapi.searchTweetsIterable(tsearch):
                    self.count_tweet_received += 1
                    # Set limits
                    self.metadata = self.tapi.getMetadata()
                    self.update_limits()
                    self.update_status()
                    # Check if we are going to reach the limit, block the process to wait for the limit to reset
                    self.limit_check_wait()
                    if self.opts.count > 0 and count >= self.opts.count:
                        break

                    if self.opts.geo_only:
                        # Filter out tweets that don't have coordinates
                        if not tweet.get('coordinates'):
                            continue
                        coords =  tweet["coordinates"]["coordinates"]
                        try:
                            if coords[0] == 0.0 and coords[1] == 0.0:
                                continue
                        except:
                            continue
                    self.writer.write(tweet)
                    self.count_tweet_saved += 1
                    count += 1
                    if count % 1000:
                        self.writer.flush()
                    # Update status, and send it to the main process
                    self.update_status()
            except:
                self.metadata = self.tapi.getMetadata()
                self.update_limits()
                self.limit_check_wait()
                continue
            # Finish writing
            self.writer.finish()
            # Get next search job
            tsearch = self.next_twitter_search()
##        PROCNAME = "chrome.exe"
##        count = 0
##        for proc in psutil.process_iter():
##            if proc.name() == PROCNAME:
##                print (proc.name())
##                count +=1
##                proc.terminate()
##        print(count)
        print("Task Completed")
        self.send_status("Task complete")
