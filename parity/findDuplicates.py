#!/usr/bin/env python3
"""Find equal and isomorphic games, using only the Python standard library.

Reduction: follow Knor's default constructSymGame / SymGame::toExplicit, without
bisimulation (https://github.com/trolando/knor/tree/master/src). An HOA state is
an environment vertex (owner 1, priority 0). The environment assigns the
uncontrollable APs; the resulting function from controllable valuations to
(successor, colour) is a controller vertex (owner 0, priority 0). Equal residual
functions are shared, even across source states, as in Knor's symbolic export.
Different functions with the same range remain different vertices. Controller
edges lead to globally shared (successor, colour) outcome vertices, owned by 1,
with one edge to the successor state. State acceptance is moved to INCOMING
edges, as Knor does; transition acceptance stays on its transition. For max
acceptance, colour p becomes p+2-odd; for min acceptance it becomes
2*ceil(number_of_colours/2)-p+2-odd. Thus all games use max-even, the controller
is Even, and auxiliary priority 0 cannot affect the winner.

A reduced ordered decision diagram, ordered by uncontrollable then controllable
AP indices, avoids enumerating valuations. AP *names*, state names, and other
labels are discarded. Explicit Boolean labels (!, &, |, parentheses, t/f and
aliases) and exactly one acceptance colour per state or transition are
supported, with the canonical acceptance formula specified by acc-name.
Non-parity, nondeterministic, incomplete, uncoloured, implicit-label,
and malformed inputs are warned about and skipped, never guessed at.

Numbering: retain numeric HOA state IDs, swapping Start with 0 as Knor does;
allocate residual vertices on first encounter (file state order, low branch
before high), then outcome vertices in first-transition encounter order.
This deliberately replaces Sylvan's allocation-dependent BDD pointer ordering
with reproducible ordering. Edges are sets. Level 1 hashes this numbered graph;
level 2 uses directed WL refinement (up to eight rounds) as a filter, then an
exact, iterative, colour-constrained backtracking matcher. WL equality alone
never establishes a duplicate. Matching ignores a distinguished initial vertex,
like label-stripped PGSolver graph isomorphism; it does not assert rooted-game
or automaton-language equivalence. Unreachable states are retained.

CSV groups are disjoint confirmed equivalence classes: 'identical' if every
member has the same numbered graph, otherwise 'isomorphic'. Timeout pairs have
their own 'suspected' rows and are NOT merged or emitted as manifest exclusions.
Representatives minimise (length of relative path, relative path), independently
of process scheduling. Graphs use compact arrays and temporary on-disk storage;
only candidate graphs are loaded together. --max-size limits input bytes, not
the size of the expanded game. All diagnostics and statistics go to stderr.
"""

import argparse
from array import array
from collections import Counter, defaultdict
import csv
import hashlib
import heapq
import math
import multiprocessing
from pathlib import Path
import pickle
import re
import struct
import sys
import tempfile
import time


class InputError(ValueError):
    pass


class BDD:
    def __init__(self):
        self.nodes = [(math.inf, 0, 0), (math.inf, 1, 1)]
        self.unique = {}
        self.cache = {}
        self.alias_cache = {}

    def node(self, var, low, high):
        if low == high:
            return low
        key = (var, low, high)
        if key not in self.unique:
            self.unique[key] = len(self.nodes)
            self.nodes.append(key)
        return self.unique[key]

    def op(self, op, a, b):
        if a > b:
            a, b = b, a
        if op == '&':
            if a == 0 or a == b:
                return a
            if a == 1:
                return b
        else:
            if a == 0 or a == b:
                return b
            if a == 1:
                return 1
        key = (op, a, b)
        if key not in self.cache:
            va, la, ha = self.nodes[a]
            vb, lb, hb = self.nodes[b]
            v = min(va, vb)
            self.cache[key] = self.node(
                v, self.op(op, la if va == v else a, lb if vb == v else b),
                self.op(op, ha if va == v else a, hb if vb == v else b))
        return self.cache[key]

    def negate(self, a):
        if a < 2:
            return 1 - a
        key = ('!', a)
        if key not in self.cache:
            v, low, high = self.nodes[a]
            self.cache[key] = self.node(v, self.negate(low), self.negate(high))
        return self.cache[key]


