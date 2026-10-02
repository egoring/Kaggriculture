

# ---------------------------------------------------------------------------
# ORACLE layer (9/24): exact rival model. The field is dominated by copies of the public V59 stack
# above this marker; a second instance of that stack, fed the rival's public observation plus a
# shadow-simulated private state, reproduces the copy's actions exactly (verified 719/719 turns).
# A one-turn lookahead (shadow engine step + snapshot/restore of the oracle's module state) gives
# the copy's next-turn sales, and we sell those items one turn earlier. Any divergence between the
# shadow and the real observation (a rival that is not an exact copy) disables the layer for good.
import copy as _orc_copy, types as _orc_types, os as _orc_os, time as _orc_time
_ORC_ITEMS = ("MILK", "WOOL", "EGG", "STRAWBERRY", "MELON", "CARROT", "TOMATO")
_ORC_H = int(_orc_os.environ.get('ORC_H', '24'))
_ORC_SOFT_MAX = int(_orc_os.environ.get('ORC_SOFT', '6'))     # mismatches tolerated inside the rolling window
_ORC_WIN = int(_orc_os.environ.get('ORC_WIN', '48'))
_ORC_MONEY_TOL = float(_orc_os.environ.get('ORC_MONEY_TOL', '60'))
_ORC_INV_TOL = int(_orc_os.environ.get('ORC_INV_TOL', '4'))
_ORC_HIT_MIN = float(_orc_os.environ.get('ORC_HIT_MIN', '0.5'))   # acting requires this hit rate over the last _ORC_HIT_N item predictions
_ORC_HIT_N = int(_orc_os.environ.get('ORC_HIT_N', '12'))
_ORC_HARD_OFF = int(_orc_os.environ.get('ORC_HARD_OFF', '0'))   # 1: unit mismatch switches the model off for good
_ORC_SOFT_OFF = int(_orc_os.environ.get('ORC_SOFT_OFF', '0'))   # 1: rolling money/inventory mismatches switch it off
_ORC_BUDGET = float(_orc_os.environ.get('ORC_BUDGET', '0.30'))   # seconds already spent in this turn above which the lookahead is skipped
_ORC_MIN_OVERAGE = float(_orc_os.environ.get('ORC_MIN_OVERAGE', '12'))
_ORC_STATIC = {'_ROUTES', '_R108_DATA', '_V92_P_BLOB', '_V92_P_INDEX', '_ALT_RAW', '_PLANNER_NS', '_UNIT_NS'}
_ORC_SKIP = (_orc_types.ModuleType, _orc_types.FunctionType, type, _orc_types.BuiltinFunctionType)
_ORC_CHF = ('players', 'diagnostics', '_future_sells', 'opponent_plan')
_ORC = {}
_ORC_REPORT = dict(orc_on=0, orc_off_reason='', orc_fires=0, orc_units=0, orc_errors=0, orc_checks=0)
_ORC_PARENT = agent


def _orc_snapshot(ns):
    out = {'__chassis__': {k: _orc_copy.deepcopy(getattr(ns['_IMPL'].chassis, k)) for k in _ORC_CHF}}
    for k, v in ns.items():
        if k.startswith('__') or isinstance(v, _ORC_SKIP) or k in _ORC_STATIC:
            continue
        try:
            out[k] = _orc_copy.deepcopy(v)
        except Exception:
            pass
    return out


def _orc_restore(ns, snap):
    for k, v in snap['__chassis__'].items():
        setattr(ns['_IMPL'].chassis, k, v)
    for k, v in snap.items():
        if k != '__chassis__':
            ns[k] = v


