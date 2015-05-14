from abc import ABCMeta, abstractmethod
import re
import csv
from pykml.factory import KML_ElementMaker as KML
from pykml.factory import GX_ElementMaker as GX
import lxml
import os
import logging
import copy
import datetime

# Don't move the position of fieldMap, the line numbers are used to index fields
fieldMap = {
    "id": "id_str",
    "created_at": "created_at",
    "lang": "lang",
    "place": "place.full_name",
    "country": "place.country",
    "platform": "source",
    "geo_lon": "coordinates.coordinates[0]",
    "geo_lat": "coordinates.coordinates[1]",
    "tweet_in_reply_to_id": "in_reply_to_user_id",
    "user_id": "user.id_str",
    "user_screen_name": "user.screen_name",
    "user_name": "user.name",
    "user_location": "user.location",
    "user_geoenabled": "user.geo_enabled",
    "user_profile_img": "user.profile_img_url",
    "user_followers_count": "user.followers_count",
    "user_friends_count": "user.friends_count",
    "user_favourites": "user.favourites_counts",
    "retweet_count": "retweet_count",
    "favourite_count": "favorite_count",
    "text": "text"
}


def pathGet(d, path):
    index = re.match(r'^(\w+)\[(\d+)]', path)
    if index:
        if d:
            return d[index.group(1)][int(index.group(2))]
        else:
            return d

    k, _, rem = path.partition(".")
    if rem:
        return pathGet(d[k], rem)
    if d:
        return d[k]
    else:
        return d


class TweetWriter(object):
    __metaclass__ = ABCMeta

    def __init__(self, opts, fields):
        self.fields = fields
        self.opts = opts
        self.fieldsWritten = False

    def write(self, tweet):
        if not self.fieldsWritten:
            self._writerow(self.fields)
            self.fieldsWritten = True
        row = []
        for field in self.fields:
            # Skip special fields
            if field.startswith('_'):
                if field == '_keywords':
                    res = ','.join(self.opts.keywords)
                else:
                    continue
            else:
                res = pathGet(tweet, fieldMap[field])
            row.append(res)
        self._writerow(row)

    @abstractmethod
    def _writerow(self, row):
        pass

    @abstractmethod
    def flush(self):
        pass

    @abstractmethod
    def finish(self):
        pass

    def _tweet_to_fields(self, tweet):
        return tuple(pathGet(tweet, field) for field in self.fields)


class TweetCSVWriter(TweetWriter):
    def __init__(self, opts, fields):
        super(TweetCSVWriter, self).__init__(opts, fields)

        ##My update
        if (opts.recent > 1):
            self.csvfile = open(opts.csv, "a", newline='', encoding='utf-8')
        else:
            self.csvfile = open(opts.csv, "w", newline='', encoding='utf-8')
        ## End Update
            
        #self.csvfile = open(opts.csv, "a", newline='', encoding='utf-8')
        self.writer = csv.writer(self.csvfile)

    def _writerow(self, row):
        self.writer.writerow(row)

    def flush(self):
        self.csvfile.flush()

    def finish(self):
        self.csvfile.close()


class TweetStdoutWriter(TweetWriter):
    def __init__(self, opts, fields):
        super(TweetStdoutWriter, self).__init__(opts, fields)

    def _writerow(self, row):
        print(row)

    def flush(self):
        pass

    def finish(self):
        pass

class TweetKMLWriter(TweetWriter):
    def __init__(self, opts, fields):
        super(TweetKMLWriter, self).__init__(opts, fields)
        self.placemarks = []
        self.fieldsWritten = True

    def _writerow(self, row):
        desc = map(lambda r: u': '.join(r) + u"<br>", zip(self.opts.fields, row))
        self.placemarks.append(KML.Placemark(
            KML.name(row[13]),
            KML.Point(
                KML.extrude(1),
                KML.altitudeMode("relativeToGround"),
                KML.coordinates(u"{lon},{lat},{alt}".format(lon=row[5],lat=row[4],alt=0)),
                ),
            KML.description(
                    desc
                ),
            id=row[0],
            ))

    def flush(self):
        pass

    def finish(self):
        with open(self.opts.kml, 'wb') as kml:
            kml_tree = KML.kml(
                KML.Document(
                    KML.Folder(
                        KML.name('Tweets'),
                        id='tweets'
                        )
                    )
                )
            for pm in self.placemarks:
                kml_tree.Document.Folder.append(pm)
            content = lxml.etree.tostring(kml_tree)
            kml.write(bytes(content))

class RollingWriter(object):
    def __init__(self, res_dir, opts, fields, writer_classes, date_iter):
        self.writer_classes = writer_classes
        self.date_iter = date_iter
        self.opts = copy.copy(opts)
        self.fields = fields

        # Make the result directory.
        
        date_str = datetime.date.today().strftime("%Y-%m-%d")
        keywords = ' '.join(opts.keywords)        
        dir_name = "%s %.20s" % (date_str, keywords)
        logging.debug("Result dir name: '%s'" % dir_name)
        self.result_dir = res_dir
        if not os.path.exists(self.result_dir):
            os.makedirs(self.result_dir)

        self.roll()

    def roll(self): 
        # Create the subdirectory
        next_date = next(self.date_iter)
        if not next_date:
            return
##        Original Code
##        sub_date_str = next_date.strftime("%Y-%m-%d")
##        self.cur_res_dir = os.path.join(self.result_dir,sub_date_str)
##        Original Code End

##        Modified Code
        self.cur_res_dir = os.path.join(self.result_dir)
##        Modified Code End
        if not os.path.exists(self.cur_res_dir):
            os.makedirs(self.cur_res_dir)
        # Prepare writers
        if self.opts.csv:
            self.opts.csv = os.path.join(self.cur_res_dir, os.path.basename(self.opts.csv))
        if self.opts.kml:
            self.opts.kml = os.path.join(self.cur_res_dir, os.path.basename(self.opts.kml))

        self.writers = [wclass(self.opts, self.fields) for wclass in self.writer_classes]

    def write(self, row):
        [writer.write(row) for writer in self.writers]

    def flush(self):
        [writer.flush() for writer in self.writers]

    def finish(self):
        [writer.finish() for writer in self.writers]
        self.writers = []
        self.roll()