TOKEN = re.compile(r'\s*(\d+|@[0-9A-Za-z_-]+|[tf!&|()])')


def label_bdd(text, bdd, variables, aliases, active=()):
    values, ops = [], []
    precedence = {'|': 1, '&': 2, '!': 3}

    def reduce_op():
        op = ops.pop()
        if op == '!':
            values.append(bdd.negate(values.pop()))
        else:
            right, left = values.pop(), values.pop()
            values.append(bdd.op(op, left, right))

    pos, want_value = 0, True
    while pos < len(text.rstrip()):
        match = TOKEN.match(text, pos)
        if not match:
            raise InputError('invalid Boolean label near ' + repr(text[pos:pos+30]))
        token, pos = match[1], match.end()
        if token == '(' and want_value:
            ops.append(token)
        elif token == '!' and want_value:
            ops.append(token)
        elif token == ')' and not want_value:
            while ops and ops[-1] != '(':
                reduce_op()
            if not ops:
                raise InputError('unbalanced Boolean label')
            ops.pop()
        elif token in ('&', '|') and not want_value:
            while ops and ops[-1] != '(' and precedence[ops[-1]] >= precedence[token]:
                reduce_op()
            ops.append(token)
            want_value = True
        elif want_value and token not in ('&', '|', ')'):
            if token in ('t', 'f'):
                value = int(token == 't')
            elif token.startswith('@'):
                if token not in aliases or token in active:
                    raise InputError('undefined or cyclic alias ' + token)
                if token not in bdd.alias_cache:
                    bdd.alias_cache[token] = label_bdd(aliases[token], bdd, variables, aliases, active+(token,))
                value = bdd.alias_cache[token]
            else:
                ap = int(token)
                if ap >= len(variables):
                    raise InputError('AP index out of range')
                value = bdd.node(variables[ap], 0, 1)
            values.append(value)
            want_value = False
        else:
            raise InputError('invalid Boolean expression')
    if want_value or '(' in ops:
        raise InputError('incomplete Boolean expression')
    while ops:
        reduce_op()
    if len(values) != 1:
        raise InputError('invalid Boolean expression')
    return values[0]


class TransitionBDD:
    def __init__(self, guards):
        self.guards = guards
        self.nodes = [(math.inf, 0, 0)]
        self.unique = {}
        self.cache = {}

    def node(self, var, low, high):
        if low == high:
            return low
        key = (var, low, high)
        if key not in self.unique:
            self.unique[key] = len(self.nodes)
            self.nodes.append(key)
        return self.unique[key]

    def ite(self, guard, outcome, otherwise):
        if guard == 0:
            return otherwise
        if guard == 1:
            return outcome
        key = (guard, outcome, otherwise)
        if key not in self.cache:
            vg, lg, hg = self.guards.nodes[guard]
            vt, lt, ht = self.nodes[otherwise] if otherwise > 0 else (math.inf, 0, 0)
            v = min(vg, vt)
            self.cache[key] = self.node(
                v, self.ite(lg if vg == v else guard, outcome, lt if vt == v else otherwise),
                self.ite(hg if vg == v else guard, outcome, ht if vt == v else otherwise))
        return self.cache[key]


STATE = re.compile(r'State:\s*(?:\[([^]]*)\]\s*)?(\d+)\s*'
                   r'(?:"(?:[^"\\]|\\.)*"\s*)?(?:\{([^}]*)\}\s*)?$')
TRANSITION = re.compile(r'(?:\[([^]]*)\]\s*)?(\d+)\s*(?:\{([^}]*)\}\s*)?$')


def colour(text, count):
    if text is None:
        return -1
    parts = text.split()
    if len(parts) != 1 or not parts[0].isdigit() or int(parts[0]) >= count:
        raise InputError('expected exactly one acceptance colour in range')
    return int(parts[0])


