import pickle
from tapeagent import make_tape_agent
acts=pickle.load(open('/root/kg/rows_t13.pkl','rb'))['t13_raw']
agent=make_tape_agent(acts)
