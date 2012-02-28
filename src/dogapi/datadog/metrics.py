__all__ = [
    'HttpMetricApi',
    'StatsdMetricApi',
]

import time
from dogapi.common import *

class MetricApi(object):
    default_metric_type = MetricType.Gauge

    def metric(self, name, points, host=None, device=None, metric_type=None):
        """
        Submit a series of data points to the metric API.

        :param name: name of the metric (e.g. ``"system.load.1"``)
        :type name: string

        :param values: data series. list of (POSIX timestamp, intever value) tuples. (e.g. ``[(1317652676, 15), (1317652706, 18), ...]``)
        :type values: list

        :param host: optional host to scope the metric (e.g.
        ``"hostA.example.com"``). defaults to local hostname. to submit without
        a host, explicitly set host=None.
        :type host: string

        :param device: optional device to scope the metric (e.g. ``"eth0"``)
        :type device: string

        :raises: Exception on failure
        """
        if host is None:
            host = self._default_host
        
        now = time.time()
        if isinstance(points, (float, int)):
            points = [(now, points)]
        elif isinstance(points, tuple):
            points = [points]
        
        return self.metrics([{
            'metric':   name,
            'points':   [[ts, val] for ts, val in points],
            'type':     metric_type,
            'host':     host,
            'device':   device,
        }])


    def metrics(self, metrics):
        """
        Submit a series of metrics with 1 or more data points to the metric API

        :param values A dictionary of names to a list values, in the form of {name: [(POSIX timestamp, integer value), ...], name2: [(POSIX timestamp, integer value), ...]}
        :type values: dict

        :param host: optional host to scope the metric (e.g.
        ``"hostA.example.com"``). to submit without a host, explicitly set
        host=None.
        :type host: string

        :param device: optional device to scope the metric (e.g. ``"eth0"``)
        :type device: string

        :raises: Exception on failure
        """
        return self._metrics(metrics)

    def _metrics(self, metrics):
        raise NotImplementedError()


class HttpMetricApi(MetricApi):
    def _metrics(self, metrics):
        request = { "series": metrics }
        self.http_request('POST', '/series', request)
        if self.json_responses:
            return {}
        else:
            return None

class StatsdMetricApi(MetricApi):
    def _metrics(self, metrics):    
        requests = []
        for metric_series in metrics:
            metric_name = metric_series.get('metric', None)
            metric_points = metric_series.get('points', [])
            metric_type = metric_series.get('type', self.default_metric_type)

            # Don't send incomplete requests
            if not (metric_name or metric_points):
                continue

            if metric_type == MetricType.Gauge:
                # Note: not all StatsD implementations support gauges
                statsd_type_abbrev = "g"

            elif metric_type == MetricType.Counter:
                sampling_rate = metric_series.get('sampling_rate', None)
                try:
                    sampling_rate = float(sampling_rate)
                except:
                    sampling_rate = None

                if sampling_rate:
                    statsd_type_abbrev = "c|@{0}".format(sampling_rate)
                else:                            
                    statsd_type_abbrev = "c"

            elif metric_type == MetricType.Timer:
                statsd_type_abbrev = metric_series.get('unit', 'ms')

            else:
                log.warn("Stats doesn't support the {0} metric type".format(metric_type))
                continue

            for _ts, value in metric_points:
                requests.append("{0}:{1}|{2}".format(metric_name, value, statsd_type_abbrev))

        self.statsd_request(requests)
        if self.json_responses:
            return {}
        else:
            return None