def check_acceptance(formula, acceptance):
    tokens = re.findall(r'(?:Fin|Inf)\s*\(\s*\d+\s*\)|[&|()]', formula)
    if ''.join(re.sub(r'\s+', '', t) for t in tokens) != re.sub(r'\s+', '', formula):
        raise InputError('unsupported parity acceptance formula')
    postfix, operators = [], []
    precedence = {'|': 1, '&': 2}
    want_value = True
    for token in tokens:
        if token.startswith(('Fin', 'Inf')) and want_value:
            postfix.append((token[:3], int(re.search(r'\d+', token)[0])))
            want_value = False
        elif token == '(' and want_value:
            operators.append(token)
        elif token == ')' and not want_value:
            while operators and operators[-1] != '(':
                postfix.append(operators.pop())
            if not operators:
                raise InputError('unbalanced acceptance formula')
            operators.pop()
        elif token in precedence and not want_value:
            while operators and operators[-1] != '(' and precedence[operators[-1]] >= precedence[token]:
                postfix.append(operators.pop())
            operators.append(token)
            want_value = True
        else:
            raise InputError('invalid acceptance formula')
    if want_value or '(' in operators:
        raise InputError('incomplete acceptance formula')
    postfix.extend(reversed(operators))
    count = int(acceptance[3])
    if sum(isinstance(t, tuple) for t in postfix) != count:
        raise InputError('acceptance formula does not mention every colour exactly once')
    priorities = range(count-1, -1, -1) if acceptance[1] == 'max' else range(count)
    odd = acceptance[2] == 'odd'
    expected = [('Inf' if p % 2 == odd else 'Fin', p) for p in priorities]
    expected.extend('|' if kind == 'Inf' else '&' for kind, _ in reversed(expected[:-1]))
    if postfix != expected:
        raise InputError('acceptance formula does not match canonical acc-name parity formula')


