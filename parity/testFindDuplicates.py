#!/usr/bin/env python3

import itertools
import csv
import io
import pickle
import random
import subprocess
import sys
import tempfile
import unittest
from array import array
from pathlib import Path

try:
    from . import findDuplicates as m
except ImportError:
    import findDuplicates as m


def game(edges, owners=None, priorities=None):
    n = len(edges)
    flat, offsets = array('I'), array('Q', [0])
    for row in edges:
        flat.extend(sorted(set(row)))
        offsets.append(len(flat))
    return array('B', owners or [0]*n), array('Q', priorities or [0]*n), offsets, flat


def brute(a, b):
    n = len(a[0])
    for p in itertools.permutations(range(n)):
        if all((a[0][v], a[1][v]) == (b[0][p[v]], b[1][p[v]]) and
               {p[t] for t in a[3][a[2][v]:a[2][v+1]]} == set(b[3][b[2][p[v]]:b[2][p[v]+1]])
               for v in range(n)):
            return True
    return False


class Tests(unittest.TestCase):
    def parse(self, body, states=1, aps=2, controlled='1', acc='max even 2', aliases=''):
        count = int(acc.split()[-1])
        priorities = list(range(count-1, -1, -1) if acc.startswith('max') else range(count))
        odd = acc.split()[1] == 'odd'
        formula = ''
        for priority in reversed(priorities):
            atom = f'Inf({priority})' if priority % 2 == odd else f'Fin({priority})'
            operator = '|' if priority % 2 == odd else '&'
            formula = f'{atom} {operator} ({formula})' if formula else atom
        header = (f'HOA: v1\nStates: {states}\nStart: 0\nAP: {aps}\n'
                  f'controllable-AP: {controlled}\nacc-name: parity {acc}\n'
                  f'Acceptance: {count} {formula}\n{aliases}--BODY--\n')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'test.ehoa'
            path.write_text(header + body + '\n--END--\n')
            return m.read_game(path)

    def test_symbolic_sharing_and_same_range_distinct_functions(self):
        g = self.parse('State: 0\n[0&1 | !0&!1] 0 {0}\n[0&!1 | !0&1] 0 {1}\n'
                       'State: 1\n[0&1 | !0&!1] 0 {0}\n[0&!1 | !0&1] 0 {1}', states=2)
        self.assertEqual(len(g[0]), 6)
        self.assertEqual(list(g[0]), [1, 1, 0, 0, 1, 1])
        self.assertEqual(list(g[1]), [0, 0, 0, 0, 2, 3])
        self.assertEqual(list(g[3]), [2, 3, 2, 3, 4, 5, 4, 5, 0, 0])

    def test_state_acceptance_moved_to_incoming_transition(self):
        a = self.parse('State: 0 {0}\n[t] 1\nState: 1 {1}\n[t] 0', states=2)
        b = self.parse('State: 0\n[t] 1 {1}\nState: 1\n[t] 0 {0}', states=2)
        self.assertEqual(a, b)

    def test_min_and_odd_normalization(self):
        a = self.parse('State: 0\n[t] 0 {1}', acc='min odd 3')
        b = self.parse('State: 0\n[t] 0 {2}', acc='max even 4')
        self.assertEqual(a, b)

    def test_mismatched_acceptance(self):
        with self.assertRaises(m.InputError):
            m.check_acceptance('Inf(1) & Fin(0)', ['parity', 'max', 'odd', '2'])

    def test_aliases_and_unsatisfiable_guard(self):
        a = self.parse('State: 0\n[@x | !@x] 0 {1}\n[0 & !0] 0 {0}', aliases='Alias: @x 0 & !1\n')
        b = self.parse('State: 0 "ignored label"\n[t] 0 {1}')
        self.assertEqual(a, b)

    def test_alias_renaming(self):
        body = 'State: 0\n[@a] 0 {0}\n[!@a] 0 {1}'
        expected = self.parse(body, aliases='Alias: @a 0\n')
        for name in ('@0', '@0abc', '@-', '@-a', '@_', '@a-0'):
            with self.subTest(name=name):
                actual = self.parse(body.replace('@a', name), aliases=f'Alias: {name} 0\n')
                self.assertEqual(actual, expected)
                self.assertEqual(m.numbered_hash(actual), m.numbered_hash(expected))

    def test_alias_expansion_is_linear(self):
        class CountingAliases(dict):
            reads = 0

            def __getitem__(self, key):
                self.reads += 1
                if self.reads > 4 * len(self):
                    raise AssertionError('alias expansion exceeded a linear work budget')
                return super().__getitem__(key)

        for base in ('0', 'f'):
            with self.subTest(base=base):
                aliases = CountingAliases({'@a0': base})
                for i in range(1, 21):
                    aliases[f'@a{i}'] = f'@a{i-1} | @a{i-1}'
                bdd = m.BDD()
                expected = bdd.node(0, 0, 1) if base == '0' else 0
                self.assertEqual(m.label_bdd('@a20', bdd, [0], aliases), expected)
                for i in range(10):
                    self.assertEqual(m.label_bdd(f'@a20 | @a{i}', bdd, [0], aliases), expected)

    def test_alias_cache_is_per_bdd(self):
        aliases = {'@a': '0'}
        first, second = m.BDD(), m.BDD()
        self.assertEqual(m.label_bdd('@a', first, [0], aliases), first.node(0, 0, 1))
        second.node(0, 0, 1)
        self.assertEqual(m.label_bdd('@a', second, [1], aliases), second.node(1, 0, 1))

    def test_reject_undefined_and_cyclic_aliases(self):
        for aliases in ('', 'Alias: @a @a\n', 'Alias: @a @b\nAlias: @b @a\n',
                        'Alias: @a @b\nAlias: @b @missing\n'):
            with self.subTest(aliases=aliases), self.assertRaisesRegex(m.InputError, 'undefined or cyclic alias'):
                self.parse('State: 0\n[@a] 0 {0}\n[!@a] 0 {1}', aliases=aliases)

    def test_reject_bad_inputs(self):
        for body in ['State: 0\n[0] 0 {0}', 'State: 0\n[t] 0 {0}\n[t] 0 {1}',
                     'State: 0\n[t] 0', 'State: 0\n[t] 0 {0 1}',
                     'State: 0\n[0$] 0 {0}', 'State: 0\n0 {0}']:
            with self.subTest(body=body), self.assertRaises(m.InputError):
                self.parse(body)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'pointer.ehoa'
            path.write_text('version https://git-lfs.github.com/spec/v1\noid sha256:abc\nsize 1000\n')
            r = m.parse_file((str(path), path.name, str(Path(tmp)/'cache'), 1))
            self.assertIn('Git LFS pointer', r['error'])
            path.write_text('HOA: v1\n'+' '*200)
            r = m.parse_file((str(path), path.name, str(Path(tmp)/'cache'), 100))
            self.assertIn('max-size', r['error'])

    def test_wl_collision_is_not_an_isomorphism(self):
        a = game([[(v+1)%6] for v in range(6)])
        b = game([[1], [2], [0], [4], [5], [3]])
        with tempfile.TemporaryDirectory() as tmp:
            fingerprints = []
            for i, g in enumerate((a, b)):
                path = Path(tmp)/str(i)
                with path.open('wb') as output:
                    pickle.dump(g, output)
                fingerprints.append(m.refine({'path': str(i), 'cache': str(path)})[1])
            self.assertEqual(*fingerprints)
        self.assertFalse(m.isomorphic(a, b, [0]*6, [0]*6))

    def test_timeout(self):
        a = game([[0]])
        self.assertIsNone(m.isomorphic(a, a, [0], [0], timeout=1e-20))

    def test_random_matches_against_exhaustive_bijections(self):
        rng = random.Random(55)
        for i in range(80):
            n = rng.randrange(2, 7)
            edges = [[w for w in range(n) if rng.random() < .3] for _ in range(n)]
            own, prio = [rng.randrange(2) for _ in range(n)], [rng.randrange(3) for _ in range(n)]
            a = game(edges, own, prio)
            p = list(range(n))
            rng.shuffle(p)
            new, no, np = [None]*n, [0]*n, [0]*n
            for v in range(n):
                new[p[v]] = [p[w] for w in edges[v]]
                no[p[v]], np[p[v]] = own[v], prio[v]
            if i % 2:
                new[rng.randrange(n)].append(rng.randrange(n))
            b = game(new, no, np)
            self.assertEqual(m.isomorphic(a, b, [0]*n, [0]*n), brute(a, b), i)

    def test_boolean_bdd_truth_tables(self):
        rng = random.Random(55)

        def expression(depth):
            if not depth or rng.random() < .2:
                return str(rng.randrange(3))
            if rng.random() < .3:
                return '!('+expression(depth-1)+')'
            return '('+expression(depth-1)+rng.choice(['&','|'])+expression(depth-1)+')'

        for _ in range(100):
            text = expression(4)
            bdd = m.BDD()
            root = m.label_bdd(text, bdd, [0, 1, 2], {})
            for val in itertools.product([False, True], repeat=3):
                r = root
                while r > 1:
                    var, low, high = bdd.nodes[r]
                    r = high if val[var] else low
                py = ''.join(str(val[int(c)]) if c.isdigit() else
                             {'!': ' not ', '&': ' and ', '|': ' or '}.get(c, c) for c in text)
                self.assertEqual(bool(r), eval(py.strip()), text)

    def test_cli_determinism_and_manifest(self):
        text = ('HOA: v1\nStates: 1\nStart: 0\nAP: 0\ncontrollable-AP:\n'
                'acc-name: parity max even 1\nAcceptance: 1 Inf(0)\n'
                '--BODY--\nState: 0 {0}\n[t] 0\n--END--\n')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'a.ehoa').write_text(text)
            (root/'z.ehoa').write_text(text.replace('State: 0', 'State: 0 "label"'))
            (root/'pointer.ehoa').write_text('version https://git-lfs.github.com/spec/v1\n')
            results = []
            for jobs in (1, 2):
                out = root/f'output{jobs}.csv'
                run = subprocess.run([sys.executable, '-B', str(Path(m.__file__)),
                                      '--root', tmp, '--out', str(out), '--jobs', str(jobs),
                                      '--manifest-rows'], check=True, capture_output=True, text=True)
                self.assertIn('Git LFS pointer', run.stderr)
                results.append((out.read_text(), run.stdout))
            self.assertEqual(*results)
            manifest = list(csv.DictReader(io.StringIO(results[0][1])))
            self.assertEqual(manifest, [{'pattern': 'z.ehoa', 'params': '', 'enabled': '0',
                                        'reason': 'duplicate-of:a.ehoa'}])

    def test_cli_timeout_does_not_emit_exclusions(self):
        header = ('HOA: v1\nStates: 3\nStart: 0\nAP: 0\ncontrollable-AP:\n'
                  'acc-name: parity max even 1\nAcceptance: 1 Inf(0)\n--BODY--\n')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, targets in [('a', [1, 2, 0]), ('b', [2, 0, 1])]:
                body = ''.join(f'State: {v} {{0}}\n[t] {t}\n' for v, t in enumerate(targets))
                (root/(name+'.ehoa')).write_text(header + body + '--END--\n')
            out = root/'duplicates.csv'
            run = subprocess.run([sys.executable, '-B', str(Path(m.__file__)),
                                  '--root', tmp, '--out', str(out), '--jobs', '1',
                                  '--timeout', '1e-20', '--manifest-rows'],
                                 check=True, capture_output=True, text=True)
            with out.open() as source:
                rows = list(csv.DictReader(source))
            self.assertEqual([r['level'] for r in rows], ['suspected', 'suspected'])
            self.assertEqual(list(csv.DictReader(io.StringIO(run.stdout))), [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
