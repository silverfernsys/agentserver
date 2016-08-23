import logging

def log_kafka(id, origin, name, stats, **kwargs):
    logging.getLogger(origin).debug('Flushed {0} stats for agent.id = {1}, process = {2} to Kafka.'
        .format(len(stats), id, name))