# Finite-synthesis-datasets

The datasets for finite-synthesis include three classes:
* The first one is  from the **Random** family, composed of LTLf formulas formed by random conjunction, generated as described in [ZTLPV17](https://arxiv.org/pdf/1705.08426.pdf). 
* The second one is from [TV19](https://www.ijcai.org/Proceedings/2019/0777.pdf) and [BLTV20](https://arxiv.org/pdf/1911.08145.pdf), which describes **Two-player games**, split into the *Single-Counter*, *Double-Counters* and *Nim* dataset families.
* The third one is from [XLZSPV20](https://ojs.aaai.org/index.php/AAAI/article/view/16809/16616), originated from [RV07](https://www.cs.rice.edu/~vardi/papers/spin07rj.pdf) and [GH06](https://www.researchgate.net/publication/221105722_Larger_Automata_and_Less_Work_for_LTL_Model_Checking), which consists of **Pattern formuls**, split into the *GF* and *U* dataset families.
Moreover, for each family, we only consider the version of having the agent as the first player.

For other benchmark classes, see the README files in the corresponding
directories.

## Random

The **Random** datasets are constructed from basic cases taken from LTL
synthesis datasets [Lily](https://www.react.uni-saarland.de/tools/unbeast/)
and [Load balancer](https://www.react.uni-saarland.de/tools/unbeast/).
Formally, a random conjunction formula $RC(L)$
has the form:

$RC(L) = \bigwedge_{1\leq i\leq L}P_i(v_1,v_2,...,v_k)$

where $L$  is the number of conjuncts, or the length of the formula, and $P_i$
is a randomly selected basic case.
Variables $v_1,v_2,...,v_k$
are chosen randomly from a set of $m$
candidate variables. Given $L$
and $m$
(the size of the candidate variable
set), we generate a formula $RC(L)$
in the following way:
* Randomly select $L$ basic cases;
* For each case $\phi$, substitute every variable $v$ with a random new variable $v$ chosen from $m$ atomic propositions.
If $v$ is an environment-variable in $\phi$, then $v$ is also an environment-variable in $RC(L)$. The same applies to the agent-variables.

This class of datasets has 1400 instances, from which there are 1000 are from [DF21](http://www.diag.uniroma1.it//degiacom/papers/2021/icaps2021df.pdf), and 400 are from [ZTLPV17](https://arxiv.org/pdf/1705.08426.pdf).

## Two-player game

### Single-Counter family

This dataset family is a simple example where the behavior of the system is
completely determined by the actions of the environment. Therefore, the
challenge in this family lies mostly in proving that the specification is
realizable. The system stores an $n$-bit counter (where $n$
 is the scaling parameter) which it must
increment upon a signal by the environment. The system wins if the counter
eventually overflows to $0$. To guarantee that the game is winning
for the system, the specification assumes that the environment will send the
increment signal at least once every two timesteps.

### Double-Counter family

This dataset family is similar to the Single-Counter one, except that in this
case there are two $n$-bit counters, one incremented by the
environment and another by the system. The goal of the system is for its
counter to eventually catch up with the environment’s counter. To guarantee
that this is achievable, the specification assumes that the environment cannot
increment its counter twice in a row.

### Nim family

This dataset family describes a generalized version of the game of Nim
[Bouton1901](https://paradise.caltech.edu/ist4/lectures/Bouton1901.pdf) with
$n$
heaps of $m$
tokens each. The environment and the
system take turns removing any number of tokens from one of the heaps, and the
player who removes the last token loses.

## Pattern formulas

### GF family

$GF(n) = G(p_1) \wedge F(q_2) \wedge F(q_3) \wedge ... \wedge F(q_n)$

### U family

$U(n)=p_1 U (p_2 U (\dots p_{n-1} U p_n ) \dots))$