def read_game(path):
    with open(path, encoding='utf-8') as source:
        first = source.readline().strip()
        if first.startswith('version https://git-lfs.github.com/spec/v1'):
            raise InputError('Git LFS pointer (content unavailable)')
        if first != 'HOA: v1':
            raise InputError('expected HOA: v1')
        headers, aliases, starts = {}, {}, []
        for line in source:
            line = line.strip()
            if line == '--BODY--':
                break
            if not line:
                continue
            key, sep, value = line.partition(':')
            if not sep:
                raise InputError('invalid header')
            if key == 'Start':
                starts.append(value.strip())
            elif key == 'Alias':
                name, expression = value.strip().split(None, 1)
                aliases[name] = expression
            else:
                headers[key] = value.strip()
        else:
            raise InputError('truncated header (no --BODY--)')
        acceptance = headers.get('acc-name', '').split()
        if (len(acceptance) != 4 or acceptance[0] != 'parity'
                or acceptance[1] not in ('min', 'max') or acceptance[2] not in ('even', 'odd')):
            raise InputError('unsupported acceptance: ' + headers.get('acc-name', '(missing)'))
        n, ap_count, count = int(headers['States']), int(headers['AP'].split()[0]), int(acceptance[3])
        if n <= 0 or count <= 0 or int(headers['Acceptance'].split()[0]) != count:
            raise InputError('invalid state/acceptance count')
        check_acceptance(headers['Acceptance'].split(None, 1)[1], acceptance)
        if len(starts) != 1 or not starts[0].isdigit() or int(starts[0]) >= n:
            raise InputError('expected a single initial state')
        start = int(starts[0])
        controlled = set(map(int, headers['controllable-AP'].split()))
        if not controlled <= set(range(ap_count)):
            raise InputError('controllable AP index out of range')
        order = [i for i in range(ap_count) if i not in controlled] + sorted(controlled)
        variables = [0] * ap_count
        for rank, ap in enumerate(order):
            variables[ap] = rank
        env_count = ap_count - len(controlled)

        def swap(s):
            return start if s == 0 else 0 if s == start else s

        state_colours = array('q', [-1]) * n
        state_begin, state_end = array('Q', [0]) * n, array('Q', [0]) * n
        state_edges, inter_offsets, inter_edges = array('I'), array('Q', [0]), array('I')
        outcome_ids, outcomes = {}, []
        residual_ids, control_unique, control_nodes = {}, {}, [None]
        seen = bytearray(n)
        guards, labels = BDD(), {}
        current, state_label, state_colour = None, None, -1
        transition_bdd, root, coverage = None, 0, 0

        def finish_state():
            if current is None:
                return
            if coverage != 1:
                raise InputError('incomplete transition relation at state ' + str(current))
            local_cache = {}

            def intern_control(r):
                if r <= 0:
                    if r == 0:
                        raise InputError('incomplete transition relation')
                    return r
                if r not in local_cache:
                    var, low, high = transition_bdd.nodes[r]
                    key = (var-env_count, intern_control(low), intern_control(high))
                    if key not in control_unique:
                        control_unique[key] = len(control_nodes)
                        control_nodes.append(key)
                    local_cache[r] = control_unique[key]
                return local_cache[r]

            state_begin[swap(current)] = len(state_edges)
            pending, visited, residuals = [root], set(), set()
            while pending:
                r = pending.pop()
                if r in visited:
                    continue
                visited.add(r)
                if r > 0 and transition_bdd.nodes[r][0] < env_count:
                    _, low, high = transition_bdd.nodes[r]
                    pending.extend((high, low))
                    continue
                c = intern_control(r)
                if c in residuals:
                    continue
                residuals.add(c)
                if c not in residual_ids:
                    residual_ids[c] = len(inter_offsets)-1
                    stack, visited_control, targets = [c], set(), set()
                    while stack:
                        t = stack.pop()
                        if t in visited_control:
                            continue
                        visited_control.add(t)
                        if t < 0:
                            targets.add(-t-1)
                        else:
                            stack.extend(control_nodes[t][1:])
                    inter_edges.extend(sorted(targets))
                    inter_offsets.append(len(inter_edges))
                state_edges.append(residual_ids[c])
            state_end[swap(current)] = len(state_edges)

        ended = False
        for line in source:
            line = line.strip()
            if not line:
                continue
            if line == '--END--':
                finish_state()
                ended = True
                break
            if line.startswith('State:'):
                finish_state()
                match = STATE.fullmatch(line)
                if not match:
                    raise InputError('unsupported state declaration: ' + line[:100])
                state_label, s, sig = match.groups()
                current = int(s)
                if current >= n or seen[current]:
                    raise InputError('duplicate/out-of-range state ID')
                seen[current] = 1
                state_colour = colour(sig, count)
                state_colours[swap(current)] = state_colour
                if len(guards.nodes) > 100000 or len(labels) > 4096 or len(guards.cache) > 100000:
                    guards, labels = BDD(), {}
                transition_bdd, root, coverage = TransitionBDD(guards), 0, 0
            else:
                match = TRANSITION.fullmatch(line)
                if current is None or not match:
                    raise InputError('unsupported transition: ' + line[:100])
                label, target, sig = match.groups()
                target = int(target)
                if target >= n:
                    raise InputError('successor out of range')
                if state_label is not None:
                    if label is not None:
                        raise InputError('both state and transition labels')
                    label = state_label
                if label is None:
                    raise InputError('implicit transition labels are unsupported')
                prio = colour(sig, count)
                if (state_colour < 0) == (prio < 0):
                    raise InputError('expected either state or transition acceptance')
                if label not in labels:
                    labels[label] = label_bdd(label, guards, variables, aliases)
                guard = labels[label]
                if guards.op('&', coverage, guard) != 0:
                    raise InputError('nondeterministic transition relation at state ' + str(current))
                coverage = guards.op('|', coverage, guard)
                if guard == 0:
                    continue
                key = (swap(target), prio)
                if key not in outcome_ids:
                    outcome_ids[key] = len(outcomes)
                    outcomes.append(key)
                root = transition_bdd.ite(guard, -outcome_ids[key]-1, root)
        if not ended or not all(seen):
            raise InputError('truncated body or missing states')
        state_based = sum(p >= 0 for p in state_colours)
        if state_based not in (0, n):
            raise InputError('mixed state/transition acceptance is unsupported')

    inter_count = len(inter_offsets)-1
    offsets, edges = array('Q', [0]), array('I')
    for s in range(n):
        edges.extend(sorted(n+i for i in state_edges[state_begin[s]:state_end[s]]))
        offsets.append(len(edges))
    for i in range(inter_count):
        edges.extend(n+inter_count+t for t in inter_edges[inter_offsets[i]:inter_offsets[i+1]])
        offsets.append(len(edges))
    owners = array('B', [1])*n + array('B', [0])*inter_count + array('B', [1])*len(outcomes)
    priorities = array('Q', [0])*(n+inter_count)
    for target, prio in outcomes:
        p = state_colours[target] if prio < 0 else prio
        if acceptance[1] == 'min':
            p = 2*((count+1)//2) - p
        priorities.append(p + 2 - (acceptance[2] == 'odd'))
        edges.append(target)
        offsets.append(len(edges))
    return owners, priorities, offsets, edges


def little_bytes(values):
    if sys.byteorder == 'little' or values.itemsize == 1:
        return values.tobytes()
    values = values[:]
    values.byteswap()
    return values.tobytes()


def numbered_hash(game):
    digest = hashlib.sha256()
    for values in game:
        digest.update(struct.pack('<Q', len(values)))
        digest.update(little_bytes(values))
    return digest.hexdigest()


def predecessors(game):
    n, edges = len(game[0]), game[3]
    degrees = array('I', [0])*n
    for target in edges:
        degrees[target] += 1
    offsets = array('Q', [0])
    for degree in degrees:
        offsets.append(offsets[-1]+degree)
    positions, incoming = offsets[:-1], array('I', [0])*len(edges)
    for v in range(n):
        for j in range(game[2][v], game[2][v+1]):
            target = edges[j]
            incoming[positions[target]] = v
            positions[target] += 1
    return offsets, incoming


def seed_colours(game, pred):
    owners, priorities, offsets, edges = game
    return [(owners[v], priorities[v], offsets[v+1]-offsets[v],
             pred[0][v+1]-pred[0][v], v in edges[offsets[v]:offsets[v+1]])
            for v in range(len(owners))]


def histogram_hash(signatures):
    counts = Counter(signatures)
    digest = hashlib.sha256()
    for key, count in sorted(counts.items()):
        digest.update(repr((key, count)).encode('ascii'))
        digest.update(b'\n')
    return digest.hexdigest()


def parse_file(task):
    path, relative, cache_path, max_size = task
    try:
        with open(path, 'rb') as source:
            if source.readline(100).startswith(b'version https://git-lfs.github.com/spec/v1'):
                raise InputError('Git LFS pointer (content unavailable)')
        if max_size and Path(path).stat().st_size > max_size:
            raise InputError('exceeds --max-size (' + str(Path(path).stat().st_size) + ' bytes)')
        game = read_game(path)
        identity = numbered_hash(game)
        coarse = histogram_hash(seed_colours(game, predecessors(game)))
        with open(cache_path, 'wb') as output:
            pickle.dump(game, output, protocol=pickle.HIGHEST_PROTOCOL)
        return {'path': relative, 'cache': cache_path, 'identity': identity,
                'coarse': coarse, 'vertices': len(game[0]), 'edges': len(game[3])}
    except (InputError, ValueError, KeyError, IndexError, RecursionError, OverflowError, OSError) as error:
        return {'path': relative, 'error': str(error)}


def load_game(record):
    with open(record['cache'], 'rb') as source:
        return pickle.load(source)


def refine(record):
    game = load_game(record)
    incoming = predecessors(game)
    signatures = seed_colours(game, incoming)
    digest = hashlib.sha256()
    previous_count = 0
    for round_number in range(9):
        digest.update(histogram_hash(signatures).encode('ascii'))
        palette = {s: i for i, s in enumerate(sorted(set(signatures)))}
        colours = array('I', (palette[s] for s in signatures))
        if len(palette) == previous_count or len(palette) == len(colours) or round_number == 8:
            break
        previous_count = len(palette)
        signatures = [(colours[v],
                       tuple(sorted(colours[t] for t in game[3][game[2][v]:game[2][v+1]])),
                       tuple(sorted(colours[t] for t in incoming[1][incoming[0][v]:incoming[0][v+1]])))
                      for v in range(len(colours))]
    with open(record['cache'] + '.colours', 'wb') as output:
        pickle.dump(colours, output, protocol=pickle.HIGHEST_PROTOCOL)
    return record['path'], digest.hexdigest()


def isomorphic(a, b, ca, cb, timeout=10):
    """Return True/False, or None on timeout; always verify a full bijection."""
    deadline = time.monotonic() + timeout

    def check_time():
        if time.monotonic() >= deadline:
            raise TimeoutError

    try:
        n = len(a[0])
        if n != len(b[0]) or len(a[3]) != len(b[3]) or Counter(ca) != Counter(cb):
            return False
        pa, pb = predecessors(a), predecessors(b)
        classes = defaultdict(list)
        for v, c in enumerate(cb):
            classes[c].append(v)

        def neighbours(graph, v):
            return graph[1][graph[0][v]:graph[0][v+1]]

        ao, bo = (a[2], a[3]), (b[2], b[3])
        counts = Counter(ca)
        seeds = sorted(range(n), key=lambda v: (counts[ca[v]], -(a[2][v+1]-a[2][v]), v))
        order, queued, frontier = [], bytearray(n), []
        for seed in seeds:
            if queued[seed]:
                continue
            heapq.heappush(frontier, (counts[ca[seed]], seed))
            queued[seed] = 1
            while frontier:
                check_time()
                _, v = heapq.heappop(frontier)
                order.append(v)
                for t in list(neighbours(ao, v)) + list(neighbours(pa, v)):
                    if not queued[t]:
                        queued[t] = 1
                        heapq.heappush(frontier, (counts[ca[t]], t))
        forward, reverse = array('q', [-1])*n, array('q', [-1])*n

        def candidates(v):
            best = None
            for left, right in ((ao, bo), (pa, pb)):
                for t in neighbours(left, v):
                    if forward[t] >= 0:
                        opposite = pb if right is bo else bo
                        options = neighbours(opposite, forward[t])
                        if best is None or len(options) < len(best):
                            best = options
            return iter(classes[ca[v]] if best is None else best)

        def feasible(v, w):
            if reverse[w] >= 0 or ca[v] != cb[w] or (a[0][v], a[1][v]) != (b[0][w], b[1][w]):
                return False
            for left, right in ((ao, bo), (pa, pb)):
                av, bw = neighbours(left, v), neighbours(right, w)
                if (v in av) != (w in bw):
                    return False
                if {forward[t] for t in av if forward[t] >= 0} != {t for t in bw if reverse[t] >= 0}:
                    return False
                if Counter(ca[t] for t in av if forward[t] < 0 and t != v) != Counter(
                        cb[t] for t in bw if reverse[t] < 0 and t != w):
                    return False
            return True

        frames, depth = [], 0
        while depth >= 0:
            check_time()
            if depth == n:
                for v in range(n):
                    check_time()
                    w = forward[v]
                    if (a[0][v], a[1][v]) != (b[0][w], b[1][w]) or {
                            forward[t] for t in neighbours(ao, v)} != set(neighbours(bo, w)):
                        return False
                return True
            v = order[depth]
            if len(frames) == depth:
                frames.append(candidates(v))
            if forward[v] >= 0:
                reverse[forward[v]] = -1
                forward[v] = -1
            for w in frames[depth]:
                check_time()
                if feasible(v, w):
                    forward[v], reverse[w] = w, v
                    depth += 1
                    break
            else:
                frames.pop()
                depth -= 1
        return False
    except TimeoutError:
        return None


def path_key(record):
    return len(record['path']), record['path']


def find_groups(records, pool, timeout):
    numbered = defaultdict(list)
    for record in sorted(records, key=path_key):
        numbered[record['identity']].append(record)
    identical = []
    for bucket in numbered.values():
        groups = []
        for record in bucket:
            for group in groups:
                if load_game(record) == load_game(group[0]):
                    group.append(record)
                    break
            else:
                groups.append([record])
        identical.extend(groups)
    print(f'Level 1: {sum(len(g)>1 for g in identical)} identical groups, '
          f'{sum(len(g)-1 for g in identical)} non-representatives', file=sys.stderr)
    coarse = defaultdict(list)
    for group in identical:
        coarse[group[0]['coarse']].append(group)
    candidates = [g[0] for bucket in coarse.values() if len(bucket) > 1 for g in bucket]
    print(f'WL refinement: {len(candidates)} distinct numbered games in candidate buckets', file=sys.stderr)
    refined = dict(pool.imap_unordered(refine, candidates))
    buckets = defaultdict(list)
    confirmed = []
    for bucket in coarse.values():
        if len(bucket) == 1:
            confirmed.extend(bucket)
        else:
            for group in bucket:
                buckets[refined[group[0]['path']]].append(group)
    suspected = []
    for bucket in buckets.values():
        groups = []
        for identical_group in sorted(bucket, key=lambda g: path_key(g[0])):
            record = identical_group[0]
            for group in groups:
                representative = group[0]
                with open(record['cache'] + '.colours', 'rb') as source:
                    ca = pickle.load(source)
                with open(representative['cache'] + '.colours', 'rb') as source:
                    cb = pickle.load(source)
                result = isomorphic(load_game(record), load_game(representative), ca, cb, timeout)
                if result is True:
                    group.extend(identical_group)
                    break
                if result is None:
                    suspected.append((representative, record))
                    print(f"warning: isomorphism timeout: {representative['path']} / {record['path']}", file=sys.stderr)
            else:
                groups.append(identical_group[:])
        confirmed.extend(groups)
    membership = {r['path']: i for i, group in enumerate(confirmed) for r in group}
    suspected = [pair for pair in suspected if membership[pair[0]['path']] != membership[pair[1]['path']]]
    return [sorted(g, key=path_key) for g in confirmed if len(g) > 1], suspected


def positive_int(text):
    value = int(text)
    if value <= 0:
        raise argparse.ArgumentTypeError('must be positive')
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--root', type=Path, default=Path('parity'))
    parser.add_argument('--out', type=Path, default=Path('parity/duplicates.csv'))
    parser.add_argument('--max-size', type=positive_int, metavar='BYTES', help='skip larger inputs (default: no limit)')
    parser.add_argument('--jobs', type=positive_int, default=2, help='parser/refinement processes (default: 2)')
    parser.add_argument('--timeout', type=float, default=10, metavar='SECONDS', help='exact matching timeout per pair (default: 10)')
    parser.add_argument('--manifest-rows', action='store_true', help='print confirmed non-representatives as manifest CSV to stdout')
    args = parser.parse_args()
    if not args.root.is_dir():
        parser.error('--root must be a directory')
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error('--timeout must be positive and finite')
    started = time.monotonic()
    paths = sorted(args.root.rglob('*.ehoa'))
    records, skipped = [], 0
    with tempfile.TemporaryDirectory(prefix='parity-duplicates-') as temporary:
        tasks = [(str(p), p.relative_to(args.root).as_posix(), str(Path(temporary)/str(i)), args.max_size)
                 for i, p in enumerate(paths)]
        with multiprocessing.Pool(args.jobs) as pool:
            for i, record in enumerate(pool.imap_unordered(parse_file, tasks), 1):
                if 'error' in record:
                    skipped += 1
                    print(f"warning: {record['path']}: {record['error']}", file=sys.stderr)
                else:
                    records.append(record)
                if i % 25 == 0 or i == len(paths):
                    print(f'Parsed {i}/{len(paths)} inputs ({time.monotonic()-started:.1f}s)', file=sys.stderr)
            groups, suspected = find_groups(records, pool, args.timeout)
        rows = []
        for i, group in enumerate(sorted(groups, key=lambda g: path_key(g[0])), 1):
            level = 'identical' if len({r['identity'] for r in group}) == 1 else 'isomorphic'
            rows.extend((i, level, r['path'], group[0]['path']) for r in sorted(group, key=lambda r: r['path']))
        for i, pair in enumerate(sorted(suspected, key=lambda pair: (pair[0]['path'], pair[1]['path'])), len(groups)+1):
            rows.extend((i, 'suspected', r['path'], pair[0]['path']) for r in pair)
        with args.out.open('w', newline='', encoding='utf-8') as output:
            writer = csv.writer(output, lineterminator='\n')
            writer.writerow(('group', 'level', 'path', 'representative'))
            writer.writerows(rows)
        if args.manifest_rows:
            writer = csv.writer(sys.stdout, lineterminator='\n')
            writer.writerow(('pattern', 'params', 'enabled', 'reason'))
            for group in sorted(groups, key=lambda g: path_key(g[0])):
                for record in sorted(group[1:], key=lambda r: r['path']):
                    writer.writerow((record['path'], '', 0, 'duplicate-of:' + group[0]['path']))
        levels = Counter(row[1] for row in rows if row[2] == row[3])
        print(f'Parsed {len(records)}/{len(paths)}; skipped {skipped}. '
              f'Final groups: {dict(sorted(levels.items()))}; '
              f'{sum(len(g)-1 for g in groups)} confirmed non-representatives; '
              f'{len(suspected)} suspected pairs. Runtime: {time.monotonic()-started:.1f}s', file=sys.stderr)
        for group in sorted(groups, key=lambda g: (-len(g), path_key(g[0])))[:10]:
            print(f"  {len(group)} games: {group[0]['path']}", file=sys.stderr)


if __name__ == '__main__':
    main()
