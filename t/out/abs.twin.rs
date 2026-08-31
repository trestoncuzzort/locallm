use vstd::prelude::*;

verus! {

proof fn abs(x: int) -> (r: int)
    ensures
        (r >= 0),
        ((r == x) || (r == (-x))),
{
    (-x)
}

} // verus!

fn main() {}
