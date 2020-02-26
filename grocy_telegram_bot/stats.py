from prometheus_client import Summary
from prometheus_client.metrics import MetricWrapperBase

START_TIME = Summary('start_processing_seconds', 'Time spent in the /start handler')


def get_metrics() -> []:
    entries = set()
    for name, obj in globals().items():
        if isinstance(obj, MetricWrapperBase):
            entries.add(obj)

    return list(entries)


def format_metrics() -> str:
    def format_sample(sample):
        result = "  "
        if len(sample[0]) > 0:
            result += str(sample[0])
        if len(sample[1]) > 0:
            result += str(sample[1])

        if len(result) > 0:
            result += " "
        result += str(sample[2])

        return result

    def format_samples(samples):
        return "\n".join(list(map(format_sample, samples)))

    def format_metric(metric):
        name = metric._name
        samples = list(metric._samples())
        samples_text = format_samples(samples)

        return "{}:\n{}".format(name, samples_text)

    return "\n\n".join(map(format_metric, get_metrics()))