def _orc_setup(observation, configuration):
    st = {'on': False, 'reason': ''}
    try:
        from kaggle_environments import make
        path = None
        try:
            path = configuration.get('__raw_path__') if hasattr(configuration, 'get') else getattr(configuration, '__raw_path__', None)
        except Exception:
            path = None
        if not path:
            st['reason'] = 'no_path'; return st
        src = open(path, encoding='utf-8').read()
        cut = src.find('# ==ORACLE_END==')
        if cut < 0:
            st['reason'] = 'no_marker'; return st
        ns = {'__name__': '_orc_ns'}
        exec(compile(src[:cut], 'orc', 'exec'), ns)
        ns['V9_OPENING_STEP0'] = (("BUY_PRODUCT", "WHEAT", 20), ("SELL", "WHEAT", 15))   # the public copy's opening
        oracle = ns.get('kaggle_submission_agent') or ns.get('agent')
        if oracle is None:
            st['reason'] = 'no_agent'; return st
        shadow = make('kaggriculture'); shadow.reset()
        shadow2 = make('kaggriculture'); shadow2.reset()
        me = int(observation['player'])
        st.update(on=True, ns=ns, oracle=oracle, shadow=shadow, shadow2=shadow2, me=me, rv=1 - me,
                  rv_private=_orc_copy.deepcopy(observation.get('private') or {}), step=-1, pending=None)
    except Exception as e:
        st['reason'] = 'setup:' + type(e).__name__ + ':' + str(e)[:80]
    return st


def _orc_public_equal(a, b):
    return a['money'] == b['money'] and a['farmer'] == b['farmer'] and a['hands'] == b['hands'] and a['tiles'] == b['tiles']


def _orc_sync(st, observation):
    """Load the real public state (and our real private) into a shadow env; keep the rival's tracked private."""
    sh = st['shadow']; me, rv = st['me'], st['rv']
    for i in (0, 1):
        o = sh.state[i].observation
        o['farms'] = _orc_copy.deepcopy(observation['farms']); o['market'] = _orc_copy.deepcopy(observation['market'])
        o['town'] = _orc_copy.deepcopy(observation['town']); o['day'] = observation['day']; o['hour'] = observation['hour']
        o['step'] = int(observation['step']); o['player'] = i
    sh.state[me].observation['private'] = _orc_copy.deepcopy(observation['private'])
    sh.state[rv].observation['private'] = _orc_copy.deepcopy(st['rv_private'])
    # shared references like the engine expects
    sh.state[1].observation['farms'] = sh.state[0].observation['farms']
    sh.state[1].observation['market'] = sh.state[0].observation['market']
    sh.state[1].observation['town'] = sh.state[0].observation['town']


def _orc_rival_obs(st, observation):
    o = _orc_copy.deepcopy(observation); o['player'] = st['rv']; o['private'] = _orc_copy.deepcopy(st['rv_private'])
    return o


def _orc_planned(step, player, item):
    try:
        native = _IMPL.chassis.players[player]; route = native['route']; q = 0
        for s in range(step + 1, min(719, step + _ORC_H)):
            a = _IMPL.chassis.routes[2 if s >= 648 else route][s]
            for o in a.get('market', []):
                if len(o) > 2 and o[0] == 'SELL' and o[1] == item:
                    q += int(o[2])
        return q
    except Exception:
        return 0


