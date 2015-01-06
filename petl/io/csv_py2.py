from __future__ import absolute_import, print_function, division, \
    unicode_literals


# standard library dependencies
import csv
import codecs
import cStringIO


# internal dependencies
from petl.util.base import RowContainer, data


def fromcsv_impl(source, **csvargs):
    return CSVView(source, **csvargs)


class CSVView(RowContainer):

    def __init__(self, source=None, **csvargs):
            self.source = source
            self.csvargs = csvargs

    def __iter__(self):
        with self.source.open_('rU') as csvfile:
            reader = csv.reader(csvfile, **self.csvargs)
            for row in reader:
                yield tuple(row)


def tocsv_impl(table, source, write_header=True, **csvargs):
    _writecsv(table, source=source, mode='wb', write_header=write_header,
              **csvargs)


def appendcsv_impl(table, source, write_header=False, **csvargs):
    _writecsv(table, source=source, mode='ab', write_header=write_header,
              **csvargs)


def _writecsv(table, source, mode, write_header, **csvargs):
    rows = table if write_header else data(table)
    with source.open_(mode) as csvfile:
        writer = csv.writer(csvfile, **csvargs)
        for row in rows:
            writer.writerow(row)


# Additional classes for Unicode CSV support in PY2
# taken from the original csv module docs
# http://docs.python.org/2/library/csv.html#examples


class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")


class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self


class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([unicode(s).encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


def fromucsv_impl(source, encoding='utf-8', **csvargs):
    return UnicodeCSVView(source, encoding=encoding, **csvargs)


class UnicodeCSVView(RowContainer):
    def __init__(self, source, encoding, **csvargs):
        self.source = source
        self.encoding = encoding
        self.csvargs = csvargs

    def __iter__(self):
        with self.source.open_('rb') as f:
            reader = UnicodeReader(f, encoding=self.encoding, **self.csvargs)
            for row in reader:
                yield tuple(row)


def toucsv_impl(table, source, encoding='utf-8', write_header=True,
                **csvargs):
    _writeucsv(table, source=source, mode='wb', encoding=encoding,
               write_header=write_header, **csvargs)


def appenducsv_impl(table, source, encoding='utf-8', write_header=False,
                    **csvargs):
    _writeucsv(table, source=source, mode='ab', encoding=encoding,
               write_header=write_header, **csvargs)


def _writeucsv(table, source, mode, write_header, encoding, **csvargs):
    rows = table if write_header else data(table)
    with source.open_(mode) as f:
        writer = UnicodeWriter(f, encoding=encoding, **csvargs)
        for row in rows:
            writer.writerow(row)


def teecsv_impl(table, source, write_header, **csvargs):
    return TeeCSVContainer(table, source=source, write_header=write_header,
                           **csvargs)


class TeeCSVContainer(RowContainer):
    def __init__(self, table, source=None, write_header=True, **csvargs):
        self.table = table
        self.source = source
        self.write_header = write_header
        self.csvargs = csvargs

    def __iter__(self):
        with self.source.open_('wb') as f:
            writer = csv.writer(f, **self.csvargs)
            it = iter(self.table)
            hdr = next(it)
            if self.write_header:
                writer.writerow(hdr)
            yield hdr
            for row in it:
                writer.writerow(row)
                yield row


def teeucsv_impl(table, source, write_header, encoding='utf-8', **csvargs):
    return TeeUCSVContainer(table, source=source, write_header=write_header,
                            encoding=encoding, **csvargs)


class TeeUCSVContainer(RowContainer):
    def __init__(self, table, source=None, write_header=True, encoding='utf-8',
                 **csvargs):
        self.table = table
        self.source = source
        self.write_header = write_header
        self.encoding = encoding
        self.csvargs = csvargs

    def __iter__(self):
        with self.source.open_('wb') as f:
            writer = UnicodeWriter(f, encoding=self.encoding, **self.csvargs)
            it = iter(self.table)
            hdr = next(it)
            if self.write_header:
                writer.writerow(hdr)
            yield hdr
            for row in it:
                writer.writerow(row)
                yield row