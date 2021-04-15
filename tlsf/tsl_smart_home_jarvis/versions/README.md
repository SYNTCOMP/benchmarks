# README Versioned Specifications

## Specifications and how to combine
Specifications are contained in subfolder `specifications`.
To switch the version of the assumptions used in a specification, simply change the number after the v in the import.
For example if you want to use version 2 of the *Room device* instead of version 1:
>Change
>import "../deviceModels/Room_v1.tsl.
>to
>import "../deviceModels/Room_v==2==.tsl.

Specifications, which feature requirements over the same devices, are put together in combined specifications, e.g. *AllShades*. These combinations should not be splittable, so there exists a dependency that could lead to conflict. All other combinations should be splittable, except for *Coffee*.

## Converting to TLSF
As these so called building block specifications are given in TSL, `tslresolve` and `tsl2tlsf` are a requirement, if one wants to generate TLSF specifications. See [tsltools@github](https://github.com/reactive-systems/tsltools).
To transform one specification *spec.tsl* from TSL to TLSF apply:
>$ tslresolve spec.tsl | tsl2tlsf > spec.tlsf