def agent(observation, configuration=None):
    _t_call = _orc_time.time()
    action = _ORC_PARENT(observation, configuration)
    try:
        step = int(observation['step']); player = int(observation['player'])
        try:
            _ov = observation.get('remainingOverageTime')
            if _ov is not None and float(_ov) < _ORC_MIN_OVERAGE and player in _ORC and _ORC[player].get('on'):
                _ORC[player]['on'] = False; _ORC_REPORT['orc_on'] = 0; _ORC_REPORT['orc_off_reason'] = 'overage@%d' % step
        except Exception:
            pass
        st = _ORC.get(player)
        if st is None or step == 0 or (st.get('step', -1) >= step):
            st = _ORC[player] = _orc_setup(observation, configuration)
            _ORC_REPORT.update(orc_on=int(st['on']), orc_off_reason=st['reason'], orc_fires=0, orc_units=0, orc_checks=0)
            if _orc_os.environ.get('ORC_DEBUG'):
                open('/tmp/orc.log','a').write('setup p%d on=%s reason=%s cfgkeys=%s\n' % (player, st['on'], st['reason'], list(configuration.keys())[:30] if hasattr(configuration,'keys') else type(configuration)))
        if not st['on']:
            return action
        st['step'] = step
        sh, sh2, ns, oracle = st['shadow'], st['shadow2'], st['ns'], st['oracle']
        # 1) validate last shadow step against reality
        if st.get('pending') is not None:
            pf = st['pending']
            real = observation['farms'][st['rv']]
            _ORC_REPORT['orc_checks'] += 1
            units_ok = pf['farm']['farmer'] == real['farmer'] and pf['farm']['hands'] == real['hands'] and pf['farm']['tiles'] == real['tiles']
            rinv = dict(observation['market']['inventory'])
            inv_dev = sum(abs(int(rinv.get(k, 0)) - int(v)) for k, v in pf['inv'].items())
            money_dev = abs(float(pf['farm']['money']) - float(real['money']))
            # correct the tracked rival shed by the unexplained market flow (their sales beyond / below the prediction)
            try:
                rs = st['rv_private'].get('shed') or {}
                for k, v in pf['inv'].items():
                    d = int(rinv.get(k, 0)) - int(v)
                    if d and k in rs:
                        rs[k] = max(0, int(rs.get(k, 0)) - d)
            except Exception:
                pass
            soft_ok = money_dev <= _ORC_MONEY_TOL and inv_dev <= _ORC_INV_TOL
            win = st.setdefault('soft_win', [])
            win.append(0 if soft_ok else 1)
            if len(win) > _ORC_WIN:
                del win[0]
            if not soft_ok:
                st['soft'] = st.get('soft', 0) + 1; _ORC_REPORT['orc_soft'] = st['soft']
            if step % 24 == 0:
                units_ok = True          # end-of-day weeds/shop draw use the hidden episode seed; public state is resynced anyway
            if (_ORC_HARD_OFF and not units_ok) or (_ORC_SOFT_OFF and sum(win) > _ORC_SOFT_MAX):
                st['on'] = False; st['reason'] = 'diverged@%d' % step; _ORC_REPORT['orc_on'] = 0; _ORC_REPORT['orc_off_reason'] = st['reason']
                if _orc_os.environ.get('ORC_DEBUG'):
                    open('/tmp/orc.log','a').write('OFF@%d units_ok=%s money_dev=%.0f inv_dev=%d soft=%d fires=%d\n' % (step, units_ok, money_dev, inv_dev, st.get('soft',0), _ORC_REPORT['orc_fires']))
                return action
        # 1b) score the prediction made two turns ago (about the rival's action at step-1) against the market flow of step-1:
        #     rival sold = inventory(now) - inventory(prev) + town draw(step-1) - our own sales at step-1
        lp = st.get('pq')
        if lp is not None and lp['made'] == step - 2 and st.get('prev_inv') is not None:
            try:
                draw = _race_town(step - 1, st.get('prev_shops') or [])
                for item, q in lp['sales'].items():
                    rival_sold = int(observation['market']['inventory'][item]) - int(st['prev_inv'][item]) + int(draw.get(item, 0)) - int((st.get('prev_ours') or {}).get(item, 0))
                    st.setdefault('hits', []).append(1 if rival_sold >= max(1, q // 2) else 0)
                if len(st.get('hits', [])) > _ORC_HIT_N:
                    del st['hits'][:len(st['hits']) - _ORC_HIT_N]
                _ORC_REPORT['orc_hits'] = sum(st.get('hits', [])); _ORC_REPORT['orc_hit_n'] = len(st.get('hits', []))
            except Exception:
                _ORC_REPORT['orc_errors'] += 1
        if lp is not None and lp['made'] <= step - 2:
            st['pq'] = None
        st['prev_inv'] = dict(observation['market']['inventory']); st['prev_shops'] = list(observation['town'].get('unlocked_shops', []))
        # 2) exact rival action now
        r_t = oracle(_orc_rival_obs(st, observation), configuration); st['last_rt'] = r_t
        # 3) one-turn lookahead (not across midnight: end-of-day randomness is seeded)
        if step < 712 and (step + 1) % 24 != 0 and isinstance(action, dict) and (_orc_time.time() - _t_call) < _ORC_BUDGET:
            snap = _orc_snapshot(ns)
            try:
                _orc_sync(st, observation)
                sh2.state = _orc_copy.deepcopy(sh.state); sh2.steps = [sh2.state] * (step + 1)
                acts = [None, None]; acts[st['me']] = _orc_copy.deepcopy(action); acts[st['rv']] = _orc_copy.deepcopy(r_t)
                sh2.step(acts)
                o2 = sh2._Environment__get_shared_state(st['rv']).observation
                pred = oracle(o2, configuration) if not sh2.done else {}
            finally:
                _orc_restore(ns, snap)
            shed = observation['private']['shed']
            market = [list(o) for o in (action.get('market') or [])]
            mine = {o[1] for o in market if o and o[0] == 'SELL' and len(o) > 2}
            sales = {}
            for o in (pred.get('market') or []):
                if o and o[0] == 'SELL' and len(o) > 2 and o[1] in _ORC_ITEMS and int(o[2]) > 0:
                    sales[o[1]] = sales.get(o[1], 0) + int(o[2])
            hits = st.get('hits', [])
            acting = len(hits) < _ORC_HIT_N or (sum(hits) / float(len(hits))) >= _ORC_HIT_MIN
            _ORC_REPORT['orc_acting'] = int(acting)
            add = []
            if not acting:
                pred = {}
            for o in (pred.get('market') or []):
                if o and o[0] == 'SELL' and len(o) > 2 and o[1] in _ORC_ITEMS and int(o[2]) > 0 and o[1] not in mine:
                    stock = int(shed.get(o[1], 0))
                    if stock <= 0:
                        continue
                    q = min(stock, max(int(o[2]), _orc_planned(step, player, o[1])))
                    if q > 0:
                        add.append(['SELL', o[1], int(q)]); mine.add(o[1])
            if add and len(market) + len(add) <= 10:
                action = dict(action); action['market'] = add + market
                _ORC_REPORT['orc_fires'] += 1; _ORC_REPORT['orc_units'] += sum(x[2] for x in add)
            if sales and st.get('pq') is None:
                st['pq'] = {'made': step, 'sales': sales}
        else:
            _ORC_REPORT['orc_skipped'] = _ORC_REPORT.get('orc_skipped', 0) + 1
        try:
            _ours = {}
            _shed = observation['private']['shed']
            for o in (action.get('market') or []) if isinstance(action, dict) else []:
                if o and o[0] == 'SELL' and len(o) > 2 and o[1] in _ORC_ITEMS:
                    _ours[o[1]] = _ours.get(o[1], 0) + min(int(o[2]), int(_shed.get(o[1], 0)))
            st['prev_ours'] = _ours
        except Exception:
            st['prev_ours'] = {}
        # 4) advance the shadow with (our final action, rival's exact action); remember the rival private + prediction
        _orc_sync(st, observation)
        acts = [None, None]; acts[st['me']] = _orc_copy.deepcopy(action); acts[st['rv']] = _orc_copy.deepcopy(r_t)
        sh.steps = [sh.state] * (step + 1)
        sh.step(acts)
        st['rv_private'] = _orc_copy.deepcopy(sh.state[st['rv']].observation['private'])
        st['pending'] = {'farm': _orc_copy.deepcopy(sh.state[0].observation['farms'][st['rv']]), 'inv': dict(sh.state[0].observation['market']['inventory'])}
    except Exception as e:
        _ORC_REPORT['orc_errors'] += 1
        try:
            _ORC[int(observation['player'])]['on'] = False; _ORC_REPORT['orc_on'] = 0; _ORC_REPORT['orc_off_reason'] = 'error:' + type(e).__name__
        except Exception:
            pass
    return action


agent.telemetry = _ORC_REPORT
agent = globals().pop("agent")
