To see how to run the benchmark, execute `amba_spec_generator.py -h`.
The script can produce the original GR1 spec and GR1+ specs, in formats for Slugs/Reboot and TLSF.
The script needs the compiler for StructureSlugs format (comes with Slugs);
to configure the path, edit `config_paths.py`.

We now talk about GR1+ versions in more detail. The following LTL parts may be added at user request:

- Assumption `GF req_ready -> GF ready`: the original specification assumes that `GF ready` holds.
  We add system output `req_ready` and require `GF ready` to hold
  only if the system requests that.
  This assumption is activated by using the parameter `-gfgf` to the the spsec generator.

- Guarantee `FG (...)`. The original specification has the property
  `r -> (!l <-> X !m)` (the variable names are not important)
  in its system-transitions specification,
  so this formula should hold on every transition, provided the environment satisfies
  its properties. We instead use `FG(r -> (!l <-> X !m))`, meaning that the system
  should eventually always satisfy it, provided that the environment always satisfies
  its properties. This gives the system some leeway to satisfy that original
  system-transition property.
  This property is activated by using the parameter `-fg` to the the spsec generator.

- Parameterized guarantee `∀i: FG (...)`. The AMBA specification is naturally parameterized
  by the number of clients it serves. The previous GR1++ property used only global signals,
  i.e. those shared by all the clients. The version here uses the same idea as before:
  giving the system more freedom by moving some of its transition properties into `FG(..)`,
  but, in contrast, this time we use parameterized signals, those specific to individual
  clients. This makes automata corresponding to new properties much larger.
  This property is activated by using the parameter `-fg-ind` to the the spsec generator.

author: ayrat

