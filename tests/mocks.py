import os, re

FIXTURES_DIR =  os.path.join(os.path.abspath(os.path.dirname(__file__)), 'fixtures')

def pal_mock_query(q, interval=None):
    try:
        agent_id = re.search(r'agent_id = "(.+?)"', q).group(1)
        data = open(os.path.join(FIXTURES_DIR, 'plyql', 'result_{0}.json'.format(agent_id))).read()
        return data
    except (AttributeError, IOError):
        return '[]'